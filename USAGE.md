# dump_riv.py 使用说明

Rive (.riv) 文件解析、可视化和性能分析工具。

---

## 安装要求

- Python 3.6+
- 无第三方依赖
- 以下文件需在同一目录：
  - `dump_riv.py` — 主脚本
  - `riv_schema.json` — 类型和属性映射表（从 rive-runtime 源码自动提取）
  - `riv_graph.py` — 图形可视化模块（`--graph` 模式需要）

---

## 四种模式

### 模式一：文本树（默认）

```bash
python3 dump_riv.py file.riv              # 输出到终端
python3 dump_riv.py file.riv output.txt   # 输出到文件
```

以缩进树形结构展示 .riv 文件的完整对象层级，包含所有属性值和交叉引用。

输出示例：
```
[0] Backboard (typeKey=23) @28
  [1] Artboard "New Artboard" (typeKey=1) @30
    width: 155.89453125
    name: "New Artboard"
    [2] Node "Root" (typeKey=2) @69
      [3] Shape (typeKey=3) @133
        [4] Ellipse (typeKey=4) @144
          width: 95.46
        [5] Fill (typeKey=20) @213
          [6] SolidColor (typeKey=18) @150
            colorValue: #FF2F5E72
    [7] LinearAnimation "Idle" (typeKey=31) @1191
      [8] KeyedObject (typeKey=25) @1201
        objectId: #3 Shape (2)
        [9] KeyedProperty (typeKey=26) @1205
          propertyKey: rotation (15)
          [10] KeyFrameDouble (typeKey=30) @1213
            frame: 0
            value: 0.0
```

**交叉引用说明：**
- `objectId: #3 Shape (2)` — KeyedObject 动画的目标是全局索引 #3 的 Shape（Artboard 内组件索引 2）
- `propertyKey: rotation (15)` — 动画的属性是 rotation（propertyKey=15）
- `animationId: #7 "Idle" (0)` — AnimationState 引用的是第 0 个动画 "Idle"

---

### 模式二：HTML 列表（--html）

```bash
python3 dump_riv.py file.riv --html              # 输出到终端
python3 dump_riv.py file.riv --html output.html   # 写入文件并自动打开浏览器
```

生成可交互的 HTML 页面：

- **展开/折叠**：点击节点行展开子树和属性
- **Expand All / Collapse All / Expand Level 2**：批量控制展开层级
- **搜索框**：实时过滤，匹配类型名、对象名、属性名和值
- **类别过滤**：点击图例切换显示/隐藏各类别

---

### 模式三：图形可视化（--graph）

```bash
python3 dump_riv.py file.riv --graph              # 输出到终端
python3 dump_riv.py file.riv --graph output.html   # 写入文件并自动打开浏览器
```

生成 Canvas 绘制的交互式节点图：

#### 画布操作

| 操作 | 效果 |
|------|------|
| 鼠标滚轮 | 缩放（以光标位置为中心） |
| 拖拽空白区域 | 平移画布 |
| 点击节点 | 选中，右侧面板显示属性 |
| 拖拽节点 | 移动节点位置（连接线跟随） |
| 双击节点 | 展开/折叠子节点 |
| 右键节点 | 弹出菜单（聚焦子树/展开/折叠/恢复全树） |
| 鼠标按住有关联的节点 | 显示橙色虚线连接到关联目标，目标高亮 |

#### 工具栏按钮

| 按钮 | 功能 |
|------|------|
| Fit | 适配视口，显示全部节点 |
| + / − | 放大 / 缩小 |
| Root | 展开全部节点，定位到根节点 |
| Artboard | 概览模式：只显示 Backboard→Artboard 层，子节点折叠 |
| Timeline | 显示所有 LinearAnimation 及其父链，子节点折叠 |
| StateMachine | 显示所有 StateMachine 及其父链，子节点折叠 |
| Schema | 弹出 typeKey/propertyKey 对照表，可搜索 |
| 📊 Stats | 弹出性能统计面板（见下文） |

#### 节点标识

- 圆圈颜色按类别区分（右下角图例说明）
- 有子节点的圆圈底部显示 `+`（已折叠）或 `−`（已展开）
- 面包屑导航：聚焦子树时显示路径，可逐级返回

#### 右侧属性面板

- **Object 信息**：Type、Name、Index、TypeKey、Offset、Category、Children
- **Properties 列表**：属性名、类型、值，颜色属性带色块预览
- **交叉引用链接**：objectId、animationId 显示为蓝色可点击链接，点击跳转到目标节点
- **? 图标**：悬停显示字段含义说明
- **Show Keys 按钮**：切换显示/隐藏 propertyKey 编号
- **Filter 搜索框**：过滤当前节点的属性列表

---

### 模式四：性能统计（--stats）

```bash
python3 dump_riv.py file.riv --stats              # 输出到终端
python3 dump_riv.py file.riv --stats report.txt   # 输出到文件
```

输出运行时性能分析报告。也可在 `--graph` 模式中点击 📊 Stats 按钮查看图形化版本。

#### 统计内容

**渲染评分（1~5 星）**
- 综合评估渲染复杂度，星数越多越重

**每帧渲染成本**
- Draw calls、Clip passes、Mesh 变形、Image 纹理
- 热点 Shape 表（仅显示有多次绘制/裁剪/Mesh 的 Shape）
- Draw call 分布直方图

**渲染调用明细**
- drawPath / clipPath / drawImage / drawImageMesh 次数
- 路径总数、控制顶点、⭐渲染点数（最直接的 GPU 开销指标）
- 绘制类型分布：Fill+Solid / Fill+Linear / Fill+Radial / Stroke+Solid 等，每种显示次数、控制顶点、渲染点数

**Image 纹理**（🔥 高亮）
- 每张图片的名称、尺寸（宽×高）、绘制类型（drawImage/drawImageMesh）

**Mesh 变形**
- Mesh 数量、Mesh 顶点数、关联纹理及尺寸

**动画**
- 汇总：动画总数、循环动画数、总插值属性数、路径重算动画数
- Top 5 最重动画（按每帧插值属性数排序）
- 🔥 路径重算明细：哪些动画改变了哪些对象的哪些属性导致路径重算

**State Machine**（按性能影响排序）
- Layers（同时播放动画数）— 最影响性能
- Listeners（每帧 hit test）— 中等影响
- Conditions、Inputs — 低影响
- States、Transitions — 不影响性能

**⚠ 性能警告**
- 自动检测并提示：渲染点数过多、Draw calls 过多、裁剪过多、Mesh 过多、内嵌资源过大、层级过深、存在路径重算动画

#### 图形化统计（--graph 中的 Stats 面板）

点击 📊 Stats 按钮弹出，包含：
- 环形图：渲染调用类型占比（drawPath/clipPath/drawImage/drawImageMesh）
- 柱状图：热点 Shape 的 draw call 对比
- 柱状图：绘制类型分布（Fill+Solid 等），显示次数和渲染点数
- 柱状图：Top 5 最重动画（绿色=无路径重算，红色=有路径重算）
- 柱状图：State Machine 各指标
- 环形图：对象类别分布
- 所有图表支持鼠标悬停高亮和中文 tooltip 说明

---

## 帮助

```bash
python3 dump_riv.py --help
```

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `dump_riv.py` | 主脚本，包含解析器、树构建、文本/HTML/Stats 输出 |
| `riv_graph.py` | Canvas 图形可视化和 Stats 图表的 HTML 生成模块 |
| `riv_schema.json` | 从 rive-runtime 源码提取的 256 个类型名和 472 个属性名映射 |
| `RIV_FORMAT.md` | Rive .riv 二进制文件格式技术文档 |
| `PERFORMANCE_GUIDE.md` | 性能分析指南：各指标含义、阈值、优化方向 |

---

## 典型工作流

### 快速评估性能

```bash
python3 dump_riv.py animation.riv --stats
```

查看渲染评分、Draw calls、渲染点数、是否有路径重算动画。

### 定位性能瓶颈

```bash
python3 dump_riv.py animation.riv --graph output.html
```

1. 打开 HTML，点击 📊 Stats 查看统计图表
2. 关注 🔥 高亮的指标
3. 在图形视图中点击热点 Shape 查看其属性
4. 右键 → Focus on this subtree 查看子树细节

### 对比优化效果

```bash
python3 dump_riv.py before.riv --stats > before.txt
python3 dump_riv.py after.riv --stats > after.txt
diff before.txt after.txt
```

### 查看文件结构

```bash
python3 dump_riv.py animation.riv | head -50          # 快速浏览
python3 dump_riv.py animation.riv --html output.html   # 交互式浏览
```
