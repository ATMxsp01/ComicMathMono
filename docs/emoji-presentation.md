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
- 两者都没有的（26 个，全是 CJK 相关圈字与 Noto 内部私用区码点）**直接丢弃** ——
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

之前字体的 cmap format 14 表里 **371 条全是 `None`**（等于没有变体），
所以 VS15/VS16 完全无效。现在 `apply_emoji_presentation()` 会写入真实的变体映射：

```
(cp, U+FE0F) -> 彩色字形    # 强制 emoji 呈现
(cp, U+FE0E) -> 单色字形    # 强制文本呈现
```

各 **223 条**。于是：

| 输入 | 结果 |
|---|---|
| `☀` | 单色（Unicode 默认） |
| `☀` + U+FE0F | 彩色 |
| `☀` + U+FE0E | 单色 |
| `⌚` | 彩色（Unicode 默认） |
| `⌚` + U+FE0E | 单色 |

## 4. 一个容易错过的连带问题：不可见字符不能丢

第一版实现把 **37 个 Tag 字符**（`U+E0020`–`U+E007F`）也一起丢了 ——
它们属于 `Default_Ignorable`，本身不可见，但**标签序列旗帜**（例如
`U+1F3F4` + 一串 Tag 字符 + `U+E007F`，苏格兰旗那种）要靠它们做 `ccmp` 合成。
丢掉之后旗帜直接散成 7 个字形。

修正：`prepare_emoji_presentation()` 用
`fontTools.merge.unicode.is_Default_Ignorable()` 把这类字符排除在"需要单色轮廓"之外。
修完之后标签旗恢复成 1 个字形。

## 5. 已知取舍

- 丢弃的 **26 个码点** 不再由本字体提供，改由系统回退链负责：
  `U+3030` `U+303D` `U+3297` `U+3299` `U+1F237`（CJK 类，唯一单色源是 Noto Sans CJK / Jigmo）
  以及 21 个 Noto 内部私用区码点（`U+FE4E5`–`U+FE4EE`、`U+FE82C`、`U+FE82E`–`U+FE837`，
  全系统只有 Noto Color Emoji 有）。
  `U+1F549` OM SYMBOL 本来也在丢弃之列，现由 **Noto Sans Symbols** 补齐。
- 单色轮廓来自 JuliaMono / Noto Sans Symbols 2 / Noto Sans Symbols，风格与 base 不同
  （例如 `©` 用的是 Julia 的无衬线版权符号）——这是"能看见"与"风格完全统一"之间的取舍。
- 变体选择符的覆盖是"有单色有彩色才写 UVS"，所以 `😀` 这类没有单色版的
  字符不参与 VS15 切换。
