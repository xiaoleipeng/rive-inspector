# Rive Inspector

[English](README.md)

Rive (.riv) 文件解析、可视化与性能分析工具集。提供命令行和浏览器两种使用方式，帮助设计师和开发者深入了解 .riv 文件的内部结构和运行时性能特征。

## 功能概览

- **文本树** — 以缩进树形结构展示 .riv 文件的完整对象层级、属性值和交叉引用
- **HTML 列表** — 可交互的 HTML 页面，支持展开/折叠、搜索过滤、类别筛选
- **图形可视化** — Canvas 绘制的交互式节点图，支持平移/缩放、拖拽、右键菜单、属性面板
- **性能统计** — 渲染复杂度评分、Draw calls 分析、Feather/Clip/Mesh 分析、动画/状态机指标、性能警告
- **Web Inspector** — 独立的浏览器端 .riv 分析器（拖拽文件即用，无需 Python，支持中英文切换）

## 安装要求

- Python 3.6+
- 无第三方依赖

## 快速开始

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

### Web Inspector（浏览器端）

直接在浏览器中打开 `index.html`，拖拽 .riv 文件即可分析。包含树形视图、统计、图形可视化和导出四个标签页，支持中英文切换。

<img width="1265" height="562" alt="图形视图" src="https://github.com/user-attachments/assets/f3b4486c-c917-40fa-b345-ad099483b160" />

## 输出模式

### 文本树（默认）

```
[0] Backboard (typeKey=23) @28
  [1] Artboard "New Artboard" (typeKey=1) @30
    width: 155.89
    [2] Node "Root" (typeKey=2) @69
      [3] Shape (typeKey=3) @133
        [4] Ellipse (typeKey=4) @144
        [5] Fill (typeKey=20) @213
```

交叉引用自动解析：`objectId: #3 Shape (2)` 表示目标是全局索引 #3 的 Shape。

### HTML 列表 (`--html`)

生成可交互页面：展开/折叠节点、全文搜索、类别过滤、批量展开控制。

### 图形可视化 (`--graph`)

Canvas 节点图，支持：
- 鼠标滚轮缩放、拖拽平移
- 点击节点查看属性、双击展开/折叠
- 右键菜单（聚焦子树/展开/折叠/恢复）
- 工具栏快捷视图：Artboard / Timeline / StateMachine
- 交叉引用可视化（橙色虚线连接）
- 📊 Stats 按钮查看图形化统计图表

### 性能统计 (`--stats`)

输出渲染评分（1~5 星）、每帧渲染成本、热点 Shape、Image 纹理、Mesh 变形、Feather 模糊分析、Font/Audio/Text 资源、动画复杂度、State Machine 指标和性能警告。

<img width="1852" height="693" alt="统计视图" src="https://github.com/user-attachments/assets/ea082f4c-b1a8-4e97-8a8a-f785d5febd47" />

## 项目结构

```
rive-inspector/
├── dump_riv.py          # CLI：.riv 解析器、树构建、文本/HTML/Stats 输出
├── riv_graph.py         # CLI：Canvas 图形可视化和 Stats 图表生成模块
├── riv_schema.json      # 类型和属性名映射表（从 rive-runtime 源码提取）
├── index.html           # Web Inspector：独立的浏览器端 .riv 分析器
├── docs/
│   ├── RIV_FORMAT.md    # .riv 二进制格式技术规范
│   ├── USAGE.md         # CLI 详细使用说明
│   ├── PERFORMANCE_GUIDE.md  # 性能指标详解与优化指南
│   └── PREVIEW_FEASIBILITY.md  # Rive 预览集成可行性报告
├── examples/
│   └── clip.riv         # 测试用 .riv 文件
├── LICENSE
└── README.md
```

## 典型工作流

```bash
# 1. 快速评估性能
python3 dump_riv.py animation.riv --stats

# 2. 定位性能瓶颈（图形化）
python3 dump_riv.py animation.riv --graph output.html

# 3. 对比优化前后
python3 dump_riv.py before.riv --stats > before.txt
python3 dump_riv.py after.riv --stats > after.txt
diff before.txt after.txt
```

## 文档

- [docs/USAGE.md](docs/USAGE.md) — 完整使用说明和输出示例
- [docs/PERFORMANCE_GUIDE.md](docs/PERFORMANCE_GUIDE.md) — 性能指标详解与优化检查清单
- [docs/RIV_FORMAT.md](docs/RIV_FORMAT.md) — .riv 二进制格式技术规范

## 许可证

[MIT](LICENSE)
