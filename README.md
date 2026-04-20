# Rive Inspector

[中文文档](README_zh.md)

A toolkit for parsing, visualizing, and profiling Rive (.riv) files. Available as both CLI and browser-based tools, helping designers and developers understand the internal structure and runtime performance characteristics of .riv files.

## Features

- **Text Tree** — Indented tree view of the full object hierarchy, property values, and cross-references
- **HTML List** — Interactive HTML page with expand/collapse, search filtering, and category filtering
- **Graph Visualization** — Canvas-based interactive node graph with pan/zoom, drag, context menu, and property panel
- **Performance Stats** — Rendering complexity score, draw call analysis, animation/state machine metrics, and warnings
- **Web Inspector** — Standalone browser-based .riv analyzer (drag & drop, no Python required)

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

Open `rive-inspector.html` in a browser and drag & drop a .riv file to analyze it. Includes tree view, stats charts, and graph visualization tabs.

Rebuild:

```bash
python3 build_inspector.py
```

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

<img width="1265" height="562" alt="image" src="https://github.com/user-attachments/assets/f3b4486c-c917-40fa-b345-ad099483b160" />

### Performance Stats (`--stats`)

Outputs rendering score (1–5 stars), per-frame rendering cost, hot Shapes, Image textures, Mesh deformation, animation complexity, State Machine metrics, and performance warnings.

<img width="1852" height="693" alt="image" src="https://github.com/user-attachments/assets/ea082f4c-b1a8-4e97-8a8a-f785d5febd47" />

## Files

| File | Description |
|------|-------------|
| `dump_riv.py` | Main script: .riv parser, tree builder, text/HTML/stats output |
| `riv_graph.py` | Canvas graph visualization and stats chart HTML generator |
| `riv_schema.json` | Type and property name mappings extracted from rive-runtime source |
| `build_inspector.py` | Build script for `rive-inspector.html` |
| `rive-inspector.html` | Standalone browser-based .riv analyzer (build artifact) |
| `RIV_FORMAT.md` | Rive .riv binary format technical documentation |
| `PERFORMANCE_GUIDE.md` | Performance analysis guide: metrics, thresholds, optimization tips |
| `USAGE.md` | Detailed usage instructions |

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

- [USAGE.md](USAGE.md) — Full usage instructions and output examples
- [PERFORMANCE_GUIDE.md](PERFORMANCE_GUIDE.md) — Performance metrics explained with optimization checklist
- [RIV_FORMAT.md](RIV_FORMAT.md) — .riv binary format specification
