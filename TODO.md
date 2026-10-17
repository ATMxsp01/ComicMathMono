# TODO — 未完成事项（P2 及以后）

「字体体检」报告里的 P2 清单，以及后续排查中新发现、但尚未处理的项。

> **已完成**：P0（OTS 拒收、GSUB 被删）、P1（四 face 元数据/纵向指标统一、斜体覆盖率补齐、
> 组合符与 `Default_Ignorable` 0 宽、控制码不映射、Unicode 16 新组合符）、构建工程化
> （可复现构建 + CI 防漂移 + CJK 子集转 TrueType）、文档与许可订正、P2 的 A2（hmtx 尾部压缩，
> 每 face ~85 KB）、A1 的决策（保持四 face 都带 emoji）、C2（STAT 表）、C3（smart dropout）
> C4（Coptic 大写合成）、C5（WARN 定调）与 C6（name 表补齐）。fontbakery `check-universal`
> 目前 **FAIL 0 / WARN 32**。
> 详见 git 历史与 README。

状态：`[ ]` 未开始 · `[~]` 进行中 · `[x]` 完成 · `[-]` 明确不做（保留说明）

---

## 体积

- [-] **A1 · emoji 四份重复（最大项）** —— **决策已定：保持现状**（四个字重都带 emoji，
  行为最简单、fallback 链最干净、粗体也保留 VS15/VS16 切换）。四个 face 的码点覆盖保持完全一致。
  如果以后想瘦身，可选方向：只 Regular/Bold 带 emoji（省 ~8.8 MB，但斜体 emoji 要系统兜底、粗体丢
  VS 切换）；或另出「无 emoji」变体。每 face emoji 相关约 **4.4 MB**（glyf 3.39 MB + COLR 1.07 MB
  + CPAL 25 KB），约占 53%。

- [x] **A2 · hmtx 尾部压缩（已完成）** —— 每 face 省 **~84.6 KB**（四 face 共 **~330 KB**）。
  - 做法：构建收尾按 advance 重排字形，把最常见的 advance（1100，emoji 段）排到字序尾部
    （`build.py::compact_hmtx()`），`hhea.numberOfHMetrics` 63 591 → **21 321**，hmtx 254 KB → 170 KB。
  - 关键：重排必须在 **GPOS 之前**（`finalize_widths_and_order()` → `add_mark_feature()`），
    因为 GPOS 的 `Coverage` 与 `MarkArray`/`BaseArray` 是按 GID 对齐的平行数组，而 feaLib 的
    `buildCoverage` 按当前 GID 排序。GSUB（Merger 产物）不受影响：其 Coverage 在 preWrite 时
    从 `ligatures` 字典按 GID 重新生成。
  - 教训：在 layout 建好之后调 `font.setGlyphOrder()` 会让 Coverage 失序，OTS 报
    `bad start coverage index` 并拒收（本次先踩后修，已在代码注释里写明）。
  - 纯体积收益，`hmtx` 两种编码的字形 advance 完全等价（已逐字形核对）。

- [-] **A3 · 字形可达性裁剪** —— 实测只剩 6 个字形 / ~1 KB 不可达，无收益，不做。

---

## 功能改进（README「已知限制」里对应的项）

- [x] **E1 · emoji ZWJ / VS16 序列修复（C 系列之后的审计发现，已修）**
  现象：`❤️‍🔥` `🏳️‍🌈` `🏴‍☠️` `👁️‍🗨️` `🧑‍⚕️` 等**标准写法**（带 VS16）全部散成 3~4 个字形。
   - 根因：文本默认 emoji 的 cmap 是**单色**字形、VS16 才切彩色，而 Noto 的 ZWJ 连字按
     **单色**字形名写 → 一带 VS16 就匹配不上。
   - 修 1：`add_colour_ligature_variants()` 给连字补彩色变体（+1,190 条），并按组件数
     从长到短排序 `LigatureSet`（HarfBuzz 取第一个匹配，短连字会抢先）。
   - 修 2：默认彩色的 emoji 也登记 `(cp, FE0F) -> None`（DefaultUVS 1,231 条），
     否则 FE0F 会残留成不可见字形（`🏴 + FE0F + ZWJ + ☠ + FE0F` 曾散成 2 个）。
   - 结果：GSUB 里 **2,564 条**连字在 RGI emoji 形式下**全部**合成单字形；
     `verify.py` 已加入全量回归（并做了反例验证）。代价 +15 KB/face。

- [x] **D1 · mark-to-mark（已完成）** —— `add_mark_feature()` 现在同时生成 mark-to-base 与
  mark-to-mark：
  - 标记按自身墨迹分成 **above / below** 两类，第二个同类标记落在前一个的墨迹顶（或底）上；
  - 高度量化到 20 单位（379 个标记 → above 43 档 + below 15 档），GPOS 只涨 ~1.6 KB（正体）；
  - **关键坑**：`mark` 特性原来只注册在 `DFLT` 下，实测希伯来文（hebr）会**退回 HarfBuzz 的
    启发式定位**（偏移全是猜的，`shin+qamats` 得到 (158,-17)）。显式注册
    `latn/grek/cyrl/hebr/arab/armn/geor` 后才走我们的锚点（`y=-40` 正确叠加）。
  - 实测：`x + U+0301 + U+0304` → macron `y_offset=740`；`ש + dagesh + qamats` 两个标记不重叠。
  - `verify.py` 加了断言（GPOS 必须有 LookupType 6 + 叠加实测 y_offset>0）。

- [ ] **D2 · Arabic 连写形态**
  目前只有**孤立形态**（未并入 JuliaMono 的 `init`/`medi`/`fina` GSUB）。要做需要把 Julia 的
  排版规则并入（含字形重命名 + 规则重映射），或换一个覆盖更好的源字体。

- [ ] **D3 · 轮廓去重**
  用 `fontTools.ttLib.removeOverlaps` 清理 overlapping path segments（个别光栅器会有伪影）。
  会改动轮廓、增加体积，需要重跑全套验证（OTS + shaping + 视觉抽查）。

---

## 剩余 fontbakery 项

- [x] **C2 · 加 STAT 表（已完成）** —— `build.py::add_stat_table()`，每个 face 声明 `wght`(400/700)
  + `ital`(0/1)，`ital` 放最后，正体 `ital=0` 带 elidable(0x2) + LinkedValue 1.0，斜体 `ital=1`。
  - 关键约束：**静态字体每个轴只能有 1 条 AxisValue**（`STAT_in_statics`）；把变量字体的 STAT
    原样塞进静态字体会让 Windows 只读第一条，所有字重显示成同一个名字。
  - `buildStatTable(..., macNames=False)`：默认 `True` 会把 Mac(platform 1) name 记录加回来，
    直接影响 C1 的 `no_mac_entries`。
  - 体积代价约 +130~180 B/face；`verify.py` 已加断言（缺 STAT / ital 不在最后 / 每轴 >1 条 /
    wght 与 usWeightClass 不一致 / ital 值或 flags 不对，都会失败）。

- [x] **C3 · smart dropout（已完成）** —— `build.py::add_smart_dropout_prep()`：给每个 face 补一个
  7 字节的 `prep`（`PUSHW 511 / SCANCTRL / PUSHB 4 / SCANTYPE`），打开 dropout control。
  - 这条检查**与 `gasp` 无关**（早先的判断有误，已更正）：`smart_dropout` 只在 `prep` 字节码里
    找 `b8 01 ff 85 b0 04 8d`。不 hint 任何轮廓，只是把开关显式打开 —— 正是
    `gftools fix-nonhinting` 对未 hinting 字体做的事。
  - 代价 +24 B/face；**故意不加 `gasp`**（fontbakery 不要求，且字号区间写错可能在某些渲染器上
    反而关掉抗锯齿）。
  - `verify.py` 已加断言（缺 `prep` 或字节不对都会失败），并用反例验证过。

- [ ] **H1 · 真 hinting（可选，独立排期）**
  当前字体完全没有指令（无 `cvt`/`fpgm`，0 个字形带指令）。若要小字号更锐利，可对**非 emoji**
  字形跑 `ttfautohint`：
  - 42 000 个 COLR 图层字形没有意义（矢量绘制，不走字形 hinting）；
  - 需要保证 550 单位格子对齐不被破坏，并重跑全部验证（OTS/shaping/视觉抽查）；
  - 会改变小字号观感，属于"改设计"级别，不作为默认行为。
  参考现状：JuliaMono / Liberation Mono / Noto Sans Mono 都是带 hinting 的；我们的三个轮廓上游
  （ComicShanns、SeriousShanns、Noto Color Emoji）本身都没有 hinting。

- [x] **C4 · Coptic 大写缺失（已完成）** —— `build.py::add_coptic_capitals()`：从本 face 的小写
  统一缩放到 cap height(668)、水平居中、advance 550，合成 U+2CAE / U+2CDE。
  - 为什么不用 Noto Sans Coptic 的字形：它是比例字体，大写 psi 宽 738、adv = 834，塞进 550 的
    等宽格子要横向压缩 ~27%，会变形；而且它的 psi 小写是下伸设计，和我们的基线设计不协调。
  - 坑：**cap height 不能用 `H` 的 bbox 现算** —— 斜体 `H` 被倾斜放大（yMax 776 vs 真实 668，
    差 ≈ 450×tan12.7°），最初据此合成的大写会偏大（NGI 773）。改用设计常量 668。
  - 代价 +212~236 B/face；`verify.py` 加了两条断言（大小写配对齐全；合成大写的 advance/墨迹
    不越界），并用反例验证过。

- [x] **C5 · WARN 逐条定调（已完成）** —— 40 条 / 10 类，修掉 2 类，其余 8 类文档化。
  - 修：`typoascender_exceeds_Agrave` → `ASCENT/DESCENT` 928/−350 → **1030/−248**（行高 1278
    不变；斜体 Agrave 因倾斜 bbox 到 1026，所以必须按最坏值取）。verify 13i 断言。
  - 修：`unreachable_glyphs` → `drop_unreachable_glyphs()` 按
    `cmap ∪ UVS ∪ GSUB输出 ∪ COLR引用` 迭代删孤儿（含 Noto 的 12 个只有 COLR 记录+ClipList
    的空基字形，以及它们链式带出的图层字形）；Regular/Bold 删 32 个、Italic 46、BoldItalic 44。
    verify 13h 断言。**这条现在 PASS**。
  - 保留（逐条理由+实测数字见 [`docs/fontbakery-warnings.md`](docs/fontbakery-warnings.md)）：
    `contour_count`、`overlapping_path_segments`（试过清理零长/重复点，会改变 13 102 个字形
    的墨迹面积，放弃）、`post_table_version`（转 fmt2 要 +730 KB/face）、`xavgcharwidth`、
    `monospace`（bad-numberOfHMetrics + mono-outliers）、`file_size`、`cjk_not_enough_glyphs`、
    `alt_caron`（已目视确认）。
  - 结果：**FAIL 0，WARN 32（8 类 × 4 face）**。选择写文档而不是加 `.fontbakeryrc` 真豁免 ——
    避免以后这些检查的回归被一起遮住。

- [x] **C6 · name 表补齐（已完成）** —— 新增 ID 8/9（`ATMxsp01`）、10（简介）、11/12（两个
  https URL）、19（样文）、21/22（WWS，与 ID16/17 一致）。
  - **ID7（商标）留空是刻意的**：没有注册过商标就不做声明（verify 会断言它必须为空）。
  - ID18（Compatible Full）只有 Mac 读，而 Mac 记录已删 → 不加；ID23/24（CPAL 明暗）、
    ID25（可变字体前缀）不适用。
  - `OS/2.achVendID` 保持 `NONE`（按你的决定），所以 ID3 仍是 `Version 1.0;NONE;<PS 名>`。
  - `verify.py` 13b 扩展：必需 ID 集合加入 8/9/10/11/12/19/21/22，并断言 11/12 以 `https://`
    开头、21==16、22==17、ID7 为空。fontbakery 的 name 相关 6 项检查全 PASS。

---

## 源与流程

- [x] **B4 · 源字体 / Unicode 数据更新流程（已完成）** —— 写进
  [`sources/README.md`](sources/README.md) 的「更新流程（三个版本必须对齐）」：
  Nerd Fonts / Noto Color Emoji / `emoji-data.txt` 三者的关系表 + 8 步 checklist
  （重点：Noto 与 emoji-data 必须同 Unicode 版本；看 `无单色源丢弃 M 个` 是否突然变大）。
  Nerd Fonts 版本、Noto Color Emoji 版本、`data/emoji-data.txt` 三者必须互相对齐；
  写成 checklist。注意：升级 Noto Color Emoji 后要按新的 `emoji-data.txt` 重查每个新 emoji 的
  默认呈现（`Emoji_Presentation`），否则文本呈现的字形会缺单色轮廓 —— 线索见
  `docs/emoji-presentation.md` §4b、`sources/README.md`。

- [x] **B5 · 记录 CJK 子集的生成来源版本（已完成）** —— 已在 `sources/README.md` 注明由
  Noto Sans CJK **2.004**（`name` ID5，`head.fontRevision` 2.00399）生成，并说明它是派生文件。
  `sources/NotoSansCJKsc-Symbols5.ttf` 由系统 Noto Sans CJK 现场生成，但仓库里没有记录生成时用
  的版本。可在 `sources/README.md` 注明（例如 `NotoSansCJK-Regular.ttc` 的 `name` ID5）。

---

## 参考

- `tools/verify.py` —— 15 组已固化的回归断言（含 OTS、emoji 序列 shaping、四 face 一致性、name 表）。
- `.github/workflows/build.yml` —— 构建 → 回归校验 → 「dist/ 与源码一致（可复现构建）」。
- `docs/` —— 每个踩过的坑对应一份说明。
