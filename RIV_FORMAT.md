# Rive (.riv) 二进制文件格式技术文档

## 1. 概述

`.riv` 文件是 [Rive](https://rive.app) 动画工具的运行时二进制格式，用于存储 Artboard、动画、状态机等设计数据。文件采用小端序（Little-Endian），整数大量使用 LEB128 变长编码以压缩体积。

本文档基于 rive-runtime C++ 源码（major version 7）整理。

---

## 2. 文件整体结构

```
┌──────────────────────────────┐
│         File Header          │
├──────────────────────────────┤
│       Object 0               │
├──────────────────────────────┤
│       Object 1               │
├──────────────────────────────┤
│          ...                 │
├──────────────────────────────┤
│       Object N               │
└──────────────────────────────┘
```

文件由一个 **Header** 和紧随其后的 **Object 序列** 组成。Object 之间无分隔符，顺序排列直到文件末尾。

---

## 3. 基础数据类型编码

### 3.1 LEB128 (Little-Endian Base 128)

无符号变长整数编码。每个字节的低 7 位存储数据，最高位（bit 7）为延续标志：
- `1` = 后续还有字节
- `0` = 这是最后一个字节

```
值 624485 的编码:
  624485 = 0b 00100110 00001110 01100101
  编码为: 0xE5 0x8E 0x26 (3 字节)

  字节1: 1_1100101  (0xE5, 继续)
  字节2: 1_0001110  (0x8E, 继续)
  字节3: 0_0100110  (0x26, 结束)
```

### 3.2 基础类型一览

| 类型 | 编码方式 | 大小 | 说明 |
|------|---------|------|------|
| **VarUint** | LEB128 | 1-10 字节 | 无符号变长整数 |
| **Float32** | IEEE 754 LE | 4 字节 | 单精度浮点数 |
| **Uint32** | LE | 4 字节 | 32 位无符号整数 |
| **Byte** | 原始字节 | 1 字节 | 单字节 |
| **String** | VarUint(长度) + UTF-8 字节 | 变长 | 长度前缀字符串 |
| **Bytes** | VarUint(长度) + 原始字节 | 变长 | 长度前缀字节数组 |

---

## 4. File Header

Header 位于文件起始位置，包含魔数、版本信息和属性类型表（TOC）。

### 4.1 结构

```
┌─────────────────────────────────────────────────┐
│ Magic          : 4 bytes = "RIVE" (0x52495645)  │
│ MajorVersion   : VarUint                        │
│ MinorVersion   : VarUint                        │
│ FileId         : VarUint                        │
│ PropertyKeys[] : VarUint 序列, 以 0 结尾         │
│ FieldTypes     : 打包的 2-bit 字段类型数组        │
└─────────────────────────────────────────────────┘
```

### 4.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| Magic | 4 bytes | 固定为 ASCII `"RIVE"` (0x52, 0x49, 0x56, 0x45) |
| MajorVersion | VarUint | 主版本号，当前为 7 |
| MinorVersion | VarUint | 次版本号 |
| FileId | VarUint | 文件标识符，可为 0 |
| PropertyKeys | VarUint[] | 属性键列表，以 `0` 作为终止符 |
| FieldTypes | packed bits | 每个属性键对应的字段类型，2 bit 一组 |

### 4.3 属性类型表 (Property TOC)

TOC 的作用是为**运行时不认识的扩展属性**提供类型信息，使旧版运行时能跳过新版属性而不中断解析。

#### 4.3.1 PropertyKeys — 属性键列表

PropertyKeys 是一个 VarUint 序列，记录了文件中使用到的、**不在运行时内置注册表中的**扩展属性键。

**读取规则：**
1. 循环读取 VarUint
2. 如果读到的值为 `0`，表示列表结束
3. 非零值即为一个属性键

```
读取伪代码:
    propertyKeys = []
    loop:
        key = readVarUint()
        if key == 0:
            break          // 终止符，列表结束
        propertyKeys.append(key)
```

**为什么需要这个列表？**

Rive 编辑器版本不断更新，会引入新的属性。当旧版运行时遇到不认识的属性时，它需要知道该属性占多少字节才能正确跳过，否则后续数据的偏移就全乱了。PropertyKeys 列表配合后面的 FieldTypes，告诉运行时："这些属性你可能不认识，但它们的类型分别是 xxx，你按对应类型跳过即可。"

**示例：** 假设文件中使用了属性键 160、224、225、227、236，而这些都不在运行时的内置注册表中，则 PropertyKeys 的二进制为：

```
A0 01    → 160 (LEB128: 0x20 | 0x01<<7 = 32+128 = 160)
E0 01    → 224
E1 01    → 225
E3 01    → 227
EC 01    → 236
00       → 终止符
```

#### 4.3.2 FieldTypes — 字段类型打包数组

紧跟在 PropertyKeys 终止符之后。为 PropertyKeys 列表中的每个属性键记录其字段类型，使用 2-bit 编码打包进 Uint32 中。

**2-bit fieldIndex 的含义：**

| fieldIndex | 二进制 | 类型 | 读取方式 | 字节数 |
|-----------|--------|------|---------|--------|
| 0 | 00 | uint | LEB128 VarUint | 1~10 |
| 1 | 01 | string | VarUint(长度) + UTF-8 | 变长 |
| 2 | 10 | double | Float32 (4 字节 LE) | 4 |
| 3 | 11 | color | Uint32 (4 字节 LE) | 4 |

**打包规则：**

每 **4 个**属性键的类型打包进一个 Uint32（小端序 4 字节）。每个属性占 2 bit，从最低位开始填充，**只使用低 8 bit**：

```
一个 Uint32 (32 bit) 中的布局:

  bit:  31 .............. 8  7  6  5  4  3  2  1  0
        └── 未使用 (= 0) ──┘ └─┘  └─┘  └─┘  └─┘
                             属性4 属性3 属性2 属性1
```

每处理完 4 个属性（bit 位置到达 8），读取下一个 Uint32。

**读取伪代码（对应源码 `runtime_header.hpp`）：**

```
currentInt = 0
currentBit = 8          // 初始设为 8，强制第一次立即读取新的 Uint32

for each propertyKey in propertyKeys:
    if currentBit == 8:
        currentInt = readUint32()    // 读取 4 字节小端序整数
        currentBit = 0               // 重置 bit 偏移

    fieldIndex = (currentInt >> currentBit) & 0x3   // 取 2 bit
    toc[propertyKey] = fieldIndex                    // 记录到映射表
    currentBit += 2                                  // 移动到下一个槽位
```

**完整示例：** 假设有 5 个属性键，类型分别为 uint、uint、string、float、uint：

```
PropertyKeys: [160, 224, 225, 227, 236]
FieldTypes:   [  0,   0,   1,   2,   0]

第 1 组 (属性 1~4): 读取 Uint32
  属性 160 → fieldIndex=0 (uint)  → bit [1:0] = 00
  属性 224 → fieldIndex=0 (uint)  → bit [3:2] = 00
  属性 225 → fieldIndex=1 (string)→ bit [5:4] = 01
  属性 227 → fieldIndex=2 (float) → bit [7:6] = 10

  Uint32 = 0b ... 00000000_00000000_00000000_10_01_00_00
         = 0x00000090
  写入文件 (小端序): 90 00 00 00

第 2 组 (属性 5): 读取下一个 Uint32
  属性 236 → fieldIndex=0 (uint)  → bit [1:0] = 00

  Uint32 = 0x00000000
  写入文件 (小端序): 00 00 00 00
```

> **为什么每个 Uint32 只用 8 bit？** 源码中 `currentBit` 的重置阈值是 8 而非 32，所以每个 Uint32 只装 4 个属性（4×2=8 bit），高 24 bit 浪费。这简化了实现，而 TOC 通常很小（只包含运行时不认识的扩展属性），浪费可忽略。

#### 4.3.3 TOC 的使用时机

TOC 并非属性类型查找的第一选择。解析对象属性时的查找顺序为：

```
1. 内置注册表 CoreRegistry::propertyFieldId(propertyKey)
   → 编译时写死在运行时代码中，包含 468 个已知属性
   → 能区分 6 种类型: uint / string / float / color / bool / bytes

2. 如果内置注册表返回 -1（不认识），查 Header TOC
   → 从文件头动态读取
   → 只能区分 4 种类型: uint / string / float / color (2-bit 编码)

3. 两处都找不到 → 解析失败，无法跳过该属性
```

这种设计的好处：
- **前向兼容**：新版编辑器导出的文件包含新属性，旧版运行时通过 TOC 知道如何跳过
- **体积优化**：内置属性不需要在每个文件中重复存储类型信息
- **bool 和 bytes 不需要出现在 TOC 中**：它们都在内置注册表中，且 bool 用 readByte (1字节)、bytes 用 readBytes (长度前缀) 读取，与 TOC 的 4 种类型编码无关

---

## 5. Object 序列

Header 之后是连续的 Object 流，直到文件末尾。

### 5.1 单个 Object 结构

```
┌──────────────────────────────────────────┐
│ coreObjectKey : VarUint  (对象类型标识)    │
├──────────────────────────────────────────┤
│ Property 1:                              │
│   propertyKey : VarUint                  │
│   value       : 类型由 propertyKey 决定   │
├──────────────────────────────────────────┤
│ Property 2:                              │
│   propertyKey : VarUint                  │
│   value       : ...                      │
├──────────────────────────────────────────┤
│ ...                                      │
├──────────────────────────────────────────┤
│ Terminator    : VarUint = 0              │
└──────────────────────────────────────────┘
```

### 5.2 解析流程

```
读取 coreObjectKey (VarUint)
循环:
    读取 propertyKey (VarUint)
    如果 propertyKey == 0 → 对象结束，跳出
    查找 propertyKey 的字段类型:
        1) 先查内置注册表 CoreRegistry::propertyFieldId(propertyKey)
        2) 找不到则查 Header 中的 TOC
        3) 都找不到 → 解析失败
    根据字段类型读取 value
```

### 5.3 属性值的 6 种读取方式

| 字段类型 | C++ 方法 | 编码 | 说明 |
|---------|---------|------|------|
| uint (id=0) | `readVarUintAs()` | LEB128 | 无符号整数，也用于枚举值和 ID 引用 |
| string (id=1) | `readString()` | LEB128 长度 + UTF-8 | 字符串 |
| double (id=2) | `readFloat32()` | 4 字节 LE IEEE 754 | 浮点数（名为 double 但实际存储为 float32） |
| color (id=3) | `readUint32()` | 4 字节 LE | ARGB 颜色值，如 `0xFF2F5E72` |
| bool | `readByte()` | 1 字节 | `0x01` = true, `0x00` = false |
| bytes | `readBytes()` | LEB128 长度 + 原始字节 | 二进制数据（如嵌入的资源内容） |

> **关于 bool 和 uint 的区分：** 在 TOC 的 2-bit 编码中，bool 和 uint 共享 fieldIndex=0。但在内置注册表中，运行时通过 `CoreBoolType::deserialize` (readByte) 和 `CoreUintType::deserialize` (readVarUint) 区分它们。TOC 中不会出现 bool 类型的属性（bool 属性都在内置注册表中）。

> **关于 bytes 类型：** bytes 和 string 在 TOC 中共享 fieldIndex=1（都是长度前缀编码）。bytes 类型的属性同样都在内置注册表中。

### 5.4 默认值省略规则

Rive 的序列化有一个重要优化：**属性值等于 C++ 成员变量初始值时，不写入文件**。这意味着解析 .riv 文件时，如果某个对象缺少某个属性，该属性的值就是源码中定义的默认值。

例如一个 GradientStop 对象在文件中可能只有 `parentId`，没有 `colorValue` 和 `position`：

```
[28] GradientStop
  parentId: 10
  (colorValue 省略 → 默认 #FFFFFFFF 白色)
  (position 省略 → 默认 0.0)
```

常见属性的默认值（定义在各 `*_base.hpp` 的成员变量初始化中）：

| 属性 | 默认值 | 说明 |
|------|--------|------|
| x, y | 0.0 | 位置坐标 |
| scaleX, scaleY | 1.0 | 缩放 |
| rotation | 0.0 | 旋转角度 |
| opacity | 1.0 | 不透明度 |
| colorValue (SolidColor) | 0xFFFFFFFF | 白色 |
| colorValue (GradientStop) | 0xFFFFFFFF | 白色 |
| position (GradientStop) | 0.0 | 渐变起始位置 |
| frame (KeyFrame) | 0 | 第 0 帧 |
| value (KeyFrameDouble) | 0.0 | 浮点值 |
| interpolationType | 0 | hold（保持） |
| fillRule | 0 | nonZero |
| isClosed (PointsPath) | false | 开放路径 |
| inRotation, outRotation | 0.0 | 贝塞尔控制点角度 |
| inDistance, outDistance | 0.0 | 贝塞尔控制点距离 |
| thickness (Stroke) | 1.0 | 描边宽度 |

> 这就是为什么有些对象看起来"没有数据"——它们的所有属性恰好都等于默认值。例如渐变的第一个色标通常是白色、位置 0.0，全部省略后只剩 `parentId`。

---

## 6. 对象类型 (coreObjectKey)

每个对象的 `coreObjectKey` 对应一个具体的 Rive 组件类型。以下是主要类型（完整列表见 `riv_schema.json`）：

### 6.1 核心结构

| typeKey | 类型名 | 说明 |
|---------|-------|------|
| 23 | Backboard | 文件根对象，每个文件有且仅有一个 |
| 1 | Artboard | 画板，包含所有可视组件 |
| 2 | Node | 基础节点，具有位置/旋转/缩放 |
| 10 | Component | 组件基类 |
| 11 | ContainerComponent | 容器组件 |

### 6.2 Shape 绘制模型

Shape 是 Rive 的核心绘制容器。它不直接定义几何形状或颜色，而是**组合**子路径和子画法：

```
Shape (绘制容器)
├── Rectangle / Ellipse / PointsPath   ← m_Paths[]   (几何路径，可多个)
├── Fill                                ← m_ShapePaints[] (填充)
│   └── SolidColor / LinearGradient     ← 颜色来源
└── Stroke                              ← m_ShapePaints[] (描边)
    └── SolidColor                      ← 颜色来源
```

渲染时，Shape 遍历所有 Paint（Fill/Stroke），每个 Paint 用所有子路径的合并结果来绘制。因此 **Fill/Stroke 是 Shape 的子节点，不是 Rectangle 的子节点**——一个 Fill 同时应用于 Shape 下的所有路径。

对应源码：`Shape::draw()` 遍历 `m_ShapePaints`，调用 `shapePaint->draw(renderer, pickPath(this), worldTransform())`。

### 6.3 路径类型

Rive 中路径分为两类：

#### 参数化路径（运行时生成顶点）

只存储几何参数，运行时按需计算顶点坐标：

| typeKey | 类型名 | 存储的参数 | 运行时生成 |
|---------|-------|-----------|-----------|
| 4 | Ellipse | width, height | 椭圆近似贝塞尔曲线 |
| 7 | Rectangle | width, height, cornerRadius* | 4 个角点（可带圆角） |
| 8 | Triangle | width, height | 3 个顶点 |
| 51 | Polygon | width, height, points | N 个等分顶点 |
| 52 | Star | width, height, points, innerRadius | 2N 个交替内外顶点 |

**顶点生成采用脏标记机制**：属性变化时调用 `markPathDirty()` 设置 `ComponentDirt::Path`，下次 `Artboard::advance()` 时才重新计算。如果属性没变（如只改了 opacity 或 rotation），路径不会重新生成。

```
属性变化 → markPathDirty() → 设置 ComponentDirt::Path
                                    ↓
Artboard::advance() → Component::update(dirt)
                                    ↓
                      hasDirt(Path)? → 是: 重新计算顶点
                                    → 否: 跳过
```

#### 自由路径（顶点直接存储在文件中）

由编辑器中钢笔工具绘制，每个顶点的坐标和控制点都序列化到 .riv 文件：

| typeKey | 类型名 | 说明 |
|---------|-------|------|
| 12 | Path | 路径基类 |
| 16 | PointsPath | 点路径容器（isClosed 控制是否闭合） |
| 5 | StraightVertex | 直线顶点：x, y, radius（圆角） |
| 6 | CubicDetachedVertex | 独立控制点贝塞尔顶点：x, y, inRotation, inDistance, outRotation, outDistance |
| 34 | CubicAsymmetricVertex | 非对称贝塞尔顶点：rotation, inDistance, outDistance |
| 35 | CubicMirroredVertex | 镜像贝塞尔顶点：rotation, distance（入/出对称） |

自由路径在文件中的结构示例：

```
PointsPath (isClosed=true)
├── CubicDetachedVertex (x=12.17, y=-15.71, inRot=-2.48, inDist=4.26, outRot=0.66, outDist=5.93)
├── CubicDetachedVertex (x=19.87, y=0,      inRot=-1.57, inDist=6.39, outRot=1.57, outDist=10.97)
├── CubicDetachedVertex (x=0,     y=19.87,  inRot=0,     inDist=10.97, outRot=π,   outDist=10.97)
├── CubicDetachedVertex (x=-19.87,y=0,      inRot=1.57,  inDist=10.97, outRot=-1.57,outDist=6.54)
└── CubicDetachedVertex (x=-11.83,y=-15.96, inRot=2.50,  inDist=6.07, outRot=-0.64, outDist=4.12)
```

> 注意：默认值（x=0, y=0, frame=0, value=0.0 等）不会序列化到文件中以节省空间。解析时如果某个属性不存在，应视为其默认值。

#### 控制顶点 vs 渲染点数

路径有两个维度的"点数"：

- **控制顶点**：Rive 对象层面的 PathVertex 数量，影响脏标记更新和动画插值计算
- **渲染点数**：`buildPath()` 生成的 RenderPath 命令中的坐标点总数，**直接影响 GPU 路径填充/描边开销**

| 路径类型 | 控制顶点 | 渲染点数 | 说明 |
|---------|---------|---------|------|
| Rectangle | 4 | 4 | moveTo + 3×lineTo |
| Triangle | 3 | 3 | moveTo + 2×lineTo |
| Ellipse | 4 | 13 | moveTo + 4×cubicTo（每个 cubicTo 3 点） |
| Polygon(N) | N | N | moveTo + (N-1)×lineTo |
| Star(N) | 2N | 2N | moveTo + (2N-1)×lineTo |
| 自由路径(N个CubicVertex) | N | 1+3N | moveTo + N×cubicTo |
| 自由路径(N个StraightVertex) | N | N | moveTo + (N-1)×lineTo |

> **性能分析时应关注渲染点数而非控制顶点数。** 同样 4 个控制顶点，Ellipse 生成 13 个渲染点（4 段三次贝塞尔曲线），Rectangle 只生成 4 个（4 条直线），GPU 开销差 3 倍多。

### 6.4 绘制方式

Fill 和 Stroke 定义如何渲染路径，它们是 Shape 的子节点：

| typeKey | 类型名 | 说明 |
|---------|-------|------|
| 20 | Fill | 填充（子节点为颜色来源） |
| 24 | Stroke | 描边（子节点为颜色来源，额外有 thickness, cap, join） |
| 18 | SolidColor | 纯色（colorValue 属性） |
| 22 | LinearGradient | 线性渐变（startX/Y, endX/Y） |
| 17 | RadialGradient | 径向渐变 |
| 19 | GradientStop | 渐变色标（colorValue, position） |
| 47 | TrimPath | 路径裁剪（start, end, offset, mode） |

颜色来源挂在 Fill/Stroke 下：

```
Fill
└── SolidColor (colorValue=#FF2F5E72)

Stroke (thickness=2.0)
└── LinearGradient (startX=-10, endX=10)
    ├── GradientStop (color=#FFFF0000, position=0.0)
    └── GradientStop (color=#FF0000FF, position=1.0)
```

Artboard 自身也可以有 Fill（作为背景色），此时 Fill 的 parentId 指向 Artboard（组件索引 0）。

### 6.5 动画

| typeKey | 类型名 | 说明 |
|---------|-------|------|
| 31 | LinearAnimation | 时间轴动画（fps, duration, speed, loopValue） |
| 25 | KeyedObject | 关键帧对象引用（objectId 指向 Artboard 内的组件索引） |
| 26 | KeyedProperty | 关键帧属性引用（propertyKey 指向被动画的属性，如 rotation=15） |
| 30 | KeyFrameDouble | 浮点关键帧（frame, value, interpolationType） |
| 37 | KeyFrameColor | 颜色关键帧（frame, value） |
| 84 | KeyFrameBool | 布尔关键帧 |
| 142 | KeyFrameString | 字符串关键帧 |
| 50 | KeyFrameId | ID 关键帧 |

动画数据的层级结构和交叉引用：

```
LinearAnimation "Idle" (fps=60, duration=120, loopValue=1)
├── KeyedObject (objectId=8)          ← 组件索引 8，指向 Artboard 内的某个 Shape
│   ├── KeyedProperty (propertyKey=15)  ← 属性 15 = rotation
│   │   ├── KeyFrameDouble (frame=0, value=0.0)    ← 第 0 帧，旋转 0°
│   │   └── KeyFrameDouble (frame=60, value=6.28)   ← 第 60 帧，旋转 360°
│   └── KeyedProperty (propertyKey=18)  ← 属性 18 = opacity
│       ├── KeyFrameDouble (frame=0, value=1.0)
│       └── KeyFrameDouble (frame=60, value=0.0)
└── KeyedObject (objectId=24)         ← 指向 SolidColor
    └── KeyedProperty (propertyKey=38)  ← 属性 38 = colorValue
        ├── KeyFrameColor (frame=0, value=#FFFF0000)
        └── KeyFrameColor (frame=60, value=#FF0000FF)
```

> **objectId** 是 Artboard 内的组件索引（不是全局对象索引），需要通过组件索引表转换。
>
> **默认值省略**：frame=0 和 value=0.0 等默认值不会序列化到文件中。解析时如果 KeyFrameDouble 没有 frame 属性，表示 frame=0；没有 value 属性，表示 value=0.0。

### 6.6 状态机

| typeKey | 类型名 | 说明 |
|---------|-------|------|
| 53 | StateMachine | 状态机 |
| 57 | StateMachineLayer | 状态机层（每层独立运行一个动画） |
| 56 | StateMachineNumber | 数值输入 |
| 59 | StateMachineBool | 布尔输入 |
| 58 | StateMachineTrigger | 触发器输入 |
| 61 | AnimationState | 动画状态（引用一个 LinearAnimation） |
| 63 | EntryState | 入口状态 |
| 64 | ExitState | 退出状态 |
| 62 | AnyState | 任意状态（可从任何状态转换） |
| 65 | StateTransition | 状态转换 |
| 68 | TransitionTriggerCondition | 触发器转换条件 |
| 70 | TransitionNumberCondition | 数值转换条件 |
| 114 | StateMachineListener | 事件监听器（每帧做命中测试） |

> **性能提示：** Layer 数量 = 最多同时播放的动画数，是状态机最主要的性能指标。Listener 每帧做路径命中测试也有开销。States/Transitions 数量不影响运行时性能。详见 `PERFORMANCE_GUIDE.md`。

### 6.7 资源

| typeKey | 类型名 | 说明 |
|---------|-------|------|
| 105 | ImageAsset | 图片资源（存储 width/height/cdnUrl） |
| 141 | FontAsset | 字体资源 |
| 406 | AudioAsset | 音频资源 |
| 106 | FileAssetContents | 资源内嵌二进制内容（bytes 属性） |
| 100 | Image | 图片绘制实例（引用 ImageAsset，每个产生一次 drawImage 调用） |
| 109 | Mesh | 网格变形（附加在 Image 上，使 drawImage 变为 drawImageMesh） |

> **Image 的两种绘制方式：**
> - **drawImage**：直接绘制纹理，开销较低
> - **drawImageMesh**：Image 下有 Mesh 子节点时，需要每帧计算网格顶点的骨骼蒙皮变换后再绘制，开销较高
>
> 纹理尺寸（ImageAsset 的 width/height）直接影响 GPU 显存占用。

---

## 7. 属性键 (propertyKey)

属性键是全局唯一的整数，每个键值在源码中只定义一次，标识一个特定属性。子类通过继承共享父类的属性键（如 `parentId` 定义在 `ComponentBase` 中，所有组件子类都使用它）。以下是常见属性：

### 7.1 通用属性

| propertyKey | 名称 | 字段类型 | 说明 |
|------------|------|---------|------|
| 4 | name | string | 组件名称 |
| 5 | parentId | uint | 父组件在 Artboard 中的索引 |

### 7.2 变换属性

| propertyKey | 名称 | 字段类型 | 说明 |
|------------|------|---------|------|
| 13 | x | float | X 坐标 |
| 14 | y | float | Y 坐标 |
| 15 | rotation | float | 旋转角度（弧度） |
| 16 | scaleX | float | X 缩放 |
| 17 | scaleY | float | Y 缩放 |
| 18 | opacity | float | 不透明度 (0.0-1.0) |

### 7.3 尺寸属性

| propertyKey | 名称 | 字段类型 | 上下文 |
|------------|------|---------|-------|
| 7 | width | float | Artboard/LayoutComponent |
| 8 | height | float | Artboard/LayoutComponent |
| 20 | width | float | ParametricPath (椭圆/矩形等) |
| 21 | height | float | ParametricPath |

### 7.4 绘制属性

| propertyKey | 名称 | 字段类型 | 说明 |
|------------|------|---------|------|
| 37 | colorValue | color | SolidColor 颜色值 |
| 38 | colorValue | color | GradientStop/KeyFrameColor 颜色值 |
| 39 | position | float | GradientStop 位置 (0.0-1.0) |
| 47 | thickness | float | Stroke 线宽 |
| 40 | fillRule | uint | 填充规则 |

### 7.5 动画属性

| propertyKey | 名称 | 字段类型 | 说明 |
|------------|------|---------|------|
| 56 | fps | uint | 帧率 |
| 57 | duration | uint | 持续时间（帧数） |
| 58 | speed | float | 播放速度 |
| 59 | loopValue | uint | 循环模式 (0=oneShot, 1=loop, 2=pingPong) |
| 67 | frame | uint | 关键帧所在帧号 |
| 68 | interpolationType | uint | 插值类型 |
| 70 | value | float | KeyFrameDouble 的值 |

---

## 8. 对象层级关系

.riv 文件中的对象是**平铺存储**的，但运行时通过两种机制还原出树形层级。文件中对象的排列顺序是固定的：先是可视组件（有 `parentId`），然后是动画和状态机（无 `parentId`）。

### 8.1 机制一：parentId（可视组件）

Artboard 内的可视组件（Node、Shape、Ellipse、Fill、Stroke 等）通过 `parentId` 属性（propertyKey=5）声明父子关系。

`parentId` 的值是**父对象在当前 Artboard 组件列表中的索引**，Artboard 自身是索引 0，后续组件按出现顺序依次编号：

```
对象序列                    组件索引    parentId    含义
─────────────────────────  ────────    ────────    ──────────
Artboard "MyArt"           0           (无)        顶层
  Node "Root"              1           0           父 = Artboard
    Shape                  2           1           父 = Root
      Ellipse              3           2           父 = Shape
      Fill                 4           2           父 = Shape
        SolidColor         5           4           父 = Fill
```

**关键规则：**
- 只有可视组件参与 `parentId` 编号，动画/状态机对象不参与
- `parentId` 是 Artboard 内的局部索引，不是全局对象索引
- 多个 Artboard 各自独立编号

对应源码：`file.cpp` 中 `File::read()` 通过 `importStack` 将带 `parentId` 的对象添加到 Artboard 的组件列表。

### 8.2 机制二：Import Stack（动画/状态机）

动画、状态机等对象**没有 `parentId`**。它们的层级关系由 `file.cpp` 中的 `importStack.makeLatest()` 隐式建立——按类型嵌套规则，后出现的对象自动成为前面特定类型对象的子节点。

嵌套规则（基于 `file.cpp` 中 `makeImporter()` 的 switch-case）：

| 父类型 | 可包含的子类型 |
|-------|-------------|
| Backboard | Artboard |
| Artboard | LinearAnimation, StateMachine |
| LinearAnimation | KeyedObject |
| KeyedObject | KeyedProperty |
| KeyedProperty | KeyFrameDouble, KeyFrameColor, KeyFrameBool, KeyFrameString, KeyFrameId, KeyFrameUint, KeyFrameCallback |
| StateMachine | StateMachineLayer, StateMachineNumber, StateMachineBool, StateMachineTrigger, StateMachineListener |
| StateMachineLayer | EntryState, ExitState, AnyState, AnimationState, BlendStateDirect, BlendState1DInput, BlendState1DViewModel |
| AnimationState / AnyState / EntryState | StateTransition, BlendStateTransition |
| StateTransition | TransitionTriggerCondition, TransitionNumberCondition, TransitionBoolCondition, TransitionViewModelCondition, TransitionArtboardCondition |
| StateMachineListener | ListenerTriggerChange, ListenerBoolChange, ListenerNumberChange, ListenerFireEvent, ListenerAlignTarget, ListenerViewModelChange |

**解析逻辑：** 运行时维护一个类型栈。遇到新对象时，从栈顶向下查找能容纳该类型的父节点，找到后将新对象挂为其子节点，并将栈截断到该层再压入新对象：

```
处理顺序                          栈状态
──────────────────────────────    ──────────────────────────
LinearAnimation "Idle"            [Artboard, LinearAnimation]
  KeyedObject                     [Artboard, LinearAnimation, KeyedObject]
    KeyedProperty                 [.., KeyedObject, KeyedProperty]
      KeyFrameDouble              [.., KeyedProperty, KeyFrameDouble]
      KeyFrameDouble              [.., KeyedProperty, KeyFrameDouble]  ← 替换上一个
    KeyedProperty                 [.., KeyedObject, KeyedProperty]     ← 回退到 KeyedObject 层
      KeyFrameDouble              [.., KeyedProperty, KeyFrameDouble]
  KeyedObject                     [Artboard, LinearAnimation, KeyedObject]  ← 回退到 LinearAnimation 层
StateMachine "SM1"                [Artboard, StateMachine]             ← 回退到 Artboard 层
  StateMachineLayer               [Artboard, StateMachine, Layer]
    AnimationState                [.., Layer, AnimationState]
      StateTransition             [.., AnimationState, Transition]
        TransitionTriggerCondition[.., Transition, Condition]
    EntryState                    [.., Layer, EntryState]              ← 回退到 Layer 层
```

### 8.3 两种机制的切换

在一个 Artboard 的对象序列中，**先出现的是所有可视组件（有 parentId），后出现的是动画和状态机（无 parentId）**。一旦遇到第一个没有 `parentId` 的对象，就从机制一切换到机制二，后续不再回到机制一。

```
Artboard 内的对象序列:

  ┌─ 可视组件区 (parentId 机制) ─┐
  │ Node, Shape, Ellipse, Fill,  │
  │ Stroke, SolidColor, ...      │
  └──────────────────────────────┘
  ┌─ 动画/状态机区 (Stack 机制) ──┐
  │ LinearAnimation, KeyedObject, │
  │ StateMachine, Layer, State,   │
  │ Transition, Listener, ...     │
  └──────────────────────────────┘
```

### 8.4 完整层级示例

```
Backboard
└── Artboard "New Artboard"
    │
    │── [parentId 机制] 可视组件树
    │   └── Node "Root" (parentId=0)
    │       ├── Shape (parentId=1)
    │       │   ├── Ellipse (parentId=2)
    │       │   ├── Fill (parentId=2)
    │       │   │   └── SolidColor (parentId=5)
    │       │   └── Stroke (parentId=2)
    │       │       └── SolidColor (parentId=7)
    │       └── Node "Group" (parentId=1)
    │
    │── [Stack 机制] LinearAnimation "Idle"
    │   ├── KeyedObject (objectId=3)
    │   │   ├── KeyedProperty (propertyKey=18)
    │   │   │   ├── KeyFrameDouble (frame=0)
    │   │   │   └── KeyFrameDouble (frame=25)
    │   │   └── KeyedProperty (propertyKey=13)
    │   │       └── KeyFrameDouble (frame=0)
    │   └── KeyedObject (objectId=12)
    │       └── ...
    │
    └── [Stack 机制] StateMachine "State Machine 1"
        ├── StateMachineTrigger "Pressed"
        ├── StateMachineLayer "Layer 1"
        │   ├── EntryState
        │   │   └── StateTransition (stateToId=0)
        │   ├── AnimationState (animationId=2)
        │   │   └── StateTransition (stateToId=5)
        │   │       └── TransitionTriggerCondition (inputId=0)
        │   ├── AnyState
        │   └── ExitState
        └── StateMachineListener (targetId=3)
            └── ListenerTriggerChange (inputId=0)
```

---

## 9. 解析示例

以下是 `new_file.riv` 文件的实际十六进制及其逐字节解析：

```
偏移  十六进制                              解析
────  ────────────────────────────────────  ──────────────────────────────────

=== File Header ===

0000  52 49 56 45                           Magic: "RIVE"
0004  07                                    MajorVersion: 7 (LEB128)
0005  00                                    MinorVersion: 0 (LEB128)
0006  D4 AC 22                              FileId: 562772 (LEB128)
0009  A0 01                                 PropertyKey[0]: 160 (LEB128)
000B  E0 01                                 PropertyKey[1]: 224 (LEB128)
000D  E1 01                                 PropertyKey[2]: 225 (LEB128)
000F  E3 01                                 PropertyKey[3]: 227 (LEB128)
0011  EC 01                                 PropertyKey[4]: 236 (LEB128)
0013  00                                    PropertyKeys 终止符
0014  00 00 00 00                           FieldTypes Uint32 #1: 0x00000000
                                              160=uint, 224=uint, 225=uint, 227=uint
0018  00 00 00 00                           FieldTypes Uint32 #2: 0x00000000
                                              236=uint
                                            (5个属性, 每4个一组, 需要2个Uint32)

=== Object 0 ===

001C  17                                    coreObjectKey: 23 = Backboard
001D  00                                    propertyKey: 0 → 对象结束 (无属性)

=== Object 1 ===

001E  01                                    coreObjectKey: 1 = Artboard
001F  07                                    propertyKey: 7 (width, float)
0020  00 E5 1B 43                           value: 155.89453125 (Float32 LE)
0024  08                                    propertyKey: 8 (height, float)
0025  00 E5 1B 43                           value: 155.89453125 (Float32 LE)
0029  0B                                    propertyKey: 11 (originX, float)
002A  00 00 00 3F                           value: 0.5 (Float32 LE)
002E  0C                                    propertyKey: 12 (originY, float)
002F  00 00 00 3F                           value: 0.5 (Float32 LE)
0033  EC 01                                 propertyKey: 236 (defaultStateMachineId, uint)
0035  00                                    value: 0 (LEB128)
0036  04                                    propertyKey: 4 (name, string)
0037  0C                                    string length: 12 (LEB128)
0038  4E 65 77 20 41 72 74 62 6F 61 72 64   "New Artboard" (UTF-8)
0044  00                                    propertyKey: 0 → 对象结束
```

**LEB128 解码示例 — FileId 562772：**

```
字节: D4       AC       22
二进制: 1_1010100  1_0101100  0_0100010
        ↑继续     ↑继续     ↑结束

数据位:  1010100    0101100    0100010
拼接(低位在前): 0100010_0101100_1010100
             = 0x89654 = 562772
即: 84 + (44 << 7) + (34 << 14) = 84 + 5632 + 557056 = 562772
```

---

## 10. 属性类型判定的优先级

详见 [4.3.3 TOC 的使用时机](#433-toc-的使用时机)。

---

## 11. 工具

项目中提供了 `dump_riv.py` 脚本，支持四种模式解析和分析 .riv 文件。

依赖文件：`riv_schema.json`（类型/属性映射表）和 `riv_graph.py`（图形模式），需与 `dump_riv.py` 在同一目录。

> 详细使用说明见 `USAGE.md`，性能分析指南见 `PERFORMANCE_GUIDE.md`。

### 11.1 文本模式（默认）

以缩进树形结构输出到终端或文件：

```bash
python3 dump_riv.py input.riv              # 输出到终端
python3 dump_riv.py input.riv output.txt   # 输出到文件
```

输出示例：

```
[0] Backboard (typeKey=23) @28
  [1] Artboard "New Artboard" (typeKey=1) @30
    width: 155.89453125
    height: 155.89453125
    name: "New Artboard"
    [2] Node "Root" (typeKey=2) @69
      [3] Node "Button" (typeKey=2) @89
        [5] Shape (typeKey=3) @133
          [6] Ellipse (typeKey=4) @144
    [81] LinearAnimation "Back" (typeKey=31) @1191
      [82] KeyedObject (typeKey=25) @1201
        [83] KeyedProperty (typeKey=26) @1205
          [84] KeyFrameDouble (typeKey=30) @1213
    [337] StateMachine "State Machine 1" (typeKey=53) @3149
      [339] StateMachineLayer "Layer 1" (typeKey=57) @3180
        [340] AnimationState (typeKey=61) @3192
          [341] StateTransition (typeKey=65) @3197
```

### 11.2 HTML 列表模式 (`--html`)

生成可交互的 HTML 页面，支持展开/折叠、搜索过滤、类别筛选：

```bash
python3 dump_riv.py input.riv --html              # HTML 输出到终端
python3 dump_riv.py input.riv --html output.html   # 写入文件并自动打开浏览器
```

功能：
- 点击节点行展开/折叠子树和属性
- Expand All / Collapse All / Expand Level 2 按钮
- 搜索框实时过滤（递归匹配，父节点因子节点匹配而保留）
- 图例区域点击切换类别显示/隐藏

### 11.3 图形模式 (`--graph`)

生成 Canvas 绘制的树形图，节点用圆圈表示，连接线表示父子关系，右侧面板显示属性：

```bash
python3 dump_riv.py input.riv --graph              # HTML 输出到终端
python3 dump_riv.py input.riv --graph output.html   # 写入文件并自动打开浏览器
```

**画布交互：**
- 上下树形布局：父节点在上，子节点在下，圆圈按类别着色
- 鼠标滚轮缩放，拖拽空白区域平移画布
- 点击节点选中，选中后可拖拽移动节点位置
- Fit / + / − 缩放按钮
- 右下角图例显示各类别颜色含义（structure、shape、paint、animation 等）

**关联关系可视化：**
- 鼠标按下选中有关联的节点时（如 KeyedObject），橙色虚线连接到关联目标节点（如被动画的 Shape），目标节点高亮为橙色并显示光环
- 鼠标抬起后虚线消失，选中状态保留

**右侧属性面板：**
- 点击节点显示 Object 信息（Type、Name、Index、TypeKey、Offset、Category、Children）
- 下方列出所有属性，颜色类型带色块预览
- 交叉引用属性（objectId、animationId）显示为蓝色可点击链接，点击跳转到目标节点
- 每个字段旁的 `?` 图标悬停显示含义说明，例如：
  - Index → "Global object index in the .riv file"
  - Offset → "Byte offset of this object in the .riv file"
  - parentId → "Index of parent component within the Artboard (Artboard=0)"
  - objectId → "KeyedObject: component index within Artboard being animated"
  - frame → "Keyframe position in frames (default 0 if omitted)"
- 面板可通过 ◀ 按钮收起/展开

### 11.4 性能统计模式 (`--stats`)

输出运行时性能分析报告：

```bash
python3 dump_riv.py input.riv --stats              # 输出到终端
python3 dump_riv.py input.riv --stats report.txt   # 输出到文件
```

统计内容：
- **渲染评分**（1~5 星）：综合评估渲染复杂度
- **每帧渲染成本**：drawPath / clipPath / drawImage / drawImageMesh 调用次数
- **渲染调用明细**：路径总数、控制顶点、⭐渲染点数、绘制类型分布（Fill+Solid/Linear/Radial × Stroke）
- **Image 纹理**：每张图片的名称、尺寸、绘制类型
- **Mesh 变形**：Mesh 数量、顶点数、关联纹理
- **动画**：Top 5 最重动画、🔥路径重算明细
- **State Machine**：按性能影响排序（Layers > Listeners > Conditions > 其他）
- **⚠ 性能警告**：自动检测渲染点数过多、Draw calls 过多等问题

也可在 `--graph` 模式中点击 📊 Stats 按钮查看图形化版本（含环形图、柱状图、悬停 tooltip）。

> 各指标的详细含义和优化建议见 `PERFORMANCE_GUIDE.md`。

---

## 12. 源码参考

| 文件 | 内容 |
|------|------|
| `include/rive/runtime_header.hpp` | Header 解析逻辑 |
| `include/rive/core/binary_reader.hpp` | 二进制读取器接口 |
| `include/rive/core/reader.h` | LEB128 / Float32 / Uint32 底层解码函数 |
| `src/core/binary_reader.cpp` | 读取器实现 |
| `src/file.cpp` → `readRuntimeObject()` | 对象解析主循环 |
| `src/generated/core_registry.cpp` | 对象工厂 + 属性类型注册表 |
| `include/rive/generated/**/*_base.hpp` | 各类型的 typeKey 和 propertyKey 定义 |
| `src/core/field_types/core_*_type.cpp` | 各字段类型的反序列化实现 |
| `dump_riv.py` | .riv 解析脚本（文本/HTML/图形/统计四种输出模式） |
| `riv_graph.py` | Canvas 图形可视化 HTML 生成模块 |
| `riv_schema.json` | 从源码自动提取的类型名、属性名、字段类型映射表 |
| `USAGE.md` | 工具详细使用说明 |
| `PERFORMANCE_GUIDE.md` | 性能分析指南：各指标含义、阈值、优化检查清单 |
