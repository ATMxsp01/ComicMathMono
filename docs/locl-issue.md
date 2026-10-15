# 记一次合并字体里的 `locl` 陷阱：数字为什么"消失"了

> 这篇文章记录 `ComicMathMono` 构建过程中踩到的一个坑，以及为什么 `build.py` 里有一个
> 看起来突兀的 `strip_locl()`。对任何用 `fontTools.merge.Merger` 合并字体的人都有参考价值。

## 现象

在 kitty 里使用 `ComicMathMono`，会出现：

- 单独一个 `9` → 正常显示；
- `9p` → **只看得到 `p`，`9` 不见了**；
- `9`、`10` 之类的数字在"拉丁文上下文"里会消失，前面还留出一段空白。

而且表现很"玄学"：在 shell 里正常，在某个 TUI 里不正常；从 TUI 复制 `9p` 到 shell，
一开始 `9` 看不到，再敲几个字又能看到了。

## 结论（先给答案）

字体里被塞进了一条**本不该存在的 `locl` 特性**，它在**拉丁文片段**里把 ASCII 数字/空格/`#`/`*`
替换成了 Noto 的空/宽字形。根因不在终端，也不在应用，而在字体合并器：

**`fontTools.merge.Merger` 会自动合成 `locl`。** 它的官方文档写得很清楚：

> If multiple glyphs map to the same Unicode value, and the glyphs are considered
> sufficiently different (that is, they differ in any of paths, widths, or height),
> then subsequent glyphs are renamed and **a lookup in the `locl` feature will be
> created to disambiguate them.** … a lookup will be inserted into the `locl`
> feature (creating it if necessary) **under the `latn` script** …
>
> —— `fontTools/merge/__init__.py`（类 `Merger` 的 docstring）

## 为什么会被合成

`build.py` 用 `Merger().merge([base, noto])` 把整份 Noto Color Emoji (COLRv1) 合并进来。
`base`（ComicShanns + Julia）和 `noto` 在很多**码点**上重合，且字形不同（base 是 550 宽的文本字形，
Noto 是 1100 宽的 emoji/空格形）。于是 `Merger`：

1. 把后来者（Noto）的重合字形重命名，例如 `nine` → `nine.1`；
2. 合成一条 `locl` 规则，把 `nine` → `nine.1` 串起来，注册在 `latn/dflt` 下。

关键点：**判重是按"码点"，不是按"字形名"。** 只要两个字体都覆盖同一码点、且字形不同，就算重复。
例如：

| 码点 | base 字形名 | Noto 字形名 | 是否进 locl |
|---|---|---|---|
| U+0039 `9` | `nine` | `nine` | ✅ |
| U+2665 `♥` | `oct-heart` | `heart` | ✅ |
| U+26A1 `⚡` | `oct-zap` | `uni26A1` | ✅ |
| U+2764 `❤` | （base 没有） | `uni2764` | ❌ 不进 |

## 为什么会"看不见"

`locl` 在 OpenType 里是**默认自动生效**的特性（只要脚本/语言匹配上就会应用）。所以凡是
"拉丁脚本片段"，里面的数字/空格都会被换成 Noto 的那个字形。

而 Noto 那些目标字形在这个合并字体里是**空轮廓 + 双倍宽**（彩色的部分在 COLRv1 里，
终端不一定渲染）；再加上成品用 `post` 表 format 3.0 保存、重载时按 gid 命名，
这些目标字形就变成了 `glyph12908` 这种名字，locl 映射最终看起来是：

```
nine -> glyph12908      # 一个 1100 宽、没有轮廓的字形
space -> glyph12874
...
```

于是 `9` 被换成了一个空白宽字形 —— 看起来就是"9 不见了"。

这也解释了那些"玄学"：
- 单独 `9`：片段是 Common 脚本，`locl` 不触发 → 正常；
- `9p`：片段是 Latin 脚本 → `locl` 触发 → `9` 消失；
- shell 里看着正常：语法高亮插件（如 fast-syntax-highlighting）会把数字**单独染色**，
  变成独立的 Common 片段，从而绕过了 `locl`；TUI 把整行当同一个样式片段，就中招了。

## 修复

`build.py` 的 `strip_locl()`：在合并完成后**删除整条 `locl`**（含其孤儿 lookup）。

之所以可以整条删，是因为本字体的 base（ComicShanns/SeriousShanns/Julia）**本来就没有任何合法的
`locl`**——这条 `locl` 完全是 `Merger` 合成的。对"base 自带合法 `locl`"的场景，则应只删合成出来的那部分。

## 给同样在做字体合并的人的提醒

- 合并后用 `ttx -l` / `fontTools` 看一下 GSUB 里是否凭空多了 `locl`；
- 合并顺序会影响谁能拿到"正统"字形名；
- 若不需要 Merger 的消歧，可以考虑**只把目标字体里 base 缺失的码点并入**（本项目里的
  `copy_julia_into()` 就是这个思路），从源头避免"同码点重复"，也就不会合成 `locl`；
- 排查时 `post` 表 format 3.0 + gid 命名会让字形名看起来很陌生，别被误导。
