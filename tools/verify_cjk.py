#!/usr/bin/env python3
"""校验 dist/ComicMathMono-CJK-{Regular,Bold}.ttf 的不变量。

这些字体是 CJK 伴生字体，故意只含 CJK W/F 码点；下面的断言就是这份设计契约：

  · family/full/PS 名 = ComicMathMono CJK / ComicMathMonoCJK-*
    （不使用 Yozai / 悠哉 / Y.Oz 等 OFL 保留名称）
  · 只含 EAW = W/F 的码点；没有 ASCII / 比例拉丁 / ASCII 标点
  · 所有 glyph advance = 1100，post.isFixedPitch=1，panose bProportion=9
  · URO 全满；《通用规范汉字表》8105 全满；GB2312 汉字全满
  · Yozai+Jigmo 之外的 27 个缺口码点由 Noto 子集补齐
  · 无 Mac name 记录；带 smart-dropout prep；.notdef 非空

用法：
    python3 tools/verify_cjk.py
"""
import os
import re
import sys
import unicodedata

from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from make_noto_gap_subset import GAP_UNICODES  # noqa: E402

WIDE = 1100
SMART_DROPOUT = bytes.fromhex('B801FF85B0048D')
RFN_RE = re.compile(r'Yozai|悠哉|Y\.?Oz', re.IGNORECASE)

FILES = {
    'Regular': (os.path.join(ROOT, 'dist', 'ComicMathMono-CJK-Regular.ttf'), 20992),
    'Bold': (os.path.join(ROOT, 'dist', 'ComicMathMono-CJK-Bold.ttf'), 17629),
}


def load_8105():
    chars = []
    with open(os.path.join(ROOT, 'data', '8105.txt'), encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            chars.extend(line)
    if len(chars) != 8105 or len(set(chars)) != 8105:
        raise SystemExit(f'data/8105.txt 应为 8105 个唯一字符，实际 {len(chars)}/{len(set(chars))}')
    return chars


def jis0208():
    out = set()
    for b1 in range(0xA1, 0xFF):
        for b2 in range(0xA1, 0xFF):
            try:
                ch = bytes([b1, b2]).decode('euc_jp')
            except UnicodeDecodeError:
                continue
            if len(ch) == 1 and unicodedata.east_asian_width(ch) in ('W', 'F'):
                out.add(ch)
    return out


def gb2312_hanzi():
    out = set()
    for b1 in range(0xA1, 0xF8):
        for b2 in range(0xA1, 0xFF):
            try:
                ch = bytes([b1, b2]).decode('gb2312')
            except UnicodeDecodeError:
                continue
            if 0x4E00 <= ord(ch) <= 0x9FFF:
                out.add(ch)
    return out


def check_one(style, path, expected_uro, chars_8105, gb_han, jis_0208):
    errors = []

    def bad(code, detail):
        errors.append(f'{code}: {detail}')

    if not os.path.exists(path):
        return [f'找不到 {path}']
    font = TTFont(path, lazy=True)
    cmap = font.getBestCmap()
    hmtx = font['hmtx']

    # name / RFN
    if font['name'].getDebugName(1) != 'ComicMathMono CJK':
        bad('name-family', font['name'].getDebugName(1))
    if font['name'].getDebugName(2) != style:
        bad('name-style', font['name'].getDebugName(2))
    if font['name'].getDebugName(6) != f'ComicMathMonoCJK-{style}':
        bad('name-ps', font['name'].getDebugName(6))
    for nid in (1, 2, 3, 4, 5, 6, 16, 17):
        val = font['name'].getDebugName(nid) or ''
        if RFN_RE.search(val):
            bad('rfn-in-primary-name', f'ID{nid}={val!r}')
    if any(rec.platformID == 1 for rec in font['name'].names):
        bad('mac-name-record', '存在 platformID=1 的 name 记录')

    # metrics
    if font['head'].unitsPerEm != 1000:
        bad('upem', font['head'].unitsPerEm)
    if font['post'].isFixedPitch != 1:
        bad('post.isFixedPitch', font['post'].isFixedPitch)
    if font['OS/2'].panose.bProportion != 9:
        bad('panose.bProportion', font['OS/2'].panose.bProportion)
    if font['hhea'].advanceWidthMax != WIDE:
        bad('hhea.advanceWidthMax', font['hhea'].advanceWidthMax)
    if font['OS/2'].xAvgCharWidth != WIDE:
        bad('OS/2.xAvgCharWidth', font['OS/2'].xAvgCharWidth)
    if (font['hhea'].ascender, font['hhea'].descender, font['hhea'].lineGap) != (1030, -248, 0):
        bad('hhea-vertical', (font['hhea'].ascender, font['hhea'].descender, font['hhea'].lineGap))
    if (font['OS/2'].sTypoAscender, font['OS/2'].sTypoDescender, font['OS/2'].sTypoLineGap) != (1030, -248, 0):
        bad('os2-typo-vertical',
            (font['OS/2'].sTypoAscender, font['OS/2'].sTypoDescender, font['OS/2'].sTypoLineGap))

    # cmap / advances
    bad_eaw = [cp for cp in cmap if unicodedata.east_asian_width(chr(cp)) not in ('W', 'F')]
    if bad_eaw:
        bad('non-wide-codepoints', [(hex(cp), chr(cp)) for cp in bad_eaw[:10]])
    ascii_cps = [cp for cp in cmap if cp < 0x80]
    if ascii_cps:
        bad('ascii-codepoints', [hex(cp) for cp in ascii_cps[:10]])
    bad_adv = [(cp, hmtx[g][0]) for cp, g in cmap.items() if hmtx[g][0] != WIDE]
    if bad_adv:
        bad('non-1100-advance', [(hex(cp), w) for cp, w in bad_adv[:10]])

    uro = sum(1 for cp in cmap if 0x4E00 <= cp <= 0x9FFF)
    if uro != expected_uro:
        bad('uro-count', f'{uro} != {expected_uro}')

    miss_8105 = [c for c in chars_8105 if ord(c) not in cmap]
    if miss_8105:
        bad('8105-missing', f'{len(miss_8105)} 个，例如 {"".join(miss_8105[:20])}')

    miss_gb = [c for c in gb_han if ord(c) not in cmap]
    if miss_gb:
        bad('gb2312-hanzi-missing', f'{len(miss_gb)} 个，例如 {"".join(miss_gb[:20])}')

    miss_jis = [c for c in jis_0208 if ord(c) not in cmap]
    if miss_jis:
        bad('jis0208-missing', f'{len(miss_jis)} 个，例如 {"".join(miss_jis[:20])}')

    miss_gap = [cp for cp in GAP_UNICODES if cp not in cmap]
    if miss_gap:
        bad('gap27-missing', [hex(cp) for cp in miss_gap])

    # required structural bits
    if 'prep' not in font or SMART_DROPOUT not in font['prep'].program.getBytecode():
        bad('smart-dropout', 'prep 缺少 smart dropout 指令')
    if font['glyf']['.notdef'].numberOfContours == 0:
        bad('notdef-blank', '.notdef 为空')
    if font['OS/2'].version != 4:
        bad('os2-version', font['OS/2'].version)

    print(f'{"PASS" if not errors else "FAIL"} {os.path.basename(path)}: '
          f'cmap={len(cmap)} URO={uro} 8105={len(chars_8105) - len(miss_8105)}/8105 '
          f'GB2312-hanzi={len(gb_han) - len(miss_gb)}/{len(gb_han)} '
          f'JIS0208-CJK={len(jis_0208) - len(miss_jis)}/{len(jis_0208)} '
          f'advance={WIDE} prep=smart-dropout')
    for e in errors:
        print(f'  ✗ {e}')
    return errors


def main():
    chars_8105 = load_8105()
    gb_han = gb2312_hanzi()
    jis_0208 = jis0208()
    print(f'data/8105.txt: {len(chars_8105)} 字；GB2312 汉字: {len(gb_han)} 字；JIS X 0208: {len(jis_0208)} 字')
    all_errors = []
    for style, (path, uro) in FILES.items():
        all_errors += check_one(style, path, uro, chars_8105, gb_han, jis_0208)
    if all_errors:
        print(f'\n{len(all_errors)} 项失败', file=sys.stderr)
        return 1
    print('\nCJK 伴生字体校验通过 ✓')
    return 0


if __name__ == '__main__':
    sys.exit(main())
