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
  (229 FE0E / 1448 FE0F entries in **all four** faces). Keycap base characters (`0-9` `#` `*`) are
  deliberately **DefaultUVS** so the `ccmp` keycap ligature still matches — `1️⃣` (with VS16)
  collapses to a single glyph — see [`docs/merge-renaming.md`](docs/merge-renaming.md) §3.2.
- A GPOS `mark` lookup is generated for all 400 combining marks. They come from JuliaMono
  designed **centred in a 550 cell, baseline-aligned**, so the correct placement is simply
  "put the mark's origin back on the base's origin" — without GPOS, HarfBuzz's own heuristic
  pushed them into the right half of the cell (measured: +182 too far right).
- **Metadata is normalised across the four faces**: one version (`1.0`, identical in
  `head.fontRevision`, name ID5 and ID3), one set of vertical metrics — `typo` 1030/−248
  (line height 1278) drives line spacing; `Agrave` reaches 989 (1026 in slanted faces), and the
  tallest Latin glyph is `hcircumflex` at 1167 (box drawing/emoji reach 1317 in the slanted
  faces), so tall glyphs can overflow the line box by design. `usWinAscent/Descent` 1317/1029
  cover every glyph so nothing is clipped on Windows, selected via `fsSelection` bit 7
  (USE_TYPO_METRICS); plus
  `post.isFixedPitch = 1`,
  `xAvgCharWidth = 550`, `fsType = 0`, and underline metrics. Combining
  marks *and* `Default_Ignorable` characters (ZWJ, tag characters, …) are zero-width, and
  C0/C1 control codes are not mapped. name ID0 lists the upstream copyright notices (an OFL
  requirement), and the legacy Mac (platform-1) name records are dropped. The remaining name
  fields are filled in too — ID3/4/6 (unique/full/PostScript name), 8/9 (manufacturer,
  designer), 10/19 (description, sample text), 11/12 (vendor/designer URL), 16/17
  (typographic) and 21/22 (WWS) — while ID7 (trademark) is deliberately empty, since no
  trademark has been registered. A `STAT` table declares
  `wght` (400/700) and `ital` (0/1, always the last axis) with **exactly one AxisValue per axis per
  face** — the static-font rule; copying a variable font's multi-value STAT into statics makes
  Windows label every weight with the first entry's name.
- The font is **completely unhinted** (no `cvt`/`fpgm`, zero glyph instructions — none of the
  upstream sources that provide outlines have any), but it carries the standard 7-byte `prep`
  snippet that switches on **smart dropout control** (`PUSHW 511 / SCANCTRL / PUSHB 4 /
  SCANTYPE`), so 1-pixel hairlines don't disappear at small sizes. This is exactly what
  `gftools fix-nonhinting` adds to unhinted fonts; no `gasp` table is used.
- Glyphs are **reordered by advance** at the end of the build so that the commonest advance
  (1100 — the emoji block) forms the tail of the glyph order. `hmtx` can then trim everything
  after the first 21 317 entries, which saves ~85 KB per face (four faces: ~330 KB) — without it
  the zero-width ZWJ/tag glyphs sit inside the emoji tail and every one of the ~64 k glyphs
  needs its own explicit entry.

### Coverage

The font is defined as **ComicShannsMono ⊎ JuliaMono Nerd Font Mono ⊎ Noto Color Emoji**, and
`tools/verify.py` asserts it *is* a superset of every source it is built from — that is the
property which lets the fallback chain below be empty of the two source families.

**22,539** codepoints in every face — identical across all four (they carry the colour emoji
and the UVS table; C0/C1 control characters are deliberately not mapped). Two of them are
**synthesised**: JuliaMono ships only the Coptic *small* letters `U+2CAF` (psi) and `U+2CDF`
(Old Nubian ngi), so their capitals `U+2CAE`/`U+2CDE` are generated by uniformly scaling the
small glyph to the cap height (668), centring it in the cell and keeping the 550-unit advance —
see `build.py::add_coptic_capitals()`.

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
| Emoji presentation (VS15 / VS16) | implemented — 229 FE0E / 1448 FE0F entries in all four faces |
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

Verify (four faces, and the version you actually installed):

```bash
fc-list | grep -i ComicMathMono          # expect 4 lines: Regular / Bold / Italic / Bold Italic
python3 -c "from fontTools.ttLib import TTFont; \
  print(TTFont('$HOME/.local/share/fonts/ComicMathMono/ComicMathMono-Regular.ttf')['name'].getDebugName(5))"
# -> Version 1.0
```

Uninstall:

```bash
rm -rf ~/.local/share/fonts/ComicMathMono
```

System-wide (needs root; still no `fc-cache`):

```bash
sudo install -d /usr/share/fonts/ComicMathMono
sudo install -m644 dist/ComicMathMono-*.ttf /usr/share/fonts/ComicMathMono/
```

After installing, **restart** running terminals / IDEs / browsers — they read the font files at
startup, so already-open windows keep using the old file.

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

Run `python3 tools/verify.py` afterwards to check the invariants learned from the bugs
documented in [`docs/`](docs/) — including an OTS sanitizer pass (browsers reject fonts that
fail it), a raw `glyf` reserved-flag check, and a HarfBuzz check that emoji sequences
(keycap / flag / ZWJ) still ligate into a single glyph
(see the CI workflow in [`.github/workflows/build.yml`](.github/workflows/build.yml)).

The build is **reproducible**: `build.py` re-execs itself with `PYTHONHASHSEED=0` (fontTools'
OT-table layout depends on Python's string hash randomisation, so without it every build produced
a different `GPOS`) and pins `head.created/modified` to `SOURCE_DATE_EPOCH` (default 2000-01-01).
Building twice therefore yields byte-identical fonts, and CI fails if the committed `dist/`
does not match a fresh build.

### Known limitations

- **No CJK.** CJK ideographs and CJK punctuation are out of scope by design — the only
  script-like leftovers are 5 CJK-adjacent emoji, which *are* included via a tiny 4 KB
  glyph subset extracted from Noto Sans CJK (see [`docs/emoji-presentation.md`](docs/emoji-presentation.md)).
  21 further codepoints are intentionally absent (Noto-internal PUA / unassigned — nothing types them).
- **Arabic** is covered only as far as JuliaMono covers it, and only in its **isolated** forms —
  we deliberately do not carry JuliaMono's `init`/`medi`/`fina` GSUB, so no letter joining;
  proper Arabic shaping needs a dedicated font.
- **Hebrew** is covered, including niqqud (vowel points).
- **Two/three-em dashes** (`U+2E3A`/`U+2E3B`) keep their source ink width (1067/1600) but a
  550-unit advance, so they deliberately overhang the cell; a monospace grid cannot represent
  multi-cell dashes without breaking alignment.
- **Line box overflow**: typo metrics are 1030/−248; `hcircumflex` reaches 1167 and some
  descenders reach −567, so these glyphs can spill into adjacent lines. `usWin` 1317/1029
  prevents clipping on Windows, but the typographic line box does not clear every glyph.
- **No kerning**, and no layout features beyond `ccmp` + `mark`.
- **Marks stack**: GPOS mark-to-base *and* mark-to-mark are generated. Marks are split into
  above/below classes, and a second mark is placed on the ink top (or bottom) of the first one.
  Mark-to-mark uses **per-glyph** anchors (`y_offset = yMax(first) − yMin(second)`), so stacked
  marks sit directly on each other rather than being pushed a full glyph height too high.
- **Precomposed + extra mark**: HarfBuzz normally composes `a + acute` to `aacute`; a contextual
  `ccmp` rule decomposes it back to `a + acute` **only when another combining mark follows**, so
  the second mark can use mark-to-mark instead of falling back to the baseline.
- **Italic `a` unified**: Italic/BoldItalic `a` and its common accented forms now use the upright
  ComicShanns single-storey `a`, scaled to the italic face's x-height/width and sheared by
  `post.italicAngle`; `a` therefore matches Regular/Bold instead of the old double-storey form.
- **Terminal cell fitting is minimal**: only glyphs that actually overflow their 550-unit cell
  are touched — left/right overflow is shifted back, and only glyphs wider than the cell are
  compressed (10-unit bearings). Unoverflowing glyphs are left unchanged. This covers all letters
  plus italic digits/punctuation/currency/math symbols, including Greek polytonic capitals.
  SeriousShanns' italic overhangs by up to ~70 units (`C/E/I`, `d`, `/`, `%`), and kitty clips
  out-of-cell ink by design — so only those affected italic glyphs become a little narrower.
- **Colour emoji need COLRv1** support in the renderer (kitty, Chromium, Firefox 116+, …).
  Emoji are present in all four faces, so bold/italic prose does not fall back to a
  different emoji font either. ZWJ sequences work in both spellings — with and without
  VS16 — as do skin-tone, keycap, flag and tag sequences (verified for all 2,564
  ligatures in `GSUB`).
- Source fonts are snapshotted (`sources/README.md`); newer Nerd Font / Noto releases bring
  new glyphs.

### Validation

`python3 tools/verify.py` is the regression gate we actually rely on (OTS sanitising, HarfBuzz
shaping of the emoji/VS16/keycap sequences, coverage vs. sources, vertical metrics, `hmtx`,
`STAT`, `prep`, case pairs, unreachable glyphs, …).

`fontbakery check-universal dist/*.ttf` currently reports **0 FAIL**. The 9 remaining WARN classes
(contour counts of the comic outlines, zero-length segments, `post` format 3 vs 2, `xAvgCharWidth`
for a monospaced font, double-width emoji, file size, partial CJK punctuation, decomposed carons,
`bad-numberOfHMetrics`; 48 warnings in total)
are deliberate trade-offs — each one is explained, with measurements, in
[`docs/fontbakery-warnings.md`](docs/fontbakery-warnings.md).

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
  彩色默认的（⌚ ⏰ ⏩…）给**彩色字形**（VS15 切单色），并写入真正的 cmap format 14 变体表
  （四个 face 各 229 条 FE0E / 1448 条 FE0F）。键盘帽基字符（`0-9` `#` `*`）是例外，故意写成 **DefaultUVS**，
  这样 `ccmp` 键盘帽连字才匹配得上——带 VS16 的 `1️⃣` 也能合成单字形，见
  [`docs/emoji-presentation.md`](docs/emoji-presentation.md) 与
  [`docs/merge-renaming.md`](docs/merge-renaming.md) §3.2。
- 组合重音符号（重音、希伯来元音点、阿拉伯元音符号等）以 **0 宽** 收录，
  分解写法在终端与浏览器里都不会出现「豆腐块」，见 [`docs/combining-marks.md`](docs/combining-marks.md)。
  并额外生成 GPOS `mark` 定位（400 个组合符）：它们来自 JuliaMono，是按
  **550 宽格子居中 + 基线对齐**设计的，所以正确定位就是「把标记原点挪回基准字形原点」——
  没有 GPOS 时 HarfBuzz 的启发式会把它们推到格子右半边（实测偏右 +182）。
- `Merger` 重命名字形会导致引用它的排版规则失效（受害者是彩色键盘帽 `1️⃣`），
  `revive_renamed_rules()` 把这类引用改回可达字形修复，见 [`docs/merge-renaming.md`](docs/merge-renaming.md)。
- **四个 face 的元数据完全统一**：同一个版本号（`1.0`，`head.fontRevision`、name ID5/ID3 三处一致）、
  同一套纵向指标（`typo` 1030/−248，行高 1278，且始终高于最高字形 `Agrave` 988 / 斜体 1026；
  `usWinAscent/Descent` 1317/1029 覆盖全部字形避免 Windows 裁剪，并用 `fsSelection` bit7 选中
  typo 指标）；`post.isFixedPitch=1`、`xAvgCharWidth=550`、
  `fsType=0`，下划线度量也补上了。name 表也补全了：ID3/4/6（唯一 ID/全名/PS 名）、8/9（厂商/
  设计者）、10/19（简介/样文）、11/12（厂商/设计者 URL）、16/17（typographic）与 21/22（WWS）；
  ID7（商标）**故意留空**（没有注册过商标）。组合标记**和**
  `Default_Ignorable`（ZWJ、Tag 字符等）一律 0 宽，C0/C1 控制码不再映射到字形。name ID0 里列出
  了各上游的版权声明（OFL 要求），并删掉了遗留的 Mac（platform 1）name 记录。另有 `STAT` 表声明
  `wght`（400/700）与 `ital`（0/1，且 `ital` 必须是最后一个轴），**每个 face 每个轴只写 1 条**
  —— 这是静态字体的规则；把变量字体的多条 STAT 原样塞进静态字体，Windows 会把所有字重都显示成
  第一条的名字。
- 字体**完全没有 hinting**（无 `cvt`/`fpgm`，0 个字形带指令 —— 提供轮廓的上游源本来就没有），
  但带一个标准的 7 字节 `prep` 片段，打开 **smart dropout control**
  （`PUSHW 511 / SCANCTRL / PUSHB 4 / SCANTYPE`），避免小字号下 1 像素的细线整段消失。
  这正是 `gftools fix-nonhinting` 给未 hinting 字体补的内容；没有使用 `gasp` 表。
- 构建收尾会**按 advance 重排字形**，把最常见的 advance（1100，即 emoji 段）排到字序尾部；
  这样 `hmtx` 只需前 21 317 条显式记录，每 face 省约 85 KB（四 face 共约 330 KB）。不重排的话
  0 宽的 ZWJ/Tag 字形会插在 emoji 尾部里面，6.3 万个字形全都要写显式记录。

### 覆盖范围

本字体定义为 **ComicShannsMono ⊎ JuliaMono Nerd Font Mono ⊎ Noto Color Emoji**，
`tools/verify.py` 会断言它确实是所有上游源字体的**超集** —— 正是这条性质让下面的 fallback
链可以不再保留那两个上游等宽字族。

**四个 face 各 22,539 个码点**（四个字重都带彩色 emoji 与 UVS 表，覆盖完全一致；
C0/C1 控制码有意不映射）。其中 **2 个是合成字形**：JuliaMono 只有科普特**小写**
`U+2CAF`(psi) 与 `U+2CDF`(Old Nubian ngi)，对应大写 `U+2CAE`/`U+2CDE` 由小写统一缩放到
cap height(668)、在格子里居中、advance 仍为 550 —— 见 `build.py::add_coptic_capitals()`。

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
| emoji 默认呈现与 VS15/VS16 | 已实现（四个 face 各 229 FE0E / 1448 FE0F） |
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

验证（应有 4 个 face，并确认装进去的是哪个版本）：

```bash
fc-list | grep -i ComicMathMono          # 期望 4 行：Regular / Bold / Italic / Bold Italic
python3 -c "from fontTools.ttLib import TTFont; \
  print(TTFont('$HOME/.local/share/fonts/ComicMathMono/ComicMathMono-Regular.ttf')['name'].getDebugName(5))"
# -> Version 1.0
```

卸载：

```bash
rm -rf ~/.local/share/fonts/ComicMathMono
```

装到系统级（需要 root，同样不要 `fc-cache`）：

```bash
sudo install -d /usr/share/fonts/ComicMathMono
sudo install -m644 dist/ComicMathMono-*.ttf /usr/share/fonts/ComicMathMono/
```

装完后**重启**正在运行的终端 / IDE / 浏览器 —— 它们在启动时就把字体文件读进内存了，
已开的窗口会继续用旧文件。

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
`tools/verify.py` 把踩过的坑对应的不变量都固化成了断言：除等宽/UVS/GPOS mark/覆盖超集之外，
还会跑 OTS（浏览器就是用同一套检查决定收不收字体）、检查 glyf 简单字形的 flag 保留位，
并用 HarfBuzz 实测 emoji 序列（键盘帽/旗帜/ZWJ）是否仍合成成单个字形；
CI 见 [`.github/workflows/build.yml`](.github/workflows/build.yml)。

构建是**可复现**的：`build.py` 会带 `PYTHONHASHSEED=0` 自重启（fontTools 排布 OT 表时受
Python 字符串哈希随机化影响，不固定的话每次构建出来的 `GPOS` 都不一样），并把
`head.created/modified` 固定为 `SOURCE_DATE_EPOCH`（默认 2000-01-01）。因此连跑两次得到
byte-identical 的字体，CI 也会在「提交的 dist/ 和重新构建的结果不一致」时直接失败。

### 已知限制

- **不含 CJK**。汉字与中文标点按设计排除在外。唯一相关的 5 个 CJK 类 emoji **已收录** ——
  做法是从 Noto Sans CJK 里抠出一个 4 KB 的 5 字形子集，见 [`docs/emoji-presentation.md`](docs/emoji-presentation.md)。
  另有 21 个码点故意不收（Noto 内部私用区/未分配码点，正常打字永远不会用到）。
- **阿拉伯文**只覆盖 JuliaMono 有的部分，且**只有孤立形态**（没有并入 JuliaMono 的
  `init`/`medi`/`fina`，因此不做字母连写）；正确的阿拉伯文排版需要专用字体。
- **希伯来文**已覆盖，含元音点（niqqud）。
- **两倍/三倍长破折号**（`U+2E3A`/`U+2E3B`）保留源字形的墨迹宽度（1067/1600），
  但 advance 仍是 550，因此会故意伸出格子；等宽网格无法在不破坏对齐的前提下表示多格破折号。
- **行框溢出**：typo 指标为 1030/−248，而 `hcircumflex` 到 1167、部分下伸部到 −567，
  这些字形可能侵入相邻行；`usWin` 1317/1029 保证 Windows 不裁切，但排版行框并不包住所有字形。
- **没有 kerning**，排版特性只有 `ccmp` 与 `mark`。
- **组合符可以叠加**：GPOS 同时生成了 mark-to-base 与 mark-to-mark。标记按 above/below 分类，
  第二个标记会落在前一个标记的墨迹顶（或底）上；mark-to-mark 使用**逐字形**锚点
  （`y_offset = yMax(第一个) − yMin(第二个)`），不会把第二个标记整体抬高一个自身高度。
- **预组合字母 + 额外标记**：HarfBuzz 会先把 `a + acute` 合成 `aacute`；GSUB 里加了一条
  contextual `ccmp` 规则，**只有后面还跟着组合符时**才拆回 `a + acute`，让第二个标记走
  mark-to-mark，而不是落回基线。
- **斜体 a 统一**：Italic/BoldItalic 的 `a` 及常见带符形式改用 ComicShanns 的**单层 a**，
  按斜体 face 的 x-height/宽度缩放，再按 `post.italicAngle` 倾斜；因此斜体 a 与
  Regular/Bold 风格一致，不再是原来的双层 a。
- **终端 cell 收格是最小改动**：只处理真正越出 550 格的字形 —— 左右越界就平移回格内，
  只有宽度超过格子的才水平压缩（留 10 单位侧边距）；未越界的字形完全不动。
  范围覆盖所有字母，以及斜体的数字/标点/货币/数学符号，希腊多调号大写也在内。
  SeriousShanns 斜体最多越界约 70 单位（`C/E/I`、`d`、`/`、`%`），kitty 会按 cell 裁切，
  所以只有这些受影响的斜体字形会比上游略窄。
- **彩色 emoji 需要渲染器支持 COLRv1**（kitty、Chromium、Firefox 116+ 等）。ZWJ 序列**带不带
  VS16 都能合成**（肤色、键盘帽、国旗、Tag 旗帜同理；GSUB 里 2,564 条连字全部实测）。
- 源字体是快照（见 `sources/README.md`）；更新的 Nerd Font / Noto 版本会带来新字形。

### 校验

日常回归靠 `python3 tools/verify.py`（OTS 消毒、HarfBuzz 对 emoji/VS16/键盘帽序列的 shaping、
与源字体的覆盖比对、纵向指标、`hmtx`、`STAT`、`prep`、大小写配对、不可达字形……）。

`fontbakery check-universal dist/*.ttf` 目前 **0 FAIL**；剩下的 9 类 WARN（comic 轮廓数、
零长线段、`post` format 3、等宽字体的 `xAvgCharWidth`、双宽 emoji、文件体积、CJK 标点、
分解式 caron、`bad-numberOfHMetrics`，共 48 条）都是有意取舍，逐条的理由与实测数字见
[`docs/fontbakery-warnings.md`](docs/fontbakery-warnings.md)。

### 许可证

- **构建脚本 / 工具**：MIT，见 [`LICENSE`](LICENSE)
- **字体（`dist/` 及 `sources/` 中 OFL 部分）**：SIL OFL 1.1，见 [`LICENSE-OFL-1.1.txt`](LICENSE-OFL-1.1.txt)
- **第三方声明**：见 [`NOTICE.md`](NOTICE.md)

### 致谢

ComicShannsMono、SeriousShanns、JuliaMono、Noto Color Emoji 以及 Nerd Fonts 项目。
