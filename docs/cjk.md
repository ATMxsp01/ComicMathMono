# ComicMathMono CJK：Yozai 衍生 CJK 伴生字体

`dist/ComicMathMono-CJK-{Regular,Bold}.ttf` 是主字体的 **CJK 伴生层**，family 为
`ComicMathMono CJK`。它不烤进主字体，而是通过 fontconfig 的 `monospace` 链排在
`ComicMathMono` 后面；主字体负责拉丁/数学/emoji，它只负责 CJK。

## 1. 为什么是 Yozai

- Yozai 的手写、圆润、略随意的笔画和 ComicShanns 的 comic 拉丁是同一路的；
  Sarasa（思源黑体）太“几何/办公”，风格上和 ComicMath 各写各的。
- Yozai 的假名/标点也是手写风，中文和日文混排时风格统一。
- 但 Yozai 是**比例字体**（拉丁 A=718、i=226、W=899），不能直接当终端字体；
  必须只取 CJK、强制等宽，做成伴生字体。

## 2. 源与版本

| 用途 | 源 | 版本 | 文件 |
|---|---|---|---|
| Regular | Yozai Medium | 0.868 | `sources/yozai/Yozai-Medium.ttf` |
| Bold | Yozai Bold | 0.850 | `sources/yozai/Yozai-Bold.ttf` |
| 27 个缺口 | Noto Sans CJK SC 子集 | 2.004 | `sources/NotoSansCJKsc-Gap27-{Regular,Bold}.ttf` |

- 0.868 只有 Light / Regular / Medium；Medium 的视觉重量最接近 ComicMathMono Regular。
- 0.868 没有 Bold；0.850 是最后一个带真 Bold 的版本。
- 0.850 Bold 对《通用规范汉字表》8,105 字、GB2312 汉字、JIS X 0208 都是 **100%** 覆盖；
  缺的 3,363 个 URO 字都在 8,105 之外，粗体遇到时回退到 Medium 或 Jigmo。

## 3. 子集规则：只取 CJK W/F

`tools/make_cjk_companion.py` 只保留 **EAW = W/F 的 CJK 相关码点**：

**包含**

- URO、Yozai 有的 ExtA/ExtB（其余由 Jigmo 补）
- CJK 标点（`，。！？：；、（）【】「」『』…`）
- 全角形式（含全角字母数字；它们是 W/F 的 CJK 宽度字形）
  - 这里的 `ＡＢＣ１２３` 是**全角 CJK 宽度**字形，不是 Yozai 的比例拉丁；它们占 2 格，
    不会破坏等宽。ASCII / 比例拉丁 / ASCII 标点已全部排除。
  - 如果你连全角拉丁/数字也不想留，可以删掉 `FF10–FF19`、`FF21–FF3A`、`FF41–FF5A`；
    但 CMM / Jigmo 都没有这些码点，会落到系统 Noto/Sarasa，完整性不如保留。
- 全角平假名/片假名、注音符号、CJK 笔画
- Enclosed CJK、CJK 兼容表意、竖排形式、CJK 兼容形式
- 27 个 Yozai/Jigmo 都没有的缺口码点（从 Noto 补）

**排除**

- ASCII / Latin / Latin-1 / 比例拉丁 / ASCII 标点
- 希腊文、西里尔文、IPA、组合附加符
- 制表符、几何图形、箭头、数学符号
- **半角片假名**（H，窄字形；若塞进 1100 会破坏等宽，交给 Jigmo 61/63，极少数回退系统 CJK）
- PUA、所有 500 / 0 宽字形

这样伴生字体里没有任何比例字形，`post.isFixedPitch=1` 才是真的。

## 4. 度量

| 项目 | 值 |
|---|---|
| upem | 1000 |
| 所有字形 advance | **1100**（= 主字体 550 的严格 2 倍） |
| 轮廓居中 | 每个简单字形 **+50**，复合字形跟着组件移动 |
| `post.isFixedPitch` | 1 |
| panose | `bFamilyType=2`、`bProportion=9`（monospaced） |
| hhea | 1030 / -248 / 0 |
| OS/2 typo | 1030 / -248 / 0 |
| `usWinAscent/Descent` | 1030 / 248 |
| `hhea.advanceWidthMax` | 1100 |
| `OS/2.xAvgCharWidth` | 1100 |
| hinting | 无；带 7 字节 smart-dropout `prep` |

## 5. 覆盖

| 范围 | Regular | Bold | 说明 |
|---|---:|---:|---|
| URO | **20,992 / 20,992** | 17,629 / 20,992 | Bold 缺的 3,363 字回退 Medium |
| 通用规范汉字表 8,105 | **8,105 / 8,105** | **8,105 / 8,105** | 三级全满 |
| GB2312 汉字 | **6,763 / 6,763** | **6,763 / 6,763** | 全满 |
| ExtA | 521 / 6,592 | 259 / 6,592 | 其余 Jigmo 全补 |
| ExtB | 655 / 42,720 | 366 / 42,720 | 其余 Jigmo 全补 |
| 平假名 | 93 / 93 | 88 / 93 | Bold 少 5 个罕见假名 |
| 片假名 | 96 / 96 | 94 / 96 | Bold 少 2 个罕见假名 |
| 半角片假名 | 0 | 0 | Jigmo 61/63；其余回退系统 CJK |
| 谚文 | 0 | 0 | 交给 Jigmo |
| 兼容表意 | 103 / 472 | 103 / 472 | 其余 Jigmo |
| 27 个缺口 | 全有 | 全有 | Noto 子集 |

`tools/verify_cjk.py` 会断言：只含 W/F、没有 ASCII、所有 advance=1100、URO 数、
8105 全满、GB2312 汉字全满、JIS X 0208 假名/汉字全满、27 个缺口全有、无 Mac name、`.notdef` 非空、
smart-dropout `prep` 存在。

## 6. 27 个缺口码点

Yozai ∪ Jigmo 之后仍缺的 CJK W/F：

```text
U+115F U+3164
U+32CC U+32CD U+32CE U+32CF U+337A U+33DE U+33DF U+33FF
U+FE14 U+FE15 U+FE16 U+FE17 U+FE18 U+FE19
U+FE34 U+FE47 U+FE48 U+FE49 U+FE4A U+FE4B U+FE4C U+FE4D U+FE4E U+FE4F
U+FFE6
```

全部由 `sources/NotoSansCJKsc-Gap27-{Regular,Bold}.ttf` 补齐。重新生成需要系统的
Noto Sans CJK：

```bash
python3 tools/make_noto_gap_subset.py
```

## 7. fontconfig 链

```xml
<match target="pattern">
    <test qual="any" name="family"><string>monospace</string></test>
    <edit name="family" mode="prepend" binding="strong">
        <string>ComicMathMono</string>       <!-- 拉丁 / 数学 / emoji -->
        <string>ComicMathMono CJK</string>   <!-- CJK（Yozai 衍生） -->
        <string>Jigmo</string>               <!-- ExtA / ExtB–J / 谚文 / 兼容表意 -->
        <string>Jigmo2</string>
        <string>Jigmo3</string>
    </edit>
</match>
```

- Sarasa Mono SC 已从链里移除；不再需要。
- `monospace` 链里**不再需要 Noto Color Emoji**：CMM 的彩色 emoji 来自
  Noto COLRv1 2.057（Unicode 18），比系统 Noto 2.051 更新；相比系统 Noto，
  CMM 只缺 `U+0000`/`U+000D` 和 21 个 Noto 内部 PUA（`U+FE4E5–FE4EE`、
  `U+FE82C`、`U+FE82E–FE837`），都不是可键入字符。所有真实 emoji 和
  ZWJ / 键盘帽 / 旗帜序列都有（HarfBuzz 实测合成单字形）。
- 全局 append 规则仍保留 `Noto Color Emoji`，供 sans-serif/serif 等不在 CMM
  链里的场景使用。
- kitty 的 fallback 查询的是 generic `monospace`，所以伴生字体必须放在这条链里，
  而不是只追加在 `ComicMathMono` family 后面。
- 主字体 `ComicMathMono` 仍然负责 ASCII/Latin/数学/emoji；伴生字体没有任何 ASCII，
  不会抢走英文。

## 8. 命名与 OFL

Yozai 是 OFL-1.1，保留名称（Reserved Font Names）包括 `Yozai`、`悠哉`、`悠哉字体`，
以及 Y.OzFont 的 `Y.Oz` / `YOz`。

按 OFL 1.1 第 3 条，限制**只适用于 primary font name as presented to the users**，
也就是 family / full / PostScript name。因此：

| 用途 | 是否可用 Yozai |
|---|---|
| family / full / PostScript name | ❌ 不可 |
| 文件名 / 项目名 / 工具名 | ✅ 可用（描述性，不是 primary font name） |
| README / NOTICE / name ID 10 | ✅ 可用（来源说明，OFL 第 4 条允许致谢） |

本项目的做法：

```text
Family:     ComicMathMono CJK
Full name:  ComicMathMono CJK Regular / Bold
PostScript: ComicMathMonoCJK-Regular / Bold
文件:       ComicMathMono-CJK-Regular.ttf / -Bold.ttf
源目录:     sources/yozai/
```

来源写在 `sources/yozai/README.md`、`NOTICE.md` 和 name ID 10 里；字体菜单里保持
`ComicMathMono CJK`，不使用保留名称。

## 9. 构建与校验

```bash
python3 tools/make_cjk_companion.py
python3 tools/verify_cjk.py
```

- 构建是**可复现**的：脚本会带 `PYTHONHASHSEED=0` 重启，`head.created/modified` 固定为
  `SOURCE_DATE_EPOCH`。连续构建两次的 SHA-256 应完全一致。
- CI 会运行同一个构建脚本，并用 `git diff -- dist/` 检查提交的伴生字体是否与源码一致。
- `tools/make_noto_gap_subset.py` 只在**重新生成 27 字形子集**时需要系统 Noto；
  日常构建只依赖仓库里的 `sources/NotoSansCJKsc-Gap27-*.ttf`。

## 10. 已知 fontbakery 结果

CJK 伴生字体不是 Google Fonts 字体，以下项是**有意保留**的：

| 检查 | 结果 | 原因 |
|---|---|---|
| `file_size/massive-font` | FAIL | 20,992 个 URO 字形，14.3 MB / 12.0 MB；CJK 字体不可避免 |
| `whitespace_glyphs` | FAIL | 故意只含 CJK W/F，不含 U+0020/U+00A0；空格由主字体提供（550 宽） |
| `opentype/post_table_version` | WARN | 用 format 3 省体积；主字体同样取舍 |
| `opentype/monospace` / `bad-numberOfHMetrics` | WARN | 所有 advance=1100，fontTools 会自动压到 1；规范建议 3，见 fontTools #3014 |
| `cjk_chws_feature` | WARN | 终端字体不做竖排 `chws/vchw` |
| `overlapping_path_segments` | WARN | Yozai 手写轮廓本身有重叠；不修，避免改变字形 |

主字体四个 face 仍保持 **FAIL 0**；完整说明见
[`fontbakery-warnings.md`](fontbakery-warnings.md)。
