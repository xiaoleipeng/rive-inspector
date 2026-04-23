# Rive Inspector

[中文文档](README_zh.md) · [🌐 Online Demo](https://xiaoleipeng.github.io/rive-inspector/)

A comprehensive toolkit for parsing, visualizing, profiling, and previewing Rive (.riv) files. Available as both CLI and browser-based tools, helping designers and developers understand the internal structure and runtime performance characteristics of .riv files.

## ✨ Features

### 🌐 Web Inspector (Browser)

> **[Launch Online →](https://xiaoleipeng.github.io/rive-inspector/)**
>
> Drag & drop a .riv file to start. No installation required. Supports Chinese/English switching.

#### 🌳 Tree View
- Full object hierarchy with expand/collapse
- Full-text search filtering
- Category color coding (Structure/Shape/Paint/Animation/StateMachine...)
- Property display with cross-reference resolution
- Bulk expand controls (Expand All / Collapse All / Level 2)

#### 📊 Stats View
- **Render Score** (1–5 stars) — overall complexity assessment
- **Per-frame Render Cost** — drawPath / clipPath / drawImage / drawImageMesh
- **Render Point Calculation** — accurate GPU cost based on rive-runtime source code, including rounded corners (Rectangle/Polygon/Star cornerRadius)
- **Clip Analysis** — clip path render points via ClippingShape sourceId resolution
- **Feather Analysis** — count, strength, inner mode, path bounds, blur area estimate, high-cost warnings
- **Hot Shapes** — shapes with multiple draws/clips/meshes, sortable detail table
- **Image Textures** — name, dimensions, draw type (drawImage/drawImageMesh)
- **Mesh Deformation** — mesh count, vertex count, associated textures
- **Font/Audio/Text Assets** — embedded size, CDN marker, text content extraction
- **Animation Analysis** — per-frame interpolation count, path recalculation detection
- **State Machine Metrics** — layers, listeners, conditions, inputs, states, transitions
- **Performance Warnings** — auto-detection of high vertices, draw calls, clips, meshes, feathers, path recalcs
- **Clickable Detail Modals** — click section headers (▸) to view full data tables

#### 🔗 Graph View
- Canvas-based interactive node graph
- Scroll to zoom, drag to pan, click to select
- Double-click to expand/collapse subtrees
- Right-click context menu (focus subtree / expand / collapse / restore)
- Toolbar quick views: Artboard / Timeline / StateMachine
- Cross-reference visualization (orange dashed lines)
- Property panel with clickable cross-reference links
- 📊 Stats button for graphical statistics with charts

#### 👁 Preview
- **Live Rive Animation Playback** — WebGL2 rendering via Rive WASM runtime
- **Artboard / StateMachine / Animation Selection** — switch between different artboards and playback targets
- **Layout Fit Modes** — Contain / Cover / Fill / FitWidth / FitHeight / None / ScaleDown / Layout
- **Background Toggle** — dark / white / black / checkerboard
- **Runtime Version Selector** — 15+ versions from v2.20.0 to v2.37.3
  - Key versions bundled locally for offline use (marked with ●)
  - Internal versions highlighted: v2.27.2 (≈Android 10.1.4), v2.27.3 (≈Android 10.1.5), v2.20.0/v2.20.2 (V1)
  - Other versions loaded from jsDelivr CDN
- **Interactive Control Panel** (left sidebar):
  - **Inputs** — Trigger buttons, Boolean checkboxes, Number sliders
  - **Text** — Live text editing via setTextRunValue
  - **ViewModel** — String/Number/Boolean/Color/Enum/Trigger property controls
- **3-step Loading Progress** — JS download → WASM load → renderer init

#### 💾 Export
- Export text report (.txt)
- Export JSON data (.json)
- Export stats report (.txt)

### 🖥 CLI Tool (Python)

```bash
# Text tree output
python3 dump_riv.py file.riv

# Interactive HTML list (auto-opens browser)
python3 dump_riv.py file.riv --html output.html

# Graph visualization (auto-opens browser)
python3 dump_riv.py file.riv --graph output.html

# Performance stats
python3 dump_riv.py file.riv --stats

# Help
python3 dump_riv.py --help
```

Requirements: Python 3.6+, no third-party dependencies.

## 🚀 Quick Start

### Online (Recommended)

Visit **[https://xiaoleipeng.github.io/rive-inspector/](https://xiaoleipeng.github.io/rive-inspector/)** and drag & drop a .riv file.

### Local with HTTP Server

```bash
git clone https://github.com/xiaoleipeng/rive-inspector.git
cd rive-inspector
python3 -m http.server 8080
# Open http://localhost:8080
```

### CLI

```bash
git clone https://github.com/xiaoleipeng/rive-inspector.git
cd rive-inspector
python3 dump_riv.py your_file.riv --stats
```

## 📁 Project Structure

```
rive-inspector/
├── index.html              # Web Inspector (standalone, all-in-one)
├── dump_riv.py             # CLI: .riv parser, tree builder, text/HTML/stats
├── riv_graph.py            # CLI: Canvas graph visualization generator
├── riv_schema.json         # Type/property name mappings (from rive-runtime)
├── vendor/rive/            # Bundled Rive WASM runtimes (offline support)
│   ├── 2.37.3/             # Latest version
│   ├── 2.27.2/             # ≈Android 10.1.4
│   ├── 2.27.3/             # ≈Android 10.1.5
│   └── .../                # Other key versions
├── docs/
│   ├── RIV_FORMAT.md       # .riv binary format specification
│   ├── USAGE.md            # CLI usage instructions
│   ├── PERFORMANCE_GUIDE.md # Performance metrics & optimization guide
│   ├── PREVIEW_DESIGN.md   # Preview feature technical design
│   └── PREVIEW_FEASIBILITY.md # Preview integration feasibility report
├── examples/
│   └── clip.riv            # Sample .riv file
├── LICENSE                 # MIT
└── README.md
```

## 📖 Documentation

- [docs/USAGE.md](docs/USAGE.md) — CLI usage instructions and output examples
- [docs/PERFORMANCE_GUIDE.md](docs/PERFORMANCE_GUIDE.md) — Performance metrics explained with optimization checklist
- [docs/RIV_FORMAT.md](docs/RIV_FORMAT.md) — .riv binary format specification
- [docs/PREVIEW_DESIGN.md](docs/PREVIEW_DESIGN.md) — Preview feature technical design
- [docs/PREVIEW_FEASIBILITY.md](docs/PREVIEW_FEASIBILITY.md) — Preview integration feasibility report

## 🔧 Typical Workflow

```bash
# 1. Quick performance assessment
python3 dump_riv.py animation.riv --stats

# 2. Locate performance bottlenecks (graphical)
python3 dump_riv.py animation.riv --graph output.html

# 3. Compare before/after optimization
python3 dump_riv.py before.riv --stats > before.txt
python3 dump_riv.py after.riv --stats > after.txt
diff before.txt after.txt
```

## License

[MIT](LICENSE)
