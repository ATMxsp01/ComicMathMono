# sources/ — 上游源字体

`build.py` / `tools/make_cjk_companion.py` 需要以下源字体。本仓库已内置这些文件（便于直接构建），
它们均来自上游开源项目，许可证见 [`../NOTICE.md`](../NOTICE.md)。

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
| `NotoSansSymbols-Regular.ttf` | notofonts/symbols | Noto Sans Symbols Regular | 2.003 | OFL-1.1 |
| `NotoSansCJKsc-Symbols5.ttf` | noto-cjk（子集） | 5 个 CJK 类 emoji 的单色轮廓 | 由 Noto Sans CJK **2.004** 生成（`name` ID5） | OFL-1.1 |
| `NotoSansCJKsc-Gap27-Regular.ttf` | noto-cjk（子集） | 27 个 CJK W/F 缺口（Regular） | 由 Noto Sans CJK **2.004** 生成 | OFL-1.1 |
| `NotoSansCJKsc-Gap27-Bold.ttf` | noto-cjk（子集） | 27 个 CJK W/F 缺口（Bold） | 由 Noto Sans CJK **2.004** 生成 | OFL-1.1 |
| `yozai/Yozai-Medium.ttf` | lxgw/yozai-font | Yozai Medium（CJK 伴生 Regular） | 0.868 | OFL-1.1 |
| `yozai/Yozai-Bold.ttf` | lxgw/yozai-font | Yozai Bold（CJK 伴生 Bold） | 0.850 | OFL-1.1 |
| `Noto-COLRv1.ttf` | noto-emoji | Noto Color Emoji（COLRv1 版） | 2.057（Unicode 18.0） | OFL-1.1 |

> `NotoSansCJKsc-Symbols5.ttf` 是**派生文件**：由本机 `/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc`
> （Version 2.004，`head.fontRevision` 2.00399）经 `tools/make_cjk_symbol_subset.py` 转成
> TrueType/glyf 并只保留 5 个字形 + `.notdef`，**不是**上游直接发布的文件。
>
> `NotoSansCJKsc-Gap27-{Regular,Bold}.ttf` 同样是派生文件，由 `tools/make_noto_gap_subset.py`
> 从 Noto Sans CJK SC 的 Regular/Bold face 各抠出 27 个 CFF 字形并转成 TrueType/glyf。
> `yozai/` 是 CJK 伴生字体 `ComicMathMono CJK` 的源；详见 [`yozai/README.md`](yozai/README.md)。

## 重新获取

**Nerd Fonts 系列**（`ComicShannsMono`、`SeriousShanns`、`JuliaMono`）：
从 <https://github.com/ryanoasis/nerd-fonts/releases> 下载对应的 `*.tar.xz`，
取其中的 `*NerdFontMono-{Regular,Bold,Italic,BoldItalic}.ttf`，按上表重命名。

**Noto Color Emoji（COLRv1）**：

```bash
curl -fLo sources/Noto-COLRv1.ttf \
  https://raw.githubusercontent.com/googlefonts/noto-emoji/main/2D/fonts/Noto-COLRv1.ttf
```

> 注意：`build.py` 需要的是 **COLRv1** 版（矢量彩色），而不是系统常见的 CBDT 位图版
> `NotoColorEmoji.ttf`。两者文件名不同，别拿错。

## JuliaMono 可选

如果不想在仓库里放 JuliaMono 副本，可以把 `sources/julia/` 删掉，
`build.py` 会自动回退到系统已安装的 `juliamono-nerd/mono/` 目录（见 `SYSTEM_JULIA_DIRS`）。

**Noto Sans Symbols / Noto Sans Symbols 2**（给「默认文本呈现」的 emoji 补单色轮廓；
优先用 Symbols 2，其次 Symbols）：

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

**Noto Sans CJK 子集**（5 个「CJK 类 emoji」的单色轮廓，4.0 KB，**TrueType/glyf**）——
**不需要手动下载**，用仓库里的脚本从系统的 Noto Sans CJK 现场生成：

```bash
python3 tools/make_cjk_symbol_subset.py
# 或指定源与输出：
python3 tools/make_cjk_symbol_subset.py /usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc \
    -o sources/NotoSansCJKsc-Symbols5.ttf
```

它是构建的**必需**输入（`build.py` 用它补 U+3030/U+303D/U+3297/U+3299/U+1F237），
但构建本身不需要系统装有 CJK 字体 —— 子集已经在仓库里了。

## CJK 伴生字体源

`ComicMathMono CJK` 使用两份 Yozai 和两份 Noto 缺口子集：

```bash
# Yozai（Medium 做 Regular；0.850 Bold 做 Bold）
curl -fLo sources/yozai/Yozai-Medium.ttf \
  https://github.com/lxgw/yozai-font/releases/download/v0.868/Yozai-Medium.ttf
curl -fLo sources/yozai/Yozai-Bold.ttf \
  https://github.com/lxgw/yozai-font/releases/download/v0.850/Yozai-Bold.ttf

# 27 个缺口的 Noto 子集（需要系统 Noto Sans CJK；只需重新生成时运行）
python3 tools/make_noto_gap_subset.py

# 构建 CJK 伴生字体
python3 tools/make_cjk_companion.py
python3 tools/verify_cjk.py
```

- Yozai 的版本、SHA-256、许可与保留名称见 [`yozai/README.md`](yozai/README.md)。
- `NotoSansCJKsc-Gap27-{Regular,Bold}.ttf` 是 TrueType/glyf 派生文件，日常构建不需要
  系统 Noto；只有重新生成这两个子集时才需要。
- 设计、覆盖、度量、命名与 fontbakery 取舍见 [`../docs/cjk.md`](../docs/cjk.md)。

## 更新流程（三个版本必须对齐）

emoji 的行为由三个输入共同决定，**升级任何一个都要检查另外两个**：

| 输入 | 决定什么 | 当前版本 |
|---|---|---|
| Nerd Fonts 三个上游 | 拉丁/希腊/西里尔/数学符号轮廓；JuliaMono 的 emoji **单色**轮廓 | ComicShanns 1.3.2 / NF 3.5.1、SeriousShanns 4.0.0 / NF 3.2.1、JuliaMono 0.062 / NF 3.4.0 |
| `Noto-COLRv1.ttf` | 彩色字形、ZWJ 连字、COLR 图层 | 2.057（Unicode 18.0） |
| `data/emoji-data.txt` | 每个码点的 `Emoji_Presentation`（默认彩色 / 默认文本） | Unicode 18.0.0（2026-01-30） |

### checklist

1. 按上表换源文件（文件名必须一致）。
2. **Noto Color Emoji 与 `emoji-data.txt` 要同一 Unicode 版本**：字体里的码点集合来自 Noto，
   而"这个码点默认是彩色还是文本"来自 `emoji-data.txt`；两者错版本会出现
   「文本呈现的 emoji 没有单色轮廓 → 字符整个消失」（见 `docs/emoji-presentation.md` §3.1）。
3. `python3 build.py && python3 tools/make_cjk_companion.py`
4. `python3 tools/verify.py && python3 tools/verify_cjk.py`，重点看输出里的这几项：
   - `UVS：VS16 N 条`（应随 emoji 数量增长）
   - `emoji 连字 N 条全部合成单字形`
   - `cmap=…` / `colour-default=…`
   - `CJK 伴生字体校验通过 ✓`（只含 W/F、无 ASCII、全部 1100、8105/GB2312 全满）
5. 检查构建日志的 `emoji 呈现：默认彩色 N 个交还 Noto；无单色源丢弃 M 个`：
   如果 **M 突然变大**，说明新 emoji 在 Nerd Fonts / JuliaMono / Noto Sans Symbols 里
   都找不到单色轮廓，需要补源（否则文本呈现会缺字形）。
6. `fontbakery check-universal`：主字体四个 face 应保持 **FAIL 0**；CJK 伴生字体有 4 条
   有意的 FAIL（`massive-font` / `whitespace_glyphs`），见 `docs/fontbakery-warnings.md` §3。
7. 更新本文件版本表、`NOTICE.md`（上游版权与版本）、`README.md` 的覆盖数字。
8. 提交 `dist/`（CI 会重新构建主字体和 CJK 伴生字体并校验 byte-identical）。

### 只升级 Nerd Fonts 时

- `cmap` 会变大（JuliaMono 新符号）；`verify.py` 的"覆盖 ≥ 各源"检查会自动跟上。
- 如果 JuliaMono 改了大写/小写集合，`case_mapping` 断言（13f）可能报新缺失 → 按
  `build.py::add_coptic_capitals()` 的方式补合成，或更新断言。

### 只升级 CJK 源时

1. 换 `sources/yozai/Yozai-Medium.ttf` / `Yozai-Bold.ttf`，更新
   [`yozai/README.md`](yozai/README.md) 的版本与 SHA-256。
2. 如果 Yozai 新版本补上了那 27 个缺口，可以删掉对应的 Noto 子集条目；否则保持
   `NotoSansCJKsc-Gap27-*` 不变。
3. `python3 tools/make_cjk_companion.py && python3 tools/verify_cjk.py`
4. 重新跑 `fontbakery check-universal dist/ComicMathMono-CJK-*.ttf`，按
   `docs/fontbakery-warnings.md` §3 复核 FAIL/WARN 是否仍只有已知项。
5. 更新 `docs/cjk.md` 的覆盖表和 `README.md` 的 CJK 数字。
