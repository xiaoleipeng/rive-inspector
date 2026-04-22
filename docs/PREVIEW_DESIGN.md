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

## 9. 交互控制面板

### 9.1 需求

在预览 Tab 左侧增加控制面板，支持动态调整 .riv 文件的运行时数据，包括：
1. **State Machine Inputs** — 触发器、数值、布尔开关
2. **Text Runs** — 修改文本内容
3. **ViewModel Properties** — 修改绑定数据（字符串、数值、布尔、颜色、枚举、触发器）

参考布局：[Rive Marketplace 预览页](https://rive.app/marketplace/)

### 9.2 布局设计

```
┌──────────────────────────────────────────────────────────┐
│ [⏸] [Artboard ▼] [SM: State Machine 1 ▼] [🎨]    500×500│  ← 顶部工具栏
├──────────────┬───────────────────────────────────────────┤
│ 左侧控制面板  │              Canvas 预览区                 │
│ (260px,可滚动)│                                           │
│              │                                           │
│ ▼ Inputs     │                                           │
│  bump    [触发]│         Rive WebGL2 渲染                  │
│  speed   [═══]│                                           │
│  active  [✓] │                                           │
│              │                                           │
│ ▼ Text       │                                           │
│  title  [___]│                                           │
│  desc   [___]│                                           │
│              │                                           │
│ ▼ ViewModel  │                                           │
│  name   [___]│                                           │
│  score  [═══]│                                           │
│  done   [✓]  │                                           │
│  color  [■]  │                                           │
│  type   [▼]  │                                           │
│  fire   [触发]│                                           │
└──────────────┴───────────────────────────────────────────┘
```

面板特性：
- 可折叠的分组（Inputs / Text / ViewModel）
- 无数据时分组自动隐藏
- 面板可通过按钮收起/展开，收起时 Canvas 占满宽度

### 9.3 Rive API 映射

#### 9.3.1 State Machine Inputs

```javascript
// 获取当前状态机的所有输入
const inputs = riveInstance.stateMachineInputs(smName);
// 每个 input: { name: string, type: number, value: number|boolean, fire(): void }
// type: 56=Number, 59=Boolean, 58=Trigger
```

| Input 类型 | 控件 | 交互 |
|-----------|------|------|
| Trigger (58) | 按钮 | 点击调用 `input.fire()` |
| Boolean (59) | checkbox | 切换设置 `input.value = true/false` |
| Number (56) | range slider + 数字框 | 拖动/输入设置 `input.value = n` |

#### 9.3.2 Text Runs

```javascript
// 从我们的解析数据中获取所有 TextValueRun 的名称
const textRuns = currentData.objects
  .filter(o => o.typeName === 'TextValueRun' && o.name);

// 读取/写入
const val = riveInstance.getTextRunValue(runName);
riveInstance.setTextRunValue(runName, newValue);
```

| 控件 | 交互 |
|------|------|
| text input | 输入时实时调用 `setTextRunValue()` |

#### 9.3.3 ViewModel Properties

```javascript
// 初始化时启用 autoBind
const riveOpts = { ..., autoBind: true };

// onLoad 后获取绑定的 ViewModel 实例
const vmi = riveInstance.viewModelInstance;
if (!vmi) return; // 文件没有 ViewModel

// 遍历属性
const vm = riveInstance.defaultViewModel();
const properties = vm.properties; // [{name, type}]
```

| 属性类型 | 控件 | API |
|---------|------|-----|
| String | text input | `vmi.string("prop").value = "..."` |
| Number | range slider + 数字框 | `vmi.number("prop").value = n` |
| Boolean | checkbox | `vmi.boolean("prop").value = true` |
| Color | color picker | `vmi.color("prop").value = 0xFFRRGGBB` |
| Enum | select 下拉 | `vmi.enum("prop").value = "Option1"` |
| Trigger | 按钮 | `vmi.trigger("prop").trigger()` |

### 9.4 实现要点

#### 数据扫描时机

在 Rive `onLoad` 回调中扫描，此时所有数据已就绪：

```javascript
onLoad: () => {
  populatePreviewControls();  // 现有：填充 Artboard/SM 下拉
  buildControlPanel();        // 新增：构建左侧控制面板
}
```

#### 控件生成逻辑

```javascript
function buildControlPanel() {
  let html = '';

  // 1. Inputs
  const smName = getCurrentSmName();
  const inputs = smName ? riveInstance.stateMachineInputs(smName) : [];
  if (inputs && inputs.length) {
    html += '<div class="pv-group"><div class="pv-group-title">▼ Inputs</div>';
    for (const inp of inputs) {
      if (inp.type === 58)      html += triggerControl(inp);
      else if (inp.type === 59) html += boolControl(inp);
      else if (inp.type === 56) html += numberControl(inp);
    }
    html += '</div>';
  }

  // 2. Text Runs
  const textRuns = getNamedTextRuns();
  if (textRuns.length) {
    html += '<div class="pv-group"><div class="pv-group-title">▼ Text</div>';
    for (const run of textRuns) html += textControl(run);
    html += '</div>';
  }

  // 3. ViewModel
  const vmi = riveInstance.viewModelInstance;
  if (vmi) {
    const vm = riveInstance.defaultViewModel();
    const props = vm ? vm.properties : [];
    if (props.length) {
      html += '<div class="pv-group"><div class="pv-group-title">▼ ViewModel</div>';
      for (const p of props) html += vmPropertyControl(vmi, p);
      html += '</div>';
    }
  }

  document.getElementById('preview-panel').innerHTML = html;
  bindControlEvents(); // 绑定事件
}
```

#### 事件绑定策略

使用事件委托，在面板容器上监听 `input`/`change`/`click` 事件，通过 `data-*` 属性识别目标：

```javascript
panel.addEventListener('input', e => {
  const el = e.target;
  if (el.dataset.smInput) {
    // SM Input: number/boolean
    const inp = smInputMap[el.dataset.smInput];
    inp.value = el.type === 'checkbox' ? el.checked : parseFloat(el.value);
  } else if (el.dataset.textRun) {
    // Text Run
    riveInstance.setTextRunValue(el.dataset.textRun, el.value);
  } else if (el.dataset.vmProp) {
    // ViewModel property
    updateVmProperty(el.dataset.vmProp, el.dataset.vmType, el.value);
  }
});
```

### 9.5 CSS 结构

```css
#preview-panel {
  width: 260px; flex-shrink: 0; overflow-y: auto;
  background: #1f2335; border-right: 1px solid #3b4261;
  padding: 8px; font-size: 12px;
}
.pv-group { margin-bottom: 8px; }
.pv-group-title {
  color: #7aa2f7; font-weight: 600; cursor: pointer;
  padding: 4px 0; border-bottom: 1px solid #3b4261;
}
.pv-row { display: flex; align-items: center; padding: 3px 0; gap: 8px; }
.pv-label { color: #9aa5ce; min-width: 80px; overflow: hidden; text-overflow: ellipsis; }
.pv-input { flex: 1; background: #1a1b26; border: 1px solid #3b4261;
            color: #c0caf5; padding: 2px 6px; border-radius: 3px; font: inherit; }
.pv-btn { background: #3b4261; border: none; color: #c0caf5;
          padding: 3px 12px; border-radius: 3px; cursor: pointer; }
.pv-range { flex: 1; }
```

### 9.6 HTML 结构变更

```html
<!-- 预览 Tab 内容改为左右布局 -->
<div id="tab-preview" class="tabcontent">
  <div id="preview-toolbar">...</div>
  <div id="preview-body">
    <div id="preview-panel"></div>        <!-- 新增：左侧控制面板 -->
    <div id="preview-container">
      <canvas id="preview-canvas"></canvas>
      <div id="preview-msg"></div>
    </div>
  </div>
</div>
```

### 9.7 切换 Artboard/SM 时的刷新

切换 Artboard 或 StateMachine 后，控制面板需要重新构建：
- Inputs 随 StateMachine 变化
- Text Runs 随 Artboard 变化
- ViewModel 随 Artboard 变化

在 `onPreviewAbChange` 和 `onPreviewSmChange` 的回调中调用 `buildControlPanel()`。

### 9.8 工作量评估

| 任务 | 预估 |
|------|------|
| HTML/CSS 布局（面板 + 左右分栏） | 0.5h |
| Inputs 控件生成 + 事件绑定 | 1h |
| Text Runs 控件 | 0.5h |
| ViewModel 属性控件（6 种类型） | 1.5h |
| 切换 AB/SM 时刷新 | 0.5h |
| 测试 + 边界情况 | 1h |
| **合计** | **~5h** |
