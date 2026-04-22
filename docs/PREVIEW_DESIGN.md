# Rive 预览功能技术方案

## 1. 目标

在 index.html 中新增"👁 预览"Tab，加载并播放 .riv 动画，后续支持与"图形"视图的结构联动。

## 2. 技术选型

**运行时**：`@rive-app/webgl2`（高级 API + WebGL2 渲染）

选择理由：
- 高级 API 封装了渲染循环、资源加载、状态机驱动，代码量最小
- WebGL2 完整支持 Feather/Mesh/Clip 等特效
- UMD 格式，可通过 `<script>` 标签直接引入，无需构建工具

**加载方式**：本地文件懒加载（文件存放在 `vendor/rive/` 目录）

```
vendor/rive/rive.js    (JS API, ~312KB, 来自 @rive-app/webgl2@2.37.3)
vendor/rive/rive.wasm  (WASM 引擎, ~2.3MB, 同上)
```

rive.js 通过 `<script>` 懒加载引入，WASM 由 rive.js 内部加载（通过 `setWasmUrl` 指向本地路径）。
全部本地化，不依赖外部 CDN，离线可用。

## 3. 实现方案

### 3.1 整体架构

```
index.html
├── 现有 Tab: 树形 / 统计 / 图形 / 导出
├── 新增 Tab: 👁 预览
│   ├── Canvas (WebGL2)          ← Rive runtime 渲染
│   ├── 控制栏
│   │   ├── ▶/⏸ 播放/暂停
│   │   ├── Artboard 下拉选择
│   │   ├── StateMachine/Animation 下拉选择
│   │   └── 背景色切换（亮/暗/透明）
│   └── 状态信息（fps、Artboard 尺寸）
└── 数据流
    handleFile() 读取 ArrayBuffer
        ├── parseRiv()     → 现有解析（树形/统计/图形）
        └── 保存 buffer    → 预览 Tab 使用（懒加载时传给 Rive runtime）
```

### 3.2 代码结构

不新增 JS/CSS 文件，预览逻辑在 index.html 内完成（与现有架构一致）。
Rive 运行时文件存放在 `vendor/rive/` 目录：

```
rive-inspector/
├── index.html              ← 新增预览 Tab 的 HTML/CSS/JS
├── vendor/
│   └── rive/
│       ├── rive.js         ← Rive WebGL2 高级 API (312KB)
│       └── rive.wasm       ← Rive WASM 渲染引擎 (2.3MB)
└── ...

index.html 新增内容:
├── CSS: #tab-preview 样式、控制栏样式
├── HTML: <div id="tab-preview"> + <canvas> + 控制栏
└── JS:
    ├── loadRiveWasm()        — 懒加载 CDN 脚本
    ├── initPreview(buffer)   — 用 ArrayBuffer 初始化 Rive 实例
    ├── renderPreviewView()   — Tab 切换时调用
    └── cleanupPreview()      — 切换文件/关闭时清理
```

### 3.3 关键代码流程

#### Step 1: 保存原始 ArrayBuffer

```javascript
// handleFile() 中，保存 buffer 供预览使用
function handleFile(file) {
  const reader = new FileReader();
  reader.onload = e => {
    const buffer = e.target.result;
    const {header, objects, fileSize} = parseRiv(buffer);
    // ... 现有逻辑 ...
    currentData = {header, objects, tree, stats, filename: file.name, buffer}; // ← 新增 buffer
    showMain();
  };
  reader.readAsArrayBuffer(file);
}
```

#### Step 2: 懒加载 Rive WASM

```javascript
let riveLoaded = false;

function loadRiveRuntime() {
  return new Promise((resolve, reject) => {
    if (riveLoaded) { resolve(); return; }
    const script = document.createElement('script');
    script.src = 'vendor/rive/rive.js';
    script.onload = () => {
      rive.RuntimeLoader.setWasmUrl('vendor/rive/rive.wasm');
      riveLoaded = true;
      resolve();
    };
    script.onerror = () => reject(new Error('Failed to load Rive runtime'));
    document.head.appendChild(script);
  });
}
```

#### Step 3: 初始化预览

```javascript
let riveInstance = null;

async function initPreview(buffer) {
  await loadRiveRuntime();

  // 清理旧实例
  if (riveInstance) { riveInstance.cleanup(); riveInstance = null; }

  const canvas = document.getElementById('preview-canvas');

  // 高级 API：一行代码完成加载+渲染
  riveInstance = new rive.Rive({
    buffer: buffer,                    // 直接用已有的 ArrayBuffer
    canvas: canvas,
    autoplay: true,
    artboard: artboardName || undefined,
    stateMachines: smName || undefined,
    onLoad: () => {
      // 填充 Artboard/StateMachine 下拉列表
      updatePreviewControls();
    },
    onLoadError: (e) => {
      showPreviewError(e);
    }
  });
}
```

#### Step 4: 控制栏交互

```javascript
function updatePreviewControls() {
  // Artboard 列表
  const abNames = riveInstance.animationNames; // 从 Rive 实例获取
  // StateMachine 列表
  const smNames = riveInstance.stateMachineNames;
  // 填充下拉框 ...
}

function onArtboardChange(name) {
  // 重新加载指定 Artboard
  initPreview(currentData.buffer);
}

function togglePlayPause() {
  if (riveInstance.isPlaying) riveInstance.pause();
  else riveInstance.play();
}
```

### 3.4 HTML 结构

```html
<!-- Tab 按钮 -->
<button class="tab" data-tab="preview">👁 预览</button>

<!-- Tab 内容 -->
<div id="tab-preview" class="tabcontent">
  <div id="preview-toolbar">
    <button id="preview-play" class="btn-sm">⏸</button>
    <select id="preview-artboard" class="btn-sm"></select>
    <select id="preview-sm" class="btn-sm"></select>
    <button id="preview-bg" class="btn-sm">🎨</button>
    <span id="preview-info"></span>
  </div>
  <div id="preview-container">
    <canvas id="preview-canvas"></canvas>
  </div>
  <div id="preview-loading" class="hidden">Loading Rive runtime...</div>
  <div id="preview-error" class="hidden"></div>
</div>
```

### 3.5 CSS 要点

```css
#tab-preview { padding: 0; display: flex; flex-direction: column; }
#preview-toolbar { display: flex; gap: 6px; padding: 8px 12px;
                   background: #24283b; border-bottom: 1px solid #3b4261; align-items: center; }
#preview-container { flex: 1; position: relative; overflow: hidden; }
#preview-canvas { width: 100%; height: 100%; display: block; }
```

## 4. 关键技术点

### 4.1 WebGL2 上下文管理

同一页面中，图形 Tab 的 `gcanvas` 使用 Canvas 2D，预览 Tab 的 `preview-canvas` 使用 WebGL2。两个 Canvas 独立，不冲突。

**注意**：WebGL2 上下文在 Canvas 不可见时（Tab 切换）不会自动释放。需要在切换离开预览 Tab 时暂停渲染循环，避免后台 GPU 消耗。

```javascript
// Tab 切换时
if (tab === 'preview') {
  riveInstance?.startRendering();
} else {
  riveInstance?.stopRendering();
}
```

### 4.2 Canvas 尺寸适配

Rive 的 `resizeDrawingSurfaceToCanvas()` 方法处理 DPI 缩放：

```javascript
// 窗口 resize 时
window.addEventListener('resize', () => {
  if (riveInstance) riveInstance.resizeDrawingSurfaceToCanvas();
});
```

### 4.3 资源加载

.riv 文件中的资源有两种情况：
- **内嵌资源**：FileAssetContents 中的 bytes，Rive runtime 自动处理
- **外部资源**（CDN URL）：runtime 会尝试通过 cdnUuid 从 Rive CDN 加载

对于外部资源加载失败的情况，Rive 高级 API 提供 `assetLoader` 回调，可以自定义处理。初期可以忽略，让 runtime 自行处理。

### 4.4 内存管理

```javascript
function cleanupPreview() {
  if (riveInstance) {
    riveInstance.cleanup();
    riveInstance = null;
  }
}

// 切换文件时清理
// 页面关闭时清理
window.addEventListener('beforeunload', cleanupPreview);
```

### 4.5 错误处理

| 场景 | 处理 |
|------|------|
| CDN 不可达 | 显示"无法加载 Rive 运行时，预览需要网络连接" |
| WebGL2 不支持 | 显示"浏览器不支持 WebGL2，无法预览" |
| .riv 文件加载失败 | 显示具体错误信息（版本不兼容等） |
| 外部资源加载失败 | 预览继续，缺失的资源显示为空白 |

## 5. 实施步骤

```
Step 1: 基础框架                              [0.5天]
  - 新增 Tab HTML/CSS
  - handleFile 保存 buffer
  - Tab 切换逻辑
  - i18n 键

Step 2: Rive 集成                             [0.5天]
  - 懒加载 CDN 脚本
  - 初始化 Rive 实例
  - 基础播放

Step 3: 控制栏                                [0.5天]
  - 播放/暂停
  - Artboard 选择
  - StateMachine/Animation 选择
  - 背景色切换

Step 4: 健壮性                                [0.5天]
  - WebGL2 检测 + fallback 提示
  - CDN 加载失败处理
  - Canvas resize 适配
  - Tab 切换时暂停/恢复渲染
  - 内存清理

合计: ~2天
```

## 6. 后续扩展（P1/P2）

预览功能上线后，联动功能的扩展点：

```javascript
// P1: 图形→预览联动
// 在图形 Tab 选中节点时，记录节点名称
// 切换到预览 Tab 时，通过 Rive API 定位

// Rive 高级 API 不直接暴露 node 访问
// 需要切换到 low-level API (@rive-app/webgl2-advanced) 才能做联动
// 这意味着 P1 阶段需要将高级 API 替换为低级 API

// P2: 预览→图形联动
// 需要低级 API 的坐标变换能力
```

**重要决策**：如果确定要做 P1 联动，建议 P0 直接用 `@rive-app/webgl2-advanced`（低级 API），避免后续重写。代价是 P0 代码量增加（需要手写渲染循环），但总工作量更少。

### 建议

| 如果 | 则用 |
|------|------|
| 只做 P0 预览，联动不确定 | `@rive-app/webgl2`（高级 API，代码最少） |
| 确定要做 P1 联动 | `@rive-app/webgl2-advanced`（低级 API，一步到位） |

## 7. 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 仓库体积增加 ~2.6MB | 确定 | git clone 变慢 | 可接受，GitHub 限制 100MB/文件、1GB/仓库 |
| Rive runtime 版本与 .riv 文件版本不兼容 | 低 | 加载失败 | 捕获错误并提示；固定 runtime 版本 |
| WebGL2 上下文丢失（GPU 驱动问题） | 低 | 预览黑屏 | 监听 webglcontextlost 事件，提示刷新 |

## 8. GitHub Pages 部署方案

### 8.1 外部 CDN 可用性

**结论：GitHub Pages 完全支持加载外部 CDN 资源。**

GitHub Pages 是纯静态托管，不设置 CSP（Content-Security-Policy）限制，页面中的 `<script src="https://cdn.jsdelivr.net/...">` 可以正常加载。jsDelivr 和 unpkg 都是广泛使用的公共 CDN，在全球范围内可用。

但存在风险：
- 中国大陆部分网络环境下 jsDelivr/unpkg 可能被间歇性屏蔽
- 企业内网可能限制外部域名访问
- CDN 服务本身可能出现故障

### 8.2 Rive 运行时库的来源与存放

Rive Web 运行时由两个文件组成：

| 文件 | 大小 | 作用 |
|------|------|------|
| `rive.js` | 312 KB | JavaScript API + WASM 加载器 |
| `rive.wasm` | 2.3 MB | WebAssembly 渲染引擎 |

来源：npm 包 `@rive-app/webgl2@2.37.3`

**推荐方案：两个文件都放在仓库中，本地加载。**

理由：
1. GitHub 仓库单文件限制 100MB，2.3MB 的 WASM 完全没问题
2. GitHub Pages 站点总大小限制 1GB，当前项目远小于此
3. 本地加载 = 离线可用，不依赖任何外部 CDN
4. 版本锁定，不会因 CDN 更新导致兼容性问题

存放位置：

```
rive-inspector/
├── vendor/
│   └── rive/
│       ├── rive.js        (312KB, 来自 @rive-app/webgl2@2.37.3)
│       └── rive.wasm      (2.3MB, 来自 @rive-app/webgl2@2.37.3)
├── index.html
└── ...
```

加载方式：

```html
<!-- 方式一：直接 script 标签引入 -->
<script src="vendor/rive/rive.js"></script>

<!-- 方式二：懒加载（推荐，仅在切换到预览 Tab 时加载） -->
<script>
function loadRiveRuntime() {
  return new Promise((resolve, reject) => {
    if (window.rive) { resolve(); return; }
    const s = document.createElement('script');
    s.src = 'vendor/rive/rive.js';
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
}
</script>
```

WASM 路径配置：`rive.js` 默认从 unpkg CDN 加载 WASM，需要在初始化前重定向到本地：

```javascript
// 在 rive.js 加载后、创建 Rive 实例前调用
rive.RuntimeLoader.setWasmUrl('vendor/rive/rive.wasm');
```

### 8.3 版本更新流程

当需要升级 Rive 运行时版本时：

```bash
# 下载新版本
curl -L "https://cdn.jsdelivr.net/npm/@rive-app/webgl2@NEW_VERSION/rive.js" -o vendor/rive/rive.js
curl -L "https://cdn.jsdelivr.net/npm/@rive-app/webgl2@NEW_VERSION/rive.wasm" -o vendor/rive/rive.wasm
# 提交
git add vendor/rive/ && git commit -m "chore: upgrade rive runtime to NEW_VERSION"
```
