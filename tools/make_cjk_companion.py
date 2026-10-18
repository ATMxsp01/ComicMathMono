#!/usr/bin/env python3
"""构建 CJK 伴生字体 ComicMathMono CJK（Regular / Bold）。

来源：
  · Regular: sources/yozai/Yozai-Medium.ttf  (v0.868)
  · Bold   : sources/yozai/Yozai-Bold.ttf    (v0.850)
  · 27 个 Yozai/Jigmo 都没有的 CJK W/F 缺口：sources/NotoSansCJKsc-Gap27-{Regular,Bold}.ttf

原则：
  · 只保留 EAW = W/F 的 CJK 相关码点；不引入 Yozai 的比例拉丁/ASCII 标点/符号。
  · 所有保留字形 advance 强制 1100（= 2 × ComicMathMono 的 550），轮廓 +50 居中。
  · post.isFixedPitch=1、panose bProportion=9，fontconfig 才会稳定判成 mono。
  · 字体 family 使用 ComicMathMono CJK，不使用 Yozai/悠哉 等 OFL 保留名称；
    来源说明只放在 name ID 10 / README / NOTICE 里。

用法：
    python3 tools/make_cjk_companion.py
    python3 tools/make_cjk_companion.py --regular-src ... --bold-src ...
"""
import argparse
import os
import sys
import unicodedata

from fontTools import subset
from fontTools.misc import timeTools
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

SOURCE_DATE_EPOCH = int(os.environ.get('SOURCE_DATE_EPOCH', '946684800'))
BUILD_TIME = SOURCE_DATE_EPOCH - timeTools.epoch_diff

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, 'sources')
DIST = os.path.join(ROOT, 'dist')

DEFAULT_REGULAR = os.path.join(SOURCES, 'yozai', 'Yozai-Medium.ttf')
DEFAULT_BOLD = os.path.join(SOURCES, 'yozai', 'Yozai-Bold.ttf')
DEFAULT_GAP_REGULAR = os.path.join(SOURCES, 'NotoSansCJKsc-Gap27-Regular.ttf')
DEFAULT_GAP_BOLD = os.path.join(SOURCES, 'NotoSansCJKsc-Gap27-Bold.ttf')

CELL = 550
WIDE = 1100
SHIFT = (WIDE - 1000) // 2          # 50; Yozai upem=1000
ASCENT = 1030
DESCENT = -248

# CJK 相关区块。只取其中 EAW = W/F 的码点；A/N/H 与组合符会在 wanted() 里排除。
CJK_RANGES = [
    (0x2E80, 0x2EFF),   # CJK Radicals Supplement
    (0x2F00, 0x2FDF),   # Kangxi Radicals
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0x3040, 0x30FF),   # Hiragana + Katakana
    (0x3100, 0x312F),   # Bopomofo
    (0x3130, 0x318F),   # Hangul Compatibility Jamo
    (0x31A0, 0x31BF),   # Bopomofo Extended
    (0x31C0, 0x31EF),   # CJK Strokes
    (0x31F0, 0x31FF),   # Katakana Phonetic Extensions
    (0x3200, 0x33FF),   # Enclosed CJK Letters and Months + CJK Compatibility
    (0x3400, 0x4DBF),   # CJK Ext A
    (0x4E00, 0x9FFF),   # CJK URO
    (0xA960, 0xA97F),   # Hangul Jamo Extended-A
    (0xAC00, 0xD7AF),   # Hangul Syllables
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
    (0xFE10, 0xFE1F),   # Vertical Forms
    (0xFE30, 0xFE4F),   # CJK Compatibility Forms
    (0xFE50, 0xFE6F),   # Small Form Variants
    (0xFF00, 0xFFEF),   # Halfwidth and Fullwidth Forms（只收 W/F）
    (0x1F200, 0x1F2FF), # Enclosed Ideographic Supplement
    # 生僻扩展：Yozai 只覆盖少量，Jigmo 负责其余；这里把 Yozai 有的也收进来
    (0x20000, 0x2A6DF), (0x2A700, 0x2B73F), (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF), (0x2CEB0, 0x2EBEF), (0x2EBF0, 0x2EE5F),
    (0x30000, 0x3134F), (0x31350, 0x323AF), (0x323B0, 0x3347F),
]

DROP_TABLES = ['GSUB', 'GPOS', 'GDEF', 'BASE', 'JSTF', 'MATH', 'morx', 'feat',
               'prop', 'kern', 'vhea', 'vmtx', 'VORG', 'DSIG', 'hdmx', 'LTSH',
               'VDMX', 'meta', 'STAT', 'fvar', 'gvar', 'avar', 'HVAR', 'MVAR', 'VVAR']

# 这些 name ID 会被重写；其余（版权 0、设计者 8/9）保留或按需处理。
REWRITE_NAME_IDS = {1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 16, 17, 19}


def ensure_reproducible_hash_seed():
    """强制 PYTHONHASHSEED=0，保证 CJK 伴生字体可复现。"""
    if os.environ.get('PYTHONHASHSEED') != '0':
        os.environ['PYTHONHASHSEED'] = '0'
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__), *sys.argv[1:]])


def in_ranges(cp):
    for lo, hi in CJK_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def wanted_codepoints():
    out = []
    for lo, hi in CJK_RANGES:
        for cp in range(lo, hi + 1):
            ch = chr(cp)
            cat = unicodedata.category(ch)
            if cat == 'Cn' or cat.startswith('M'):
                continue
            if unicodedata.east_asian_width(ch) not in ('W', 'F'):
                continue
            out.append(cp)
    return out


def set_cmap_entry(font, cp, glyph_name):
    for table in font['cmap'].tables:
        if table.format in (4, 12) and table.isUnicode() and hasattr(table, 'cmap'):
            if table.format == 4 and cp > 0xFFFF:
                continue
            table.cmap[cp] = glyph_name


def subset_yozai(src, tmp_path, wanted):
    font = TTFont(src)
    cmap = font.getBestCmap()
    actual = [cp for cp in wanted if cp in cmap]
    opts = subset.Options()
    opts.layout_features = []
    opts.drop_tables += DROP_TABLES
    opts.notdef_outline = True
    opts.recalc_bounds = True
    opts.recalc_timestamp = False
    opts.name_IDs = ['*']
    opts.name_legacy = True
    opts.name_languages = ['*']
    opts.hinting = False
    opts.glyph_names = False
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=actual)
    sub.subset(font)
    font.save(tmp_path)
    print(f'  子集 {os.path.basename(src)}: 请求 {len(actual)} 个码点')
    return actual


def translate_and_set_advance(font):
    glyf = font['glyf']
    hmtx = font['hmtx']
    order = list(font.getGlyphOrder())

    # 所有简单字形整体 +50；复合字形会跟着组件一起移动
    for name in order:
        g = glyf[name]
        if g.numberOfContours > 0:
            g.coordinates = GlyphCoordinates([(x + SHIFT, y) for x, y in g.coordinates])
            g.recalcBounds(glyf)

    # 复合字形重新算 bbox
    for name in order:
        g = glyf[name]
        if g.numberOfContours == -1:
            try:
                g.recalcBounds(glyf)
            except Exception:
                pass

    # 所有字形统一 1100 宽
    for name in order:
        g = glyf[name]
        if g.numberOfContours != 0 and hasattr(g, 'xMin'):
            lsb = round(g.xMin)
        else:
            lsb = 0
        hmtx.metrics[name] = [WIDE, lsb]

    font['hhea'].advanceWidthMax = WIDE
    font['OS/2'].xAvgCharWidth = WIDE


def merge_gap_glyphs(base, gap_font_path, gap_unicodes):
    if not os.path.exists(gap_font_path):
        print(f'  警告：找不到缺口子集 {gap_font_path}，跳过', file=sys.stderr)
        return 0

    gap = TTFont(gap_font_path)
    gap_cmap = gap.getBestCmap()
    gap_glyphs = gap.getGlyphSet()
    base_cmap = base.getBestCmap()
    order = list(base.getGlyphOrder())
    glyf = base['glyf']
    hmtx = base['hmtx']

    copied = 0
    for cp in gap_unicodes:
        if cp in base_cmap:
            continue
        src_name = gap_cmap.get(cp)
        if not src_name or src_name not in gap_glyphs:
            print(f'  警告：缺口子集缺少 U+{cp:04X}', file=sys.stderr)
            continue
        rec = DecomposingRecordingPen(gap_glyphs)
        gap_glyphs[src_name].draw(rec)
        pen = TTGlyphPen(None)
        rec.replay(pen)
        g = pen.glyph()
        if g.numberOfContours > 0:
            g.coordinates = GlyphCoordinates([(x + SHIFT, y) for x, y in g.coordinates])
            g.recalcBounds(glyf)
            lsb = round(g.xMin)
        else:
            lsb = 0
        dst_name = f'noto.gap.{cp:04X}'
        while dst_name in glyf.glyphs:
            dst_name += '.1'
        order.append(dst_name)
        glyf.glyphs[dst_name] = g
        hmtx.metrics[dst_name] = [WIDE, lsb]
        set_cmap_entry(base, cp, dst_name)
        copied += 1

    base.setGlyphOrder(order)
    print(f'  合并 Noto 缺口字形: {copied} 个')
    return copied


def set_name(font, nid, value):
    # 只写 Windows/Unicode 记录；Mac Roman 放不下中文，而且 fontbakery 的
    # no_mac_entries 也不建议保留 Mac 记录。
    font['name'].setName(value, nid, 3, 1, 0x409)


SMART_DROPOUT = bytes.fromhex('B801FF85B0048D')  # PUSHW 0x01FF; SCANCTRL; PUSHB 4; SCANTYPE


def ensure_notdef(font):
    """Bold 源的 .notdef 是空的；补一个简单的空心方框。"""
    glyf = font['glyf']
    g = glyf['.notdef']
    if g.numberOfContours != 0:
        return
    pen = TTGlyphPen(None)
    # 外框
    pen.moveTo((100, 0))
    pen.lineTo((100, 700))
    pen.lineTo((1000, 700))
    pen.lineTo((1000, 0))
    pen.closePath()
    # 内框（反方向，挖空）
    pen.moveTo((200, 100))
    pen.lineTo((900, 100))
    pen.lineTo((900, 600))
    pen.lineTo((200, 600))
    pen.closePath()
    g = pen.glyph()
    g.recalcBounds(glyf)
    glyf['.notdef'] = g
    font['hmtx'].metrics['.notdef'] = [WIDE, round(g.xMin)]


def add_smart_dropout(font):
    """给无 hinting 的字体补上 smart dropout 的 prep 指令（fontbakery 建议）。"""
    prep = newTable('prep')
    prog = Program()
    prog.fromBytecode(SMART_DROPOUT)
    prep.program = prog
    font['prep'] = prep
    mp = font['maxp']
    mp.maxSizeOfInstructions = max(getattr(mp, 'maxSizeOfInstructions', 0), len(SMART_DROPOUT))
    mp.maxStackElements = max(getattr(mp, 'maxStackElements', 0), 3)


def finalize(font, style, weight, out_path):
    name = font['name']
    for rec in list(name.names):
        if rec.nameID in REWRITE_NAME_IDS:
            name.names.remove(rec)

    family = 'ComicMathMono CJK'
    full = f'{family} {style}'
    ps = f'ComicMathMonoCJK-{style}'
    set_name(font, 0,
             'Copyright 2020, 2024 LXGW (https://github.com/lxgw/yozai-font). '
             'Original Font Data Copyright (C) Y.OzVox. '
             'Modified 2026 for ComicMathMono CJK (CJK-only subset, '
             'advance 1100, centered, monospaced metadata, renamed).')
    set_name(font, 1, family)
    set_name(font, 2, style)
    set_name(font, 3, f'{full}; 1.0; 2026')
    set_name(font, 4, full)
    set_name(font, 5, 'Version 1.0; ComicMathMono CJK')
    set_name(font, 6, ps)
    set_name(font, 10,
             'CJK layer derived from Yozai (悠哉字体) v0.868 Medium / v0.850 Bold '
             'by LXGW, based on Y.OzFont. '
             'Subset to CJK W/F codepoints, advance 1100, centered, monospaced metadata, renamed.')
    set_name(font, 13,
             'This Font Software is licensed under the SIL Open Font License, Version 1.1. '
             'This license is available with a FAQ at: https://scripts.sil.org/OFL')
    set_name(font, 14, 'https://scripts.sil.org/OFL')
    set_name(font, 16, family)
    set_name(font, 17, style)

    font['head'].fontRevision = 1.0
    font['head'].created = font['head'].modified = BUILD_TIME
    font.recalcTimestamp = False
    font['head'].unitsPerEm = 1000
    font['head'].macStyle = 0x01 if style == 'Bold' else 0x00

    hhea = font['hhea']
    hhea.ascender = ASCENT
    hhea.descender = DESCENT
    hhea.lineGap = 0
    hhea.advanceWidthMax = WIDE

    os2 = font['OS/2']
    os2.usWeightClass = weight
    os2.sTypoAscender = ASCENT
    os2.sTypoDescender = DESCENT
    os2.sTypoLineGap = 0
    os2.usWinAscent = ASCENT
    os2.usWinDescent = -DESCENT
    os2.xAvgCharWidth = WIDE
    os2.version = 4
    os2.fsSelection = 0xA0 if style == 'Bold' else 0xC0
    try:
        os2.panose.bProportion = 9       # monospaced
        os2.panose.bFamilyType = 2       # Latin text
        os2.panose.bSerifStyle = 0       # sans
    except Exception:
        pass
    try:
        os2.recalcCodePageRanges()
    except Exception:
        pass

    # 去掉所有 Mac 平台 name 记录（fontbakery no_mac_entries）
    for rec in list(font['name'].names):
        if rec.platformID == 1:
            font['name'].names.remove(rec)

    font['post'].isFixedPitch = 1
    font['post'].italicAngle = 0

    # fontbakery 按 OpenType 规范建议 numberOfHMetrics=3；所有 advance 都是 1100，
    # 所以 3 个 longHorMetric 之后全是共享同一 advance 的 lsb。
    font['hhea'].numberOfHMetrics = 3

    ensure_notdef(font)
    add_smart_dropout(font)

    try:
        font['maxp'].recalc(font)
    except Exception:
        pass

    font.save(out_path)


def verify(path):
    font = TTFont(path, lazy=True)
    cmap = font.getBestCmap()
    hmtx = font['hmtx']
    bad_width = [cp for cp, g in cmap.items() if hmtx[g][0] != WIDE]
    bad_eaw = [cp for cp in cmap
               if unicodedata.east_asian_width(chr(cp)) not in ('W', 'F')]
    uro = sum(1 for cp in cmap if 0x4E00 <= cp <= 0x9FFF)
    stats = {
        'glyphs': font['maxp'].numGlyphs,
        'cmap': len(cmap),
        'uro': uro,
        'bad_width': len(bad_width),
        'bad_eaw': len(bad_eaw),
        'fixed': font['post'].isFixedPitch,
        'size_mb': os.path.getsize(path) / 1e6,
    }
    print(f'  校验 {os.path.basename(path)}: '
          f'glyphs={stats["glyphs"]} cmap={stats["cmap"]} URO={uro} '
          f'non-1100={stats["bad_width"]} non-W/F={stats["bad_eaw"]} '
          f'fixedPitch={stats["fixed"]} {stats["size_mb"]:.1f} MB')
    if bad_width:
        print(f'    非 1100 宽示例: {[hex(cp) for cp in bad_width[:10]]}', file=sys.stderr)
    if bad_eaw:
        print(f'    非 W/F 示例: {[(hex(cp), chr(cp)) for cp in bad_eaw[:10]]}', file=sys.stderr)
    return not bad_width and not bad_eaw and stats['fixed'] == 1


def build_one(src, gap_src, style, weight, out):
    print(f'== {style}: {src}')
    wanted = wanted_codepoints()
    tmp = os.path.join(ROOT, '.build', f'_cjk_{style}.ttf')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    actual = subset_yozai(src, tmp, wanted)
    font = TTFont(tmp)
    translate_and_set_advance(font)
    merge_gap_glyphs(font, gap_src, [0x115F, 0x3164, 0x32CC, 0x32CD, 0x32CE, 0x32CF,
                                      0x337A, 0x33DE, 0x33DF, 0x33FF,
                                      0xFE14, 0xFE15, 0xFE16, 0xFE17, 0xFE18, 0xFE19,
                                      0xFE34, 0xFE47, 0xFE48, 0xFE49, 0xFE4A, 0xFE4B,
                                      0xFE4C, 0xFE4D, 0xFE4E, 0xFE4F, 0xFFE6])
    finalize(font, style, weight, out)
    ok = verify(out)
    print(f'  写出: {out}')
    return ok


def main():
    ensure_reproducible_hash_seed()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--regular-src', default=DEFAULT_REGULAR)
    ap.add_argument('--bold-src', default=DEFAULT_BOLD)
    ap.add_argument('--gap-regular', default=DEFAULT_GAP_REGULAR)
    ap.add_argument('--gap-bold', default=DEFAULT_GAP_BOLD)
    ap.add_argument('--out-regular', default=os.path.join(DIST, 'ComicMathMono-CJK-Regular.ttf'))
    ap.add_argument('--out-bold', default=os.path.join(DIST, 'ComicMathMono-CJK-Bold.ttf'))
    args = ap.parse_args()
    os.makedirs(DIST, exist_ok=True)
    ok = build_one(args.regular_src, args.gap_regular, 'Regular', 400, args.out_regular)
    ok = build_one(args.bold_src, args.gap_bold, 'Bold', 700, args.out_bold) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
