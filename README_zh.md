# Rive Inspector

[English](README.md) · [🌐 在线体验](https://xiaoleipeng.github.io/rive-inspector/)

Rive (.riv) 文件解析、可视化、性能分析与预览工具集。提供命令行和浏览器两种使用方式，帮助设计师和开发者深入了解 .riv 文件的内部结构和运行时性能特征。

## ✨ 功能概览

### 🌐 Web Inspector（浏览器端）

> **[立即使用 →](https://xiaoleipeng.github.io/rive-inspector/)**
>
> 拖拽 .riv 文件即可开始分析，无需安装。支持中英文切换。

#### 🌳 树形视图
- 完整对象层级，支持展开/折叠
- 全文搜索过滤
- 类别颜色编码（结构/形状/绘制/动画/状态机...）
- 属性显示与交叉引用解析
- 批量展开控制（全部展开 / 全部折叠 / 展开2层）

#### 📊 统计视图
- **渲染评分**（1~5 星）— 综合复杂度评估
- **每帧渲染成本** — drawPath / clipPath / drawImage / drawImageMesh
- **渲染点数计算** — 基于 rive-runtime 源码的精确 GPU 开销计算，包含圆角处理（Rectangle/Polygon/Star cornerRadius）
- **Clip 分析** — 通过 ClippingShape sourceId 解析裁剪路径渲染点数
- **Feather 分析** — 数量、强度、内羽化模式、路径尺寸、模糊面积估算、高开销警告
- **热点 Shape** — 多次绘制/裁剪/Mesh 的形状，可排序详情表
- **Image 纹理** — 名称、尺寸、绘制类型（drawImage/drawImageMesh）
- **Mesh 变形** — Mesh 数量、顶点数、关联纹理
- **Font/Audio/Text 资源** — 嵌入大小、CDN 标记、文本内容提取
- **动画分析** — 每帧插值属性数、路径重算检测
- **State Machine 指标** — 层数、监听器、条件、输入、状态、转换
- **性能警告** — 自动检测高顶点数、Draw calls、裁剪、Mesh、Feather、路径重算
- **可点击详情弹窗** — 点击区块标题（▸）查看完整数据表

#### 🔗 图形视图
- Canvas 绘制的交互式节点图
- 滚轮缩放、拖拽平移、点击选中
- 双击展开/折叠子树
- 右键菜单（聚焦子树 / 展开 / 折叠 / 恢复）
- 工具栏快捷视图：Artboard / Timeline / StateMachine
- 交叉引用可视化（橙色虚线连接）
- 属性面板，支持点击交叉引用跳转
- 📊 Stats 按钮查看图形化统计图表

#### 👁 预览
- **实时 Rive 动画播放** — 通过 Rive WASM 运行时 WebGL2 渲染
- **Artboard / 状态机 / 动画选择** — 切换不同画板和播放目标
- **布局适配模式** — Contain / Cover / Fill / FitWidth / FitHeight / None / ScaleDown / Layout
- **背景切换** — 深色 / 白色 / 黑色 / 棋盘格
- **运行时版本选择** — 15+ 版本，从 v2.20.0 到 v2.37.3
  - 关键版本本地打包，支持离线使用（标记 ●）
  - 内部版本高亮显示：v2.27.2（≈Android 10.1.4）、v2.27.3（≈Android 10.1.5）、v2.20.0/v2.20.2（V1）
  - 其他版本通过 jsDelivr CDN 加载
- **交互控制面板**（左侧边栏）：
  - **Inputs** — 触发器按钮、布尔开关、数值滑块
  - **Text** — 实时文本编辑（setTextRunValue）
  - **ViewModel** — 字符串/数值/布尔/颜色/枚举/触发器属性控制
- **3 步加载进度** — JS 下载 → WASM 加载 → 渲染器初始化

#### 💾 导出
- 导出文本报告（.txt）
- 导出 JSON 数据（.json）
- 导出性能统计（.txt）

### 🖥 CLI 工具（Python）

```bash
# 文本树输出
python3 dump_riv.py file.riv

# 交互式 HTML 列表（自动打开浏览器）
python3 dump_riv.py file.riv --html output.html

# 图形可视化（自动打开浏览器）
python3 dump_riv.py file.riv --graph output.html

# 性能统计
python3 dump_riv.py file.riv --stats

# 查看帮助
python3 dump_riv.py --help
```

环境要求：Python 3.6+，无第三方依赖。

## 🚀 快速开始

### 在线使用（推荐）

访问 **[https://xiaoleipeng.github.io/rive-inspector/](https://xiaoleipeng.github.io/rive-inspector/)**，拖拽 .riv 文件即可。

### 本地 HTTP 服务器

```bash
git clone https://github.com/xiaoleipeng/rive-inspector.git
cd rive-inspector
python3 -m http.server 8080
# 打开 http://localhost:8080
```

### CLI

```bash
git clone https://github.com/xiaoleipeng/rive-inspector.git
cd rive-inspector
python3 dump_riv.py your_file.riv --stats
```

## 📁 项目结构

```
rive-inspector/
├── index.html              # Web Inspector（独立单文件）
├── dump_riv.py             # CLI：.riv 解析器、树构建、文本/HTML/统计输出
├── riv_graph.py            # CLI：Canvas 图形可视化生成模块
├── riv_schema.json         # 类型/属性名映射表（来自 rive-runtime）
├── vendor/rive/            # 本地打包的 Rive WASM 运行时（离线支持）
│   ├── 2.37.3/             # 最新版本
│   ├── 2.27.2/             # ≈Android 10.1.4
│   ├── 2.27.3/             # ≈Android 10.1.5
│   └── .../                # 其他关键版本
├── docs/
│   ├── RIV_FORMAT.md       # .riv 二进制格式技术规范
│   ├── USAGE.md            # CLI 使用说明
│   ├── PERFORMANCE_GUIDE.md # 性能指标与优化指南
│   ├── PREVIEW_DESIGN.md   # 预览功能技术设计
│   └── PREVIEW_FEASIBILITY.md # 预览集成可行性报告
├── examples/
│   └── clip.riv            # 示例 .riv 文件
├── LICENSE                 # MIT
└── README.md
```

## 📖 文档

- [docs/USAGE.md](docs/USAGE.md) — CLI 使用说明和输出示例
- [docs/PERFORMANCE_GUIDE.md](docs/PERFORMANCE_GUIDE.md) — 性能指标详解与优化检查清单
- [docs/RIV_FORMAT.md](docs/RIV_FORMAT.md) — .riv 二进制格式技术规范
- [docs/PREVIEW_DESIGN.md](docs/PREVIEW_DESIGN.md) — 预览功能技术设计
- [docs/PREVIEW_FEASIBILITY.md](docs/PREVIEW_FEASIBILITY.md) — 预览集成可行性报告

## 🔧 典型工作流

```bash
# 1. 快速性能评估
python3 dump_riv.py animation.riv --stats

# 2. 定位性能瓶颈（图形化）
python3 dump_riv.py animation.riv --graph output.html

# 3. 对比优化前后
python3 dump_riv.py before.riv --stats > before.txt
python3 dump_riv.py after.riv --stats > after.txt
diff before.txt after.txt
```

## 许可证

[MIT](LICENSE)
