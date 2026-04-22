# Rive 性能分析指南

本文档说明 `dump_riv.py --stats` 和 `--graph` 模式中各项统计指标的含义、性能影响，以及设计和开发应关注的优化方向。

---

## 1. 每帧渲染成本（最关键）

Rive 每帧渲染的核心流程：

```
Artboard::draw()
  → 遍历每个 Shape
    → Shape::draw()
      → applyClip()          ← clipPath 调用
      → 遍历每个 Paint (Fill/Stroke)
        → Paint::draw(path)  ← drawPath 调用
  → 遍历每个 Image
    → drawImage / drawImageMesh 调用
```

### 1.1 Draw calls（绘制调用次数）

**指标：** `drawPath` 次数

**含义：** 每个 Shape 下的每个 Fill 和 Stroke 各产生一次 drawPath 调用。这是渲染性能的**最核心指标**。

**计算方式：** `drawPath = 所有 Shape 的 (Fill数 + Stroke数) 之和 + Artboard 背景 Fill`

**关注阈值：**
| 范围 | 评估 |
|------|------|
| < 20 | 轻量，无需优化 |
| 20~50 | 中等，注意热点 Shape |
| > 50 | 较重，需要优化 |

**优化方向：**
- 减少 Shape 数量（合并相似形状）
- 减少每个 Shape 的 Fill/Stroke 数量（一个 Shape 多个 Fill 会成倍增加 draw call）
- 避免不必要的 Stroke（描边比填充更贵）

### 1.2 clipPath（裁剪调用次数）

**含义：** 每个 ClippingShape 产生额外的 stencil buffer 通道。裁剪需要先渲染裁剪路径到 stencil buffer，再用 stencil 测试绘制被裁剪内容。

**性能影响：** 每次 clip 相当于额外 1~2 次 draw call 的开销。嵌套裁剪成倍增加。

**关注阈值：** > 10 需要关注

### 1.3 drawImage / drawImageMesh

**drawImage：** 绘制一张图片纹理，需要一次纹理绑定。

**drawImageMesh：** 绘制带网格变形的图片，除了纹理绑定外，还需要每帧计算网格顶点的骨骼蒙皮变换。

**性能影响：**
- 纹理尺寸直接影响 GPU 显存占用和带宽
- drawImageMesh 比 drawImage 多了 CPU 端的蒙皮计算

---

## 2. 渲染调用明细

### 2.1 路径总数与渲染点数

| 指标 | 含义 | 性能影响 |
|------|------|---------|
| 路径总数 | Shape 内的路径对象数 + Artboard 背景 | 影响路径合并计算 |
| 控制顶点 | Rive 对象层面的 PathVertex 数量 | 影响脏标记更新和动画插值 |
| **⭐ 渲染点数** | **RenderPath 命令的坐标点总数** | **直接影响 GPU 路径填充/描边开销** |

**渲染点数是最直接的 GPU 开销指标。** 同样 4 个控制顶点，Ellipse 生成 13 个渲染点（4 段贝塞尔），Rectangle 只生成 4 个（4 条直线）。

**控制顶点到渲染点的换算：**

| 路径类型 | 控制顶点 | 渲染点数 | 说明 |
|---------|---------|---------|------|
| Rectangle | 4 | 4 | moveTo + 3×lineTo |
| Triangle | 3 | 3 | moveTo + 2×lineTo |
| Ellipse | 4 | 13 | moveTo + 4×cubicTo(每个3点) |
| Polygon(N边) | N | N | moveTo + (N-1)×lineTo |
| Star(N角) | 2N | 2N | moveTo + (2N-1)×lineTo |
| 自由路径(N个CubicVertex) | N | 1+3N | moveTo + N×cubicTo |
| 自由路径(N个StraightVertex) | N | N | moveTo + (N-1)×lineTo |

**关注阈值：** 渲染点数 > 500 需要关注

### 2.2 绘制类型分布

统计每种 Paint+Color 组合的调用次数和控制的渲染点数：

| 类型 | 性能开销（从低到高） |
|------|-------------------|
| Fill+Solid | 最低：纯色填充 |
| Stroke+Solid | 中等：描边需要计算线宽、端点、拐角 |
| Fill+Linear | 较高：线性渐变需要逐像素插值 |
| Stroke+Linear | 高：描边 + 渐变 |
| Fill+Radial | 高：径向渐变需要逐像素计算距离 |
| Stroke+Radial | 最高：描边 + 径向渐变 |

**设计建议：**
- 优先使用 SolidColor，避免不必要的渐变
- 渐变色标数量影响插值精度但不显著影响性能
- 线性渐变比径向渐变便宜

### 2.3 渐变色标总数

渐变色标（GradientStop）数量影响渐变的颜色过渡精度。性能影响较小，但过多色标会增加内存占用。

---

## 3. 热点 Shape

**仅在存在差异时显示**（有 Shape 的 draw calls > 1 或有 clip 时）。

一个 Shape 有多个 Fill/Stroke 时，draw call 会成倍增加。例如：

```
Shape "Button"
├── Rectangle
├── Fill + SolidColor      ← 1 次 drawPath
├── Fill + LinearGradient  ← 1 次 drawPath
└── Stroke + SolidColor    ← 1 次 drawPath
                           = 3 次 draw calls
```

**开发关注：** 如果某个 Shape 的 draw calls 远高于其他，考虑是否可以减少 Paint 数量或拆分为更简单的 Shape。

---

## 4. Image 纹理

每张 Image 的关键信息：

| 字段 | 含义 |
|------|------|
| 名称 | 引用的 ImageAsset 名称 |
| 尺寸 | 纹理宽×高（像素），直接影响 GPU 显存 |
| 类型 | drawImage（静态图片）或 drawImageMesh（网格变形图片） |

**性能影响：**
- 纹理尺寸越大，GPU 显存占用和带宽消耗越大
- drawImageMesh 每帧需要 CPU 计算蒙皮变换
- 多张大纹理可能导致 GPU 显存不足

**设计建议：**
- 纹理尺寸应匹配实际显示尺寸，避免使用过大的源图
- 在嵌入式/移动设备上，单张纹理建议不超过 512×512
- 尽量减少 drawImageMesh 的使用，用骨骼动画替代网格变形

---

## 5. Mesh 变形

| 指标 | 含义 |
|------|------|
| Mesh 数量 | 网格变形对象数，每个每帧需要蒙皮计算 |
| Mesh 顶点 | 网格顶点总数，每个顶点每帧做骨骼权重插值 |
| 纹理 | 关联的 ImageAsset 及其尺寸 |

**性能影响：** Mesh 顶点数 × 骨骼数 = 每帧蒙皮计算量。顶点越多、骨骼越多，CPU 开销越大。

---

## 6. 动画每帧计算量

### 6.1 每帧插值属性数

**含义：** 动画 advance 时，需要对多少个属性做关键帧插值计算。

**计算方式：** 每个 KeyedProperty = 1 个插值属性。一个动画的所有 KeyedObject 下的 KeyedProperty 总数。

**性能影响：** 每个属性每帧需要：
1. 查找当前时间所在的关键帧区间
2. 计算插值因子（线性/贝塞尔）
3. 插值计算并写入目标属性

**关注阈值：** 单个动画 > 50 属性/帧 需要关注

### 6.2 🔥 路径重算次数（最关键的动画性能指标）

**含义：** 动画改变了会触发路径重新计算的属性。

**触发路径重算的属性：**
- `width`, `height`（参数化路径的尺寸变化 → 重新生成顶点）
- `x`, `y`（顶点坐标变化 → 重新构建 RenderPath）
- `inRotation`, `outRotation`, `inDistance`, `outDistance`（贝塞尔控制点变化）
- `radius`, `cornerRadius`（圆角变化）

**不触发路径重算的属性（仅变换矩阵）：**
- Node 的 `x`, `y`（位移）
- `rotation`（旋转）
- `scaleX`, `scaleY`（缩放）
- `opacity`（透明度）
- `colorValue`（颜色变化）

**性能差异：**
- 变换类属性：只更新 4×4 矩阵，开销极小
- 路径重算属性：需要重新调用 `buildPath()` 生成 RenderPath 命令，开销与渲染点数成正比

**设计建议：**
- 优先使用位移/旋转/缩放/透明度动画
- 避免动画改变 Shape 的 width/height（会触发路径重算）
- 如果必须改变形状大小，用 scaleX/scaleY 替代 width/height

> **注意：** 统计中 Node.x/y（propertyKey=13/14）是变换属性不触发重算，但 Vertex.x/y（propertyKey=24/25）是顶点坐标会触发重算。脚本通过 propertyKey 值区分两者。

### 6.3 循环动画

循环动画（loop/pingPong）会持续运行，每帧都消耗计算资源。oneShot 动画播放完毕后不再消耗。

**关注点：** 循环动画的属性数 × 同时播放的循环动画数 = 持续的每帧开销。

---

## 7. State Machine

按性能影响从大到小排列：

| 指标 | 性能影响 | 说明 |
|------|---------|------|
| **Layers** | ⭐⭐⭐ 高 | 每个 Layer 独立运行一个动画。Layer 数 = 最多同时播放的动画数。35 个 Layer 意味着每帧可能同时插值 35 个动画 |
| **Listeners** | ⭐⭐ 中 | 每帧对每个 Listener 做路径命中测试（hit test），需要遍历路径判断点是否在形状内 |
| Conditions | ⭐ 低 | 每帧对活跃状态的转换条件求值，但只是简单数值比较 |
| Inputs | ⭐ 低 | 输入变化触发条件重新求值 |
| States | 无 | 每层同一时刻只有一个活跃状态，状态总数不影响性能 |
| Transitions | 无 | 状态间的连接定义，不直接影响运行时性能 |

**关注阈值：**
- Layers > 10：每帧同时插值的动画过多
- Listeners > 10：每帧 hit test 开销较大

---

## 8. 渲染评分

综合评分（1~5 星），基于以下规则：

| 条件 | 加分 |
|------|------|
| 基础分 | +1 |
| Draw calls > 20 | +1 |
| Draw calls > 50 | +1 |
| Clip > 5 | +1 |
| Mesh > 10 | +1 |
| 存在路径重算动画 | +1 |

星数越多，渲染越重。1~2 星为轻量，3 星中等，4~5 星需要优化。

---

## 9. 性能优化检查清单

### 设计师检查项

- [ ] 避免一个 Shape 下放多个 Fill/Stroke（每个都是一次 draw call）
- [ ] 优先使用 SolidColor，减少渐变使用
- [ ] 纹理尺寸匹配实际显示尺寸，不要使用过大的源图
- [ ] 动画优先使用位移/旋转/缩放/透明度，避免动画 width/height
- [ ] 减少不必要的 ClippingShape
- [ ] 控制 StateMachine Layer 数量

### 开发者检查项

- [ ] 检查 `--stats` 输出的 Draw calls 是否在目标设备的承受范围内
- [ ] 检查渲染点数是否过多（> 500）
- [ ] 检查是否有路径重算动画（🔥 标记），评估是否可以用变换替代
- [ ] 检查 Image 纹理尺寸是否合理
- [ ] 检查 Mesh 顶点数和骨骼数
- [ ] 检查循环动画的属性数 × Layer 数 = 持续每帧开销

### 快速命令

```bash
# 文本统计
python3 dump_riv.py your_file.riv --stats

# 图形化统计（浏览器打开，可交互查看图表）
python3 dump_riv.py your_file.riv --graph output.html

# 查看完整对象树（定位具体问题）
python3 dump_riv.py your_file.riv
```
