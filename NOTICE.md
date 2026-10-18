# Third-Party Notices / 第三方声明

ComicMathMono 是**衍生作品**。`dist/` 下的成品字体和 `sources/` 下的源字体均来自以下上游项目。
再分发时请一并保留本文件与各许可证文本。

## 上游字体

### ComicShannsMono Nerd Font Mono — MIT
- 用途：Regular / Bold 的拉丁基底
- 版本：`1.3.2`（Nerd Fonts `3.5.1`）
- 上游：Comic Shanns Mono by dtinth — <https://github.com/dtinth/comic-shanns-mono>
- 补丁：Nerd Fonts — <https://github.com/ryanoasis/nerd-fonts>
- 版权：Copyright (c) 2018 Shannon Miwa；Copyright (c) 2023 Jesus Gonzalez；Copyright (c) 2023 Rodrigo Batista de Moraes；Copyright (c) 2024 Fini Jastrow

### SeriousShanns Nerd Font Mono — MIT
- 用途：Italic / Bold Italic 的拉丁基底（并补拉丁扩展）
- 版本：`4.0.0`（Nerd Fonts `3.2.1`）
- 上游：<https://github.com/kaBeech/serious-shanns>
- 版权：Original work Copyright (c) 2018 Shannon Miwa；Modified work Copyright (c) 2019 dtinth；Modified work Copyright (c) 2023-2024 Kyle Beechly

### JuliaMono — SIL Open Font License 1.1
- 用途：希腊 / 数学 / 箭头 / 技术 / 盲文 / 文本符号层
- 版本：`0.062`（Nerd Fonts `3.4.0`）
- 上游：<https://github.com/cormullion/juliamono>
- 版权：Copyright (c) 2020 - 2026 The JuliaMono Project Authors
- **保留字体名（Reserved Font Name）：`JuliaMono`**

### Noto Color Emoji（COLRv1）— SIL Open Font License 1.1
- 用途：彩色 emoji
- 版本：`2.057`（Unicode 18.0，2026-09）
- 上游：<https://github.com/googlefonts/noto-emoji>
- 版权：Copyright 2022 Google Inc.

> 依 OFL-1.1 要求，本衍生字体已**重命名**：主字体为 `ComicMathMono`，CJK 伴生字体为
> `ComicMathMono CJK`，均不在 primary font name 中使用任何上游保留字体名。

### Yozai（悠哉字体）— SIL Open Font License 1.1
- 用途：`ComicMathMono CJK` 伴生字体的汉字/假名层
- 版本：`Yozai-Medium.ttf` **0.868**（Regular）；`Yozai-Bold.ttf` **0.850**（Bold）
- 上游：<https://github.com/lxgw/yozai-font>
- 原始字体：Y.OzFont by Y.OzVox — <http://yozvox.web.fc2.com>
- 版权：Copyright 2020, 2024 LXGW；Original Font Data Copyright (C) Y.OzVox
- **保留字体名（Reserved Font Names）**：`Yozai`、`悠哉`、`悠哉字体`，以及
  Y.OzFont 的 `Y.Oz` / `YOz`
- 衍生说明：`ComicMathMono CJK` 只保留 CJK W/F 码点，advance 1100、轮廓 +50 居中、
  `post.isFixedPitch=1`，并重命名。来源写在 `sources/yozai/README.md`、本文件与
  name ID 10（description）中；primary font name 不使用保留名称。
- 许可全文：[`sources/yozai/LICENSE.txt`](sources/yozai/LICENSE.txt)

### Noto Sans CJK SC（子集）— SIL Open Font License 1.1
- 用途：
  - `sources/NotoSansCJKsc-Symbols5.ttf`：5 个「CJK 类 emoji」
    （`U+3030` `U+303D` `U+3297` `U+3299` `U+1F237`）的单色轮廓
  - `sources/NotoSansCJKsc-Gap27-{Regular,Bold}.ttf`：Yozai ∪ Jigmo 之后仍缺的
    27 个 CJK W/F 码点（竖排形式、CJK 兼容形式、Enclosed CJK、谚文填充符、`U+FFE6`）
- 上游：<https://github.com/notofonts/noto-cjk>
- 版权：Copyright 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'.
  Copyright 2014-2021 Google Inc. All Rights Reserved.（原始声明保留在子集的 name 表里）
- 生成方式：
  - `python3 tools/make_cjk_symbol_subset.py`
  - `python3 tools/make_noto_gap_subset.py`

### Noto Sans Symbols 2 — SIL Open Font License 1.1
- 用途：为「默认文本呈现」的 emoji 字符补单色轮廓（否则这些字符文本渲染会空白）
- 版本：`2.008`
- 上游：<https://github.com/notofonts/symbols>
- 版权：Copyright 2022 The Noto Project Authors

### Noto Sans Symbols — SIL Open Font License 1.1
- 用途：为极少数「默认文本呈现」的 emoji（如 `U+1F549` OM SYMBOL）补单色轮廓
- 版本：`2.003`
- 上游：<https://github.com/notofonts/symbols>
- 版权：Copyright 2022 The Noto Project Authors

## 数据文件

### `data/emoji-data.txt` — Unicode License
- 来源：<https://unicode.org/Public/UCD/latest/ucd/emoji/emoji-data.txt>
- 用途：判定每个码点的默认呈现（`Emoji_Presentation`），构建时据此决定
  「给单色轮廓」还是「给彩色字形」
- 版权：© Unicode, Inc.；依 Unicode License v3 分发（文件头部保留原始声明）

### `data/8105.txt` — 通用规范汉字表
- 来源：<https://github.com/cuiwenyuan/Hanzi-Chinese-Characters>
  （`通用规范汉字表_文本.txt` 第 2 列）
- 用途：`tools/verify_cjk.py` 断言 CJK 伴生字体覆盖《通用规范汉字表》全部 8,105 字
  （一级 3,500 / 二级 3,000 / 三级 1,605）
- 说明：这是 2013 年国务院公布的规范字表，属于公开标准数据；文件只保留字表本身。

## MIT License（适用于 ComicShannsMono / SeriousShanns 部分）

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## SIL Open Font License 1.1

适用于 JuliaMono、Yozai（悠哉字体）、Noto Color Emoji、Noto Sans Symbols / Symbols 2、
Noto Sans CJK SC 子集部分，以及合并后的成品字体（`ComicMathMono` / `ComicMathMono CJK`）。
全文见 [`LICENSE-OFL-1.1.txt`](LICENSE-OFL-1.1.txt)；Yozai 的版权与保留名称另见
[`sources/yozai/LICENSE.txt`](sources/yozai/LICENSE.txt)。
