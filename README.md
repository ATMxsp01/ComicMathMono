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

### Coverage

Roughly **19,800** codepoints in the Regular face (Regular also carries the colour emoji):

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
| Colour emoji (Noto COLRv1) | 100% of source |
| Hebrew / Arabic | partial (JuliaMono's coverage) |
| CJK | **not included** (by design) |

### Install

```bash
mkdir -p ~/.local/share/fonts/ComicMathMono
cp dist/ComicMathMono-*.ttf ~/.local/share/fonts/ComicMathMono/
fc-cache -f
```

kitty example (`~/.config/kitty/kitty.conf`):

```conf
font_family ComicMathMono
```

> No `font_features ... -locl` workaround is needed — the shipped fonts contain no bogus `locl`.

### Build from source

```bash
pip install -r requirements.txt
python3 build.py        # writes into dist/
```

Source fonts live in [`sources/`](sources/) — see [`sources/README.md`](sources/README.md) for
provenance and how to (re)download them.

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
- 组合重音符号（重音、希伯来元音点、阿拉伯元音符号等）以 **0 宽** 收录，
  分解写法在终端与浏览器里都不会出现「豆腐块」，见 [`docs/combining-marks.md`](docs/combining-marks.md)。
- `Merger` 重命名字形会导致引用它的排版规则失效（受害者是彩色键盘帽 `1️⃣`），
  `revive_renamed_rules()` 把这类引用改回可达字形修复，见 [`docs/merge-renaming.md`](docs/merge-renaming.md)。

### 覆盖范围

Regular face 约 **19,800** 个码点（彩色 emoji 只在 Regular 里）：

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
| 彩色 emoji（Noto COLRv1） | 源字体的 100% |
| 希伯来 / 阿拉伯 | 部分（JuliaMono 覆盖多少就多少） |
| CJK | **不含**（有意为之） |

### 安装

```bash
mkdir -p ~/.local/share/fonts/ComicMathMono
cp dist/ComicMathMono-*.ttf ~/.local/share/fonts/ComicMathMono/
fc-cache -f
```

kitty 配置示例（`~/.config/kitty/kitty.conf`）：

```conf
font_family ComicMathMono
```

> 成品字体已不含那条有问题的 `locl`，**不需要**再加 `font_features ... -locl` 之类的规避。

### 从源码构建

```bash
pip install -r requirements.txt
python3 build.py        # 产物写入 dist/
```

源字体在 [`sources/`](sources/)，来源与重新下载方式见 [`sources/README.md`](sources/README.md)。

### 许可证

- **构建脚本 / 工具**：MIT，见 [`LICENSE`](LICENSE)
- **字体（`dist/` 及 `sources/` 中 OFL 部分）**：SIL OFL 1.1，见 [`LICENSE-OFL-1.1.txt`](LICENSE-OFL-1.1.txt)
- **第三方声明**：见 [`NOTICE.md`](NOTICE.md)

### 致谢

ComicShannsMono、SeriousShanns、JuliaMono、Noto Color Emoji 以及 Nerd Fonts 项目。
