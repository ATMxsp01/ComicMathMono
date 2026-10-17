# fontbakery `check-universal` 的已知 WARN 与豁免理由

本文档记录 `fontbakery check-universal` 在本项目四个 face 上**仍然会报、但我们有意不修**的
检查项，以及为什么。目标：让后来的人一眼看出"这是已知的取舍"，而不是漏修。

复现：

```bash
pip install -r requirements.txt
fontbakery check-universal --skip-network dist/*.ttf
```

## 当前基线

| 项目 | 结果 |
|---|---|
| FAIL | **0** |
| WARN | 48（9 个检查 code × 4 face；本文 §2 按 8 个小节归类，其中 2.5 含 2 个 code） |
| PASS | 见运行输出 |

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

## 3. 与本文件相关的不变量

| 不变量 | 由谁保证 |
|---|---|
| 行高 1278、`sTypoAscender ≥ Agrave` 高度 | `build.py` 的 `ASCENT/DESCENT` + `verify.py` 13i |
| 没有不可达字形（含 UVS / COLR 引用） | `build.py::drop_unreachable_glyphs()` + `verify.py` 13h |
| 等宽 0/550/1100、`hmtx` 尾部压缩 | `verify.py` 4/13c |
| 四 face 纵向指标与覆盖一致 | `verify.py` 家族级检查 |
| 构建可复现 | `.github/workflows/build.yml` 的 dist/ diff 检查 |
| name 表 ID 齐全（8/9/10/11/12/19/21/22）、URL 为 https、WWS 与 typographic 一致、ID7 为空 | `verify.py` 13b |
