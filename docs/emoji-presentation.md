# 第四个坑：emoji 的"默认呈现"与 VS15 / VS16

> 前三篇分别是 [`locl-issue.md`](locl-issue.md)（数字消失）、
> [`combining-marks.md`](combining-marks.md)（组合符）、
> [`merge-renaming.md`](merge-renaming.md)（重命名让排版规则失效）。
> 这篇讲**为什么一批符号会"看不见"**，以及怎么把 emoji 呈现模型做对。

## 1. 现象

以下这些字符在终端和浏览器里**完全空白**（不是豆腐块，是什么都没有）：

```
U+00A9 ©   U+00AE ®   U+25AA ▪   U+25B6 ▶
U+2600 ☀   U+2764 ❤   U+26A0 ⚠   U+2708 ✈   ...
```

一共 **206 个**。而 `⌚ ⏩ ⚡` 这几个又相反：Unicode 说它们**默认就该是彩色**，
我们字体里却只有单色轮廓（终端里因为回退到彩色字体才看起来"正常"，
但浏览器里就是单色）。

## 2. 根因：字体只有彩色字形，没有文本字形

Unicode 给每个 emoji 字符定义了**默认呈现**（`Emoji_Presentation`）：

| 默认呈现 | 例子 | 字体应该提供 |
|---|---|---|
| **文本**（`Emoji_Presentation=No`） | `© ® ▪ ▶ ☀ ❤ ⚠ ✈ ⌨ ⏸` | **单色轮廓**（+ VS16 时切彩色） |
| **彩色**（`Emoji_Presentation=Yes`） | `⌚ ⏩ ⏰ 😀 ⭐` | **彩色字形**（+ VS15 时切单色） |

而 Noto Color Emoji 的彩色字形，**轮廓是空的**（0 个轮廓点，画面全在 COLRv1 图层树里）。
我们构建时：

1. `merge_noto_emoji()` 把 Noto 整字体并进来；
2. FILL 通道又用 `skip=noto_cmap` **跳过所有 Noto 已覆盖的码点**。

于是对"默认文本呈现"的那批字符，字体里**只剩一个空轮廓的彩色字形** ——
渲染器按文本方式取轮廓来画，自然什么都画不出来 → **字符消失**。

> 排查提示：只看"码点覆盖"是发现不了这个问题的（码点确实在），
> 必须检查**字形是否真的有可渲染的轮廓**。

## 3. 修复（`build.py`）

### 3.1 默认文本呈现 → 必须给单色轮廓

`prepare_emoji_presentation()` 在合并 Noto 之前跑：

- 对每个"Noto 有、且默认是文本呈现"的码点，依次从
  **JuliaMono → Noto Sans Symbols 2** 拷一份单色轮廓进来；
- **Noto Sans Symbols 2 是比例符号字体**：world map 等 75 个字形原本按
  1000~1370 单位宽设计，只改 advance 会让墨迹横跨 2~2.5 格并压到相邻字符上。
  `build.py::normalize_symbol_font()` 会把超过 550 的轮廓水平压缩、重新居中，
  使文本呈现形态真正落进单格；加 VS16 仍走 Noto 的 1100 彩色字形。
- 两者都没有的**直接丢弃** ——
  与其留一个"看不见"的字符，不如让系统回退字体去兜底。

### 3.2 默认彩色呈现 → 把 cmap 让给 Noto

对这 9 个（`⌚ ⌛ ⏩ ⏪ ⏫ ⏬ ⏰ ⏳ ⚡`），把 base 里的 cmap 映射删掉，
让 Noto 的彩色字形占住 cmap；base 原来的单色字形保留下来给 VS15 用。

### 3.3 COLR 引用要跟着重命名走

`Merger` 会把"base 与 Noto 同名"的字形改名成 `X.1`（见
[`merge-renaming.md`](merge-renaming.md)）。**COLR 的引用也必须跟着改**，
否则彩色图层会挂到 base 的单色字形上（等于没有彩色）。
`fix_colr_renames()` 负责这件事 —— 注意它与 `revive_renamed_rules()` **方向相反**：

| 函数 | 方向 | 作用对象 |
|---|---|---|
| `revive_renamed_rules()` | `X.N → X` | GSUB/GPOS（让规则重新能匹配上） |
| `fix_colr_renames()` | `X → X.N` | COLR（让彩色图层跟着变色字形走） |

### 3.4 生成真正的 UVS 表（VS15 / VS16）

Noto 源字体的 cmap format 14 里 **371 条全是 DefaultUVS**（值为 `None`，即「沿用默认
字形」）—— 因为它是 emoji 专用字体，默认字形本身就是彩色字形。但合并进本项目后，
默认字形是单色轮廓，所以必须写入真实的 NonDefault 映射，VS15/VS16 才会切换：

```
(cp, U+FE0F) -> 彩色字形    # 强制 emoji 呈现
(cp, U+FE0E) -> 单色字形    # 强制文本呈现
```

NonDefault 各 **217 条**；FE0E 总计 **229 条**（含 12 条 DefaultUVS），FE0F 总计 **1,448 条**
（含 1,231 条 DefaultUVS），四个 face 完全一致。

**例外：键盘帽基字符**（`0-9` `#` `*`，共 12 个）仍然写成 **DefaultUVS**。
原因见 [`merge-renaming.md`](merge-renaming.md) §3.2：它们的 VS16 一旦指向彩色数字
字形，`ccmp` 键盘帽连字（输入是单色字形）就会失配，`1️⃣` 会散成「彩色数字 + 帽框」。
通用原则是「cmap14 选中的字形，必须和后续连字要匹配的字形一致」。

于是：

| 输入 | 结果 |
|---|---|
| `☀` | 单色（Unicode 默认） |
| `☀` + U+FE0F | 彩色 |
| `☀` + U+FE0E | 单色 |
| `⌚` | 彩色（Unicode 默认） |
| `⌚` + U+FE0E | 单色 |
| `⌚` + U+FE0F | 彩色（DefaultUVS：字形本来就对，FE0F 只被"消费掉"） |

### 3.5 VS16 必须能被"消费"，否则会留下不可见字形

默认彩色的 emoji（cmap 已经指向 COLR 基字形）也要登记 `(cp, U+FE0F) -> None`（DefaultUVS）。
它们都是合法的 `emoji + FE0F` 写法，不登记的话 FE0F 会作为"不可见字形"残留 ——
实测 `🏴 + FE0F + ZWJ + ☠ + FE0F` 会散成 2 个字形。目前 DefaultUVS 共 **1,231** 条
（键盘帽 12 + 默认彩色 1,219），NonDefault VS16 217 条。

### 3.6 ZWJ 连字必须同时接受彩色字形

这是**最隐蔽的一类**，也是后来审计才发现的：`❤️‍🔥`、`🏳️‍🌈`、`🏴‍☠️`、`👁️‍🗨️`、`🧑‍⚕️`
这些标准写法实测全部散成 3~4 个字形。

根因是三者对不上：

| | 用的是什么 |
|---|---|
| `cmap` | 文本默认 emoji（❤ 🏳 👁 ⚖ ☠ ♀ ♂ ⚕ …）→ **单色**字形 |
| `cmap14` | `cp + FE0F` → **彩色**字形 |
| `GSUB` 连字 | Noto 按**单色**字形名写的组件 |

所以只要序列按 RGI 规则带上 VS16，首字符就变成了彩色字形，连字永远匹配不上。

修法（`build.py::add_colour_ligature_variants()`）：为每条连字补一个"把单色组件换成
对应彩色组件"的变体（组件里有多处时取所有组合），共 **+1,190 条**。同时把每个
`LigatureSet` 按组件数**从长到短排序** —— HarfBuzz 按集合顺序取第一个匹配，变体追加在
末尾时短连字（如「跑步+肤色」）会抢先匹配，长序列又散开。

修完实测：GSUB 里 **2,564 条**连字在 RGI emoji 形式下**全部**合成单字形；
`tools/verify.py` 把这条做成了回归测试。

## 4. 一个容易错过的连带问题：不可见字符不能丢

第一版实现把 **37 个 Tag 字符**（`U+E0020`–`U+E007F`）也一起丢了 ——
它们属于 `Default_Ignorable`，本身不可见，但**标签序列旗帜**（例如
`U+1F3F4` + 一串 Tag 字符 + `U+E007F`，苏格兰旗那种）要靠它们做 `ccmp` 合成。
丢掉之后旗帜直接散成 7 个字形。

修正：`prepare_emoji_presentation()` 用
`fontTools.merge.unicode.is_Default_Ignorable()` 把这类字符排除在"需要单色轮廓"之外。
修完之后标签旗恢复成 1 个字形。

## 4b. 源字体版本

彩色 emoji 来自 Noto Color Emoji 的 COLRv1 版，本项目快照为 **2.057（Unicode 18.0，2026-09）**，
比 2.042 多 **23 个码点**。升级时要注意：新 emoji 的默认呈现要查 `data/emoji-data.txt`，
如果 Unicode 数据比源字体旧，新 emoji 会被误判成"需要单色轮廓"而被丢弃 ——
所幸 2026-01-30 版的 emoji-data 已经把这些码点标成 `Emoji_Presentation=Yes`。

## 4c. 四个字重都带 emoji

最初只有 Regular 面合并彩色 emoji，Bold/Italic 靠系统的 Noto Color Emoji 兜底。这有两个问题：

- **粗体/斜体里 VS15/VS16 切换失效** —— Bold 面既没有彩色字形也没有 UVS 表，
  `☀` + U+FE0F 只能显示成它自己的单色字形；
- 依赖系统装有 emoji 字体。

现在四个 face 都跑同一套 emoji 合并，`tools/verify.py` 会断言每个 face 里
**1228 个「默认彩色」码点全部指向彩色字形**。代价是体积（每面约 8.3–8.4 MB）。

## 4d. 5 个「CJK 类 emoji」：从 Noto Sans CJK 抠一个 4 KB 子集

`U+3030` `U+303D` `U+3297` `U+3299` `U+1F237` 这 5 个是 **Emoji，但 Unicode 规定的默认呈现是
「文本」**，所以字体必须给它们单色轮廓。麻烦在于：全系统只有 **CJK 字体**（Noto Sans CJK / Jigmo）
带这些字形，而本项目不引入 CJK 字体。

折中办法是**把字形单独抠出来**，做成一个随仓库分发的小子集：

```bash
python3 tools/make_cjk_symbol_subset.py     # 需要系统装有 Noto Sans CJK（仅生成时需要）
# -> sources/NotoSansCJKsc-Symbols5.ttf     # 4.3 KB，5 个字形 + .notdef，OFL-1.1
```

`build.py` 的 `fill_mono_symbols()` 把它作为单色轮廓的**第四个来源**（在 Symbols 2 / Symbols 之后）。
于是：构建时**不需要**系统装 CJK 字体，只有"重新生成子集"才需要。

这 5 个按**全角（2 格 / advance 1100）**给，与 CJK 和 emoji 的惯例一致。
效果：默认渲染出单色轮廓（纯文本渲染器里不再空白），加上 U+FE0F 则走 UVS 拿 Noto 的彩色版本。

## 5. 已知取舍

- 丢弃的 **21 个码点**（`U+FE4E5`–`U+FE4EE`、`U+FE82C`、`U+FE82E`–`U+FE837`）不再由本字体提供：
  它们全是 **Noto 内部私用区 / 未分配码点**（keycap 合成字形的编号之类），正常打字永远不会用到。
  `U+1F549` OM SYMBOL 曾一度在丢弃之列，现由 **Noto Sans Symbols** 补齐；
  5 个「CJK 类 emoji」则由下面的 CJK 子集补齐（见 4d 节）。
- 单色轮廓来自 JuliaMono / Noto Sans Symbols 2 / Noto Sans Symbols，风格与 base 不同
  （例如 `©` 用的是 Julia 的无衬线版权符号）——这是"能看见"与"风格完全统一"之间的取舍。
- 变体选择符的覆盖是"有单色有彩色才写 UVS"，所以 `😀` 这类没有单色版的
  字符不参与 VS15 切换（键盘帽基字符是例外，见 3.4）。
