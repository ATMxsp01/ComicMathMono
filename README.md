# ComicMathMono

**A terminal-first monospace font** — Comic-style Latin, a full math/technical layer, and color emoji,
all normalized to one clean 1000‑upem grid.

[English](#english) · [中文](#中文)

---

## English

ComicMathMono is a merged monospace font assembled from three open-source families:

| Layer | Source | License |
|---|---|---|
| Latin · box drawing · Nerd Font icons | ComicShannsMono & SeriousShanns Nerd Fonts | MIT |
| Greek · math · arrows · technical · braille | JuliaMono | OFL-1.1 |
| Color emoji | Noto Color Emoji (COLRv1) | OFL-1.1 |

Faces: **Regular, Bold, Italic, Bold Italic** (in [`dist/`](dist/)).

### Design

- **1000 upem**, single cell = **550**; emoji = **1100** (exactly two cells); combining marks = **0**.
- CJK is intentionally **not** baked in — leave it to the terminal's fontconfig fallback chain.
- Emoji are merged with `fontTools`' `Merger`. The bogus `locl` feature that `Merger` synthesizes
  for duplicate codepoints is removed, so digits/symbols are not swapped out in Latin runs.
  The whole story is in [`docs/locl-issue.md`](docs/locl-issue.md).
- Combining marks (accents, Hebrew points, Arabic harakat, …) are included as **zero-width**
  glyphs, so decomposed text renders without tofu in both terminals and browsers —
  see [`docs/combining-marks.md`](docs/combining-marks.md).
- The `Merger`'s glyph renaming would otherwise kill layout rules that reference the renamed
  duplicates (colour keycap emoji `1️⃣` were the visible casualty); `revive_renamed_rules()`
  repairs those references — see [`docs/merge-renaming.md`](docs/merge-renaming.md).
- **Emoji presentation follows Unicode**: text-default characters (© ® ▪ ☀ ❤ …) carry a
  monochrome outline and switch to colour with VS16; colour-default ones (⌚ ⏰ ⏩ …) carry the
  colour glyph and switch to monochrome with VS15. A real cmap format-14 UVS table is generated
  (229 variants each way) — see [`docs/emoji-presentation.md`](docs/emoji-presentation.md).
- A GPOS `mark` lookup is generated for all 355 combining marks. They come from JuliaMono
  designed **centred in a 550 cell, baseline-aligned**, so the correct placement is simply
  "put the mark's origin back on the base's origin" — without GPOS, HarfBuzz's own heuristic
  pushed them into the right half of the cell (measured: +182 too far right).

### Coverage

The font is defined as **ComicShannsMono ⊎ JuliaMono Nerd Font Mono ⊎ Noto Color Emoji**, and
`tools/verify.py` asserts it *is* a superset of every source it is built from — that is the
property which lets the fallback chain below be empty of the two source families.

**22,539** codepoints in every face (all four faces carry the colour emoji and the UVS table):

| Area | Coverage |
|---|---|
| ASCII letters & punctuation | 100% |
| Latin-1 / Latin Extended A–B | ~100% |
| IPA, spacing modifiers, phonetic extensions | 100% |
| Latin Extended Additional / C / D / E | 100% |
| Greek, Cyrillic | 100% |
| Combining marks | yes (zero-width) |
| Punctuation, super/subscripts, currency, number forms | ~99% |
| Arrows, math operators, misc math, **math alphanumerics** | 100% |
| Technical, box drawing, blocks, geometric shapes | 100% |
| Misc symbols, dingbats, enclosed alphanumerics, legacy computing | 100% |
| Braille | 100% |
| Nerd Font icons (incl. plane-15 Material Design Icons) | 100% |
| Colour emoji (Noto COLRv1) | 100% of source — in **all four** faces |
| Emoji presentation (VS15 / VS16) | implemented — 224 real UVS variants each way |
| Hebrew / Arabic | partial (JuliaMono's coverage) |
| CJK | **not included** (by design) |

### Recommended fontconfig fallback chain

Because ComicMathMono absorbs both upstream monospace families, the `monospace` chain only
needs to keep what genuinely lies outside this font (CJK) plus an emoji safety net:

```xml
<match target="pattern">
    <test qual="any" name="family"><string>monospace</string></test>
    <edit name="family" mode="prepend" binding="strong">
        <string>ComicMathMono</string>       <!-- 1. main font (emoji in all four weights) -->
        <string>Noto Color Emoji</string>    <!-- 2. safety net (the 21 codepoints left out are PUA/unassigned) -->
        <string>Sarasa Mono SC</string>      <!-- 3. CJK, monospaced -->
        <string>Jigmo</string>               <!-- 4. rare ideographs URO/ExtA   -->
        <string>Jigmo2</string>              <!-- 5. rare ideographs ExtB~F/I  -->
        <string>Jigmo3</string>              <!-- 6. rare ideographs ExtG/H/J  -->
    </edit>
</match>
```

This replaces a chain that had to carry `ComicShannsMono Nerd Font Mono` and
`JuliaMono Nerd Font Mono` — both are provably redundant now (measured coverage gap: **0**
codepoints for each).

### Install

```bash
./install.sh          # 原子替换到 ~/.local/share/fonts/ComicMathMono/
```

Equivalently, by hand:

```bash
mkdir -p ~/.local/share/fonts/ComicMathMono
cp dist/ComicMathMono-*.ttf ~/.local/share/fonts/ComicMathMono/
```

kitty example (`~/.config/kitty/kitty.conf`):

```conf
font_family ComicMathMono
```

> **Never run `fc-cache -f` while your terminal is running.** `fc-cache` truncates and rewrites
> the fontconfig cache files, which are `mmap`ed into running processes; a process holding such
> a mapping receives `SIGBUS` and dies — and the corrupted mapping keeps killing *later* font
> lookups too. fontconfig already invalidates its cache by directory mtime, so pre-warming is
> unnecessary. See [`docs/fc-cache-sigbus.md`](docs/fc-cache-sigbus.md).
>
> Also install with `cp` + `mv` (as `install.sh` does) rather than overwriting a font file in
> place, so a running terminal can never read a half-written file.
>
> No `font_features ... -locl` workaround is needed — the shipped fonts contain no bogus `locl`.

### Build from source

```bash
pip install -r requirements.txt
python3 build.py        # writes into dist/
```

Source fonts live in [`sources/`](sources/) — see [`sources/README.md`](sources/README.md) for
provenance and how to (re)download them.

Run `python3 tools/verify.py` afterwards to check the invariants learned from the four bugs
documented in [`docs/`](docs/) (see the CI workflow in [`.github/workflows/build.yml`](.github/workflows/build.yml)).

### Known limitations

- **No CJK.** CJK ideographs and CJK punctuation are out of scope by design — the only
  script-like leftovers are 5 CJK-adjacent emoji, which *are* included via a tiny 4 KB
  glyph subset extracted from Noto Sans CJK (see [`docs/emoji-presentation.md`](docs/emoji-presentation.md)).
  21 further codepoints are intentionally absent (Noto-internal PUA / unassigned — nothing types them).
- **Arabic** is covered only as far as JuliaMono covers it, in isolated/initial forms;
  proper Arabic shaping needs a dedicated font.
- **Hebrew** is covered, including niqqud (vowel points).
- **No kerning**, and no layout features beyond `ccmp` + `mark`.
- **Marks do not stack**: GPOS mark-to-base is provided, but not mark-to-mark, so a base with
  two combining marks shows them overlapping rather than stacked higher.
- **Colour emoji need COLRv1** support in the renderer (kitty, Chromium, Firefox 116+, …).
  Emoji are present in all four faces, so bold/italic prose does not fall back to a
  different emoji font either.
- Source fonts are snapshotted (`sources/README.md`); newer Nerd Font / Noto releases bring
  new glyphs.

### License

- **Build tooling / scripts:** MIT — see [`LICENSE`](LICENSE)
- **Fonts (`dist/`, and the OFL parts of `sources/`):** SIL Open Font License 1.1 — see
  [`LICENSE-OFL-1.1.txt`](LICENSE-OFL-1.1.txt)
- **Third-party attributions:** [`NOTICE.md`](NOTICE.md)

---

## 中文

**ComicMathMono** 是一个面向终端的合并等宽字体：把「Comic 风格拉丁/盒线/Nerd Font 图标」、
「JuliaMono 的希腊/数学/箭头/技术/盲文层」和「Noto COLRv1 彩色 emoji」融合进同一套
1000 upem 网格，单格固定 550 单位、emoji 1100（正好两格），在终端里对齐行为可预测。

包含 **Regular / Bold / Italic / Bold Italic** 四个 face，构建产物在 [`dist/`](dist/)。

### 设计要点

- **1000 upem，单格 550**；emoji **1100**（两格）；组合标记 **0 宽**。CJK **不烤进字体**，交给终端 fontconfig 回退链。
- emoji 用 `fontTools` 的 `Merger` 合并；合并器会自动合成一条 `locl`，我们把它删掉了，
  否则它在拉丁文片段里会把 ASCII 数字/空格换成 Noto 的空/宽字形（表现为「数字消失」）。
  完整来龙去脉见 [`docs/locl-issue.md`](docs/locl-issue.md)。
- emoji 的**默认呈现**按 Unicode 规则实现：文本默认的符号（© ® ▪ ☀ ❤…）给**单色轮廓**（VS16 切彩色），
  彩色默认的（⌚ ⏰ ⏩…）给**彩色字形**（VS15 切单色），并写入真正的 cmap format 14 变体表，
  见 [`docs/emoji-presentation.md`](docs/emoji-presentation.md)。
- 组合重音符号（重音、希伯来元音点、阿拉伯元音符号等）以 **0 宽** 收录，
  分解写法在终端与浏览器里都不会出现「豆腐块」，见 [`docs/combining-marks.md`](docs/combining-marks.md)。
  并额外生成 GPOS `mark` 定位（355 个组合符）：它们来自 JuliaMono，是按
  **550 宽格子居中 + 基线对齐**设计的，所以正确定位就是「把标记原点挪回基准字形原点」——
  没有 GPOS 时 HarfBuzz 的启发式会把它们推到格子右半边（实测偏右 +182）。
- `Merger` 重命名字形会导致引用它的排版规则失效（受害者是彩色键盘帽 `1️⃣`），
  `revive_renamed_rules()` 把这类引用改回可达字形修复，见 [`docs/merge-renaming.md`](docs/merge-renaming.md)。

### 覆盖范围

本字体定义为 **ComicShannsMono ⊎ JuliaMono Nerd Font Mono ⊎ Noto Color Emoji**，
`tools/verify.py` 会断言它确实是所有上游源字体的**超集** —— 正是这条性质让下面的 fallback
链可以不再保留那两个上游等宽字族。

**四个 face 各 22,539 个码点**（四个字重都带彩色 emoji 与 UVS 表）：

| 类别 | 覆盖 |
|---|---|
| ASCII 字母与标点 | 100% |
| Latin-1 / 拉丁扩展 A–B | ~100% |
| IPA、修饰符、注音扩展 | 100% |
| 拉丁扩展 Additional / C / D / E | 100% |
| 希腊、西里尔 | 100% |
| 组合重音符号 | 已收录（0 宽） |
| 标点、上下标、货币、数字形式 | ~99% |
| 箭头、数学运算符、杂项数学、**数学字母数字** | 100% |
| 技术符号、盒线、块元素、几何图形 | 100% |
| 杂项符号、装饰、圈号、遗留计算块 | 100% |
| 盲文 | 100% |
| Nerd Font 图标（含平面 15 Material Design Icons） | 100% |
| 彩色 emoji（Noto COLRv1） | 源字体的 100%，**四个字重都有** |
| emoji 默认呈现与 VS15/VS16 | 已实现（各 229 条真 UVS） |
| 希伯来 / 阿拉伯 | 部分（JuliaMono 覆盖多少就多少） |
| CJK | **不含**（有意为之） |

### 推荐的 fontconfig fallback 链

因为 ComicMathMono 已经把两个上游等宽字族都吸收进来了，`monospace` 链只需要保留真正在本字体
之外的东西（CJK）+ 一个 emoji 安全网：

```xml
<match target="pattern">
    <test qual="any" name="family"><string>monospace</string></test>
    <edit name="family" mode="prepend" binding="strong">
        <string>ComicMathMono</string>       <!-- 1. 主字体（四个字重都带 emoji） -->
        <string>Noto Color Emoji</string>    <!-- 2. 安全网（未收录的 21 个都是私用区/未分配码点） -->
        <string>Sarasa Mono SC</string>      <!-- 3. 等宽中文 -->
        <string>Jigmo</string>               <!-- 4. 生僻字 URO/ExtA  -->
        <string>Jigmo2</string>              <!-- 5. 生僻字 ExtB~F/I -->
        <string>Jigmo3</string>              <!-- 6. 生僻字 ExtG/H/J  -->
    </edit>
</match>
```

原来的链里还要写 `ComicShannsMono Nerd Font Mono` 和 `JuliaMono Nerd Font Mono` ——
现在两者都是**可证明冗余**的（实测覆盖缺口各为 **0** 个码点）。

### 安装

```bash
./install.sh          # 原子替换到 ~/.local/share/fonts/ComicMathMono/
```

等价的手工写法：

```bash
mkdir -p ~/.local/share/fonts/ComicMathMono
cp dist/ComicMathMono-*.ttf ~/.local/share/fonts/ComicMathMono/
```

kitty 配置示例（`~/.config/kitty/kitty.conf`）：

```conf
font_family ComicMathMono
```

> **终端正在运行时，千万不要跑 `fc-cache -f`。** `fc-cache` 会截断重写 fontconfig 的缓存文件，
> 而缓存是 `mmap` 进进程的 —— 持有该映射的进程会收到 `SIGBUS` 直接崩溃，**而且被破坏的映射会
> 继续害到之后每一次字体查找**。fontconfig 本来就按目录 mtime 自动失效缓存，不需要预热。
> 详见 [`docs/fc-cache-sigbus.md`](docs/fc-cache-sigbus.md)。
>
> 另外要用 `cp` + `mv` 原子替换（`install.sh` 就是这么做的），不要原地覆盖字体文件，
> 否则运行中的终端可能读到写了一半的文件。
>
> 成品字体已不含那条有问题的 `locl`，**不需要**再加 `font_features ... -locl` 之类的规避。

### 从源码构建

```bash
pip install -r requirements.txt
python3 build.py        # 产物写入 dist/
python3 tools/verify.py # 回归校验
```

源字体在 [`sources/`](sources/)，来源与重新下载方式见 [`sources/README.md`](sources/README.md)。
`tools/verify.py` 把四个坑对应的不变量都固化成了断言；CI 见 [`.github/workflows/build.yml`](.github/workflows/build.yml)。

### 已知限制

- **不含 CJK**。汉字与中文标点按设计排除在外。唯一相关的 5 个 CJK 类 emoji **已收录** ——
  做法是从 Noto Sans CJK 里抠出一个 4 KB 的 5 字形子集，见 [`docs/emoji-presentation.md`](docs/emoji-presentation.md)。
  另有 21 个码点故意不收（Noto 内部私用区/未分配码点，正常打字永远不会用到）。
- **阿拉伯文**只覆盖 JuliaMono 有的部分，且只能是孤立/词首形态；正确的阿拉伯文排版需要专用字体。
- **希伯来文**已覆盖，含元音点（niqqud）。
- **没有 kerning**，排版特性只有 `ccmp` 与 `mark`。
- **组合符不能叠加**：提供了 GPOS 的 mark-to-base，但没有 mark-to-mark，所以一个基准字形带
  两个组合符时它们会重叠，而不是往上叠。
- **彩色 emoji 需要渲染器支持 COLRv1**（kitty、Chromium、Firefox 116+ 等）。
- 源字体是快照（见 `sources/README.md`）；更新的 Nerd Font / Noto 版本会带来新字形。

### 许可证

- **构建脚本 / 工具**：MIT，见 [`LICENSE`](LICENSE)
- **字体（`dist/` 及 `sources/` 中 OFL 部分）**：SIL OFL 1.1，见 [`LICENSE-OFL-1.1.txt`](LICENSE-OFL-1.1.txt)
- **第三方声明**：见 [`NOTICE.md`](NOTICE.md)

### 致谢

ComicShannsMono、SeriousShanns、JuliaMono、Noto Color Emoji 以及 Nerd Fonts 项目。
