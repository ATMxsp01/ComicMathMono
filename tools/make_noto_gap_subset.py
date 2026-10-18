#!/usr/bin/env python3
"""从系统 Noto Sans CJK SC 里提取 27 个「Yozai 没有、Jigmo 也没有」的 CJK W/F 码点。

这些码点是 Yozai + Jigmo 并集之后仅剩的 CJK 缺口：主要是竖排形式、CJK 兼容形式、
Enclosed CJK、谚文填充符和一个全角符号。Noto Sans CJK SC 全都有。

输出是 TrueType/glyf（Noto Sans CJK 本体是 CFF，这里用 cu2qu 转成二次曲线），
供 tools/make_cjk_companion.py 合并进 ComicMathMono CJK。保留 Noto 的版权/许可
name 记录；family 名改成中性的内部名，避免看起来像在分发 Noto 本体。

用法：
    python3 tools/make_noto_gap_subset.py
    python3 tools/make_noto_gap_subset.py \
        --regular-src /usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc \
        --bold-src    /usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc
"""
import argparse
import os
import sys

from fontTools import subset
from fontTools.misc import timeTools

# 复用现有工具里的 SC face 查找与 CFF→glyf 转换
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_cjk_symbol_subset import cff_to_glyf, find_sc_face  # noqa: E402

SOURCE_DATE_EPOCH = int(os.environ.get('SOURCE_DATE_EPOCH', '946684800'))
BUILD_TIME = SOURCE_DATE_EPOCH - timeTools.epoch_diff

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGULAR = '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'
DEFAULT_BOLD = '/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc'

# Yozai(Regular+Medium) ∪ Jigmo 之后仍缺的 CJK W/F 码点
GAP_UNICODES = [
    0x115F,  # HANGUL CHOSEONG FILLER
    0x3164,  # HANGUL FILLER
    0x32CC, 0x32CD, 0x32CE, 0x32CF,  # ㋌ ㋍ ㋎ ㋏
    0x337A,  # ㍺
    0x33DE, 0x33DF,  # ㏞ ㏟
    0x33FF,  # ㏿
    0xFE14, 0xFE15, 0xFE16, 0xFE17, 0xFE18, 0xFE19,  # 竖排标点
    0xFE34,  # ︴
    0xFE47, 0xFE48, 0xFE49, 0xFE4A, 0xFE4B, 0xFE4C, 0xFE4D, 0xFE4E, 0xFE4F,
    0xFFE6,  # ￦
]

DROP_TABLES = ['GSUB', 'GPOS', 'GDEF', 'BASE', 'JSTF', 'MATH', 'morx', 'kern',
               'vhea', 'vmtx', 'VORG', 'DSIG', 'hdmx', 'LTSH', 'VDMX', 'gasp',
               'meta', 'STAT', 'fvar', 'gvar', 'avar', 'HVAR', 'MVAR', 'VVAR']


def ensure_reproducible_hash_seed():
    """强制 PYTHONHASHSEED=0，保证缺口子集可复现。"""
    if os.environ.get('PYTHONHASHSEED') != '0':
        os.environ['PYTHONHASHSEED'] = '0'
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__), *sys.argv[1:]])


def build_one(src, out, style, weight):
    if not os.path.exists(src):
        print(f'找不到 Noto Sans CJK：{src}', file=sys.stderr)
        return False
    num, fam = find_sc_face(src)
    print(f'源字体: {src}')
    print(f'TTC 面 : fontNumber={num}  family={fam}')
    font = fontTools_load(src, num)

    cmap = font.getBestCmap()
    missing = [cp for cp in GAP_UNICODES if cp not in cmap]
    if missing:
        print(f'源字体缺少：{["U+%04X" % c for c in missing]}', file=sys.stderr)
        return False

    opts = subset.Options()
    opts.layout_features = []
    opts.drop_tables += DROP_TABLES
    opts.notdef_outline = True
    opts.recalc_bounds = True
    opts.recalc_timestamp = False
    opts.name_IDs = ['*']
    opts.name_legacy = True
    opts.name_languages = ['*']
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=GAP_UNICODES)
    sub.subset(font)

    name = font['name']
    family = 'ComicMathMono CJK Gap'
    full = f'{family} {style}'
    ps = f'ComicMathMonoCJKGap-{style}'
    for nid, value in (
        (1, family), (2, style), (4, full), (6, ps), (16, family), (17, style),
        (5, f'Version 1.0; {full}'),
    ):
        for plat, enc, lang in ((3, 1, 0x409), (1, 0, 0)):
            name.setName(value, nid, plat, enc, lang)
    for rec in list(name.names):
        if rec.nameID in (3,):
            name.removeNames(nameID=3)
            break
    name.setName(f'{full}; 1.0; 2026', 3, 3, 1, 0x409)
    name.setName(f'{full}; 1.0; 2026', 3, 1, 0, 0)

    cff_to_glyf(font)
    font['head'].created = font['head'].modified = BUILD_TIME
    font.recalcTimestamp = False
    font['OS/2'].usWeightClass = weight
    font.save(out)

    chk = fontTools_load(out)
    print(f'写出: {out}')
    print(f'  glyphs={len(chk.getGlyphOrder())} cmap={len(chk.getBestCmap())} '
          f'size={os.path.getsize(out)/1024:.1f} KB')
    print(f'  码点: {["U+%04X" % c for c in sorted(chk.getBestCmap())]}')
    return True


def fontTools_load(path, num=0):
    from fontTools.ttLib import TTFont
    return TTFont(path, fontNumber=num)


def main():
    ensure_reproducible_hash_seed()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--regular-src', default=DEFAULT_REGULAR)
    ap.add_argument('--bold-src', default=DEFAULT_BOLD)
    ap.add_argument('--out-regular', default=os.path.join(ROOT, 'sources', 'NotoSansCJKsc-Gap27-Regular.ttf'))
    ap.add_argument('--out-bold', default=os.path.join(ROOT, 'sources', 'NotoSansCJKsc-Gap27-Bold.ttf'))
    args = ap.parse_args()

    ok = build_one(args.regular_src, args.out_regular, 'Regular', 400)
    ok = build_one(args.bold_src, args.out_bold, 'Bold', 700) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
