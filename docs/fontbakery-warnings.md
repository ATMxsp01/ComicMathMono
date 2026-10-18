# fontbakery `check-universal` 的已知 WARN 与豁免理由

本文档记录 `fontbakery check-universal` 在本项目四个主 face 上**仍然会报、但我们有意不修**的
检查项，以及为什么。目标：让后来的人一眼看出"这是已知的取舍"，而不是漏修。

复现主字体（四个 face）：

```bash
pip install -r requirements.txt
fontbakery check-universal --skip-network \
  dist/ComicMathMono-Regular.ttf dist/ComicMathMono-Bold.ttf \
  dist/ComicMathMono-Italic.ttf dist/ComicMathMono-BoldItalic.ttf
```

CJK 伴生字体单独看（它有意只含 CJK，见 §3）：

```bash
fontbakery check-universal --skip-network dist/ComicMathMono-CJK-*.ttf
```

## 当前基线

| 项目 | 主字体四 face | CJK 伴生字体两 face |
|---|---|---|
| FAIL | **0** | 4（2 个 code × 2 face，见 §3） |
| WARN | 48（9 个检查 code × 4 face；§2 按 8 个小节归类，其中 2.5 含 2 个 code） | 8（4 个 code × 2 face，见 §3） |
| PASS | 见运行输出 | 见运行输出 |

C5 之前是 40 条（10 类）。已修掉的两类见 §1、§2。

---

## 1. 已修复（保留记录，防止回退）

### `typoascender_exceeds_Agrave` —— 已修
- **检查什么**：`OS/2.sTypoAscender` 是否 ≥ `Agrave` 的 yMax。若小于，macOS 可能改用更大的行高。
- **事实**：`Agrave` yMax = 988（斜体因倾斜，bbox 被放大到 **1026**）。
- **修法**：`ASCENT/DESCENT` 从 `928/−350` 挪到 `1030/−248`，**行高 1278 不变**，只是把
  单位从 descent 移到 ascent（文字在行框内下移 102/1278 ≈ 8%，14px 字号约 1.1px）。
  `hhea` 同步。
- **回归保护**：`tools/verify.py` 13i 断言 `sTypoAscender ≥ Agrave yMax`。

### `unreachable_glyphs` —— 已修
- **检查什么**：有没有既不在 cmap、也不是 GSUB 输出、也不被 COLR 引用的字形。
- **事实**：上游留下了三类死字形：
  1. ComicShanns 的 4 个**未编码字形**（`Ucaseircumflex` / `lowercasearon` /
     `ccommaaccent` / `idotaccent`）——源字体里就没有 cmap 映射，也没被组件引用；
  2. 合并时被改名的 `.null` / Noto 的 `.notdef` 副本 —— 改名后没人引用；
  3. Noto 的 12 个 "有 COLR 基字形记录 + ClipList 裁剪框，但没有码点"的空彩色基字形；
     删掉它们后，其图层字形也成了孤儿（链式）。
- **修法**：`build.py::drop_unreachable_glyphs()` —— 按
  `cmap ∪ UVS ∪ GSUB输出 ∪ COLR引用` 求可达集，**迭代到不动点**（链式孤儿），删字形时
  同步删 COLR 的 `BaseGlyphPaintRecord` 与 `ClipList.clips` 条目。Regular/Bold 删 32 个，
  Italic 删 46 个，BoldItalic 删 44 个。
- **回归保护**：`tools/verify.py` 13h（判据同 fontbakery，但**额外把 cmap format 14 / UVS
  算作可达**）。

> 注意：fontbakery 的 `unreachable_glyphs` 对 COLRv1 只检查 `BaseGlyphRecordArray`（v0 结构）
> 与 `Paint.Glyph` / `LayerList.Paint[i].Glyph` 的**顶层**引用，不递归嵌套 paint，也不看
> `PaintColrGlyph` 与 `ClipList`。本项目按"真实可达性"处理，所以 `verify.py` 的 13h 是更严格的
> 判据。

---

## 2. 有意保留的 WARN（9 个 code × 4 face = 48 条）

### 2.1 `contour_count`（`contour-count`）

**检查什么**：每个字形的轮廓数是否落在"常见值"范围内（基于大量参考字体统计）。

**报什么**（Regular）：

| 字形 | 实测 | 期望 | 原因 |
|---|---|---|---|
| `at` | 1 | 2 | ComicShanns 把 @ 画成一笔连写 |
| `h` / `Uhorn` | 2 | 1 | 手写体把竖干和拱肩分成两个轮廓 |
| `hcircumflex` / `uni01A6` | 3 | 2 | 同上 + 重音 |
| `uni01CB` / `uni01F5` / `uni023A` | 4 | 3 | 同上 |
| `Iotatonos` / `uni0235` | 1 | 2 | 手写连笔 |

**为什么不修**：这是**设计差异**，不是 bug。检查本身就是启发式的
（"divergences ... may simply indicate a significantly different design"）。
强行改轮廓数会破坏字体观感。

**结论**：保留。`h` 的"第 2 个轮廓"其实是一个**全点重合的退化轮廓**（6 个点都在
(176,212)，零面积）—— 它同时导致 `overlapping_path_segments` 报警。我们评估过在构建时
清理零长/重复点，但实测会**轻微改变 13,102 个字形的墨迹面积**（bbox 不变），为"不改形状"
的承诺起见放弃了。

### 2.2 `overlapping_path_segments`（`overlapping-path-segments`）

**检查什么**：同一轮廓里是否有坐标完全重复的线段（零长段 / 重复段）。

**报什么**：`h`、`hcircumflex`、`heart`(U+2665)、`uniE0C4`，各 1~3 处，例如
`B<<177,212>-<177,212>-<177,212>>`（三个点同坐标）。

**为什么保留**：这些段**零面积**，不改变填充区域，主流光栅器（FreeType/CoreText/DirectWrite）
都能正常渲染；它们来自上游 ComicShanns / Noto 的原始轮廓。清理需要重写点序列，实测会改变
部分字形的微小面积（见 2.1），风险大于收益。

**结论**：保留。

### 2.3 `opentype/post_table_version`（`post-table-version`）

**检查什么**：`post` 表格式。建议 2（带字形名），我们用的是 3（无字形名）。

**为什么不修**：实测转 format 2 会增加 **≈ 730 KB/face**（63,611 个字形名），四个 face
合计 +2.9 MB，只为在字体检查工具里看到可读的字形名 —— 对终端字体毫无收益。

**结论**：保留。副作用：用工具打开时字形名是 `glyphNNNNN`。

### 2.4 `opentype/xavgcharwidth`（`xAvgCharWidth-wrong`）

**检查什么**：`OS/2.xAvgCharWidth` 是否等于"所有字形 advance 的平均值"。

**报什么**：我们填 **550**（格子宽），按全字形平均算出来是 **918**（因为 42,000+ 个双宽
emoji 把平均值拉高）。

**为什么不修**：规格里的"平均值"对**等宽字体**没有意义 —— 每个字符占一格 550，
`xAvgCharWidth` 填 550 才符合实际排版宽度。填 918 反而会让旧版 Windows 的字符串宽度估算
偏大 67%。

**结论**：保留。

### 2.5 `opentype/monospace`（`bad-numberOfHMetrics` + `mono-outliers`）

**检查什么**：
1. `hhea.numberOfHMetrics` 是否被压到 3（"尾部等宽段"建议值）；
2. 是否所有字形同宽。

**报什么**：
1. `numberOfHMetrics = 21,317`（不是 3）；
2. 42,297 个字形（66%）宽 1100。

**为什么不修**：
1. "压到 3"的建议只适用于**整个字体只有一个 advance** 的情况；我们有三种宽度
   （0 / 550 / 1100），尾部等宽段已经是 1100 段。我们已经做了 hmtx 压缩（见 P2-A2：
   63,591 → 21,317，省 ~338 KB），但不可能压到 3。
2. 1100 的是**双宽 emoji**（`WIDE`），这是设计，不是 outlier。

**结论**：保留。

### 2.6 `file_size`（`large-font`）

**检查什么**：文件是否 < 1 MB。

**报什么**：8.3–8.4 MB。

**为什么不修**：彩色 emoji 本体就有 8 MB。四个 face 都带 emoji 是 **A1 的明确决策**
（保证任何字重下 emoji 都不回退到别的字体）。

**结论**：保留。

### 2.7 `cjk_not_enough_glyphs`（`cjk-not-enough-glyphs`）

**检查什么**：如果字体里有 CJK 字形，是否至少有 150 个（Kana 最小集）。

**报什么**：144 个。

**为什么不修**：这 144 个是**CJK 标点/包围字母**（`uni3248`…、`uni3297`、`uni3299`…），
不是"想做 CJK 字体但没做完"。本字体**明确不支持 CJK**（见 README）。为了消掉这条 WARN 而
塞 6 个假名进去毫无意义。

**结论**：保留。

### 2.8 `alt_caron`（`decomposed-outline`）

**检查什么**：`Lcaron` / `dcaron` / `lcaron` / `tcaron` 的 caron 是否用了"逗号形"而不是
`quoteright`（撇号）。

**报什么**：这 4 个字形的 caron 是**分解轮廓**（不是组件引用），检查无法自动判断，只能人工看。

**人工确认**：已目视检查（`Lcaron`/`dcaron`/`lcaron`/`tcaron` 用的都是同一套 caron 笔画，
来自 ComicShanns/SeriousShanns 的设计，不是撇号形状）。因为无法自动断言，保留 WARN。

**结论**：保留（已人工确认无误）。

---

## 3. CJK 伴生字体（`dist/ComicMathMono-CJK-*.ttf`）

CJK 伴生字体有意只含 **CJK W/F** 码点，不烤进主字体；它的 FAIL/WARN 与主字体分开看。
运行：

```bash
fontbakery check-universal --skip-network dist/ComicMathMono-CJK-*.ttf
```

当前结果：**FAIL 4（2 个 code × 2 face）**、**WARN 8（4 个 code × 2 face）**。

### 3.1 `file_size`（`massive-font`）— FAIL，有意保留

- **报什么**：Regular 14.3 MB、Bold 12.0 MB。
- **为什么不修**：URO 20,992 / 17,629 个字形，CJK 字体不可能压到 Google Fonts 的
  体积阈值；要压只能砍 URO，违背“常用中文全覆盖”的目标。
- 这是本项目的本地终端伴生字体，不是 Google Fonts 提交物。

### 3.2 `whitespace_glyphs` — FAIL，有意保留

- **报什么**：缺 `U+0020`、`U+00A0`。
- **为什么不修**：伴生字体**只含 CJK W/F**，空格由主字体 `ComicMathMono` 提供（550 宽）。
  如果在这里补空格：
  - 用 1100 宽 → 空格变成两格，破坏浏览器/编辑器的单格空格；
  - 用 550 宽 → 字体不再是全部 1100 宽，`post.isFixedPitch` 与 `hhea.advanceWidthMax`
    的等宽契约被打破。
- 主字体在链里永远排在前面，空格不会落到这里；这是有意的职责分离。

### 3.3 `opentype/post_table_version` — WARN，有意保留

- 与主字体相同：用 `post` format 3（无字形名）省体积；CJK 字体 23k 个字形名会多出
  数百 KB，对终端没有收益。

### 3.4 `opentype/monospace` / `bad-numberOfHMetrics` — WARN，有意保留

- **报什么**：`numberOfHMetrics = 1`，规范建议 3。
- **事实**：伴生字体所有 glyph advance 都是 1100，fontTools 在 `hmtx.compile()` 里会
  自动把全等宽字体压到 1 个 longHorMetric（[fontTools #3014]）；我们显式设 3 也会被压回 1。
- 这是 fontTools 的已知行为，不影响等宽；同理，`hhea.advanceWidthMax` / `xAvgCharWidth`
  仍是 1100。

[fontTools #3014]: https://github.com/fonttools/fonttools/issues/3014

### 3.5 `cjk_chws_feature` — WARN，有意保留

- **报什么**：没有 `chws` / `vchw`。
- **为什么不修**：这是终端横排字体，不做竖排标点压缩；加了也没有排版引擎会用。

### 3.6 `overlapping_path_segments` — WARN，有意保留

- **报什么**：部分 Yozai 手写轮廓有重叠/零长段。
- **为什么不修**：和主字体 §2.2 的理由相同——清理会改变手写字形墨迹，风险大于收益。

### 3.7 已修掉的项目（防止回退）

| 检查 | 修法 |
|---|---|
| `mandatory_glyphs` / `notdef-is-blank` | Bold 空 `.notdef` 补一个空心方框 |
| `no_mac_entries` | 删除所有 platformID=1 的 name 记录 |
| `smart_dropout` | 加 7 字节 `prep`：`PUSHW 511 / SCANCTRL / PUSHB 4 / SCANTYPE` |
| `fsSelection` | Regular `0xC0`、Bold `0xA0`；OS/2 version 4 |

---

## 4. 与本文件相关的不变量

| 不变量 | 由谁保证 |
|---|---|
| 行高 1278、`sTypoAscender ≥ Agrave` 高度 | `build.py` 的 `ASCENT/DESCENT` + `verify.py` 13i |
| 没有不可达字形（含 UVS / COLR 引用） | `build.py::drop_unreachable_glyphs()` + `verify.py` 13h |
| 等宽 0/550/1100、`hmtx` 尾部压缩 | `verify.py` 4/13c |
| 四 face 纵向指标与覆盖一致 | `verify.py` 家族级检查 |
| 构建可复现 | `.github/workflows/build.yml` 的 dist/ diff 检查 |
| name 表 ID 齐全（8/9/10/11/12/19/21/22）、URL 为 https、WWS 与 typographic 一致、ID7 为空 | `verify.py` 13b |
| CJK 伴生字体只含 W/F、无 ASCII、全部 1100、8105/GB2312 全满 | `tools/verify_cjk.py` |
| CJK 构建可复现 | `make_cjk_companion.py` 的 `PYTHONHASHSEED=0` + CI dist/ diff |
