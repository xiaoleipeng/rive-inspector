"""
Graph visualization HTML generator for dump_riv.py --graph mode.
Generates a self-contained HTML with Canvas-based tree graph.
"""

import json
import html as html_mod

def generate_graph_html(header, objects, filename, tree, cat_colors, field_labels, prop_name_fn, fmt_val_fn, prop_desc_fn=None, type_names=None, prop_names=None, stats=None):
    h = html_mod.escape

    def node_to_json(node):
        o = node["obj"]
        ref_links = o.get("_ref_links", {})
        return {
            "i": o["index"], "off": o["offset"], "tk": o["typeKey"],
            "tn": o["typeName"], "cat": o["category"], "nm": o["name"], "err": o["error"],
            "props": [{"k": p["key"], "n": prop_name_fn(p["key"]), "t": p["type"],
                        "tl": field_labels.get(p["type"], "?"), "v": fmt_val_fn(p, o.get("_refs", {})),
                        "rc": f"#{p['value']:08X}" if p["type"] == 3 else None,
                        "link": ref_links.get(p["key"]),
                        "desc": prop_desc_fn(p["key"]) if prop_desc_fn else ""}
                       for p in o["properties"]],
            "ch": [node_to_json(c) for c in node["children"]],
        }

    tree_json = json.dumps([node_to_json(r) for r in tree])
    colors_json = json.dumps(cat_colors)

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{h(filename)} - Rive Graph</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#1a1b26;color:#c0caf5;overflow:hidden;height:100vh}}
#app{{display:flex;height:100vh}}
#left{{flex:1;position:relative;overflow:hidden}}
canvas{{display:block;cursor:grab}}
canvas.grabbing{{cursor:grabbing}}
#panel{{width:340px;background:#24283b;border-left:1px solid #3b4261;display:flex;flex-direction:column;overflow:hidden;transition:width .2s}}
#panel.closed{{width:0;border:none}}
#ptoggle{{position:absolute;right:340px;top:50%;transform:translateY(-50%);background:#24283b;border:1px solid #3b4261;border-right:none;color:#9aa5ce;padding:8px 4px;cursor:pointer;border-radius:4px 0 0 4px;z-index:10;font-size:14px;transition:right .2s}}
#ptoggle.closed{{right:0}}
#phdr{{padding:14px 16px;border-bottom:1px solid #3b4261;flex-shrink:0}}
#phdr h2{{font-size:14px;color:#7aa2f7;font-weight:600}}
#phdr .sub{{font-size:11px;color:#565f89;margin-top:2px}}
#pbody{{flex:1;overflow-y:auto;padding:10px 16px}}
.pg{{margin-bottom:12px}}
.pg h3{{font-size:11px;color:#565f89;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid #3b4261}}
.pp{{display:flex;justify-content:space-between;padding:3px 0;font-size:12px}}
.pp .pk{{color:#9aa5ce}}.pp .pv{{color:#c0caf5;text-align:right;max-width:180px;word-break:break-all}}
.pv.s{{color:#9ece6a}}.pv.n{{color:#ff9e64}}.pv.b{{color:#bb9af7}}.pv.c{{color:#f7768e}}
.csw{{display:inline-block;width:12px;height:12px;border-radius:2px;border:1px solid #3b4261;vertical-align:middle;margin-right:3px}}
.tip{{display:inline-block;width:14px;height:14px;line-height:14px;text-align:center;border-radius:50%;background:#3b4261;color:#9aa5ce;font-size:9px;cursor:help;margin-left:4px;vertical-align:middle}}.tip:hover{{background:#7aa2f7;color:#1a1b26}}
#hint{{position:absolute;bottom:12px;left:12px;background:rgba(36,40,59,.9);padding:8px 14px;border-radius:6px;font-size:11px;color:#565f89;pointer-events:none}}
#toolbar{{position:absolute;top:12px;left:12px;display:flex;gap:6px;z-index:5}}
#legend{{position:absolute;bottom:12px;right:352px;background:rgba(36,40,59,.95);padding:10px 14px;border-radius:6px;font-size:11px;color:#9aa5ce;display:flex;flex-wrap:wrap;gap:4px 12px;max-width:420px;transition:right .2s}}
#legend.shifted{{right:12px}}
.lg-item{{display:flex;align-items:center;gap:5px;white-space:nowrap}}
.lg-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.tbtn{{background:rgba(36,40,59,.9);border:1px solid #3b4261;color:#9aa5ce;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:12px;font-family:inherit}}
.tbtn:hover{{background:#3b4261;color:#c0caf5}}
#info{{position:absolute;top:12px;right:352px;background:rgba(36,40,59,.9);padding:6px 12px;border-radius:6px;font-size:11px;color:#9aa5ce;transition:right .2s}}
#info.shifted{{right:12px}}
#empty{{padding:40px 16px;text-align:center;color:#565f89;font-size:13px}}
#modal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center}}
#modal.open{{display:flex}}
#modal-box{{background:#24283b;border:1px solid #3b4261;border-radius:8px;width:700px;max-height:80vh;display:flex;flex-direction:column;overflow:hidden}}
#modal-hdr{{padding:12px 16px;border-bottom:1px solid #3b4261;display:flex;align-items:center;gap:10px}}
#modal-hdr h2{{font-size:14px;color:#7aa2f7;flex:1}}
#modal-hdr .close{{background:none;border:none;color:#565f89;font-size:18px;cursor:pointer;padding:0 4px}}
#modal-hdr .close:hover{{color:#c0caf5}}
.tab-bar{{display:flex;gap:0;border-bottom:1px solid #3b4261}}
.tab{{padding:8px 16px;cursor:pointer;color:#565f89;font-size:12px;border-bottom:2px solid transparent}}
.tab.active{{color:#7aa2f7;border-bottom-color:#7aa2f7}}
.tab:hover{{color:#c0caf5}}
#modal-search{{margin:10px 16px;background:#1a1b26;border:1px solid #3b4261;color:#c0caf5;padding:6px 10px;border-radius:4px;font:inherit;font-size:12px;outline:none;width:calc(100% - 32px)}}
#modal-search:focus{{border-color:#7aa2f7}}
#modal-body{{flex:1;overflow-y:auto;padding:0 16px 12px}}
.schema-row{{display:flex;padding:3px 0;font-size:12px;border-bottom:1px solid #1f2335}}
.schema-row:hover{{background:#1f2335}}
.schema-key{{color:#ff9e64;min-width:50px;text-align:right;margin-right:12px}}
.schema-name{{color:#c0caf5;flex:1}}
.schema-cat{{color:#565f89;font-size:11px;min-width:80px;text-align:right}}
#statsModal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center}}
#statsModal.open{{display:flex}}
.stat-section{{margin-bottom:16px}}
.stat-section h3{{font-size:12px;color:#7aa2f7;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #3b4261}}
.stat-row{{display:flex;justify-content:space-between;padding:2px 0;font-size:12px}}
.stat-row .sk{{color:#9aa5ce}}.stat-row .sv{{color:#c0caf5;font-weight:500}}
.stat-bar{{display:flex;align-items:center;gap:8px;padding:2px 0;font-size:11px}}
.stat-bar .bar{{height:14px;border-radius:3px;min-width:2px}}
.stat-bar .bl{{color:#9aa5ce;min-width:90px}}.stat-bar .bv{{color:#565f89;min-width:30px;text-align:right}}
.stat-warn{{color:#ffa94d;font-size:12px;padding:4px 0}}
.stat-hot{{color:#ff6b6b;font-weight:600}}
.stat-row.hot .sv{{color:#ff6b6b;font-weight:700}}
.stat-row.hot .sk::after{{content:'🔥';margin-left:4px}}
#chartTip{{display:none;position:fixed;background:#1a1b26;border:1px solid #3b4261;color:#c0caf5;padding:6px 10px;border-radius:4px;font-size:11px;pointer-events:none;z-index:200;max-width:260px;line-height:1.4}}
#chartTip .ct-label{{color:#7aa2f7;font-weight:600}}
#chartTip .ct-desc{{color:#9aa5ce;margin-top:2px}}
#ctx{{display:none;position:fixed;background:#24283b;border:1px solid #3b4261;border-radius:6px;padding:4px 0;z-index:50;min-width:180px;box-shadow:0 4px 16px rgba(0,0,0,.4)}}
#ctx.open{{display:block}}
.ctx-item{{padding:6px 14px;font-size:12px;color:#c0caf5;cursor:pointer}}
.ctx-item:hover{{background:#3b4261}}
.ctx-sep{{border-top:1px solid #3b4261;margin:2px 0}}
#breadcrumb{{position:absolute;top:44px;left:12px;display:flex;gap:4px;z-index:5;align-items:center}}
#breadcrumb .bc{{background:rgba(36,40,59,.9);border:1px solid #3b4261;color:#9aa5ce;padding:3px 8px;border-radius:4px;font-size:11px;cursor:pointer}}
#breadcrumb .bc:hover{{background:#3b4261;color:#c0caf5}}
</style></head><body>
<div id="app">
<div id="left">
<canvas id="cv"></canvas>
<div id="toolbar">
<button class="tbtn" id="zfit">Fit</button>
<button class="tbtn" id="zin">+</button>
<button class="tbtn" id="zout">−</button>
<button class="tbtn" id="goRoot">Root</button>
<button class="tbtn" id="goArtboard">Artboard</button>
<button class="tbtn" id="goTimeline">Timeline</button>
<button class="tbtn" id="goStateMachine">StateMachine</button>
<button class="tbtn" id="schemaBtn">Schema</button>
<button class="tbtn" id="statsBtn">📊 Stats</button>
</div>
<div id="breadcrumb"></div>
<div id="ctx">
<div class="ctx-item" id="ctxFocus">Focus on this subtree</div>
<div class="ctx-item" id="ctxExpand">Expand children</div>
<div class="ctx-item" id="ctxCollapse">Collapse children</div>
<div class="ctx-sep"></div>
<div class="ctx-item" id="ctxReset">Show full tree</div>
</div>
<div id="info">{h(filename)} &nbsp;|&nbsp; v{header["majorVersion"]}.{header["minorVersion"]} &nbsp;|&nbsp; {len(objects)} objects</div>
<div id="hint">Scroll to zoom · Drag to pan · Click node to select · Drag node to move</div>
<div id="legend">{"".join(f'<span class="lg-item"><span class="lg-dot" style="background:{v}"></span>{c}</span>' for c, v in cat_colors.items())}</div>
</div>
<button id="ptoggle">◀</button>
<div id="panel">
<div id="phdr"><h2>Properties</h2><div class="sub">Click a node to inspect</div>
<div style="display:flex;gap:6px;margin-top:8px"><input type="text" id="psearch" placeholder="Filter properties..." style="flex:1;background:#1a1b26;border:1px solid #3b4261;color:#c0caf5;padding:4px 8px;border-radius:4px;font:inherit;font-size:11px;outline:none"><button class="tbtn" id="keyToggle" style="font-size:10px;padding:3px 8px">Show Keys</button></div>
</div>
<div id="pbody"><div id="empty">← Select a node</div></div>
</div>
</div>
<div id="statsModal"><div style="background:#24283b;border:1px solid #3b4261;border-radius:8px;width:700px;max-height:80vh;display:flex;flex-direction:column;overflow:hidden">
<div style="padding:12px 16px;border-bottom:1px solid #3b4261;display:flex;align-items:center"><h2 style="font-size:14px;color:#7aa2f7;flex:1">📊 Performance Stats</h2><button class="close" id="statsClose" style="background:none;border:none;color:#565f89;font-size:18px;cursor:pointer">&times;</button></div>
<div id="statsBody" style="flex:1;overflow-y:auto;padding:16px"></div>
</div></div>
<div id="chartTip"></div>
<div id="modal"><div id="modal-box">
<div id="modal-hdr"><h2>Rive Schema Reference</h2><button class="close" id="modalClose">&times;</button></div>
<div class="tab-bar"><span class="tab active" data-tab="types">Type Keys</span><span class="tab" data-tab="props">Property Keys</span></div>
<input type="text" id="modal-search" placeholder="Search by key number or name..." autocomplete="off">
<div id="modal-body"></div>
</div></div>
<script>
const T={tree_json};
const CC={colors_json};

// ── Layout: compute x,y for each node ──
const NODES=[];const EDGES=[];
const X_GAP=44,Y_GAP=64,R=14;
let layoutW=0,layoutH=0;

function layoutTree(){{
  let xCounter=0;
  // measure: count leaf descendants (width in leaf units)
  function measure(n,depth){{
    n._d=depth;
    if(n.ch.length===0){{n._w=1;n._leaf=true}}
    else{{n._w=0;for(const c of n.ch){{measure(c,depth+1);n._w+=c._w}}}}
  }}
  // position: top-down, x spread by leaves, y by depth
  function position(n,xStart){{
    const y=n._d*Y_GAP+R+30;
    if(n._leaf){{
      const x=xStart*X_GAP+R+30;
      n._x=x;n._y=y;
      NODES.push(n);
      return xStart+1;
    }}
    let cur=xStart;
    for(const c of n.ch){{
      cur=position(c,cur);
      EDGES.push({{from:n,to:c}});
    }}
    const firstX=n.ch[0]._x;
    const lastX=n.ch[n.ch.length-1]._x;
    n._x=(firstX+lastX)/2;n._y=y;
    NODES.push(n);
    return cur;
  }}
  let total=0;
  for(const r of T){{measure(r,0);total+=r._w}}
  let cur=0;
  for(const r of T)cur=position(r,cur);
  for(const nd of NODES){{if(nd._x>layoutW)layoutW=nd._x;if(nd._y>layoutH)layoutH=nd._y}}
  layoutW+=R+40;layoutH+=R+40;
}}
// Initial layout done by relayout() after all code is loaded

// ── Canvas rendering ──
const cv=document.getElementById('cv');
const ctx=cv.getContext('2d');
let W,HH;
let camX=0,camY=0,zoom=1;
let selNode=null;
let linkedSet=new Set();
let showLinks=false; // only show dashed lines while mouse is down on a node

function resize(){{W=cv.parentElement.clientWidth;HH=cv.parentElement.clientHeight;cv.width=W*devicePixelRatio;cv.height=HH*devicePixelRatio;cv.style.width=W+'px';cv.style.height=HH+'px';draw()}}
window.addEventListener('resize',resize);

function toScreen(x,y){{return[(x-camX)*zoom+W/2,(y-camY)*zoom+HH/2]}}
function toWorld(sx,sy){{return[(sx-W/2)/zoom+camX,(sy-HH/2)/zoom+camY]}}

function draw(){{
  const dpr=devicePixelRatio;
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,W,HH);
  ctx.save();
  ctx.translate(W/2,HH/2);
  ctx.scale(zoom,zoom);
  ctx.translate(-camX,-camY);

  // Edges - vertical curves (parent above, child below)
  ctx.strokeStyle='#3b4261';ctx.lineWidth=1.2/zoom;
  for(const e of EDGES){{
    const my=(e.from._y+e.to._y)/2;
    ctx.beginPath();
    ctx.moveTo(e.from._x,e.from._y+R);
    ctx.bezierCurveTo(e.from._x,my,e.to._x,my,e.to._x,e.to._y-R);
    ctx.stroke();
  }}

  // Nodes
  const fontSize=Math.max(9,Math.min(12,11/zoom));
  ctx.textAlign='center';ctx.textBaseline='top';
  for(const nd of NODES){{
    const col=CC[nd.cat]||CC.other;
    const isSel=selNode&&selNode.i===nd.i;
    const isLinked=showLinks&&linkedSet.has(nd.i);

    // Highlight ring for linked nodes (only while mouse down)
    if(isLinked){{
      ctx.beginPath();ctx.arc(nd._x,nd._y,R+5/zoom,0,Math.PI*2);
      ctx.strokeStyle='#ff9e64';ctx.lineWidth=2.5/zoom;ctx.setLineDash([]);ctx.stroke();
    }}

    // Circle
    ctx.beginPath();ctx.arc(nd._x,nd._y,R,0,Math.PI*2);
    ctx.fillStyle=isSel?'#ffffff':isLinked?'#ff9e64':col;ctx.fill();
    if(isSel){{ctx.strokeStyle=col;ctx.lineWidth=3/zoom;ctx.setLineDash([]);ctx.stroke()}}

    // Label below circle
    ctx.font=`${{fontSize}}px -apple-system,BlinkMacSystemFont,sans-serif`;
    const label=nd.nm||nd.tn;
    ctx.fillStyle=isSel?'#ffffff':isLinked?'#ff9e64':'#c0caf5';
    ctx.fillText(label,nd._x,nd._y+R+4);

    // Expand/collapse indicator for nodes with children
    if(nd.ch.length>0){{
      const collapsed=collapsedSet.has(nd.i);
      const bx=nd._x,by=nd._y+R;
      const bs=5/Math.max(zoom,0.3);
      ctx.fillStyle='#3b4261';
      ctx.beginPath();ctx.arc(bx,by,bs+1,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle='#9aa5ce';ctx.lineWidth=1.2/zoom;
      // horizontal line (minus)
      ctx.beginPath();ctx.moveTo(bx-bs*0.6,by);ctx.lineTo(bx+bs*0.6,by);ctx.stroke();
      if(collapsed){{
        // vertical line (plus)
        ctx.beginPath();ctx.moveTo(bx,by-bs*0.6);ctx.lineTo(bx,by+bs*0.6);ctx.stroke();
      }}
    }}
  }}

  // Dashed lines from selected node to linked nodes (only while mouse down)
  if(showLinks&&selNode&&linkedSet.size>0){{
    ctx.strokeStyle='#ff9e64';ctx.lineWidth=2/zoom;
    ctx.setLineDash([6/zoom,4/zoom]);
    for(const nd of NODES){{
      if(!linkedSet.has(nd.i))continue;
      ctx.beginPath();
      ctx.moveTo(selNode._x,selNode._y);
      ctx.lineTo(nd._x,nd._y);
      ctx.stroke();
    }}
    ctx.setLineDash([]);
  }}

  ctx.restore();
}}

// ── Interaction ──
let dragging=false,dragX,dragY;
let dragNode=null; // node being dragged

function hitTest(sx,sy){{
  const rect=cv.getBoundingClientRect();
  const [wx,wy]=toWorld(sx-rect.left,sy-rect.top);
  let hit=null,bestD=R*1.8;
  for(const nd of NODES){{
    const dx=nd._x-wx,dy=nd._y-wy,d=Math.sqrt(dx*dx+dy*dy);
    if(d<bestD){{bestD=d;hit=nd}}
  }}
  return hit;
}}

function selectNode(nd){{
  selNode=nd;
  linkedSet.clear();
  if(nd){{
    for(const p of nd.props){{
      if(p.link!=null)linkedSet.add(p.link);
    }}
  }}
}}

let didDrag=false;

cv.addEventListener('mousedown',e=>{{
  if(e.button!==0)return;
  dragX=e.clientX;dragY=e.clientY;
  didDrag=false;
  const hit=hitTest(e.clientX,e.clientY);
  if(hit){{
    dragNode=hit;
    selectNode(hit);
    showLinks=linkedSet.size>0;
    showPanel(hit);
    cv.style.cursor='move';
  }}else{{
    dragging=true;
    cv.classList.add('grabbing');
  }}
  draw();
}});

window.addEventListener('mousemove',e=>{{
  if(dragNode){{
    didDrag=true;
    dragNode._x+=(e.clientX-dragX)/zoom;
    dragNode._y+=(e.clientY-dragY)/zoom;
    dragX=e.clientX;dragY=e.clientY;
    draw();
  }}else if(dragging){{
    didDrag=true;
    camX-=(e.clientX-dragX)/zoom;camY-=(e.clientY-dragY)/zoom;
    dragX=e.clientX;dragY=e.clientY;
    draw();
  }}
}});

window.addEventListener('mouseup',e=>{{
  dragNode=null;
  dragging=false;
  showLinks=false;
  cv.style.cursor='grab';
  cv.classList.remove('grabbing');
  draw();
}});

cv.addEventListener('wheel',e=>{{
  e.preventDefault();
  const rect=cv.getBoundingClientRect();
  const mx=e.clientX-rect.left,my=e.clientY-rect.top;
  const [wx,wy]=toWorld(mx,my);
  const factor=e.deltaY<0?1.15:1/1.15;
  zoom=Math.max(0.05,Math.min(8,zoom*factor));
  camX=wx-(mx-W/2)/zoom;camY=wy-(my-HH/2)/zoom;
  draw();
}},{{passive:false}});

cv.addEventListener('click',e=>{{
  if(didDrag)return;
  const hit=hitTest(e.clientX,e.clientY);
  selectNode(hit);
  draw();
  showPanel(hit);
}});

cv.addEventListener('dblclick',e=>{{
  const hit=hitTest(e.clientX,e.clientY);
  if(hit&&hit.ch.length>0){{
    if(collapsedSet.has(hit.i))collapsedSet.delete(hit.i);
    else collapsedSet.add(hit.i);
    relayout();
    // Re-center on the node after relayout
    selectNode(hit);
    camX=hit._x;camY=hit._y;
    draw();showPanel(hit);
  }}
}});

function fitView(){{
  if(!NODES.length)return;
  let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
  for(const n of NODES){{if(n._x<x0)x0=n._x;if(n._y<y0)y0=n._y;if(n._x>x1)x1=n._x;if(n._y>y1)y1=n._y}}
  const pw=x1-x0+200,ph=y1-y0+100;
  camX=(x0+x1)/2;camY=(y0+y1)/2;
  zoom=Math.min(W/pw,HH/ph,2);
  draw();
}}

document.getElementById('zfit').onclick=fitView;
document.getElementById('zin').onclick=()=>{{zoom=Math.min(8,zoom*1.3);draw()}};
document.getElementById('zout').onclick=()=>{{zoom=Math.max(0.05,zoom/1.3);draw()}};

// ── Panel ──
function esc(s){{const d=document.createElement('div');d.textContent=String(s);return d.innerHTML}}

function colorSwatch(hex){{
  if(!hex)return'';
  const a=parseInt(hex.substr(1,2),16)/255,r=parseInt(hex.substr(3,2),16),g=parseInt(hex.substr(5,2),16),b=parseInt(hex.substr(7,2),16);
  return`<span class="csw" style="background:rgba(${{r}},${{g}},${{b}},${{a.toFixed(2)}})"></span>`;
}}

let showKeys=false;
let panelFilter='';
let currentPanelNode=null;

function showPanel(nd){{
  currentPanelNode=nd;
  document.getElementById('psearch').value=panelFilter;
  renderPanel();
}}

function renderPanel(){{
  const nd=currentPanelNode;
  const body=document.getElementById('pbody');
  if(!nd){{body.innerHTML='<div id="empty">\u2190 Select a node</div>';return}}
  const pf=panelFilter.toLowerCase();
  const col=CC[nd.cat]||CC.other;
  let h=`<div class="pg"><h3>Object</h3>`;
  h+=`<div class="pp"><span class="pk">Type <span class="tip" title="Object type name from Rive schema (typeKey=${{nd.tk}})">?</span></span><span class="pv" style="color:${{col}}">${{esc(nd.tn)}}</span></div>`;
  if(nd.nm)h+=`<div class="pp"><span class="pk">Name <span class="tip" title="Component name set in the Rive editor">?</span></span><span class="pv s">${{esc(nd.nm)}}</span></div>`;
  h+=`<div class="pp"><span class="pk">Index <span class="tip" title="Global object index in the .riv file (sequential from 0)">?</span></span><span class="pv n">#${{nd.i}}</span></div>`;
  h+=`<div class="pp"><span class="pk">TypeKey <span class="tip" title="Numeric type identifier used in the binary format">?</span></span><span class="pv n">${{nd.tk}}</span></div>`;
  h+=`<div class="pp"><span class="pk">Offset <span class="tip" title="Byte offset of this object in the .riv file">?</span></span><span class="pv n">${{nd.off}}</span></div>`;
  h+=`<div class="pp"><span class="pk">Category <span class="tip" title="Functional category: structure, shape, paint, animation, statemachine, asset, etc.">?</span></span><span class="pv">${{esc(nd.cat)}}</span></div>`;
  h+=`<div class="pp"><span class="pk">Children <span class="tip" title="Number of direct child objects in the hierarchy tree">?</span></span><span class="pv n">${{nd.ch.length}}</span></div>`;
  h+=`</div>`;
  if(nd.props.length){{
    const filtered=pf?nd.props.filter(p=>(p.n+' '+p.v+' '+p.k).toLowerCase().includes(pf)):nd.props;
    h+=`<div class="pg"><h3>Properties (${{filtered.length}}${{pf?' / '+nd.props.length:''}})</h3>`;
    for(const p of filtered){{
      const vc=p.t===1?'s':p.t===5?'b':p.t===3?'c':'n';
      let valHtml=colorSwatch(p.rc)+esc(p.v);
      if(p.link!=null){{
        valHtml=`<a href="#" onclick="navigateTo(${{p.link}});return false" style="color:#7aa2f7;text-decoration:underline;cursor:pointer">${{valHtml}}</a>`;
      }}
      const tip=p.desc?`<span class="tip" title="${{esc(p.desc)}}">?</span>`:'';
      const keyTag=showKeys?`<span style="color:#565f89;font-size:10px;margin-left:2px">key=${{p.k}}</span>`:'';
      h+=`<div class="pp"><span class="pk">${{esc(p.n)}} <span style="color:#3b4261;font-size:10px">${{p.tl}}</span>${{keyTag}}${{tip}}</span><span class="pv ${{vc}}">${{valHtml}}</span></div>`;
    }}
    h+=`</div>`;
  }}
  if(nd.err)h+=`<div class="pg"><h3>Error</h3><div style="color:#f7768e;font-size:12px">${{esc(nd.err)}}</div></div>`;
  body.innerHTML=h;
}}

document.getElementById('keyToggle').onclick=()=>{{
  showKeys=!showKeys;
  document.getElementById('keyToggle').textContent=showKeys?'Hide Keys':'Show Keys';
  renderPanel();
}};
document.getElementById('psearch').addEventListener('input',e=>{{
  panelFilter=e.target.value;
  renderPanel();
}});

// Navigate to a node by global index: select it, center camera, show panel
function navigateTo(idx){{
  const nd=NODES.find(n=>n.i===idx);
  if(!nd)return;
  selectNode(nd);
  camX=nd._x;camY=nd._y;
  zoom=Math.max(zoom,1);
  draw();
  showPanel(nd);
}}

// Panel toggle
const panel=document.getElementById('panel');
const ptog=document.getElementById('ptoggle');
const info=document.getElementById('info');
const legend=document.getElementById('legend');
ptog.onclick=()=>{{
  panel.classList.toggle('closed');
  ptog.classList.toggle('closed');
  info.classList.toggle('shifted');
  legend.classList.toggle('shifted');
  ptog.textContent=panel.classList.contains('closed')?'\u25B6':'\u25C0';
  setTimeout(()=>{{resize()}},220);
}};

// init calls moved to end of script

// ── Subtree focus & relayout ──
let focusRoot=null; // null = show full tree, otherwise a tree node to focus on
const allTreeRoots=T;

// Build index: node.i → node (across full tree)
const nodeById={{}};
function indexNodes(n){{nodeById[n.i]=n;n.ch.forEach(indexNodes)}}
T.forEach(indexNodes);

// Collapsed set: nodes whose children are hidden
const collapsedSet=new Set();

function relayout(){{
  NODES.length=0;EDGES.length=0;
  const roots=focusRoot?[focusRoot]:allTreeRoots;
  let xCounter=0;
  function measure(n,depth){{
    n._d=depth;
    const visKids=collapsedSet.has(n.i)?[]:n.ch;
    if(visKids.length===0){{n._w=1;n._leaf=true}}
    else{{n._w=0;n._leaf=false;for(const c of visKids){{measure(c,depth+1);n._w+=c._w}}}}
  }}
  function position(n,xStart){{
    const y=n._d*Y_GAP+R+30;
    const visKids=collapsedSet.has(n.i)?[]:n.ch;
    if(visKids.length===0){{
      n._x=xStart*X_GAP+R+30;n._y=y;
      NODES.push(n);return xStart+1;
    }}
    let cur=xStart;
    for(const c of visKids){{cur=position(c,cur);EDGES.push({{from:n,to:c}})}}
    n._x=(visKids[0]._x+visKids[visKids.length-1]._x)/2;n._y=y;
    NODES.push(n);return cur;
  }}
  let cur=0;
  for(const r of roots){{measure(r,0);cur=position(r,cur)}}
  draw();
}}

function focusOn(nd){{
  focusRoot=nd;
  relayout();
  updateBreadcrumb();
  fitView();
}}

function resetFocus(){{
  focusRoot=null;
  relayout();
  updateBreadcrumb();
  fitView();
}}

// Breadcrumb: show path when focused
function updateBreadcrumb(){{
  const bc=document.getElementById('breadcrumb');
  if(!focusRoot){{bc.innerHTML='';return}}
  // Build path from root to focusRoot
  const path=[];
  function findPath(n,target){{
    if(n.i===target.i){{path.push(n);return true}}
    for(const c of n.ch){{if(findPath(c,target)){{path.unshift(n);return true}}}}
    return false;
  }}
  for(const r of allTreeRoots){{if(findPath(r,focusRoot))break}}
  let h='<span class="bc" onclick="resetFocus()">All</span>';
  for(const n of path){{
    const label=n.nm||n.tn;
    h+=` › <span class="bc" onclick="focusOn(nodeById[${{n.i}}])">${{esc(label)}}</span>`;
  }}
  bc.innerHTML=h;
}}

// Quick navigation buttons
function goToNodeByType(typeName){{
  const nd=NODES.find(n=>n.tn===typeName);
  if(nd){{selectNode(nd);camX=nd._x;camY=nd._y;zoom=Math.max(zoom,0.8);draw();showPanel(nd)}}
}}

document.getElementById('goRoot').onclick=()=>{{
  // Reset to full tree, then center on the root node (Backboard)
  collapsedSet.clear();
  focusRoot=null;
  relayout();
  updateBreadcrumb();
  const root=NODES.find(n=>n.tn==='Backboard')||NODES[0];
  if(root){{selectNode(root);camX=root._x;camY=root._y;zoom=1.5;draw();showPanel(root)}}
}};
document.getElementById('goArtboard').onclick=()=>{{
  // Show overview: collapse all Artboard children, expand top level
  collapsedSet.clear();
  focusRoot=null;
  // Collapse every Artboard's children so only Backboard→Artboard(s) visible
  function walk(n){{
    if(n.tn==='Artboard'){{collapsedSet.add(n.i)}}
    // Also collapse ViewModel children for cleaner overview
    if(n.tn==='ViewModel'){{collapsedSet.add(n.i)}}
    n.ch.forEach(walk);
  }}
  T.forEach(walk);
  relayout();
  updateBreadcrumb();
  fitView();
}};

// Helper: show nodes of a given type with their parents visible, children collapsed
function showTypeOverview(typeName){{
  collapsedSet.clear();
  focusRoot=null;
  // Collapse everything first
  function collapseAll(n){{if(n.ch.length)collapsedSet.add(n.i);n.ch.forEach(collapseAll)}}
  T.forEach(collapseAll);
  // Uncollapse ancestors of target type nodes so they're visible
  function uncollapse(n,ancestors){{
    if(n.tn===typeName){{
      for(const a of ancestors)collapsedSet.delete(a.i);
      // Keep the target itself collapsed (show it but not its children)
      collapsedSet.add(n.i);
    }}
    n.ch.forEach(c=>uncollapse(c,[...ancestors,n]));
  }}
  T.forEach(r=>uncollapse(r,[]));
  relayout();
  updateBreadcrumb();
  fitView();
}}

document.getElementById('goTimeline').onclick=()=>showTypeOverview('LinearAnimation');
document.getElementById('goStateMachine').onclick=()=>showTypeOverview('StateMachine');

// ── Context menu ──
const ctxMenu=document.getElementById('ctx');
let ctxNode=null;

cv.addEventListener('contextmenu',e=>{{
  e.preventDefault();
  const hit=hitTest(e.clientX,e.clientY);
  if(!hit){{ctxMenu.classList.remove('open');return}}
  ctxNode=hit;
  selectNode(hit);draw();showPanel(hit);
  ctxMenu.style.left=e.clientX+'px';ctxMenu.style.top=e.clientY+'px';
  ctxMenu.classList.add('open');
  // Update menu items
  const hasKids=hit.ch.length>0;
  document.getElementById('ctxExpand').style.display=hasKids?'':'none';
  document.getElementById('ctxCollapse').style.display=hasKids?'':'none';
  document.getElementById('ctxFocus').style.display=hasKids?'':'none';
}});

window.addEventListener('click',()=>ctxMenu.classList.remove('open'));

document.getElementById('ctxFocus').onclick=()=>{{
  if(ctxNode)focusOn(ctxNode);
  ctxMenu.classList.remove('open');
}};
document.getElementById('ctxExpand').onclick=()=>{{
  if(ctxNode){{collapsedSet.delete(ctxNode.i);relayout();fitView()}}
  ctxMenu.classList.remove('open');
}};
document.getElementById('ctxCollapse').onclick=()=>{{
  if(ctxNode){{collapsedSet.add(ctxNode.i);relayout();fitView()}}
  ctxMenu.classList.remove('open');
}};
document.getElementById('ctxReset').onclick=()=>{{
  collapsedSet.clear();
  resetFocus();
  ctxMenu.classList.remove('open');
}};

// ── Schema modal ──
const TYPES={json.dumps({int(k): v for k, v in (type_names or {}).items()}, ensure_ascii=False)};
const PROPS={json.dumps({int(k): v for k, v in (prop_names or {}).items()}, ensure_ascii=False)};
const modal=document.getElementById('modal');
let schemaTab='types';

function renderSchema(){{
  const q=document.getElementById('modal-search').value.toLowerCase();
  const body=document.getElementById('modal-body');
  const src=schemaTab==='types'?TYPES:PROPS;
  const entries=Object.entries(src).map(([k,v])=>[parseInt(k),v]).sort((a,b)=>a[0]-b[0]);
  let h='';
  for(const [k,v] of entries){{
    if(q&&!String(k).includes(q)&&!v.toLowerCase().includes(q))continue;
    h+=`<div class="schema-row"><span class="schema-key">${{k}}</span><span class="schema-name">${{esc(v)}}</span></div>`;
  }}
  if(!h)h='<div style="padding:20px;color:#565f89;text-align:center">No matches</div>';
  body.innerHTML=h;
}}

document.getElementById('schemaBtn').onclick=()=>{{modal.classList.add('open');renderSchema()}};
document.getElementById('modalClose').onclick=()=>modal.classList.remove('open');
modal.addEventListener('click',e=>{{if(e.target===modal)modal.classList.remove('open')}});
document.getElementById('modal-search').addEventListener('input',renderSchema);
document.querySelectorAll('.tab').forEach(t=>{{
  t.addEventListener('click',()=>{{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    schemaTab=t.dataset.tab;
    renderSchema();
  }});
}});

// ── Stats modal ──
const STATS={json.dumps(stats or {{}})};
const statsModal=document.getElementById('statsModal');

const HOT={{draws:50,clips:10,meshes:20,maxDepth:15}};
const DESC={{
  Fills:'每个 Fill 对每个 Shape 产生一次绘制调用',
  Strokes:'每个 Stroke 对每个 Shape 产生一次绘制调用',
  Gradients:'渐变需要逐像素插值计算，径向渐变开销更大',
  Clips:'裁剪形状需要额外的模板缓冲区通道',
  Meshes:'网格变形需要每帧计算每个顶点的骨骼权重',
  Images:'每张图片需要一次纹理绑定',
  Bones:'骨骼蒙皮每帧计算顶点变换',
  Layers:'每个层同时播放一个动画，层数=同时插值的动画数',
  Listeners:'每帧对每个监听器做路径命中测试',
  Conditions:'每帧对活跃状态的转换条件求值',
  Inputs:'输入变化触发条件重新求值',
  States:'每层同一时刻只有一个活跃状态',
  Transitions:'状态间的连接，不直接影响性能',
}};

function sr(k,v,hot){{
  const cls=hot?'stat-row hot':'stat-row';
  return'<div class="'+cls+'"><span class="sk">'+esc(String(k))+'</span><span class="sv">'+esc(String(v))+'</span></div>';
}}
function fmtBytes(b){{return b>1048576?(b/1048576).toFixed(1)+'MB':b>1024?(b/1024).toFixed(1)+'KB':b+' B'}}

function renderStats(){{
  const s=STATS;if(!s.file)return;
  const body=document.getElementById('statsBody');
  const cc=CC;
  const sm0=s.summary;
  const stars='\u2605'.repeat(sm0.score)+'\u2606'.repeat(5-sm0.score);
  let h='';

  // Score + File
  h+='<div class="stat-section"><h3>'+stars+' 渲染评分</h3>';
  h+=sr('文件大小',fmtBytes(s.file.size));
  h+=sr('对象数',s.file.objects);
  if(s.file.assetCount)h+=sr('内嵌资源',s.file.assetCount+' 个 ('+fmtBytes(s.file.assetBytes)+', '+(s.file.assetBytes*100/s.file.size|0)+'%)',s.file.assetBytes>1048576);
  h+='</div>';

  // Per-frame summary with donut
  h+='<div class="stat-section"><h3>每帧渲染成本</h3>';
  h+='<div style="display:flex;gap:16px;align-items:center;margin:8px 0">';
  h+='<canvas id="chartRender" width="140" height="140" style="cursor:crosshair"></canvas>';
  h+='<div style="flex:1">';
  h+=sr('Draw calls',sm0.totalDraws+'/帧',sm0.totalDraws>=HOT.draws);
  h+=sr('Clip passes',sm0.totalClips,sm0.totalClips>=HOT.clips);
  h+=sr('Mesh 变形',sm0.totalMeshes,sm0.totalMeshes>=HOT.meshes);
  h+=sr('\u2b50 Image 纹理',sm0.totalImages,sm0.totalImages>0);
  h+=sr('Artboard 背景',sm0.artboardFills+' Fill');
  h+='</div></div></div>';

  // Top Shape costs
  const sc=(s.shapeCosts||[]).filter(c=>c.draws>1||c.clips>0||c.meshes>0||c.bones>0);
  if(sc.length){{
    h+='<div class="stat-section"><h3>\U0001f525 热点 Shape ('+sc.length+' 个有多次绘制/裁剪/Mesh)</h3>';
    h+='<canvas id="chartShapes" width="300" height="'+Math.max(60,Math.min(sc.length,10)*28+20)+'" style="cursor:crosshair"></canvas>';
    h+='</div>';
  }}

  // Render detail breakdown
  const rd=s.renderDetail;
  if(rd){{
    h+='<div class="stat-section"><h3>渲染调用明细</h3>';
    h+='<div style="display:flex;gap:16px;align-items:center;margin:8px 0">';
    h+='<canvas id="chartCalls" width="140" height="140" style="cursor:crosshair"></canvas>';
    h+='<div style="flex:1">';
    h+=sr('drawPath',rd.drawPath);
    h+=sr('clipPath',rd.clipPath);
    if(rd.clipRenderPoints)h+=sr('Clip 渲染点数',rd.clipRenderPoints);
    h+=sr('drawImage',rd.drawImage);
    h+=sr('drawImageMesh',rd.drawImageMesh);
    h+=sr('总调用',rd.totalCalls);
    h+='</div></div>';
    h+=sr('路径总数',rd.totalPaths);
    h+=sr('控制顶点',rd.totalVertices);
    h+=sr('\u2b50 渲染点数',rd.totalRenderPoints||0,true);
    h+=sr('渐变色标',rd.totalGradientStops);
    // Paint breakdown chart
    const pb=rd.paintBreakdown;
    if(pb&&Object.keys(pb).length){{
      h+='<canvas id="chartPaint" width="300" height="'+Math.max(60,Object.keys(pb).length*22+10)+'" style="cursor:crosshair;margin-top:8px"></canvas>';
    }}
    h+='</div>';
  }}

  // Mesh detail
  const md=s.meshDetail;
  // Image detail
  const imgs=s.imageDetail||[];
  if(imgs.length){{
    h+='<div class="stat-section"><h3>\u2b50 Image 纹理 ('+imgs.length+' 次绘制)</h3>';
    for(const img of imgs){{
      const sz=img.width?Math.round(img.width)+'\u00d7'+Math.round(img.height):'未知';
      const dt=img.hasMesh?'drawImageMesh':'drawImage';
      h+='<div class="stat-row hot"><span class="sk">'+esc(img.name)+'</span><span class="sv">'+sz+' '+dt+'</span></div>';
    }}
    h+='</div>';
  }}

  // Mesh detail
  if(md&&md.count){{
    h+='<div class="stat-section"><h3>Mesh 变形</h3>';
    h+=sr('Mesh 数量',md.count);
    h+=sr('Mesh 顶点',md.meshVertices);
    h+=sr('纹理数量',md.textures.length);
    for(const t of md.textures){{
      const sz=t.width?Math.round(t.width)+'\u00d7'+Math.round(t.height):'';
      h+=sr(t.name,sz);
    }}
    h+='</div>';
  }}

  // Feather
  const feathers=s.featherDetail||[];
  if(feathers.length){{
    const ni=feathers.filter(f=>f.inner).length,ms=Math.max(...feathers.map(f=>f.strength));
    const shapes=new Set(feathers.map(f=>f.shapeIndex));
    h+='<div class="stat-section"><h3>Feather 羽化 ('+feathers.length+', '+shapes.size+' Shape)</h3>';
    h+=sr('inner',ni);h+=sr('最大 strength',ms.toFixed(1));
    const heavy=feathers.filter(f=>f.strength>50||(f.pathWidth+f.strength*3)*(f.pathHeight+f.strength*3)>500000).sort((a,b)=>((b.pathWidth+b.strength*3)*(b.pathHeight+b.strength*3))-((a.pathWidth+a.strength*3)*(a.pathHeight+a.strength*3)));
    const show=heavy.length?heavy:feathers.slice().sort((a,b)=>b.strength-a.strength).slice(0,5);
    if(show.length){{
      h+='<div style="margin-top:4px;font-weight:bold;color:#f7768e">\U0001f525 高开销:</div>';
      for(const f of show){{
        const sz=f.pathWidth||f.pathHeight?f.pathWidth+'\u00d7'+f.pathHeight:'?';
        h+=sr('#'+f.shapeIndex+' '+(f.shapeName||'unnamed'),f.paintType+(f.inner?' [inner]':'')+' str='+f.strength.toFixed(0)+' size='+sz+' pts='+f.renderPoints);
      }}
    }}
    h+='</div>';
  }}

  // Animation
  const anims=s.animAnalysis||[];
  if(anims.length){{
    const loopAnims=anims.filter(a=>a.loop==='loop');
    const recalcAnims=anims.filter(a=>a.pathRecalcs&&a.pathRecalcs.length);
    const totalProps=anims.reduce((s,a)=>s+a.propsPerFrame,0);
    const totalRecalcs=recalcAnims.reduce((s,a)=>s+a.pathRecalcs.length,0);
    const topHeavy=anims.slice().sort((a,b)=>b.propsPerFrame-a.propsPerFrame).slice(0,5);

    h+='<div class="stat-section"><h3>动画 ('+anims.length+' 个)</h3>';
    h+=sr('循环动画',loopAnims.length+' / '+anims.length);
    h+=sr('总插值属性',totalProps);
    h+=sr('路径重算动画',recalcAnims.length+(totalRecalcs?' (共 '+totalRecalcs+' 次/帧)':''),recalcAnims.length>0);

    // Top heavy animation chart
    if(topHeavy.length&&topHeavy[0].propsPerFrame>0){{
      h+='<canvas id="chartAnimTop" width="300" height="'+Math.max(60,topHeavy.length*28+10)+'" style="cursor:crosshair;margin-top:8px"></canvas>';
    }}

    if(recalcAnims.length){{
      h+='<div style="margin-top:8px;font-size:11px;color:#ff6b6b">\U0001f525 路径重算明细 (前5)</div>';
      for(const a of recalcAnims.slice(0,5)){{
        const targets=[...new Set(a.pathRecalcs.map(p=>p.target))].slice(0,3).join(', ');
        h+='<div style="padding:2px 0;font-size:11px"><span style="color:#ffa94d">'+esc(a.name)+'</span>: <span style="color:#ff6b6b">'+a.pathRecalcs.length+'次</span> <span style="color:#565f89">→ '+esc(targets)+'</span></div>';
      }}
      if(recalcAnims.length>5)h+='<div style="color:#565f89;font-size:11px">... 还有 '+(recalcAnims.length-5)+' 个</div>';
    }}
    h+='</div>';
  }}

  // State machine - performance priority order
  const sm=s.stateMachine;
  h+='<div class="stat-section"><h3>State Machine ('+sm.count+')</h3>';
  if(sm.count){{
    h+=sr('Layers (concurrent animations)',sm.layers,sm.layers>10);
    h+=sr('Listeners (per-frame hit test)',sm.listeners,sm.listeners>10);
    h+=sr('Conditions',sm.conditions);
    h+=sr('Inputs',sm.inputs);
    h+=sr('States',sm.states);
    h+=sr('Transitions',sm.transitions);
    h+='<canvas id="chartSM" width="300" height="100" style="cursor:crosshair;margin-top:8px"></canvas>';
  }}else h+='<div style="color:#565f89;font-size:12px">无状态机</div>';
  h+='</div>';

  // Distribution
  h+='<div class="stat-section"><h3>对象分布</h3>';
  h+='<div style="display:flex;gap:16px;align-items:center;margin:8px 0">';
  h+='<canvas id="chartDist" width="160" height="160" style="cursor:crosshair"></canvas>';
  h+='<div id="distLegend" style="flex:1;font-size:11px"></div>';
  h+='</div></div>';

  // Warnings
  if(s.warnings&&s.warnings.length){{
    h+='<div class="stat-section"><h3>⚠ 性能警告</h3>';
    for(const w of s.warnings)h+='<div class="stat-warn">• '+esc(w)+'</div>';
    h+='</div>';
  }}

  body.innerHTML=h;
  setTimeout(()=>drawCharts(s,cc),0);
}}
function drawCharts(s,cc){{
  const tip=document.getElementById('chartTip');
  function attachTip(canvas,regions,redrawFn){{
    let hIdx=-1;
    canvas.addEventListener('mousemove',e=>{{
      const rect=canvas.getBoundingClientRect();
      const mx=e.clientX-rect.left,my=e.clientY-rect.top;
      let hit=-1;
      for(let i=0;i<regions.length;i++){{
        const rg=regions[i];
        if(rg.r!==undefined){{
          const dx=mx-rg.cx,dy=my-rg.cy;
          if(Math.sqrt(dx*dx+dy*dy)>rg.r)continue;
          let a=Math.atan2(dy,dx);if(a<-Math.PI/2)a+=Math.PI*2;
          if(a>=rg.startAngle&&a<rg.endAngle){{hit=i;break}}
        }}else if(mx>=rg.x&&mx<=rg.x+rg.w&&my>=rg.y&&my<=rg.y+rg.h){{hit=i;break}}
      }}
      if(hit!==hIdx){{hIdx=hit;if(redrawFn)redrawFn(hIdx)}}
      if(hit>=0){{
        const rg=regions[hit];
        tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-10)+'px';
        tip.innerHTML='<div class="ct-label">'+esc(rg.label)+': '+esc(String(rg.value))+'</div>'+(rg.desc?'<div class="ct-desc">'+esc(rg.desc)+'</div>':'');
      }}else tip.style.display='none';
    }});
    canvas.addEventListener('mouseleave',()=>{{tip.style.display='none';if(hIdx>=0){{hIdx=-1;if(redrawFn)redrawFn(-1)}}}});
  }}
  const sm0=s.summary;
  // Rendering donut
  const rc=document.getElementById('chartRender');
  if(rc){{
    const rData=[['Draw calls',sm0.totalDraws,'#ffa94d'],['Clips',sm0.totalClips,'#f06595'],['Meshes',sm0.totalMeshes,'#da77f2'],['Images',sm0.totalImages,'#748ffc'],['Bones',sm0.totalBones,'#e8590c']].filter(d=>d[1]>0);
    function drawR(hi){{const c=rc.getContext('2d');c.clearRect(0,0,rc.width,rc.height);return drawDonut(c,70,70,55,30,rData,hi)}}
    const regions=drawR(-1);
    attachTip(rc,regions.map(r=>({{...r,desc:DESC[r.label]||''}})),drawR);
  }}
  // Shape cost bars
  const shc=document.getElementById('chartShapes');
  if(shc&&s.shapeCosts){{
    const costs=s.shapeCosts.slice(0,10);
    const maxD=Math.max(...costs.map(c=>c.draws),1);
    const barH=22,gap=6,top=6;
    shc.width=shc.parentElement.clientWidth-32||300;
    shc.height=costs.length*(barH+gap)+top;
    const regions=[];
    function drawSC(hi){{
      const c=shc.getContext('2d');c.clearRect(0,0,shc.width,shc.height);
      c.font='11px -apple-system,sans-serif';regions.length=0;
      costs.forEach((sc,i)=>{{
        const y=top+i*(barH+gap);
        const w=Math.max(sc.draws/maxD*(shc.width-180),4);
        c.fillStyle=i===hi?'#2a2e3f':'#1f2335';c.fillRect(0,y,shc.width,barH);
        c.fillStyle=i===hi?'#ffb070':'#ffa94d';c.fillRect(120,y,w,barH);
        if(sc.clips){{c.fillStyle='#f06595';c.fillRect(120+w,y,12,barH)}}
        c.fillStyle='#9aa5ce';c.textBaseline='middle';c.textAlign='right';
        c.fillText(('#'+sc.index+(sc.name?' '+sc.name:'')).substring(0,16),115,y+barH/2);
        c.textAlign='left';c.fillStyle='#c0caf5';
        c.fillText(sc.draws+' draws'+(sc.clips?' +'+sc.clips+'clip':'')+(sc.meshes?' +mesh':''),125+w+(sc.clips?14:0),y+barH/2);
        const ps=sc.paths.map(p=>p.type+'('+p.mode+')').join(',')||'-';
        regions.push({{x:0,y,w:shc.width,h:barH,label:'#'+sc.index+' '+(sc.name||'Shape'),value:sc.draws+' draws, '+sc.vertices+' verts, '+ps,desc:sc.colors.join(', ')||'-'}});
      }});
    }}
    drawSC(-1);attachTip(shc,regions,drawSC);
  }}
  // State machine bars
  const smc=document.getElementById('chartSM');
  if(smc&&s.stateMachine.count){{
    const sm=s.stateMachine;
    const items=[['Layers',sm.layers,'#da77f2'],['Listeners',sm.listeners,'#ffa94d'],['Conditions',sm.conditions,'#4a9eff'],['Inputs',sm.inputs,'#69db7c'],['States',sm.states,'#748ffc'],['Transitions',sm.transitions,'#565f89']];
    const maxV=Math.max(...items.map(d=>d[1]),1);
    smc.width=smc.parentElement.clientWidth-32||300;
    const barH=14,gap=4,top=4;
    smc.height=items.length*(barH+gap)+top;
    const regions=[];
    function drawSM(hi){{
      const c=smc.getContext('2d');c.clearRect(0,0,smc.width,smc.height);
      c.font='11px -apple-system,sans-serif';regions.length=0;
      items.forEach((d,i)=>{{
        const y=top+i*(barH+gap);const w=Math.max(d[1]/maxV*(smc.width-140),2);
        c.fillStyle=i===hi?lighten(d[2]):d[2];c.fillRect(80,y,w,barH);
        if(i===hi){{c.strokeStyle='#fff';c.lineWidth=1;c.strokeRect(80,y,w,barH)}}
        c.fillStyle='#9aa5ce';c.textBaseline='middle';c.textAlign='right';c.fillText(d[0],75,y+barH/2);
        c.textAlign='left';c.fillStyle='#c0caf5';c.fillText(String(d[1]),85+w,y+barH/2);
        regions.push({{x:0,y,w:smc.width,h:barH,label:d[0],value:d[1],desc:DESC[d[0]]||''}});
      }});
    }}
    drawSM(-1);attachTip(smc,regions,drawSM);
  }}
  // Distribution pie
  const dc=document.getElementById('chartDist');
  if(dc){{
    const dist=s.distribution;
    const dData=Object.entries(dist).map(([cat,cnt])=>[cat,cnt,cc[cat]||cc.other]).filter(d=>d[1]>0);
    const total=dData.reduce((s,d)=>s+d[1],0);
    function drawD(hi){{const c=dc.getContext('2d');c.clearRect(0,0,dc.width,dc.height);return drawDonut(c,80,80,65,35,dData,hi)}}
    const regions=drawD(-1);
    attachTip(dc,regions.map(r=>({{...r,desc:'类别: '+r.label+'，占 '+((r.value/total*100)|0)+'%'}})),drawD);
    const leg=document.getElementById('distLegend');
    if(leg)leg.innerHTML=dData.map(d=>'<div style="display:flex;align-items:center;gap:6px;padding:2px 0"><span style="width:10px;height:10px;border-radius:50%;background:'+d[2]+';flex-shrink:0"></span><span style="color:#9aa5ce;flex:1">'+esc(d[0])+'</span><span style="color:#c0caf5">'+d[1]+' ('+Math.round(d[1]*100/total)+'%)</span></div>').join('');
  }}

  // Render calls donut
  const rcc=document.getElementById('chartCalls');
  if(rcc&&s.renderDetail){{
    const rd=s.renderDetail;
    const cData=[['drawPath',rd.drawPath,'#ffa94d'],['clipPath',rd.clipPath,'#f06595'],['drawImage',rd.drawImage,'#748ffc'],['drawImageMesh',rd.drawImageMesh,'#da77f2']].filter(d=>d[1]>0);
    function drawRC(hi){{const c=rcc.getContext('2d');c.clearRect(0,0,rcc.width,rcc.height);return drawDonut(c,70,70,55,30,cData,hi)}}
    const regions=drawRC(-1);
    attachTip(rcc,regions.map(r=>({{...r,desc:DESC[r.label]||r.label+' 调用'}})),drawRC);
  }}

  // Paint breakdown bars
  const pbc=document.getElementById('chartPaint');
  if(pbc&&s.renderDetail){{
    const pb=s.renderDetail.paintBreakdown;
    const pv=s.renderDetail.paintVertices;
    const pr=s.renderDetail.paintRenderPts||{{}};
    const items=Object.entries(pb).sort((a,b)=>b[1]-a[1]);
    const maxV=Math.max(...items.map(d=>d[1]),1);
    const colors={{'Fill+Solid':'#ffa94d','Fill+Linear':'#da77f2','Fill+Radial':'#f06595','Stroke+Solid':'#ff6b6b','Stroke+Linear':'#748ffc','Stroke+Radial':'#e8590c'}};
    pbc.width=pbc.parentElement.clientWidth-32||300;
    const barH=18,gap=4,top=4;
    pbc.height=items.length*(barH+gap)+top;
    const regions=[];
    function drawPB(hi){{
      const c=pbc.getContext('2d');c.clearRect(0,0,pbc.width,pbc.height);
      c.font='11px -apple-system,sans-serif';regions.length=0;
      items.forEach(([key,cnt],i)=>{{
        const y=top+i*(barH+gap);
        const w=Math.max(cnt/maxV*(pbc.width-240),4);
        const col=colors[key]||'#565f89';
        c.fillStyle=i===hi?lighten(col):col;c.fillRect(110,y,w,barH);
        if(i===hi){{c.strokeStyle='#fff';c.lineWidth=1;c.strokeRect(110,y,w,barH)}}
        c.fillStyle='#9aa5ce';c.textBaseline='middle';c.textAlign='right';
        c.fillText(key,105,y+barH/2);
        c.textAlign='left';c.fillStyle='#c0caf5';
        c.fillText(cnt+'次 '+(pv[key]||0)+'顶点 '+(pr[key]||0)+'渲染点',115+w,y+barH/2);
        regions.push({{x:0,y,w:pbc.width,h:barH,label:key,value:cnt+'次, 控制顶点:'+(pv[key]||0)+', 渲染点:'+(pr[key]||0),desc:key.split('+')[0]+'绘制, '+key.split('+')[1]+'颜色'}});
      }});
    }}
    drawPB(-1);attachTip(pbc,regions,drawPB);
  }}

  // Animation top-5 bar chart
  const atc=document.getElementById('chartAnimTop');
  if(atc&&s.animAnalysis){{
    const topH=s.animAnalysis.slice().sort((a,b)=>b.propsPerFrame-a.propsPerFrame).slice(0,5).filter(a=>a.propsPerFrame>0);
    if(topH.length){{
      const maxP=Math.max(...topH.map(a=>a.propsPerFrame),1);
      atc.width=atc.parentElement.clientWidth-32||300;
      const barH=22,gap=6,top=4;
      atc.height=topH.length*(barH+gap)+top;
      const regions=[];
      function drawAT(hi){{
        const c=atc.getContext('2d');c.clearRect(0,0,atc.width,atc.height);
        c.font='11px -apple-system,sans-serif';regions.length=0;
        topH.forEach((a,i)=>{{
          const y=top+i*(barH+gap);
          const w=Math.max(a.propsPerFrame/maxP*(atc.width-180),4);
          const hasRecalc=a.pathRecalcs&&a.pathRecalcs.length;
          c.fillStyle=i===hi?'#2a2e3f':'#1f2335';c.fillRect(0,y,atc.width,barH);
          c.fillStyle=i===hi?(hasRecalc?'#ff8080':'#95e6a0'):(hasRecalc?'#ff6b6b':'#69db7c');
          c.fillRect(100,y,w,barH);
          c.fillStyle='#9aa5ce';c.textBaseline='middle';c.textAlign='right';
          c.fillText(a.name.substring(0,12),95,y+barH/2);
          c.textAlign='left';c.fillStyle='#c0caf5';
          const rc=hasRecalc?' \U0001f525'+a.pathRecalcs.length:'';
          c.fillText(a.propsPerFrame+'属性/帧 '+a.loop+rc,105+w,y+barH/2);
          regions.push({{x:0,y,w:atc.width,h:barH,label:a.name,value:a.propsPerFrame+'属性/帧 ('+a.loop+')',desc:hasRecalc?'触发'+a.pathRecalcs.length+'次路径重算':'仅变换类属性，无路径重算'}});
        }});
      }}
      drawAT(-1);attachTip(atc,regions,drawAT);
    }}
  }}
}}
function lighten(hex){{
  const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
  return'rgb('+Math.min(r+60,255)+','+Math.min(g+60,255)+','+Math.min(b+60,255)+')';
}}

function drawDonut(c,cx,cy,r,hole,data,highlightIdx){{
  const total=data.reduce((s,d)=>s+d[1],0);
  const regions=[];
  if(!total)return regions;
  let angle=-Math.PI/2;
  data.forEach((d,i)=>{{
    const slice=d[1]/total*Math.PI*2;
    const isHi=i===highlightIdx;
    const dr=isHi?8:0;
    const midA=angle+slice/2;
    const ox=isHi?Math.cos(midA)*6:0,oy=isHi?Math.sin(midA)*6:0;
    c.beginPath();c.moveTo(cx+ox,cy+oy);
    c.arc(cx+ox,cy+oy,r+dr,angle,angle+slice);
    c.closePath();c.fillStyle=isHi?lighten(d[2]):d[2];c.fill();
    if(isHi){{c.strokeStyle='#ffffff';c.lineWidth=2;c.stroke()}}
    regions.push({{cx,cy,r:r+8,startAngle:angle,endAngle:angle+slice,label:d[0],value:d[1]}});
    angle+=slice;
  }});
  c.beginPath();c.arc(cx,cy,hole,0,Math.PI*2);
  c.fillStyle='#24283b';c.fill();
  c.fillStyle='#c0caf5';c.font='bold 16px -apple-system,sans-serif';
  c.textAlign='center';c.textBaseline='middle';
  c.fillText(String(total),cx,cy);
  return regions;
}}

document.getElementById('statsBtn').onclick=()=>{{
  statsModal.classList.add('open');
  renderStats();
}};
document.getElementById('statsClose').onclick=()=>statsModal.classList.remove('open');
statsModal.addEventListener('click',e=>{{if(e.target===statsModal)statsModal.classList.remove('open')}});

// Initial view: Artboard overview (children collapsed) for large files
(function initView(){{
  let total=0;
  function cnt(n){{total++;n.ch.forEach(cnt)}}
  T.forEach(cnt);
  if(total>30){{
    // Auto-collapse Artboard and ViewModel children for overview
    function walk(n){{
      if(n.tn==='Artboard'||n.tn==='ViewModel')collapsedSet.add(n.i);
      n.ch.forEach(walk);
    }}
    T.forEach(walk);
  }}
}})();
relayout();
resize();
setTimeout(fitView,50);
</script></body></html>'''
