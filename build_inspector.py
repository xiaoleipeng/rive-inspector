#!/usr/bin/env python3
"""
Build rive-inspector.html - a self-contained web-based Rive file analyzer.
Embeds riv_schema.json and all JS/CSS into a single HTML file.

Usage: python3 build_inspector.py
Output: rive-inspector.html
"""
import json, os

def load_schema():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "riv_schema.json")
    with open(p) as f:
        return json.load(f)

def load_part(name):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inspector_parts", name)
    with open(p) as f:
        return f.read()

def build():
    schema = load_schema()
    schema_json = json.dumps(schema)

    css = load_part("style.css")
    parser_js = load_part("parser.js")
    tree_js = load_part("tree.js")
    stats_js = load_part("stats.js")
    ui_js = load_part("ui.js")
    graph_js = load_part("graph.js")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rive Inspector</title>
<style>{css}</style>
</head><body>
<div id="app">
<div id="dropzone">
<div class="drop-icon">📦</div>
<h1>Rive Inspector</h1>
<p>拖拽 .riv 文件到此处，或 <label for="fileinput" class="link">点击选择文件</label></p>
<input type="file" id="fileinput" accept=".riv" hidden>
</div>
<div id="main" class="hidden">
<div id="topbar">
<span id="filename"></span>
<div id="tabs">
<button class="tab active" data-tab="tree">🌳 树形</button>
<button class="tab" data-tab="stats">📊 统计</button>
<button class="tab" data-tab="graph">🔗 图形</button>
<button class="tab" data-tab="export">💾 导出</button>
</div>
<button id="newfile" class="btn-sm">Open</button>
<button id="langBtn" class="btn-sm" onclick="toggleLang()">EN</button>
</div>
<div id="tab-tree" class="tabcontent active"></div>
<div id="tab-stats" class="tabcontent"></div>
<div id="tab-graph" class="tabcontent"><canvas id="gcanvas"></canvas></div>
<div id="tab-export" class="tabcontent"></div>
</div>
</div>
<script>
// Schema
const SCHEMA={schema_json};
const TYPE_NAMES={{}};for(const[k,v]of Object.entries(SCHEMA.type_names))TYPE_NAMES[parseInt(k)]=v;
const PROP_FIELDS={{}};for(const[k,v]of Object.entries(SCHEMA.property_fields))PROP_FIELDS[parseInt(k)]=v;
const PROP_NAMES={{}};for(const[k,v]of Object.entries(SCHEMA.property_names))PROP_NAMES[parseInt(k)]=v;

{parser_js}
{tree_js}
{stats_js}
{graph_js}
{ui_js}
</script>
</body></html>'''

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rive-inspector.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"Built {out} ({len(html)//1024}KB)")

if __name__ == "__main__":
    build()
