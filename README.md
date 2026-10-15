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

- **1000 upem**, single cell = **550**; emoji = **1100** (exactly two cells).
- CJK is intentionally **not** baked in — leave it to the terminal's fontconfig fallback chain.
- Emoji are merged with `fontTools`' `Merger`. The bogus `locl` feature that `Merger` synthesizes
  for duplicate codepoints is removed, so digits/symbols are not swapped out in Latin runs.
  The whole story is in [`docs/locl-issue.md`](docs/locl-issue.md).

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

- **1000 upem，单格 550**；emoji **1100**（两格）。CJK **不烤进字体**，交给终端 fontconfig 回退链。
- emoji 用 `fontTools` 的 `Merger` 合并；合并器会自动合成一条 `locl`，我们把它删掉了，
  否则它在拉丁文片段里会把 ASCII 数字/空格换成 Noto 的空/宽字形（表现为「数字消失」）。
  完整来龙去脉见 [`docs/locl-issue.md`](docs/locl-issue.md)。

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
