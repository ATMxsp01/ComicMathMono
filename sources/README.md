# sources/ — 上游源字体

`build.py` 需要以下源字体。本仓库已内置这些文件（便于直接构建），它们均来自上游开源项目，
许可证见 [`../NOTICE.md`](../NOTICE.md)。

| 本仓库文件名 | 来源 | 对应上游 face | 版本 | 许可证 |
|---|---|---|---|---|
| `ComicR.ttf` | Nerd Fonts | ComicShannsMono Nerd Font **Mono** Regular | 1.3.2 / NF 3.5.1 | MIT |
| `ComicB.ttf` | Nerd Fonts | ComicShannsMono Nerd Font **Mono** Bold | 1.3.2 / NF 3.5.1 | MIT |
| `SShI.ttf` | Nerd Fonts | SeriousShanns Nerd Font **Mono** Italic | 4.0.0 / NF 3.2.1 | MIT |
| `SShBI.ttf` | Nerd Fonts | SeriousShanns Nerd Font **Mono** BoldItalic | 4.0.0 / NF 3.2.1 | MIT |
| `julia/JuliaMonoNerdFontMono-Regular.ttf` | Nerd Fonts | JuliaMono Nerd Font **Mono** Regular | 0.062 / NF 3.4.0 | OFL-1.1 |
| `julia/JuliaMonoNerdFontMono-Bold.ttf` | Nerd Fonts | JuliaMono Nerd Font **Mono** Bold | 0.062 / NF 3.4.0 | OFL-1.1 |
| `julia/JuliaMonoNerdFontMono-Italic.ttf` | Nerd Fonts | JuliaMono Nerd Font **Mono** Italic | 0.062 / NF 3.4.0 | OFL-1.1 |
| `julia/JuliaMonoNerdFontMono-BoldItalic.ttf` | Nerd Fonts | JuliaMono Nerd Font **Mono** BoldItalic | 0.062 / NF 3.4.0 | OFL-1.1 |
| `NotoSansSymbols2-Regular.ttf` | notofonts/symbols | Noto Sans Symbols 2 Regular | 2.008 | OFL-1.1 |
| `Noto-COLRv1.ttf` | noto-emoji | Noto Color Emoji（COLRv1 版） | 2.042 | OFL-1.1 |

## 重新获取

**Nerd Fonts 系列**（`ComicShannsMono`、`SeriousShanns`、`JuliaMono`）：
从 <https://github.com/ryanoasis/nerd-fonts/releases> 下载对应的 `*.tar.xz`，
取其中的 `*NerdFontMono-{Regular,Bold,Italic,BoldItalic}.ttf`，按上表重命名。

**Noto Color Emoji（COLRv1）**：

```bash
curl -fLo sources/Noto-COLRv1.ttf \
  https://github.com/googlefonts/noto-emoji/raw/main/fonts/Noto-COLRv1.ttf
```

> 注意：`build.py` 需要的是 **COLRv1** 版（矢量彩色），而不是系统常见的 CBDT 位图版
> `NotoColorEmoji.ttf`。两者文件名不同，别拿错。

## JuliaMono 可选

如果不想在仓库里放 JuliaMono 副本，可以把 `sources/julia/` 删掉，
`build.py` 会自动回退到系统已安装的 `juliamono-nerd/mono/` 目录（见 `SYSTEM_JULIA_DIRS`）。

**Noto Sans Symbols 2**（给「默认文本呈现」的 emoji 补单色轮廓）：

```bash
curl -fLo sources/NotoSansSymbols2-Regular.ttf \
  https://github.com/notofonts/symbols/raw/main/fonts/NotoSansSymbols2/hinted/ttf/NotoSansSymbols2-Regular.ttf
```

## data/emoji-data.txt

`build.py` 还要用 Unicode 的 `emoji-data.txt` 来判定每个码点的默认呈现：

```bash
curl -fLo data/emoji-data.txt \
  https://unicode.org/Public/UCD/latest/ucd/emoji/emoji-data.txt
```
