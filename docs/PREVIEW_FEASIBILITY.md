# Rive 预览与结构联动 — 可行性评估报告

## 1. 需求描述

在 index.html（项目根目录）网页版分析工具中：
1. **实时预览**：拖入 .riv 文件后，在页面中播放 Rive 动画
2. **结构联动**：点击"图形"视图中的节点（Shape/Node/Image 等），在预览画布中高亮对应的可视元素；反之，在预览画布中点击元素，在图形视图中定位到对应节点

## 2. 技术方案

### 2.1 Rive Web Runtime 集成

Rive 官方提供了纯浏览器端的 WASM 运行时，有两个可选包：

| 包 | 渲染方式 | 大小 | 特点 |
|---|---------|------|------|
| `@rive-app/canvas-single` | Canvas 2D | ~800KB | WASM 内嵌，单文件加载，适合我们的场景 |
| `@rive-app/webgl2` | WebGL2 | ~1.2MB | 性能更好，支持更多特效（Feather/Mesh 等） |

**推荐方案**：使用 `@rive-app/canvas-single`（或其 advanced 变体），通过 CDN 引入，无需构建工具。

```html
<!-- 高级 API：单文件，WASM 内嵌 -->
<script src="https://unpkg.com/@rive-app/canvas-advanced-single@2.x/rive.js"></script>
```

核心代码流程：
```javascript
// 1. 加载 WASM
const rive = await RiveCanvas({});

// 2. 用已有的 ArrayBuffer 加载文件（拖拽时已读取）
const file = await rive.load(new Uint8Array(buffer));

// 3. 实例化 Artboard 和 StateMachine
const artboard = file.artboardByIndex(0);
const machine = new rive.StateMachineInstance(
    artboard.stateMachineByIndex(0), artboard
);

// 4. 渲染循环
const renderer = rive.makeRenderer(canvas);
function loop(time) {
    renderer.clear();
    machine.advance(elapsed);
    artboard.advance(elapsed);
    renderer.save();
    renderer.align(rive.Fit.contain, rive.Alignment.center, ...);
    artboard.draw(renderer);
    renderer.restore();
    rive.requestAnimationFrame(loop);
}
```

**结论：完全可行。** 文件已经以 ArrayBuffer 形式在内存中（拖拽解析时），直接传给 Rive runtime 即可，无需二次加载。

### 2.2 结构联动 — 从图形节点到预览高亮

**目标**：点击图形视图中的 Shape #12，在预览画布中高亮该 Shape。

**实现路径**：

Rive low-level API 支持通过名称访问节点的 transform 属性：

```javascript
// 按名称查找节点，获取世界坐标
const node = artboard.node("Button");  // 返回 Node 引用
const x = node.worldTransformX;  // 世界空间 X
const y = node.worldTransformY;  // 世界空间 Y
```

但存在关键限制：

| 能力 | 支持情况 | 说明 |
|------|---------|------|
| 按名称查找节点 | ✅ | `artboard.node(name)` |
| 获取节点 world transform | ✅ | x, y, scaleX, scaleY, rotation |
| 按索引遍历所有组件 | ❌ | WASM API 未暴露 |
| 获取 Shape 的路径 bounds | ❌ | 未暴露 path bounding box |
| 获取 Shape 的渲染像素区域 | ❌ | 无 hit region API |
| 修改节点 opacity 做高亮 | ✅ | 可临时修改 opacity 闪烁 |

**可行方案 — 名称匹配 + Transform 叠加层**：

1. 我们的解析器已经提取了每个组件的 `name` 和 `parentId`
2. 对于有名称的节点，通过 `artboard.node(name)` 获取其世界坐标
3. 在预览 Canvas 上方叠加一个透明 Canvas，根据世界坐标绘制高亮框/光环
4. 对于参数化路径（Ellipse/Rectangle），结合已解析的 width/height 和 transform 绘制精确的高亮区域

**局限**：
- 无名称的节点无法通过 API 查找（可在 inspector 中提示用户命名）
- 自由路径（PointsPath）无法获取精确 bounds，只能用 transform 位置 + 估算尺寸
- 嵌套 transform 链需要手动计算（或依赖 worldTransform）

**结论：基本可行，但精度有限。** 有名称的节点可以精确定位，无名称的需要降级处理。

### 2.3 结构联动 — 从预览点击到图形节点

**目标**：在预览画布中点击某个可视元素，自动在图形视图中选中对应节点。

**实现路径**：

Rive 的 StateMachine 有内置的 hit test 机制（用于 Listener），但这是针对交互目标的，不是通用的"点击哪个 Shape"查询。

**可行方案 — 坐标反查**：

1. 捕获预览 Canvas 的点击坐标
2. 将屏幕坐标通过 Fit/Alignment 逆变换转为 Artboard 坐标
3. 遍历所有已知节点的世界坐标 + 估算 bounds，做 hit test
4. 找到最近/最小的匹配节点，在图形视图中选中

**局限**：
- 没有像素级精确的 hit test（不知道哪个 Shape 在最上层）
- 重叠元素只能猜测最小的那个
- 需要维护一份"节点坐标缓存"，每帧更新

**结论：可行但精度一般。** 适合大致定位，不适合像素级精确选择。

## 3. 架构设计

```
┌─────────────────────────────────────────────────────┐
│                   index.html                         │
├──────────┬──────────┬──────────┬───────────┬────────┤
│ 🌳 树形  │ 📊 统计  │ 🔗 图形  │ 👁 预览   │ 💾 导出│
│          │          │          │           │        │
│ 现有     │ 现有     │ 现有     │ 新增 Tab  │ 现有   │
│          │          │ Canvas   │           │        │
│          │          │ 节点图   │ Rive WASM │        │
│          │          │          │ Canvas    │        │
│          │          │    ↕ 联动 │           │        │
│          │          │ 点击节点 ←→ 高亮元素  │        │
└──────────┴──────────┴──────────┴───────────┴────────┘
```

### 新增 Tab："👁 预览"

| 区域 | 内容 |
|------|------|
| 主画布 | Rive runtime 渲染的动画预览 |
| 叠加层 | 透明 Canvas，绘制高亮框、节点标注 |
| 控制栏 | 播放/暂停、Artboard 选择、StateMachine 选择、速度控制 |
| 信息面板 | 当前选中节点的属性（复用图形视图的属性面板） |

### 联动机制

```
图形视图点击节点
    → 获取节点 name
    → artboard.node(name) 获取世界坐标
    → 在预览叠加层绘制高亮
    → 预览画布滚动/缩放到该区域

预览画布点击
    → 屏幕坐标 → Artboard 坐标
    → 遍历节点坐标做 hit test
    → 在图形视图中选中匹配节点
    → 滚动图形视图到该节点
```

## 4. 工作量评估

| 任务 | 复杂度 | 预估工时 | 说明 |
|------|--------|---------|------|
| Rive WASM 集成 + 基础预览 | 中 | 1-2 天 | CDN 加载 + 渲染循环 + 播放控制 |
| 预览 Tab UI（控制栏/Artboard 选择） | 低 | 0.5 天 | 复用现有 UI 风格 |
| 图形→预览联动（名称匹配+高亮） | 中 | 1-2 天 | 需处理坐标变换和叠加层绘制 |
| 预览→图形联动（点击反查） | 高 | 2-3 天 | 坐标反查 + hit test + 节点缓存 |
| 资源加载处理（外部 Font/Image） | 中 | 1 天 | CDN 资源或内嵌资源的加载回调 |
| 边界情况处理 + 测试 | 中 | 1-2 天 | 多 Artboard、无名称节点、嵌套等 |
| **合计** | | **6-10 天** | |

## 5. 风险与限制

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| WASM 文件体积（~800KB-1.2MB） | 首次加载变慢 | 懒加载：仅切换到预览 Tab 时加载 WASM |
| 无名称节点无法定位 | 联动覆盖率不完整 | UI 提示"仅支持有名称的节点"；显示覆盖率百分比 |
| 外部资源（CDN Font/Image）加载失败 | 预览不完整 | 显示占位符 + 警告；支持手动拖入资源文件 |
| 离线环境无法加载 CDN 的 WASM | 预览功能不可用 | 提供本地 WASM 文件选项；或将 WASM 内嵌到 HTML |
| Feather/Mesh 等高级特效在 Canvas 2D 下渲染不完整 | 预览与实际效果有差异 | 提供 WebGL2 渲染器选项切换 |
| 预览→图形的 hit test 不精确 | 点击选错节点 | 显示候选列表让用户选择；优先匹配最小 bounds |

## 6. 替代方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A. 集成 Rive WASM（推荐）** | 真实渲染、支持动画播放、官方维护 | 增加 ~1MB 体积、联动精度受 API 限制 |
| B. 使用 Rive 官方 Web Component `<canvas>` | 集成最简单（几行代码） | 无 low-level API，无法做联动 |
| C. 自己用 Canvas 2D 绘制静态预览 | 完全可控、无外部依赖 | 工作量巨大（需实现路径渲染、渐变、Mesh 等）、无动画 |
| D. 嵌入 iframe 加载 rive.app 预览 | 零开发量 | 需要网络、无法联动、隐私问题 |

## 7. 结论

**可行性：✅ 可行**

核心预览功能（加载 .riv + 播放动画）通过 Rive 官方 WASM runtime 可以直接实现，技术上没有障碍。

**联动功能：⚠️ 部分可行**

- **图形→预览**（点击节点高亮元素）：对有名称的节点可行且效果好，覆盖率取决于设计师的命名习惯
- **预览→图形**（点击元素定位节点）：可行但精度有限，适合辅助定位而非精确选择

**建议分阶段实施**：

| 阶段 | 内容 | 价值 |
|------|------|------|
| P0 | 基础预览：加载 + 播放 + 暂停 + Artboard/SM 选择 | 用户可以直接在分析工具中看到动画效果 |
| P1 | 图形→预览联动：点击节点高亮对应元素 | 快速定位性能热点在画面中的位置 |
| P2 | 预览→图形联动：点击画面元素反查节点 | 从视觉出发分析结构 |

P0 阶段 1-2 天即可完成，已经能提供显著的使用价值。
