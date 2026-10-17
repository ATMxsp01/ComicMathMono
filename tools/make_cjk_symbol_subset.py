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

输出是 **TrueType（glyf）**而非 CFF：Noto Sans CJK 本体是 CFF，这里用 cu2qu 转成二次曲线再写出。
（若直接输出 CFF，build.py 里还得再做一次 CFF→glyf；哪一步漏了 cu2qu，字形 flags 里就会留下
fontTools 的保留位 bit7=0x80，OTS 会拒收整份字体 —— 正是本项目修过的那个 P0。）
"""
import argparse
import os
import sys

from fontTools import subset
from fontTools.misc import timeTools
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable

# 固定时间戳，和 build.py 一样保证可复现（head 里的秒是「1904 起算」）
SOURCE_DATE_EPOCH = int(os.environ.get('SOURCE_DATE_EPOCH', '946684800'))
BUILD_TIME = SOURCE_DATE_EPOCH - timeTools.epoch_diff

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'
DEFAULT_OUT = os.path.join(ROOT, 'sources', 'NotoSansCJKsc-Symbols5.ttf')
UNICODES = [0x3030, 0x303D, 0x3297, 0x3299, 0x1F237]
DROP_TABLES = ['GSUB', 'GPOS', 'GDEF', 'BASE', 'JSTF', 'MATH', 'morx', 'kern',
               'vhea', 'vmtx', 'VORG', 'DSIG', 'hdmx', 'LTSH', 'VDMX', 'gasp',
               'meta', 'STAT', 'fvar', 'gvar', 'avar', 'HVAR', 'MVAR', 'VVAR']


def cff_to_glyf(font):
    """把 CFF（三次贝塞尔）就地转成 glyf（二次），产出真正的 TrueType。

    之前这个工具直接输出 CFF/OTTO，build.py 里再做一次转换；一旦哪一步漏了 cu2qu，
    字形 flags 里就会留下 fontTools 的保留位 bit7（0x80），OTS 会拒收整份字体。
    让「子集 → 成品」两步都是 TrueType，隐患少一半；build.py 里的 CFF 分支保留作兜底。
    """
    glyph_set = font.getGlyphSet()
    order = font.getGlyphOrder()
    glyphs = {}
    for name in order:
        pen = TTGlyphPen(glyph_set)
        glyph_set[name].draw(Cu2QuPen(pen, max_err=1.0, reverse_direction=True))
        glyphs[name] = pen.glyph()
    glyf = newTable('glyf')
    glyf.glyphOrder = order
    glyf.glyphs = glyphs
    font['glyf'] = glyf
    # CFF 源没有 loca；glyf.compile() 会把 offsets 写进 ttFont['loca']，所以必须建一个空表
    font['loca'] = newTable('loca')
    for tag in ('CFF ', 'CFF2', 'VORG'):
        if tag in font:
            del font[tag]
    # CFF 的 maxp 是 0.5；带 glyf 的表必须是 1.0。
    # maxp.recalc() 只重算轮廓相关的值，**指令相关的 max 值不管**，而 CFF 源的 maxp
    # 里根本没有这些字段 → 直接编译会 KeyError('maxZones')。本字体无 hinting，给默认值。
    mp = font['maxp']
    mp.tableVersion = 0x00010000
    for key, val in (('maxZones', 2), ('maxTwilightPoints', 0), ('maxStorage', 0),
                     ('maxFunctionDefs', 0), ('maxInstructionDefs', 0),
                     ('maxStackElements', 0), ('maxSizeOfInstructions', 0),
                     ('maxComponentElements', 0), ('maxComponentDepth', 0)):
        if not hasattr(mp, key):
            setattr(mp, key, val)
    font.sfntVersion = '\x00\x01\x00\x00'   # TrueType，而非 'OTTO'
    return len(order)


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

    # CFF → TrueType，并固定时间戳（可复现）
    cff_to_glyf(font)
    font['head'].created = font['head'].modified = BUILD_TIME
    font.recalcTimestamp = False

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
