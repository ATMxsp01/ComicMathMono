#!/usr/bin/env python3
"""从系统的 Noto Sans CJK 里提取那 5 个「CJK 类 emoji」的单色轮廓，做成一个小子集字体。

为什么需要它
------------
这 5 个码点（U+3030 U+303D U+3297 U+3299 U+1F237）是 **Emoji，但 Unicode 规定的默认
呈现是「文本」**，所以字体必须给它们**单色轮廓**，否则文本渲染只会画出空轮廓（字符消失）。
而唯一带单色轮廓的字体是 CJK 字体（Noto Sans CJK / Jigmo），本项目不引入 CJK 字体，
所以折中办法是：**把它们的字形单独抠出来**做成一个几十 KB 的子集，随仓库分发。

这样：
  · 构建（build.py）只依赖仓库里的 `sources/NotoSansCJKsc-Symbols5.ttf`，不需要系统装 CJK 字体
  · 只有「重新生成这个子集」时才需要系统装有 Noto Sans CJK

用法
----
    python3 tools/make_cjk_symbol_subset.py [CJK 字体路径] [-o 输出路径]

默认从 `/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc` 里挑 **SC（简体）** 那一面。
子集字体以 SIL OFL-1.1 分发（Noto Sans CJK 的原始许可），版权与许可声明保留在 name 表里。
"""
import argparse
import os
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'
DEFAULT_OUT = os.path.join(ROOT, 'sources', 'NotoSansCJKsc-Symbols5.ttf')
UNICODES = [0x3030, 0x303D, 0x3297, 0x3299, 0x1F237]
DROP_TABLES = ['GSUB', 'GPOS', 'GDEF', 'BASE', 'JSTF', 'MATH', 'morx', 'kern',
               'vhea', 'vmtx', 'VORG', 'DSIG', 'hdmx', 'LTSH', 'VDMX', 'gasp',
               'meta', 'STAT', 'fvar', 'gvar', 'avar', 'HVAR', 'MVAR', 'VVAR']


def find_sc_face(path):
    """在 TTC 里找到 family 含 'SC' 的那一面，返回 (fontNumber, family)。"""
    if not path.lower().endswith('.ttc'):
        return 0, TTFont(path, lazy=True)['name'].getDebugName(1)
    for i in range(32):
        try:
            f = TTFont(path, fontNumber=i, lazy=True)
        except Exception:
            break
        fam = f['name'].getDebugName(1) or ''
        if 'SC' in fam:
            return i, fam
        f.close()
    return 0, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', nargs='?', default=DEFAULT_SRC, help='Noto Sans CJK 字体路径（.ttc/.otf）')
    ap.add_argument('-o', '--out', default=DEFAULT_OUT, help='输出子集路径')
    args = ap.parse_args()

    if not os.path.exists(args.src):
        print(f'找不到 CJK 字体：{args.src}', file=sys.stderr)
        print('（Arch 上可以装 noto-fonts-cjk；这是「重新生成子集」才需要的依赖）', file=sys.stderr)
        return 1

    num, fam = find_sc_face(args.src)
    print(f'源字体: {args.src}')
    print(f'TTC 面 : fontNumber={num}  family={fam}')
    font = TTFont(args.src, fontNumber=num)

    upem = font['head'].unitsPerEm
    cmap = font.getBestCmap()
    missing = [cp for cp in UNICODES if cp not in cmap]
    if missing:
        print(f'源字体缺少这些码点：{["U+%04X" % c for c in missing]}', file=sys.stderr)
        return 1

    opts = subset.Options()
    opts.layout_features = []          # 子集不需要任何 layout 特性
    opts.drop_tables += DROP_TABLES
    opts.notdef_outline = True
    opts.recalc_bounds = True
    opts.recalc_timestamp = False
    opts.name_IDs = ['*']              # 保留版权/许可 name 记录（OFL 要求）
    opts.name_legacy = True
    opts.name_languages = ['*']
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=UNICODES)
    sub.subset(font)

    # 改成一个中性的 family 名，避免看起来像在分发 Noto Sans CJK 本体；
    # 版权(0)/许可(13,14) 原样保留。
    name = font['name']
    name.setName('ComicMathMono CJK Symbol Subset', 1, 3, 1, 0x409)
    name.setName('Regular', 2, 3, 1, 0x409)
    name.setName('ComicMathMono-CJKSymbolSubset', 4, 3, 1, 0x409)
    name.setName('ComicMathMono-CJKSymbolSubset', 6, 3, 1, 0x409)
    name.setName('Version 1.0', 5, 3, 1, 0x409)

    font.save(args.out)
    out_font = TTFont(args.out, lazy=True)
    size = os.path.getsize(args.out)
    print(f'写出: {args.out}')
    print(f'  upem={out_font["head"].unitsPerEm} glyphs={len(out_font.getGlyphOrder())} '
          f'cmap={len(out_font.getBestCmap())} size={size / 1024:.1f} KB')
    print(f'  码点: {["U+%04X" % c for c in sorted(out_font.getBestCmap())]}')
    print(f'  许可: {(out_font["name"].getDebugName(13) or "")[:60]}...')
    return 0


if __name__ == '__main__':
    sys.exit(main())
