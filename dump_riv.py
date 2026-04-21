#!/usr/bin/env python3
"""
Rive (.riv) binary file dumper.
Parses a .riv file and outputs its structure as text or interactive HTML tree.

Usage:
    python3 dump_riv.py <file.riv>                  # text to stdout
    python3 dump_riv.py <file.riv> output.txt       # text to file
    python3 dump_riv.py <file.riv> --html            # HTML to stdout
    python3 dump_riv.py <file.riv> --html out.html   # HTML to file, auto-open
"""
import json, os, struct, sys, html as html_mod, webbrowser

# ── Schema ──

def load_schema():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "riv_schema.json")
    with open(p) as f:
        raw = json.load(f)
    return (
        {int(k): v for k, v in raw["type_names"].items()},
        {int(k): v for k, v in raw["property_fields"].items()},
        {int(k): v for k, v in raw["property_names"].items()},
    )

TYPE_NAMES, BUILTIN_FIELDS, PROP_NAMES = load_schema()
FIELD_LABELS = {0: "uint", 1: "string", 2: "float", 3: "color", 4: "bytes", 5: "bool"}

CAT_MAP = {}
for cat, keys in {
    "structure": [23,1,2,10,11,38,91,13,147,92,93,95,96,97,98,409,420,451,452,513,559],
    "shape": [3,4,7,8,51,52,12,15,16,5,6,34,35,36,14,42,100,107,108,109,111,508],
    "paint": [20,24,18,22,17,19,47,21,506,507,533],
    "animation": [31,27,25,26,29,30,37,84,142,50,450,170,171,28,138,139,163,174,175],
    "statemachine": [53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,145,114,115,116,117,118,121,122,123,124,125,126,168,169,527,528],
    "image_asset": [105,104,100],
    "font_asset": [141],
    "audio_asset": [406,407,422],
    "asset": [99,102,103,106],
    "constraint": [79,80,81,82,83,85,86,87,88,89,90,165,520,521,522,523,524,525],
    "bone": [39,40,41,43,44,45,46],
    "text": [134,135,137,144,158,159,160,161,162,164,546,547],
    "viewmodel": [426,427,428,429,430,431,432,433,434,435,436,437,438,439,440,441,442,443,444,445,448,449,501,502,509,510,511,512],
    "databind": [9,446,447,471,472,473,474,475,488,489,490,498,499,500,503,504,514,515,516,517,519,530,531,532,534,535,536,537,538,539,540,541,542,543,544,545],
}.items():
    for k in keys:
        CAT_MAP[k] = cat

# ViewModel property typeKeys (all subclasses of ViewModelProperty)
VM_PROPERTY_TYPES = {430,431,434,436,439,440,443,448,502,509,511}
# ViewModelInstance value typeKeys (all subclasses of ViewModelInstanceValue)
VM_INSTANCE_VALUE_TYPES = {426,428,432,433,441,442,444,449,501}
# ViewModelInstance typeKey
VM_INSTANCE_TYPE = 437

# ── Property descriptions for tooltip ──
PROP_DESCS = {
    4: "Component name in the editor",
    5: "Index of parent component within the Artboard (Artboard=0)",
    7: "Width of Artboard or LayoutComponent",
    8: "Height of Artboard or LayoutComponent",
    9: "X position relative to Artboard origin",
    10: "Y position relative to Artboard origin",
    11: "Artboard origin X (0=left, 0.5=center, 1=right)",
    12: "Artboard origin Y (0=top, 0.5=center, 1=bottom)",
    13: "Local X position",
    14: "Local Y position",
    15: "Rotation in radians",
    16: "Scale factor on X axis (1.0 = 100%)",
    17: "Scale factor on Y axis (1.0 = 100%)",
    18: "Opacity (0.0=transparent, 1.0=opaque)",
    20: "Width of parametric path (Ellipse/Rectangle/etc)",
    21: "Height of parametric path",
    23: "Blend mode: 0=srcOver, 3=multiply, 14=screen, etc",
    24: "Vertex X coordinate in local path space",
    25: "Vertex Y coordinate in local path space",
    37: "SolidColor ARGB value",
    38: "GradientStop/KeyFrameColor ARGB value",
    39: "GradientStop position along gradient (0.0 to 1.0)",
    40: "Fill rule: 0=nonZero, 1=evenOdd",
    42: "Gradient start X in local space",
    33: "Gradient start Y in local space",
    34: "Gradient end X in local space",
    35: "Gradient end Y in local space",
    46: "Gradient opacity (0.0 to 1.0)",
    47: "Stroke thickness in pixels",
    48: "Stroke line cap: 0=butt, 1=round, 2=square",
    49: "Stroke line join: 0=miter, 1=round, 2=bevel",
    51: "KeyedObject: component index within Artboard being animated",
    53: "KeyedProperty: property key being animated (e.g. 15=rotation)",
    56: "Animation frames per second",
    57: "Animation duration in frames",
    58: "Animation playback speed multiplier",
    59: "Loop mode: 0=oneShot, 1=loop, 2=pingPong",
    67: "Keyframe position in frames (default 0 if omitted)",
    68: "Interpolation: 0=hold, 1=linear, 2=cubic",
    69: "ID of custom cubic interpolator",
    70: "Keyframe float value (default 0.0 if omitted)",
    84: "Incoming tangent rotation in radians (CubicDetachedVertex)",
    85: "Incoming tangent distance (CubicDetachedVertex)",
    86: "Outgoing tangent rotation in radians (CubicDetachedVertex)",
    87: "Outgoing tangent distance (CubicDetachedVertex)",
    88: "KeyFrameColor ARGB value",
    110: "Polygon vertex count",
    125: "Polygon corner radius",
    126: "Star inner radius ratio",
    127: "Star inner radius",
    128: "Path flags (bitfield)",
    149: "Index of LinearAnimation within the Artboard",
    151: "Target state index within the StateMachineLayer",
    152: "StateTransition flags (bitfield)",
    155: "StateMachine input index",
    160: "Exit time in frames (when to trigger transition)",
    165: "Animation ID referenced by AnimationState",
    172: "Constraint strength (0.0 to 1.0)",
    197: "Artboard ID for nested artboard",
    224: "Listener target component index",
    225: "Listener type: 0=enter, 1=exit, 2=down, 3=up, 4=move",
    236: "Default StateMachine index (0-based) for this Artboard",
    549: "ViewModel ID reference",
    554: "ViewModel property ID reference",
    566: "ViewModel ID for this instance",
}

def prop_desc(key):
    return PROP_DESCS.get(key, "")

CAT_COLORS = {
    "structure":"#4a9eff","shape":"#ff6b6b","paint":"#ffa94d","animation":"#69db7c",
    "statemachine":"#da77f2","asset":"#868e96","image_asset":"#e599f7","font_asset":"#66d9e8","audio_asset":"#ffd43b",
    "constraint":"#f06595","bone":"#e8590c",
    "text":"#20c997","viewmodel":"#748ffc","databind":"#c0eb75","other":"#adb5bd",
}

# Import stack nesting: which types nest as children of which parent types
# Based on file.cpp makeImporter() and importStack.makeLatest()
STACK_CHILDREN = {
    23: {1,105,141,406,102},  # Backboard -> Artboard, ImageAsset, FontAsset, AudioAsset, Folder
    1: {31,53,25,26},  # Artboard -> LinearAnimation, StateMachine, KeyedObject, KeyedProperty
    31: {25},          # LinearAnimation -> KeyedObject
    25: {26},          # KeyedObject -> KeyedProperty
    26: {30,37,84,142,50,450,170,171,29},  # KeyedProperty -> KeyFrame*
    53: {57,56,58,59,114},  # StateMachine -> Layer, Number, Bool, Trigger, Listener
    57: {60,61,62,63,64,73,76,527,528,145},  # Layer -> States
    61: {65,78,74,75,77,169},  # AnimationState -> Transition, BlendAnimation*, FireEvent
    62: {65,78,169},   # AnyState -> Transition, FireEvent
    63: {65,78,169},   # EntryState -> Transition, FireEvent
    73: {65,78,74,75,77,169},  # BlendStateDirect -> Transition, BlendAnimation*, FireEvent
    76: {65,78,74,75,77,169},  # BlendState1DInput -> Transition, BlendAnimation*, FireEvent
    527: {65,78,74,75,77,169}, # BlendState1D -> Transition, BlendAnimation*, FireEvent
    528: {65,78,74,75,77,169}, # BlendState1DViewModel -> Transition, BlendAnimation*, FireEvent
    65: {67,68,69,70,71,482,497},  # StateTransition -> Conditions
    78: {67,68,69,70,71,482,497},  # BlendStateTransition -> Conditions
    482: {477,478,479,480,481,483,484,485,486,496,505},  # TransitionViewModelCondition -> Comparators
    497: {477,478,479,480,481,483,484,485,486,496,505},  # TransitionArtboardCondition -> Comparators
    114: {115,116,117,118,125,126,168,487},  # Listener -> Actions
    105: {106},        # ImageAsset -> FileAssetContents
    141: {106},        # FontAsset -> FileAssetContents
    406: {106},        # AudioAsset -> FileAssetContents
    102: {105,141,406},# Folder -> Assets
}

# ── Binary readers ──

def read_leb128(data, pos):
    r, s = 0, 0
    while pos < len(data):
        b = data[pos]; pos += 1
        r |= (b & 0x7F) << s
        if (b & 0x80) == 0: return r, pos
        s += 7
    raise ValueError(f"LEB128 overflow at {pos}")

def read_string(data, pos):
    n, pos = read_leb128(data, pos)
    return data[pos:pos+n].decode("utf-8", errors="replace"), pos+n

def read_bytes_val(data, pos):
    n, pos = read_leb128(data, pos)
    return data[pos:pos+n], pos+n

def read_float32(data, pos):
    return struct.unpack_from("<f", data, pos)[0], pos+4

def read_uint32(data, pos):
    return struct.unpack_from("<I", data, pos)[0], pos+4

def type_name(k): return TYPE_NAMES.get(k, f"UnknownType_{k}")
def prop_name(k): return PROP_NAMES.get(k, f"property_{k}")
def get_field_type(pk, toc):
    ft = BUILTIN_FIELDS.get(pk)
    return ft if ft is not None else toc.get(pk)

# ── Parser ──

def parse_riv(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    pos = 0
    if data[0:4] != b"RIVE": raise ValueError("Not a RIVE file")
    pos = 4
    major, pos = read_leb128(data, pos)
    minor, pos = read_leb128(data, pos)
    file_id, pos = read_leb128(data, pos)
    pkeys = []
    while True:
        pk, pos = read_leb128(data, pos)
        if pk == 0: break
        pkeys.append(pk)
    toc = {}; ci, cb = 0, 8
    for pk in pkeys:
        if cb == 8: ci, pos = read_uint32(data, pos); cb = 0
        toc[pk] = (ci >> cb) & 3; cb += 2
    header = {"majorVersion": major, "minorVersion": minor, "fileId": file_id, "tocCount": len(pkeys)}

    objects = []
    while pos < len(data):
        off = pos
        ck, pos = read_leb128(data, pos)
        props, err = [], None
        while pos < len(data):
            pk, pos = read_leb128(data, pos)
            if pk == 0: break
            ft = get_field_type(pk, toc)
            if ft is None: err = f"unknown field type key={pk}"; break
            try:
                if ft == 0: v, pos = read_leb128(data, pos); props.append({"key":pk,"type":ft,"value":v})
                elif ft == 1: v, pos = read_string(data, pos); props.append({"key":pk,"type":ft,"value":v})
                elif ft == 2: v, pos = read_float32(data, pos); props.append({"key":pk,"type":ft,"value":v})
                elif ft == 3: v, pos = read_uint32(data, pos); props.append({"key":pk,"type":ft,"value":v})
                elif ft == 4: v, pos = read_bytes_val(data, pos); props.append({"key":pk,"type":ft,"value":v.hex(),"size":len(v)})
                elif ft == 5: v = data[pos]; pos += 1; props.append({"key":pk,"type":ft,"value":v==1})
            except Exception as e: err = str(e); break
        objects.append({
            "index": len(objects), "offset": off, "typeKey": ck,
            "typeName": type_name(ck), "category": CAT_MAP.get(ck, "other"),
            "properties": props, "error": err,
            "name": next((p["value"] for p in props if prop_name(p["key"])=="name" and p["type"]==1), None),
            "parentId": next((p["value"] for p in props if prop_name(p["key"])=="parentId" and p["type"]==0), None),
        })
    return header, objects, os.path.basename(filepath)

# ── Tree builder ──

def build_tree(objects):
    """Build hierarchical tree from flat object list.
    Returns list of root tree nodes. Each node: {obj, children: [...]}
    """
    nodes = [{"obj": o, "children": []} for o in objects]

    # Phase 1: Find artboard boundaries
    # Objects are grouped: Backboard, then for each Artboard: components, animations, state machines
    artboard_ranges = []  # (artboard_obj_idx, start_of_children, end_exclusive)
    for i, o in enumerate(objects):
        if o["typeName"] == "Artboard":
            artboard_ranges.append([i, i+1, len(objects)])
    # Close ranges
    for j in range(len(artboard_ranges)-1):
        artboard_ranges[j][2] = artboard_ranges[j+1][0]

    # Phase 2: For each artboard, build component tree via parentId
    # Two-pass: first register all component indices, then link parent-child.
    # This handles cases where a child appears before its parent in the file
    # (e.g., SolidColor before its parent Fill).
    for ab_idx, start, end in artboard_ranges:
        comp_idx_to_node = {0: nodes[ab_idx]}
        comp_counter = 1
        comp_end = start  # track where components end
        for i in range(start, end):
            if objects[i]["parentId"] is not None:
                comp_idx_to_node[comp_counter] = nodes[i]
                comp_counter += 1
                comp_end = i + 1
            else:
                break

        # Second pass: link children to parents
        for cidx, node in comp_idx_to_node.items():
            if cidx == 0:
                continue
            pid = node["obj"]["parentId"]
            parent_node = comp_idx_to_node.get(pid)
            if parent_node:
                parent_node["children"].append(node)
            else:
                nodes[ab_idx]["children"].append(node)

        i = comp_end

        # Phase 3: Remaining objects use import-stack nesting
        # Use a stack to track current nesting context
        stack = [nodes[ab_idx]]  # start with artboard as context
        while i < end:
            o = objects[i]
            tk = o["typeKey"]
            # Pop stack until we find a parent that can contain this type
            placed = False
            for depth in range(len(stack)-1, -1, -1):
                parent_tk = stack[depth]["obj"]["typeKey"]
                allowed = STACK_CHILDREN.get(parent_tk, set())
                if tk in allowed:
                    stack[depth]["children"].append(nodes[i])
                    # This node becomes the new stack top (trim stack above)
                    stack = stack[:depth+1]
                    stack.append(nodes[i])
                    placed = True
                    break
            if not placed:
                # Fallback: attach to artboard
                nodes[ab_idx]["children"].append(nodes[i])
                stack = [nodes[ab_idx], nodes[i]]
            i += 1

    # Phase 3: Build top-level tree
    # Backboard is root, artboards are its children
    roots = []
    backboard = None
    backboard_idx = None
    for i, o in enumerate(objects):
        if o["typeName"] == "Backboard":
            backboard = nodes[i]
            backboard_idx = i
            roots.append(backboard)
            break

    if backboard:
        for ab_idx, _, _ in artboard_ranges:
            backboard["children"].append(nodes[ab_idx])

        # Phase 3b: Process objects between Backboard and first Artboard/ViewModel
        # These are typically assets (ImageAsset, FontAsset, etc.)
        first_special = len(objects)
        if artboard_ranges:
            first_special = artboard_ranges[0][0]
        # Also check for ViewModels that may appear before artboards
        for i, o in enumerate(objects):
            if o["typeName"] in ("ViewModel", "Artboard") and i > backboard_idx:
                first_special = min(first_special, i)
                break

        stack = [backboard]
        for i in range(backboard_idx + 1, first_special):
            o = objects[i]
            tk = o["typeKey"]
            placed = False
            for depth in range(len(stack)-1, -1, -1):
                parent_tk = stack[depth]["obj"]["typeKey"]
                allowed = STACK_CHILDREN.get(parent_tk, set())
                if tk in allowed:
                    stack[depth]["children"].append(nodes[i])
                    stack = stack[:depth+1]
                    stack.append(nodes[i])
                    placed = True
                    break
            if not placed:
                backboard["children"].append(nodes[i])
                stack = [backboard, nodes[i]]
    else:
        for ab_idx, _, _ in artboard_ranges:
            roots.append(nodes[ab_idx])

    # Collect any orphan top-level objects (viewmodels, enums outside artboards)
    attached = set()
    def mark(n):
        attached.add(n["obj"]["index"])
        for c in n["children"]: mark(c)
    for r in roots: mark(r)

    # Phase 4: Build ViewModel trees
    # ViewModel → ViewModelProperty* (children), ViewModelInstance (children)
    # ViewModelInstance → ViewModelInstanceValue* (children)
    vm_nodes = []
    vm_stack = []  # stack of (node, typeKey)
    for n in nodes:
        if n["obj"]["index"] in attached:
            continue
        tk = n["obj"]["typeKey"]
        if tk == 435:  # ViewModel
            vm_stack = [n]
            vm_nodes.append(n)
            attached.add(n["obj"]["index"])
        elif tk in VM_PROPERTY_TYPES and vm_stack:
            # ViewModelProperty → child of ViewModel
            vm_stack[0]["children"].append(n)
            attached.add(n["obj"]["index"])
        elif tk == VM_INSTANCE_TYPE and vm_stack:
            # ViewModelInstance → child of ViewModel
            vm_stack[0]["children"].append(n)
            vm_stack = [vm_stack[0], n]
            attached.add(n["obj"]["index"])
        elif tk in VM_INSTANCE_VALUE_TYPES and len(vm_stack) >= 2:
            # ViewModelInstanceValue → child of ViewModelInstance
            vm_stack[1]["children"].append(n)
            attached.add(n["obj"]["index"])
        # Also handle unknown types that have parentId and viewModelPropertyId
        # (these are likely new VM-related types)
        elif n["obj"]["parentId"] is not None and len(vm_stack) >= 2:
            has_vm_prop_id = any(prop_name(p["key"]) == "viewModelPropertyId" for p in n["obj"]["properties"])
            if has_vm_prop_id:
                vm_stack[1]["children"].append(n)
                attached.add(n["obj"]["index"])

    for vn in vm_nodes:
        if backboard:
            backboard["children"].append(vn)
        else:
            roots.append(vn)

    # Remaining orphans
    for n in nodes:
        if n["obj"]["index"] not in attached:
            roots.append(n)

    return roots

# ── Cross-reference resolver ──

def resolve_refs(objects, tree):
    """Add human-readable annotations and target links for objectId, propertyKey, animationId."""
    # Build artboard-scoped component index → object mapping
    artboard_comp_maps = {}  # artboard_obj_index → {comp_idx: obj}
    current_ab = None
    comp_counter = 0
    for o in objects:
        if o["typeName"] == "Artboard":
            current_ab = o["index"]
            artboard_comp_maps[current_ab] = {0: o}
            comp_counter = 1
        elif current_ab is not None and o["parentId"] is not None:
            artboard_comp_maps[current_ab][comp_counter] = o
            comp_counter += 1
        elif current_ab is not None and o["parentId"] is None and o["typeName"] != "Artboard":
            pass

    obj_to_ab = {}
    current_ab = None
    for o in objects:
        if o["typeName"] == "Artboard":
            current_ab = o["index"]
        if current_ab is not None:
            obj_to_ab[o["index"]] = current_ab

    for o in objects:
        refs = {}       # key → display label string
        ref_links = {}  # key → target object global index (for graph click-to-navigate)
        for p in o["properties"]:
            pn = prop_name(p["key"])
            if pn == "objectId" and p["type"] == 0:
                ab = obj_to_ab.get(o["index"])
                if ab is not None:
                    target = artboard_comp_maps.get(ab, {}).get(p["value"])
                    if target:
                        label = f'#{target["index"]} {target["typeName"]}'
                        if target["name"]:
                            label += f' "{target["name"]}"'
                        refs[p["key"]] = label
                        ref_links[p["key"]] = target["index"]
            if pn == "propertyKey" and p["type"] == 0:
                refs[p["key"]] = prop_name(p["value"])
            if pn == "animationId" and p["type"] == 0:
                ab = obj_to_ab.get(o["index"])
                if ab is not None:
                    anim_idx = 0
                    for o2 in objects:
                        if o2["index"] <= objects[ab]["index"] if ab < len(objects) else False:
                            continue
                        if o2["typeName"] == "LinearAnimation":
                            if anim_idx == p["value"]:
                                label = f'#{o2["index"]} "{o2["name"]}"' if o2["name"] else f"#{o2['index']} animation"
                                refs[p["key"]] = label
                                ref_links[p["key"]] = o2["index"]
                                break
                            anim_idx += 1
        o["_refs"] = refs
        o["_ref_links"] = ref_links

# ── Format helpers ──

def fmt_val(p, refs=None):
    ft, v = p["type"], p["value"]
    # If there's a resolved reference, show the meaningful name directly
    if refs and p["key"] in refs:
        ref = refs[p["key"]]
        if ft == 0:
            return f"{ref} ({v})"
        return ref
    if ft == 0: return str(v)
    elif ft == 1: return f'"{v}"'
    elif ft == 2: return str(v)
    elif ft == 3: return f"#{v:08X}"
    elif ft == 4: s = v[:64]; return f"bytes[{p['size']}]={s}{'...' if len(v)>64 else ''}"
    elif ft == 5: return "true" if v else "false"
    return str(v)

# ── Text output ──

def dump_text(header, objects, filename, output=None):
    out = output or sys.stdout
    out.write(f"=== RIVE File: {filename} ===\n")
    out.write(f"Version: {header['majorVersion']}.{header['minorVersion']}\n")
    out.write(f"FileId: {header['fileId']}\nTOC: {header['tocCount']}\n\n")

    tree = build_tree(objects)
    resolve_refs(objects, tree)
    def print_node(node, indent=0):
        o = node["obj"]
        pfx = "  " * indent
        label = f" \"{o['name']}\"" if o["name"] else ""
        out.write(f"{pfx}[{o['index']}] {o['typeName']}{label} (typeKey={o['typeKey']}) @{o['offset']}\n")
        refs = o.get("_refs", {})
        for p in o["properties"]:
            out.write(f"{pfx}  {prop_name(p['key'])}: {fmt_val(p, refs)}\n")
        if o["error"]:
            out.write(f"{pfx}  !! {o['error']}\n")
        for c in node["children"]:
            print_node(c, indent+1)
    for r in tree:
        print_node(r)
    out.write(f"\n=== Total: {len(objects)} objects ===\n")

# ── HTML output ──

def dump_html(header, objects, filename):
    tree = build_tree(objects)
    resolve_refs(objects, tree)

    def node_to_json(node):
        o = node["obj"]
        refs = o.get("_refs", {})
        ref_links = o.get("_ref_links", {})
        return {
            "i": o["index"], "off": o["offset"], "tk": o["typeKey"],
            "tn": o["typeName"], "cat": o["category"],
            "nm": o["name"], "err": o["error"],
            "props": [{"k": p["key"], "n": prop_name(p["key"]), "t": p["type"],
                        "tl": FIELD_LABELS.get(p["type"],"?"), "v": fmt_val(p, refs),
                        "rc": f"#{p['value']:08X}" if p["type"]==3 else None,
                        "link": ref_links.get(p["key"]),
                        "desc": prop_desc(p["key"])}
                       for p in o["properties"]],
            "ch": [node_to_json(c) for c in node["children"]],
        }

    tree_json = json.dumps([node_to_json(r) for r in tree])
    colors_json = json.dumps(CAT_COLORS)
    h = html_mod.escape

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{h(filename)} - Rive Viewer</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'SF Mono','Cascadia Code',Consolas,monospace;background:#1a1b26;color:#c0caf5;font-size:13px}}
.hdr{{background:#24283b;padding:14px 20px;border-bottom:1px solid #3b4261;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.hdr h1{{font-size:15px;color:#7aa2f7;font-weight:600}}
.hdr .m{{color:#9aa5ce;font-size:12px}}
.bar{{background:#1f2335;padding:7px 20px;border-bottom:1px solid #3b4261;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.bar input{{background:#24283b;border:1px solid #3b4261;color:#c0caf5;padding:5px 10px;border-radius:4px;font:inherit;font-size:12px;width:240px;outline:none}}
.bar input:focus{{border-color:#7aa2f7}}
.btn{{background:#24283b;border:1px solid #3b4261;color:#9aa5ce;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:12px;font-family:inherit}}
.btn:hover{{background:#3b4261;color:#c0caf5}}
.leg{{display:flex;gap:6px;margin-left:auto;flex-wrap:wrap}}
.leg label{{display:flex;align-items:center;gap:3px;font-size:11px;color:#9aa5ce;cursor:pointer}}
.leg .d{{width:8px;height:8px;border-radius:50%}}
.cnt{{padding:8px 12px;overflow-x:auto}}
.nd{{margin-left:20px}}
.nd>.row{{display:flex;align-items:center;padding:3px 6px;cursor:pointer;border-radius:4px;gap:6px;white-space:nowrap}}
.nd>.row:hover{{background:#24283b}}
.arr{{color:#565f89;font-size:9px;width:12px;text-align:center;transition:transform .15s;flex-shrink:0}}
.arr.open{{transform:rotate(90deg)}}
.arr.leaf{{visibility:hidden}}
.idx{{color:#565f89;font-size:11px;min-width:36px}}
.badge{{padding:1px 7px;border-radius:3px;font-size:11px;font-weight:600;color:#1a1b26}}
.nm{{color:#c0caf5;font-weight:500}}
.meta{{color:#565f89;font-size:11px;margin-left:8px}}
.kids{{display:none}}.kids.open{{display:block}}
.prps{{padding:2px 0 4px 56px;display:none}}.prps.open{{display:block}}
.pr{{display:flex;gap:6px;padding:1px 6px;border-radius:3px;align-items:center}}
.pr:hover{{background:#1f2335}}
.pr .pn{{color:#9aa5ce;min-width:160px}}
.pr .pt{{color:#565f89;font-size:11px;min-width:44px}}
.pr .pv{{color:#c0caf5;word-break:break-all}}
.pv.s{{color:#9ece6a}}.pv.n{{color:#ff9e64}}.pv.b{{color:#bb9af7}}.pv.c{{color:#f7768e}}
.csw{{display:inline-block;width:13px;height:13px;border-radius:2px;border:1px solid #3b4261;vertical-align:middle;margin-right:3px}}
.err{{color:#f7768e;font-style:italic;padding:1px 6px 1px 56px;font-size:12px}}
.hl{{background:#3b4261!important;border-radius:3px}}
.stats{{padding:10px 20px;color:#565f89;font-size:12px;border-top:1px solid #3b4261}}
</style></head><body>
<div class="hdr"><h1>\U0001f4e6 {h(filename)}</h1>
<span class="m">v{header["majorVersion"]}.{header["minorVersion"]} | FileId: {header["fileId"]} | TOC: {header["tocCount"]} | Objects: {len(objects)}</span></div>
<div class="bar">
<input type="text" id="q" placeholder="Search..." autocomplete="off">
<button class="btn" id="ea">Expand All</button>
<button class="btn" id="ca">Collapse All</button>
<button class="btn" id="e2">Expand Level 2</button>
<div class="leg">{" ".join(f'<label data-c="{c}"><span class="d" style="background:{v}"></span>{c}</label>' for c,v in CAT_COLORS.items())}</div>
</div>
<div class="cnt" id="root"></div>
<div class="stats" id="st"></div>
<script>
const T={tree_json};
const CC={colors_json};
const root=document.getElementById('root');
const hiddenCats=new Set();
let query='';

function esc(s){{let d=document.createElement('div');d.textContent=String(s);return d.innerHTML}}

function colorSwatch(hex){{
  if(!hex)return'';
  const a=parseInt(hex.substr(1,2),16)/255,r=parseInt(hex.substr(3,2),16),g=parseInt(hex.substr(5,2),16),b=parseInt(hex.substr(7,2),16);
  return`<span class="csw" style="background:rgba(${{r}},${{g}},${{b}},${{a.toFixed(2)}})"></span>`;
}}

function matchQ(nd){{
  if(!query)return true;
  const s=(nd.tn+' '+(nd.nm||'')+' '+nd.props.map(p=>p.n+' '+p.v).join(' ')).toLowerCase();
  if(s.includes(query))return true;
  return nd.ch.some(c=>matchQ(c));
}}

function renderNode(nd,depth){{
  if(hiddenCats.has(nd.cat))return'';
  if(query&&!matchQ(nd))return'';
  const hasKids=nd.ch.length>0;
  const hasProps=nd.props.length>0;
  const col=CC[nd.cat]||CC.other;
  const open=depth<1;
  let h=`<div class="nd" data-i="${{nd.i}}">`;
  h+=`<div class="row" onclick="tog(${{nd.i}})">`;
  h+=`<span class="arr${{hasKids?'':' leaf'}}${{open?' open':''}}" id="a${{nd.i}}">\u25B6</span>`;
  h+=`<span class="idx">#${{nd.i}}</span>`;
  h+=`<span class="badge" style="background:${{col}}">${{esc(nd.tn)}}</span>`;
  if(nd.nm)h+=`<span class="nm">${{esc(nd.nm)}}</span>`;
  h+=`<span class="meta">@${{nd.off}}</span>`;
  h+=`</div>`;
  if(hasProps){{
    h+=`<div class="prps${{open?' open':''}}" id="p${{nd.i}}">`;
    for(const p of nd.props){{
      const vc=p.t===1?'s':p.t===5?'b':p.t===3?'c':'n';
      h+=`<div class="pr"><span class="pn">${{esc(p.n)}}</span><span class="pt">${{p.tl}}</span><span class="pv ${{vc}}">${{colorSwatch(p.rc)}}${{esc(p.v)}}</span></div>`;
    }}
    h+=`</div>`;
  }}
  if(nd.err)h+=`<div class="err">\u26A0 ${{esc(nd.err)}}</div>`;
  if(hasKids){{
    h+=`<div class="kids${{open?' open':''}}" id="k${{nd.i}}">`;
    for(const c of nd.ch)h+=renderNode(c,depth+1);
    h+=`</div>`;
  }}
  h+=`</div>`;
  return h;
}}

function render(){{
  let h='';
  for(const r of T)h+=renderNode(r,0);
  root.innerHTML=h;
  let total=0;
  function cnt(n){{total++;n.ch.forEach(cnt)}}
  T.forEach(cnt);
  const shown=root.querySelectorAll('.nd').length;
  document.getElementById('st').textContent=`Showing ${{shown}} of ${{total}} objects`;
}}

function tog(i){{
  const k=document.getElementById('k'+i);
  const p=document.getElementById('p'+i);
  const a=document.getElementById('a'+i);
  if(k){{k.classList.toggle('open');a.classList.toggle('open')}}
  if(p)p.classList.toggle('open');
}}

function setAll(open){{
  root.querySelectorAll('.kids').forEach(e=>e.classList.toggle('open',open));
  root.querySelectorAll('.prps').forEach(e=>e.classList.toggle('open',open));
  root.querySelectorAll('.arr:not(.leaf)').forEach(e=>e.classList.toggle('open',open));
}}

function expandLevel(lvl){{
  setAll(false);
  function walk(el,d){{
    if(d>lvl)return;
    const k=el.querySelector(':scope>.kids');
    const p=el.querySelector(':scope>.prps');
    const a=el.querySelector(':scope>.row>.arr');
    if(k){{k.classList.add('open')}}
    if(p&&d===lvl)p.classList.add('open');
    if(a)a.classList.add('open');
    if(k&&d<lvl)k.querySelectorAll(':scope>.nd').forEach(c=>walk(c,d+1));
  }}
  root.querySelectorAll(':scope>.nd').forEach(e=>walk(e,0));
}}

document.getElementById('ea').onclick=()=>setAll(true);
document.getElementById('ca').onclick=()=>setAll(false);
document.getElementById('e2').onclick=()=>expandLevel(2);

let deb;
document.getElementById('q').addEventListener('input',e=>{{
  clearTimeout(deb);
  deb=setTimeout(()=>{{query=e.target.value.toLowerCase();render()}},200);
}});

document.querySelectorAll('.leg label').forEach(lb=>{{
  lb.addEventListener('click',()=>{{
    const c=lb.dataset.c;
    if(hiddenCats.has(c)){{hiddenCats.delete(c);lb.style.opacity=1}}
    else{{hiddenCats.add(c);lb.style.opacity=0.3}}
    render();
  }});
}});

render();
</script></body></html>'''

# ── Stats output ──

def compute_stats(header, objects, filename, filepath, tree):
    """Compute stats dict for both text output and graph embedding."""
    import os as _os
    from collections import Counter
    file_size = _os.path.getsize(filepath)

    def get_prop(o, name):
        for p in o["properties"]:
            if prop_name(p["key"]) == name: return p["value"]
        return None
    def count_type(*names):
        return sum(1 for o in objects if o["typeName"] in names)

    # Embedded assets
    asset_bytes, asset_count = 0, 0
    for o in objects:
        if o["typeName"] == "FileAssetContents":
            for p in o["properties"]:
                if prop_name(p["key"]) == "bytes" and p["type"] == 4:
                    asset_bytes += p.get("size", 0); asset_count += 1

    artboards = [{"name": o["name"] or "unnamed", "width": get_prop(o,"width") or 0, "height": get_prop(o,"height") or 0} for o in objects if o["typeName"] == "Artboard"]

    # ── Per-Shape cost analysis ──
    path_types_param = {"Ellipse","Rectangle","Triangle","Polygon","Star"}
    path_types_free = {"PointsPath"}
    vertex_types = {"StraightVertex","CubicDetachedVertex","CubicAsymmetricVertex","CubicMirroredVertex"}
    color_types = {"SolidColor": "Solid", "LinearGradient": "Linear", "RadialGradient": "Radial"}

    shape_costs = []
    artboard_fills = 0

    # Build parent map for resolving unnamed shapes to nearest named ancestor
    parent_map = {}
    def build_parent_map(n, parent=None):
        parent_map[n["obj"]["index"]] = parent
        for c in n["children"]: build_parent_map(c, n)
    for r in tree: build_parent_map(r)

    # Build artboard component index map (needed for resolving ClippingShape sourceId)
    ab_comp_maps = {}  # artboard_obj_index → {comp_idx: obj}
    _cur_ab = None; _cc = 0
    for o in objects:
        if o["typeName"] == "Artboard":
            _cur_ab = o["index"]; ab_comp_maps[_cur_ab] = {0: o}; _cc = 1
        elif _cur_ab is not None and o["parentId"] is not None:
            ab_comp_maps[_cur_ab][_cc] = o; _cc += 1
        elif _cur_ab is not None and o["parentId"] is None and o["typeName"] != "Artboard":
            pass
    # Map object global index → artboard global index
    _obj_to_ab = {}; _cur_ab = None
    for o in objects:
        if o["typeName"] == "Artboard": _cur_ab = o["index"]
        if _cur_ab is not None: _obj_to_ab[o["index"]] = _cur_ab
    # Build global index → tree node map
    node_by_index = {}
    def _index_nodes(n):
        node_by_index[n["obj"]["index"]] = n
        for c in n["children"]: _index_nodes(c)
    for r in tree: _index_nodes(r)

    def calc_clip_render_pts(source_node):
        """Calculate total render points of all paths under a clip source node."""
        pts = 0
        def _walk(n):
            nonlocal pts
            tn = n["obj"]["typeName"]
            if tn in path_types_param:
                if tn == "Ellipse": pts += 13
                elif tn == "Rectangle":
                    cr = get_prop(n["obj"], "cornerRadiusTL") or get_prop(n["obj"], "cornerRadiusTR") or \
                         get_prop(n["obj"], "cornerRadiusBL") or get_prop(n["obj"], "cornerRadiusBR") or \
                         get_prop(n["obj"], "cornerRadius")
                    pts += 4 * 4 if cr else 4
                elif tn == "Triangle": pts += 3
                elif tn == "Polygon":
                    n_pts = get_prop(n["obj"], "points") or 5
                    cr = get_prop(n["obj"], "cornerRadius")
                    pts += n_pts * 4 if cr else n_pts
                elif tn == "Star":
                    n_pts = (get_prop(n["obj"], "points") or 5) * 2
                    cr = get_prop(n["obj"], "cornerRadius")
                    pts += n_pts * 4 if cr else n_pts
                else: pts += 4
            elif tn in path_types_free:
                rp = 1
                for vc in n["children"]:
                    vtn = vc["obj"]["typeName"]
                    if vtn in vertex_types:
                        if vtn in ("CubicDetachedVertex", "CubicAsymmetricVertex", "CubicMirroredVertex"):
                            rp += 3
                        elif vtn == "StraightVertex" and get_prop(vc["obj"], "radius"):
                            rp += 4
                        else:
                            rp += 1
                pts += rp
            for c in n["children"]: _walk(c)
        _walk(source_node)
        return pts

    def resolve_name(node):
        """Get shape name, or nearest named ancestor's name as fallback."""
        if node["obj"]["name"]:
            return node["obj"]["name"]
        idx = node["obj"]["index"]
        while idx in parent_map and parent_map[idx]:
            p = parent_map[idx]
            if p["obj"]["name"]:
                return p["obj"]["name"] + "/" + node["obj"]["typeName"]
            idx = p["obj"]["index"]
        return ""

    def analyze_shape(node):
        o = node["obj"]
        clips = 0
        clip_render_pts = 0
        paths = []
        vertices = 0
        render_points = 0
        meshes = 0
        bones = 0
        images = 0
        # Detailed paint breakdown: list of {"paint":"Fill"/"Stroke", "color":"Solid"/"Linear"/"Radial", "stops":N}
        paints = []

        for c in node["children"]:
            co = c["obj"]
            tn = co["typeName"]
            if tn in ("Fill", "Stroke"):
                paint_type = tn
                color_type = "Solid"
                stops = 0
                for gc in c["children"]:
                    gtn = gc["obj"]["typeName"]
                    if gtn == "SolidColor":
                        color_type = "Solid"
                    elif gtn == "LinearGradient":
                        color_type = "Linear"
                        stops = sum(1 for ggc in gc["children"] if ggc["obj"]["typeName"] == "GradientStop")
                    elif gtn == "RadialGradient":
                        color_type = "Radial"
                        stops = sum(1 for ggc in gc["children"] if ggc["obj"]["typeName"] == "GradientStop")
                paints.append({"paint": paint_type, "color": color_type, "stops": stops})
            elif tn == "ClippingShape":
                clips += 1
                # Resolve sourceId to calculate clip path render points
                src_id = get_prop(co, "sourceId")
                if src_id is not None:
                    ab = _obj_to_ab.get(o["index"])
                    if ab is not None:
                        src_obj = ab_comp_maps.get(ab, {}).get(src_id)
                        if src_obj:
                            src_node = node_by_index.get(src_obj["index"])
                            if src_node:
                                clip_render_pts += calc_clip_render_pts(src_node)
            elif tn in path_types_param:
                # Estimate RenderPath point count (what actually gets submitted to GPU)
                # Based on rive-runtime Path::buildPath() in src/shapes/path.cpp:
                #   CubicVertex: cubicTo(3 pts)
                #   StraightVertex no radius: lineTo(1 pt)
                #   StraightVertex with radius: lineTo(1) + cubicTo(3) = 4 pts
                # First vertex: moveTo(1) instead of lineTo; close adds line(1) or cubic(3)
                #
                # Ellipse: 4 CubicVertex → move(1)+3*cubic(3)+close_cubic(3) = 13
                # Rectangle no radius: 4 StraightVertex → move(1)+3*line(1) = 4 (close line ignored)
                # Rectangle with radius: each corner → line(1)+cubic(3)=4, first → move(1)+cubic(3)=4
                #   4*4 = 16 (close line ignored)
                # Polygon/Star: same logic, cornerRadius applies to all vertices
                if tn == "Ellipse":
                    ctrl_v, render_pts = 4, 13  # 4 CubicVertex → moveTo+4*cubicTo = 1+12
                elif tn == "Rectangle":
                    # rectangle.cpp: 4 StraightVertex, each with radius from cornerRadiusTL/TR/BL/BR
                    cr = get_prop(co, "cornerRadiusTL") or get_prop(co, "cornerRadiusTR") or \
                         get_prop(co, "cornerRadiusBL") or get_prop(co, "cornerRadiusBR") or \
                         get_prop(co, "cornerRadius")
                    if cr:
                        ctrl_v, render_pts = 4, 4 * 4  # each vertex: line+cubic=4 pts
                    else:
                        ctrl_v, render_pts = 4, 4
                elif tn == "Triangle":
                    ctrl_v, render_pts = 3, 3
                elif tn == "Polygon":
                    # polygon.cpp: each vertex gets cornerRadius()
                    n = get_prop(co, "points") or 5
                    cr = get_prop(co, "cornerRadius")
                    ctrl_v = n
                    render_pts = n * 4 if cr else n
                elif tn == "Star":
                    # star.cpp: each vertex (2*points) gets cornerRadius()
                    n = (get_prop(co, "points") or 5) * 2
                    cr = get_prop(co, "cornerRadius")
                    ctrl_v = n
                    render_pts = n * 4 if cr else n
                else:
                    ctrl_v, render_pts = 4, 4
                paths.append({"type": tn, "mode": "param", "vertices": ctrl_v, "renderPts": render_pts})
                vertices += ctrl_v
                render_points += render_pts
            elif tn in path_types_free:
                vcount = 0
                rpts = 1  # moveTo
                for vc in c["children"]:
                    vtn = vc["obj"]["typeName"]
                    if vtn in vertex_types:
                        vcount += 1
                        if vtn in ("CubicDetachedVertex", "CubicAsymmetricVertex", "CubicMirroredVertex"):
                            rpts += 3  # cubicTo
                        elif vtn == "StraightVertex" and get_prop(vc["obj"], "radius"):
                            rpts += 4  # rounded corner: lineTo(1) + cubicTo(3)
                        else:
                            rpts += 1  # lineTo (StraightVertex)
                paths.append({"type": tn, "mode": "free", "vertices": vcount, "renderPts": rpts})
                vertices += vcount
                render_points += rpts
            elif tn == "Mesh":
                meshes += 1
            elif tn == "Image":
                images += 1

        def count_bones(n):
            b = 0
            for ch in n["children"]:
                if ch["obj"]["typeName"] in ("Bone", "RootBone"): b += 1
                b += count_bones(ch)
            return b
        bones = count_bones(node)

        draws = len(paints)
        colors = [p["color"] for p in paints]

        return {
            "index": o["index"], "name": resolve_name(node),
            "draws": draws, "clips": clips, "clipRenderPoints": clip_render_pts, "paths": paths,
            "vertices": vertices, "renderPoints": render_points, "colors": colors,
            "meshes": meshes, "bones": bones, "images": images,
            "paints": paints,
        }

    def walk_shapes(node):
        nonlocal artboard_fills
        o = node["obj"]
        if o["typeName"] == "Shape":
            shape_costs.append(analyze_shape(node))
            return
        if o["typeName"] == "Artboard":
            for c in node["children"]:
                if c["obj"]["typeName"] == "Fill": artboard_fills += 1
        for c in node["children"]:
            walk_shapes(c)
    for r in tree: walk_shapes(r)

    # Also scan for standalone Image/Mesh/Bone (not inside Shape)
    standalone_images, standalone_meshes, standalone_bones = 0, 0, 0
    standalone_clips, standalone_clip_render_pts = 0, 0
    def walk_standalone(node):
        nonlocal standalone_images, standalone_meshes, standalone_bones, standalone_clips, standalone_clip_render_pts
        tn = node["obj"]["typeName"]
        if tn == "Shape": return  # already counted
        if tn == "Image": standalone_images += 1
        if tn == "Mesh": standalone_meshes += 1
        if tn in ("Bone", "RootBone"): standalone_bones += 1
        if tn == "ClippingShape":
            standalone_clips += 1
            src_id = get_prop(node["obj"], "sourceId")
            if src_id is not None:
                ab = _obj_to_ab.get(node["obj"]["index"])
                if ab is not None:
                    src_obj = ab_comp_maps.get(ab, {}).get(src_id)
                    if src_obj:
                        src_node = node_by_index.get(src_obj["index"])
                        if src_node:
                            standalone_clip_render_pts += calc_clip_render_pts(src_node)
        for c in node["children"]: walk_standalone(c)
    for r in tree: walk_standalone(r)

    # Sort by draw calls descending
    shape_costs.sort(key=lambda s: s["draws"] + s["clips"]*2, reverse=True)
    total_draws = sum(s["draws"] for s in shape_costs) + artboard_fills
    total_clips = sum(s["clips"] for s in shape_costs) + standalone_clips
    total_meshes = sum(s["meshes"] for s in shape_costs) + standalone_meshes
    total_bones = sum(s["bones"] for s in shape_costs) + standalone_bones
    total_images = sum(s["images"] for s in shape_costs) + standalone_images

    # Draw call distribution histogram
    draw_dist = Counter(s["draws"] for s in shape_costs)

    # ── Animation per-frame analysis ──
    # Properties that trigger path recomputation
    path_props = {20,21,24,25,26,31,79,80,81,82,83,84,85,86,87,110,125,126,127,161,162,163}  # width,height,vertex coords,radius,etc
    # Reuse ab_comp_maps built earlier for resolving objectId
    artboard_comp_maps = ab_comp_maps

    anim_analysis = []
    for o in objects:
        if o["typeName"] != "LinearAnimation": continue
        fps = get_prop(o,"fps") or 60; dur = get_prop(o,"duration") or 0
        loop = {0:"oneShot",1:"loop",2:"pingPong"}.get(get_prop(o,"loopValue") or 0, "?")
        props_total, path_recalcs = 0, []
        # Find KeyedObjects in this animation's tree node
        anim_node = next((n for n in _find_nodes(tree, o["index"])), None)
        if anim_node:
            for ko_node in anim_node["children"]:
                if ko_node["obj"]["typeName"] != "KeyedObject": continue
                obj_id = get_prop(ko_node["obj"], "objectId")
                # Resolve target
                ab = next((ab for ab in artboard_comp_maps if True), None)
                target = artboard_comp_maps.get(ab, {}).get(obj_id) if ab is not None else None
                target_name = ""
                if target:
                    target_name = f'#{target["index"]} {target["typeName"]}'
                    if target["name"]: target_name += f' "{target["name"]}"'
                for kp_node in ko_node["children"]:
                    if kp_node["obj"]["typeName"] != "KeyedProperty": continue
                    pk = get_prop(kp_node["obj"], "propertyKey")
                    props_total += 1
                    if pk in path_props:
                        path_recalcs.append({"target": target_name, "prop": prop_name(pk) if pk else "?"})
        anim_analysis.append({
            "name": o["name"] or "unnamed", "fps": fps, "duration": dur, "loop": loop,
            "propsPerFrame": props_total, "pathRecalcs": path_recalcs,
        })

    # State machine
    n_sm = count_type("StateMachine"); n_layers = count_type("StateMachineLayer")
    n_states = count_type("AnimationState","EntryState","ExitState","AnyState","BlendStateDirect","BlendState1DInput","BlendState1DViewModel")
    n_trans = count_type("StateTransition","BlendStateTransition")
    n_cond = count_type("TransitionTriggerCondition","TransitionNumberCondition","TransitionBoolCondition","TransitionViewModelCondition","TransitionArtboardCondition")
    n_listeners = count_type("StateMachineListener")
    n_inputs = count_type("StateMachineNumber","StateMachineBool","StateMachineTrigger")

    # Hierarchy
    max_depth = 0
    def walk_d(node, d):
        nonlocal max_depth
        if d > max_depth: max_depth = d
        for c in node["children"]: walk_d(c, d+1)
    for r in tree: walk_d(r, 0)

    cat_counts = dict(Counter(o["category"] for o in objects).most_common())

    img_assets = [o["name"] or "unnamed" for o in objects if o["typeName"] == "ImageAsset"]
    font_assets = [o["name"] or "unnamed" for o in objects if o["typeName"] == "FontAsset"]
    audio_assets = [o["name"] or "unnamed" for o in objects if o["typeName"] == "AudioAsset"]

    # Warnings
    warnings = []
    total_verts = sum(s["vertices"] for s in shape_costs)
    if total_verts > 500: warnings.append(f"顶点数较多 ({total_verts})，路径计算开销大")
    if total_draws > 50: warnings.append(f"Draw calls 较多 ({total_draws}/帧)，渲染开销大")
    if total_clips > 10: warnings.append(f"裁剪较多 ({total_clips})，stencil 开销大")
    if total_meshes > 20: warnings.append(f"Mesh 较多 ({total_meshes})，蒙皮计算开销大")
    if asset_bytes > 1024*1024: warnings.append(f"内嵌资源较大 ({asset_bytes/1024/1024:.1f}MB)，加载耗时")
    if max_depth > 15: warnings.append(f"层级较深 ({max_depth})，变换链计算开销大")
    any_path_recalc = any(a["pathRecalcs"] for a in anim_analysis)
    if any_path_recalc: warnings.append("存在动画触发路径重算（width/height/顶点坐标变化）")

    # Score
    score = min(5, 1 + (total_draws > 20) + (total_draws > 50) + (total_clips > 5) + (total_meshes > 10) + (any_path_recalc))

    # ── Detailed rendering breakdown ──
    from collections import Counter
    paint_breakdown = Counter()
    paint_vertices = Counter()
    paint_render_pts = Counter()
    total_path_count = 0
    total_path_verts = 0
    total_render_pts = 0
    total_gradient_stops = 0
    for sc in shape_costs:
        total_path_count += len(sc["paths"])
        n_paints = max(len(sc.get("paints", [])), 1)
        total_path_verts += sc["vertices"] * n_paints
        total_render_pts += sc.get("renderPoints", 0) * n_paints
        for p in sc.get("paints", []):
            key = f"{p['paint']}+{p['color']}"
            paint_breakdown[key] += 1
            paint_vertices[key] += sc["vertices"]
            paint_render_pts[key] += sc.get("renderPoints", 0)
            total_gradient_stops += p.get("stops", 0)

    # Add Artboard background paths (1 rect path per artboard fill)
    total_path_count += artboard_fills
    total_render_pts += artboard_fills * 4  # rect = 4 points

    total_clip_render_pts = sum(s.get("clipRenderPoints", 0) for s in shape_costs) + standalone_clip_render_pts

    # ── Feather analysis ──
    # Feather is child of Fill/Stroke, which is child of Shape
    feather_details = []
    shape_cost_map = {sc["index"]: sc for sc in shape_costs}

    def calc_path_bounds(shape_node):
        """Calculate bounding box of all paths under a Shape (local coords)."""
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        for c in shape_node["children"]:
            tn = c["obj"]["typeName"]
            if tn in path_types_param:
                w = get_prop(c["obj"], "width") or 0
                h = get_prop(c["obj"], "height") or 0
                if w or h:
                    min_x = min(min_x, 0); min_y = min(min_y, 0)
                    max_x = max(max_x, w); max_y = max(max_y, h)
            elif tn in path_types_free:
                for vc in c["children"]:
                    if vc["obj"]["typeName"] in vertex_types:
                        vx = get_prop(vc["obj"], "x") or 0
                        vy = get_prop(vc["obj"], "y") or 0
                        min_x = min(min_x, vx); max_x = max(max_x, vx)
                        min_y = min(min_y, vy); max_y = max(max_y, vy)
        if min_x == float('inf'):
            return 0, 0
        return max_x - min_x, max_y - min_y

    def walk_feather(node, shape_node=None, paint_node=None):
        tn = node["obj"]["typeName"]
        if tn == "Shape":
            shape_node = node
        elif tn in ("Fill", "Stroke"):
            paint_node = node
        elif tn == "Feather" and shape_node:
            sc = shape_cost_map.get(shape_node["obj"]["index"], {})
            pw, ph = calc_path_bounds(shape_node)
            feather_details.append({
                "shapeName": shape_node["obj"]["name"] or sc.get("name", ""),
                "shapeIndex": shape_node["obj"]["index"],
                "paintType": paint_node["obj"]["typeName"] if paint_node else "?",
                "strength": get_prop(node["obj"], "strength") or 12.0,
                "inner": get_prop(node["obj"], "inner") or False,
                "paths": len(sc.get("paths", [])),
                "renderPoints": sc.get("renderPoints", 0),
                "pathWidth": round(pw, 1),
                "pathHeight": round(ph, 1),
            })
        for c in node["children"]:
            walk_feather(c, shape_node, paint_node)
    for r in tree: walk_feather(r)

    # Feather warnings
    if feather_details:
        n_feathers = len(feather_details)
        n_inner = sum(1 for f in feather_details if f["inner"])
        high_str = [f for f in feather_details if f["strength"] > 50]
        if n_feathers > 20: warnings.append(f"Feather 较多 ({n_feathers})，模糊渲染开销大")
        if high_str: warnings.append(f"存在高 strength Feather ({len(high_str)} 个 >50)，GPU 模糊开销大")
        if n_inner > 10: warnings.append(f"Inner Feather 较多 ({n_inner})，需额外构建反向路径")

    render_detail = {
        "drawPath": total_draws,
        "clipPath": total_clips,
        "clipRenderPoints": total_clip_render_pts,
        "drawImage": total_images,
        "drawImageMesh": total_meshes,
        "totalCalls": total_draws + total_clips + total_images + total_meshes,
        "totalPaths": total_path_count,
        "totalVertices": total_path_verts,
        "totalRenderPoints": total_render_pts,
        "totalGradientStops": total_gradient_stops,
        "paintBreakdown": dict(paint_breakdown),
        "paintVertices": dict(paint_vertices),
        "paintRenderPts": dict(paint_render_pts),
    }

    # ── Mesh detail ──
    mesh_detail = []
    for o in objects:
        if o["typeName"] == "Mesh":
            # Find parent Image for texture size info
            tri_bytes = None
            for p in o["properties"]:
                if prop_name(p["key"]) == "triangleIndexBytes" and p["type"] == 4:
                    tri_bytes = p.get("size", 0)
            mesh_detail.append({"index": o["index"]})
    # Count mesh vertices
    mesh_verts = sum(1 for o in objects if o["typeName"] in ("MeshVertex", "ContourMeshVertex"))

    # Image/texture info: build asset list index → size map
    asset_list = []  # ordered list of ImageAssets as they appear in file
    for o in objects:
        if o["typeName"] == "ImageAsset":
            w = get_prop(o, "width") or 0
            h = get_prop(o, "height") or 0
            asset_list.append({"name": o["name"] or "unnamed", "width": w, "height": h, "index": o["index"]})

    # Image draw instances (each Image object = 1 drawImage call)
    image_draws = []
    for o in objects:
        if o["typeName"] == "Image":
            asset_ref = get_prop(o, "assetId")  # index into asset_list
            asset_info = asset_list[asset_ref] if asset_ref is not None and asset_ref < len(asset_list) else {}
            name = o["name"] or asset_info.get("name", "unnamed")
            w = asset_info.get("width", 0)
            h = asset_info.get("height", 0)
            image_draws.append({"name": name, "width": w, "height": h, "index": o["index"]})

    # Check tree for Mesh under Image
    for img in image_draws:
        node = next(_find_nodes(tree, img["index"]), None)
        img["hasMesh"] = any(c["obj"]["typeName"] == "Mesh" for c in node["children"]) if node else False

    texture_info = asset_list

    return {
        "file": {"size": file_size, "objects": len(objects), "assetBytes": asset_bytes, "assetCount": asset_count},
        "artboards": artboards,
        "shapeCosts": shape_costs[:20],
        "shapeTotal": len(shape_costs),
        "renderDetail": render_detail,
        "meshDetail": {"count": total_meshes, "meshVertices": mesh_verts, "textures": texture_info},
        "imageDetail": image_draws,
        "featherDetail": feather_details,
        "summary": {
            "totalDraws": total_draws, "totalClips": total_clips,
            "totalMeshes": total_meshes, "totalBones": total_bones,
            "totalImages": total_images, "artboardFills": artboard_fills,
            "drawDist": dict(draw_dist), "score": score,
        },
        "animAnalysis": anim_analysis,
        "stateMachine": {"count": n_sm, "layers": n_layers, "states": n_states,
                          "transitions": n_trans, "conditions": n_cond, "inputs": n_inputs, "listeners": n_listeners},
        "hierarchy": {"maxDepth": max_depth},
        "distribution": cat_counts,
        "assets": {"images": img_assets, "fonts": font_assets, "audio": audio_assets},
        "warnings": warnings,
    }

def _find_nodes(tree, index):
    """Find tree node by object index."""
    for r in tree:
        if r["obj"]["index"] == index: yield r
        for c in r["children"]: yield from _find_nodes([c], index)

def dump_stats(header, objects, filename, filepath, output=None):
    out = output or sys.stdout
    tree = build_tree(objects)
    resolve_refs(objects, tree)
    s = compute_stats(header, objects, filename, filepath, tree)

    stars = "★" * s["summary"]["score"] + "☆" * (5 - s["summary"]["score"])
    out.write(f"{'='*60}\n 性能分析: {filename}  渲染评分: {stars}\n{'='*60}\n\n")

    f = s["file"]
    out.write(f"── 文件 ──\n  大小: {f['size']:,} bytes ({f['size']/1024:.1f} KB)\n")
    out.write(f"  版本: {header['majorVersion']}.{header['minorVersion']}  对象数: {f['objects']}\n")
    if f["assetCount"]: out.write(f"  内嵌资源: {f['assetCount']} 个 ({f['assetBytes']:,} bytes, {f['assetBytes']*100//max(f['size'],1)}%)\n")

    out.write(f"\n── 每帧渲染成本 ──\n")
    sm = s["summary"]
    out.write(f"  Draw calls: {sm['totalDraws']}/帧  Clip: {sm['totalClips']}  Mesh: {sm['totalMeshes']}  Bone: {sm['totalBones']}  Image: {sm['totalImages']}\n")
    if sm["artboardFills"]: out.write(f"  Artboard 背景 Fill: {sm['artboardFills']}\n")
    # Only show Top Shape table when there are interesting differences
    hot_shapes = [sc for sc in s["shapeCosts"] if sc["draws"] > 1 or sc["clips"] > 0 or sc["meshes"] > 0 or sc["bones"] > 0]
    if hot_shapes:
        out.write(f"\n  🔥 Top 热点 Shape ({len(hot_shapes)} 个有多次绘制/裁剪/Mesh):\n")
        out.write(f"  {'Shape':<25s} {'draws':>5s} {'clip':>4s} {'路径':<15s} {'顶点':>4s} {'mesh':>4s} {'bone':>4s} {'颜色'}\n")
        out.write(f"  {'-'*25} {'-'*5} {'-'*4} {'-'*15} {'-'*4} {'-'*4} {'-'*4} {'-'*15}\n")
        for sc in hot_shapes[:10]:
            name = f'#{sc["index"]} {sc["name"]}'[:25]
            path_str = ", ".join(f'{p["type"]}({p["mode"]})' for p in sc["paths"])[:15] or "-"
            color_str = ", ".join(sc["colors"])[:15] or "-"
            out.write(f"  {name:<25s} {sc['draws']:>5d} {sc['clips']:>4d} {path_str:<15s} {sc['vertices']:>4d} {sc['meshes']:>4d} {sc['bones']:>4d} {color_str}\n")
    # Distribution
    dd = sm["drawDist"]
    if dd:
        out.write(f"\n  Draw call 分布: ")
        for k in sorted(dd.keys()):
            out.write(f"{k}次×{dd[k]}个  ")
        out.write("\n")

    # Detailed rendering breakdown
    rd = s["renderDetail"]
    out.write(f"\n── 渲染调用明细 ──\n")
    out.write(f"  drawPath: {rd['drawPath']}  clipPath: {rd['clipPath']}  drawImage: {rd['drawImage']}  drawImageMesh: {rd['drawImageMesh']}  总计: {rd['totalCalls']}\n")
    out.write(f"  路径总数: {rd['totalPaths']}  控制顶点: {rd['totalVertices']}  渲染点数: {rd['totalRenderPoints']}  渐变色标: {rd['totalGradientStops']}\n")
    clip_rp = rd.get("clipRenderPoints", 0)
    if clip_rp:
        out.write(f"  Clip 渲染点数: {clip_rp}\n")
    pb = rd["paintBreakdown"]
    pv = rd["paintVertices"]
    pr = rd.get("paintRenderPts", {})
    if pb:
        out.write(f"\n  绘制类型分布:\n")
        out.write(f"  {'类型':<20s} {'次数':>5s} {'控制顶点':>8s} {'渲染点数':>8s}\n")
        out.write(f"  {'-'*20} {'-'*5} {'-'*8} {'-'*8}\n")
        for key in sorted(pb.keys()):
            out.write(f"  {key:<20s} {pb[key]:>5d} {pv.get(key,0):>8d} {pr.get(key,0):>8d}\n")

    # Image detail
    imgs = s.get("imageDetail", [])
    if imgs:
        out.write(f"\n── 🔥 Image 纹理 ({len(imgs)} 次绘制) ──\n")
        out.write(f"  {'名称':<25s} {'尺寸':>12s} {'类型':<12s}\n")
        out.write(f"  {'-'*25} {'-'*12} {'-'*12}\n")
        for img in imgs:
            size_str = f"{int(img['width'])}×{int(img['height'])}" if img['width'] else "未知"
            draw_type = "drawImageMesh" if img.get("hasMesh") else "drawImage"
            out.write(f"  {img['name']:<25s} {size_str:>12s} {draw_type:<12s}\n")

    # Mesh detail
    md = s["meshDetail"]
    if md["count"]:
        out.write(f"\n── Mesh 变形 ──\n")
        out.write(f"  Mesh 数量: {md['count']}  Mesh 顶点: {md['meshVertices']}  纹理: {len(md['textures'])}\n")
        for t in md["textures"]:
            out.write(f"    纹理: {t['name']} ({int(t.get('width',0))}×{int(t.get('height',0))})\n")

    # Feather detail
    feathers = s.get("featherDetail", [])
    if feathers:
        n_inner = sum(1 for f in feathers if f["inner"])
        max_str = max(f["strength"] for f in feathers)
        # Blur cost ≈ (w + str*3) * (h + str*3) pixels; inner doubles path work
        for f in feathers:
            w, h, st = f["pathWidth"], f["pathHeight"], f["strength"]
            f["_blurArea"] = (w + st * 3) * (h + st * 3) if (w or h) else 0
        total_blur = sum(f["_blurArea"] for f in feathers)
        # Deduplicate by shape for summary
        shape_set = set()
        for f in feathers:
            shape_set.add(f["shapeIndex"])

        out.write(f"\n── Feather 羽化 ({len(feathers)} 个, {len(shape_set)} 个 Shape) ──\n")
        out.write(f"  inner: {n_inner}  最大 strength: {max_str:.1f}\n")

        # Sort by blur area descending, show top heavy ones
        heavy = sorted(feathers, key=lambda f: f["_blurArea"], reverse=True)
        # Show top 10 or those with strength > 50
        top = [f for f in heavy if f["strength"] > 50 or f["_blurArea"] > 500000]
        if not top:
            top = heavy[:5]
        else:
            top = top[:10]
        if top:
            out.write(f"\n  🔥 高开销 Feather (strength>50 或模糊面积大):\n")
            for f in top:
                inner_str = " [inner]" if f["inner"] else ""
                size_str = f"{f['pathWidth']}×{f['pathHeight']}" if f["pathWidth"] or f["pathHeight"] else "?"
                out.write(f"  #{f['shapeIndex']} {f['shapeName'] or 'unnamed'} → {f['paintType']}{inner_str}  str={f['strength']:.0f}  size={size_str}  pts={f['renderPoints']}\n")

    # Animation summary: aggregate, only show problematic ones in detail
    anims = s["animAnalysis"]
    total_anims = len(anims)
    loop_anims = [a for a in anims if a["loop"] == "loop"]
    recalc_anims = [a for a in anims if a["pathRecalcs"]]
    total_props = sum(a["propsPerFrame"] for a in anims)
    total_recalcs = sum(len(a["pathRecalcs"]) for a in anims)
    # Top by props per frame
    top_heavy = sorted(anims, key=lambda a: a["propsPerFrame"], reverse=True)[:5]

    out.write(f"\n── 动画 ({total_anims} 个) ──\n")
    out.write(f"  循环动画: {len(loop_anims)}  总插值属性: {total_props}  路径重算动画: {len(recalc_anims)}\n")
    if top_heavy and top_heavy[0]["propsPerFrame"] > 0:
        out.write(f"\n  Top 5 最重动画 (按每帧插值属性数):\n")
        for a in top_heavy:
            recalc_str = f" 🔥路径重算{len(a['pathRecalcs'])}次" if a["pathRecalcs"] else ""
            out.write(f"    {a['name']}: {a['propsPerFrame']}属性/帧 ({a['duration']}帧 {a['loop']}){recalc_str}\n")
    if recalc_anims:
        out.write(f"\n  🔥 触发路径重算的动画 ({len(recalc_anims)} 个, 共 {total_recalcs} 次/帧):\n")
        for a in recalc_anims[:5]:
            targets = set(pr["target"] for pr in a["pathRecalcs"])
            out.write(f"    {a['name']}: {len(a['pathRecalcs'])}次 → {', '.join(list(targets)[:3])}\n")
        if len(recalc_anims) > 5:
            out.write(f"    ... 还有 {len(recalc_anims)-5} 个\n")

    sm_data = s["stateMachine"]
    out.write(f"\n── State Machine ({sm_data['count']}) ──\n")
    layers_hot = "🔥 " if sm_data['layers'] > 10 else ""
    listen_hot = "🔥 " if sm_data['listeners'] > 10 else ""
    out.write(f"  {layers_hot}Layers (concurrent animations): {sm_data['layers']}\n")
    out.write(f"  {listen_hot}Listeners (per-frame hit test): {sm_data['listeners']}\n")
    out.write(f"  Conditions: {sm_data['conditions']}  Inputs: {sm_data['inputs']}\n")
    out.write(f"  States: {sm_data['states']}  Transitions: {sm_data['transitions']}\n")

    if s["warnings"]:
        out.write(f"\n── ⚠ 性能警告 ──\n")
        for w in s["warnings"]: out.write(f"  • {w}\n")
    out.write("\n")

HELP = """\
dump_riv.py - Rive (.riv) binary file parser and visualizer

Usage:
  python3 dump_riv.py <file.riv>                       Text tree to stdout
  python3 dump_riv.py <file.riv> output.txt             Text tree to file
  python3 dump_riv.py <file.riv> --html                 HTML list to stdout
  python3 dump_riv.py <file.riv> --html output.html     HTML list to file (auto-opens browser)
  python3 dump_riv.py <file.riv> --graph                Graph HTML to stdout
  python3 dump_riv.py <file.riv> --graph output.html    Graph HTML to file (auto-opens browser)
  python3 dump_riv.py <file.riv> --stats                Performance stats to stdout
  python3 dump_riv.py <file.riv> --stats output.txt     Performance stats to file
  python3 dump_riv.py --help                            Show this help

Modes:
  (default)   Indented text tree with cross-references
  --html      Interactive HTML with collapsible tree, search, category filter
  --graph     Canvas-based node graph with pan/zoom, drag, right-click menu,
              property panel, schema reference, and link visualization
  --stats     Performance analysis: rendering complexity, animation/state machine
              metrics, hierarchy depth, object distribution, and warnings

Requires riv_schema.json (and riv_graph.py for --graph) in the same directory.
"""

def main():
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(HELP); sys.exit(0)
    riv_path = args[0]
    html_mode = "--html" in args
    graph_mode = "--graph" in args
    stats_mode = "--stats" in args
    rest = [a for a in args[1:] if a not in ("--html", "--graph", "--stats")]
    out_path = rest[0] if rest else None
    header, objects, filename = parse_riv(riv_path)
    if stats_mode:
        if out_path:
            with open(out_path, "w") as f: dump_stats(header, objects, filename, riv_path, f)
            print(f"Stats written to {out_path}")
        else:
            dump_stats(header, objects, filename, riv_path)
    elif graph_mode:
        from riv_graph import generate_graph_html
        tree = build_tree(objects)
        resolve_refs(objects, tree)
        stats = compute_stats(header, objects, filename, riv_path, tree)
        content = generate_graph_html(header, objects, filename, tree, CAT_COLORS, FIELD_LABELS, prop_name, fmt_val, prop_desc, TYPE_NAMES, PROP_NAMES, stats)
        if out_path:
            with open(out_path, "w") as f: f.write(content)
            print(f"Graph HTML written to {out_path}")
            webbrowser.open("file://" + os.path.abspath(out_path))
        else:
            sys.stdout.write(content)
    elif html_mode:
        content = dump_html(header, objects, filename)
        if out_path:
            with open(out_path, "w") as f: f.write(content)
            print(f"HTML written to {out_path}")
            webbrowser.open("file://" + os.path.abspath(out_path))
        else:
            sys.stdout.write(content)
    else:
        if out_path:
            with open(out_path, "w") as f: dump_text(header, objects, filename, f)
            print(f"Output written to {out_path}")
        else:
            dump_text(header, objects, filename)

if __name__ == "__main__":
    main()
