#!/usr/bin/env python3
"""对 dist/ 里的成品字体做回归校验（CI 用）。

把本项目踩过的坑都变成断言：

  1. 四个 face 都在，且宽度只允许 0 / 550 / 1100 三种
  2. 没有 ``locl`` 特性                 —— docs/locl-issue.md
  3. cmap format 14 变体表存在          —— VS15/VS16 必须真的能切换（每个 face 都要有）
  4. GPOS 有 ``mark`` 定位且覆盖足够多  —— docs/combining-marks.md
  5. 没有「隐形字符」                   —— 有码点、空轮廓、又没有 COLR
  6. 默认呈现正确：文本呈现的有单色轮廓、彩色呈现的指向彩色字形
  7. 每个 face 都是上游源字体的**超集**  —— 否则 fallback 链里还得留着源字体

用法：``python3 tools/verify.py [dist 目录]``，全部通过时退出码 0。
"""
import os
import sys
import unicodedata
from fontTools.ttLib import TTFont
from fontTools.merge.unicode import is_Default_Ignorable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'dist')
FACES = ['Regular', 'Bold', 'Italic', 'BoldItalic']
ALLOWED_WIDTHS = {0, 550, 1100}
# 每个 face 必须完整覆盖的源字体（本字体 = 基底 ∪ JuliaMono ∪ NotoEmoji）
SUPERSET = {
    'Regular':    ['ComicR.ttf', 'julia/JuliaMonoNerdFontMono-Regular.ttf'],
    'Bold':       ['ComicB.ttf', 'julia/JuliaMonoNerdFontMono-Bold.ttf'],
    'Italic':     ['SShI.ttf', 'julia/JuliaMonoNerdFontMono-Italic.ttf'],
    'BoldItalic': ['SShBI.ttf', 'julia/JuliaMonoNerdFontMono-BoldItalic.ttf'],
}
# 这些码点故意不收（见 docs/emoji-presentation.md），允许成为覆盖缺口
DROPPED = ({0x3030, 0x303D, 0x3297, 0x3299, 0x1F237, 0xFE82C} |
           set(range(0xFE4E5, 0xFE4EF)) | set(range(0xFE82E, 0xFE838)))

problems = []
notes = []


def fail(msg):
    problems.append(msg)


def load_presentation():
    """Emoji_Presentation=Yes 的码点集合。"""
    path = os.path.join(ROOT, 'data', 'emoji-data.txt')
    pres = set()
    if not os.path.exists(path):
        notes.append('data/emoji-data.txt 缺失，跳过默认呈现检查')
        return None
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.split('#')[0].strip()
            if not line:
                continue
            rng, prop = (x.strip() for x in line.split(';'))
            if prop != 'Emoji_Presentation':
                continue
            a, b = (int(x, 16) for x in rng.split('..')) if '..' in rng else (int(rng, 16),) * 2
            pres.update(range(a, b + 1))
    return pres


def check_face(name, pres):
    path = os.path.join(DIST, f'ComicMathMono-{name}.ttf')
    if not os.path.exists(path):
        fail(f'{name}: 缺少产物 {path}')
        return
    f = TTFont(path, lazy=False)
    cmap = f.getBestCmap()
    glyf = f['glyf']
    hmtx = f['hmtx']
    size_mb = os.path.getsize(path) / 1048576

    # 1. 等宽
    widths = {hmtx.metrics[g][0] for g in cmap.values() if g in hmtx.metrics}
    bad = widths - ALLOWED_WIDTHS
    if bad:
        fail(f'{name}: 出现非等宽 advance {sorted(bad)}')

    # 2. 不应有 locl
    if 'GSUB' in f:
        tags = [fr.FeatureTag for fr in f['GSUB'].table.FeatureList.FeatureRecord]
        if 'locl' in tags:
            fail(f'{name}: GSUB 里仍有 locl 特性（数字会消失）')

    # 3. UVS：每个 face 都要有，否则粗体/斜体里 VS15/VS16 会失效
    n_uvs = {}
    for t in f['cmap'].tables:
        if t.format == 14:
            for sel, lst in t.uvsDict.items():
                n_uvs[sel] = len(lst)
    for sel in (0xFE0F, 0xFE0E):
        if n_uvs.get(sel, 0) < 200:
            fail(f'{name}: cmap format 14 的 U+{sel:04X} 变体过少（{n_uvs.get(sel, 0)}）')

    # 4. GPOS mark
    n_marks = 0
    if 'GPOS' in f:
        for lk in f['GPOS'].table.LookupList.Lookup:
            if lk.LookupType == 4:
                for st in lk.SubTable:
                    n_marks = max(n_marks, getattr(st.MarkArray, 'MarkCount', 0))
    if n_marks < 300:
        fail(f'{name}: GPOS mark 定位缺失或过少（{n_marks} 个标记）')

    # 5/6. 隐形字符 与 默认呈现
    colr = set()
    if 'COLR' in f:
        colr = {r.BaseGlyph for r in f['COLR'].table.BaseGlyphList.BaseGlyphPaintRecord}
    invisible, wrong_pres = [], []
    # U+2800 是「盲文空白」，字形本身就是空的
    EXPECTED_BLANK = {0x2800}
    for cp, g in cmap.items():
        gl = glyf.glyphs.get(g)
        if gl is None or getattr(gl, 'numberOfContours', -1) != 0:
            continue
        if cp in EXPECTED_BLANK:
            continue
        cat = unicodedata.category(chr(cp))
        if g in colr:
            # 彩色字形：只有「默认文本呈现」的才需要额外提供单色轮廓
            if pres is not None and cp not in pres:
                wrong_pres.append(cp)
        elif not (is_Default_Ignorable(cp) or
                  cat in ('Zs', 'Zl', 'Zp', 'Mn', 'Me', 'Cc', 'Cf', 'Co', 'Cn')):
            invisible.append(cp)
    if invisible:
        fail(f'{name}: 有 {len(invisible)} 个隐形字符（空轮廓且无 COLR）'
             f'：{["U+%04X" % c for c in invisible[:5]]}')
    if wrong_pres:
        fail(f'{name}: 有 {len(wrong_pres)} 个「默认文本呈现」的码点只有彩色字形'
             f'（文本渲染会空白）：{["U+%04X" % c for c in wrong_pres[:5]]}')

    # 6b. 默认彩色的码点必须真的指向彩色字形
    n_colr = 0
    if pres is not None:
        n_colr = sum(1 for cp, g in cmap.items() if cp in pres and g in colr)
        if n_colr < 1200:
            fail(f'{name}: 默认彩色的码点只有 {n_colr} 个指向彩色字形（应为 1200+）')

    # 7. 上游源字体的超集
    for rel in SUPERSET[name]:
        sp = os.path.join(ROOT, 'sources', rel)
        if not os.path.exists(sp):
            notes.append(f'{name}: 源字体 {rel} 缺失，跳过超集检查')
            continue
        gap = set(TTFont(sp, lazy=True).getBestCmap()) - set(cmap) - DROPPED
        if gap:
            fail(f'{name}: 不是 {rel} 的超集，缺 {len(gap)} 个码点：'
                 f'{["U+%04X" % c for c in sorted(gap)[:5]]}')

    notes.append(f'{name}: cmap={len(cmap)} width={sorted(widths)} '
                 f'UVS={ {hex(k): v for k, v in sorted(n_uvs.items())} } '
                 f'marks={n_marks} colour-default={n_colr} size={size_mb:.2f}MB')


def main():
    pres = load_presentation()
    for face in FACES:
        check_face(face, pres)
    for n in notes:
        print('  ' + n)
    if problems:
        print('\nFAILED:')
        for p in problems:
            print('  ✗ ' + p)
        return 1
    print('\nOK: 全部校验通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
