# Rive Inspector

[中文文档](README_zh.md)

A toolkit for parsing, visualizing, and profiling Rive (.riv) files. Available as both CLI and browser-based tools, helping designers and developers understand the internal structure and runtime performance characteristics of .riv files.

## Features

- **Text Tree** — Indented tree view of the full object hierarchy, property values, and cross-references
- **HTML List** — Interactive HTML page with expand/collapse, search filtering, and category filtering
- **Graph Visualization** — Canvas-based interactive node graph with pan/zoom, drag, context menu, and property panel
- **Performance Stats** — Rendering complexity score, draw call analysis, Feather/Clip/Mesh analysis, animation/state machine metrics, and warnings
- **Web Inspector** — Standalone browser-based .riv analyzer (drag & drop, no Python required, bilingual zh/en)

## Requirements

- Python 3.6+
- No third-party dependencies

## Quick Start

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

### Web Inspector (Browser)

Open `index.html` in a browser and drag & drop a .riv file to analyze it. Includes tree view, stats, graph visualization, and export tabs. Supports Chinese/English switching.

<img width="1265" height="562" alt="Graph View" src="https://github.com/user-attachments/assets/f3b4486c-c917-40fa-b345-ad099483b160" />

## Output Modes

### Text Tree (default)

```
[0] Backboard (typeKey=23) @28
  [1] Artboard "New Artboard" (typeKey=1) @30
    width: 155.89
    [2] Node "Root" (typeKey=2) @69
      [3] Shape (typeKey=3) @133
        [4] Ellipse (typeKey=4) @144
        [5] Fill (typeKey=20) @213
```

Cross-references are auto-resolved: `objectId: #3 Shape (2)` means the target is the Shape at global index #3.

### HTML List (`--html`)

Interactive page with collapsible nodes, full-text search, category filtering, and bulk expand controls.

### Graph Visualization (`--graph`)

Canvas node graph with:
- Scroll to zoom, drag to pan
- Click nodes to view properties, double-click to expand/collapse
- Right-click menu (focus subtree / expand / collapse / restore)
- Toolbar quick views: Artboard / Timeline / StateMachine
- Cross-reference visualization (orange dashed lines)
- 📊 Stats button for graphical statistics

### Performance Stats (`--stats`)

Outputs rendering score (1–5 stars), per-frame rendering cost, hot Shapes, Image textures, Mesh deformation, Feather blur analysis, Font/Audio/Text assets, animation complexity, State Machine metrics, and performance warnings.

<img width="1852" height="693" alt="Stats View" src="https://github.com/user-attachments/assets/ea082f4c-b1a8-4e97-8a8a-f785d5febd47" />

## Project Structure

```
rive-inspector/
├── dump_riv.py          # CLI: .riv parser, tree builder, text/HTML/stats output
├── riv_graph.py         # CLI: Canvas graph visualization and stats chart generator
├── riv_schema.json      # Type and property name mappings (from rive-runtime source)
├── index.html           # Web Inspector: standalone browser-based .riv analyzer
├── docs/
│   ├── RIV_FORMAT.md    # .riv binary format specification
│   ├── USAGE.md         # Detailed CLI usage instructions
│   ├── PERFORMANCE_GUIDE.md  # Performance metrics and optimization guide
│   └── PREVIEW_FEASIBILITY.md  # Rive preview integration feasibility report
├── examples/
│   └── clip.riv         # Sample .riv file for testing
├── LICENSE
└── README.md
```

## Typical Workflow

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

## Documentation

- [docs/USAGE.md](docs/USAGE.md) — Full CLI usage instructions and output examples
- [docs/PERFORMANCE_GUIDE.md](docs/PERFORMANCE_GUIDE.md) — Performance metrics explained with optimization checklist
- [docs/RIV_FORMAT.md](docs/RIV_FORMAT.md) — .riv binary format specification

## License

[MIT](LICENSE)
