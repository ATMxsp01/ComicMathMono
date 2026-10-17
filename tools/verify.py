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
  8. glyf 简单字形的 flag 不含保留位 bit7 —— CFF→glyf 没做 cu2qu 时 OTS 会拒收整份字体
  9. GSUB 里有 ``ccmp``                 —— 键盘帽/旗帜/ZWJ emoji 序列靠它合成
 10. 组合标记与 Default_Ignorable 都是 0 宽；C0/C1 控制码不映射
 11. win 指标覆盖字形 bbox；等宽/嵌入/版本/斜体元数据自洽；hmtx 尾部等宽段被压掉；
     STAT 有 wght+ital（ital 在最后、每轴 1 条）且与 OS/2 一致；prep 带 smart dropout 开关；
     有大小写映射的码点必须成对齐全；没有不可达字形；sTypoAscender ≥ Agrave 高度
 12. name 表没有 Mac(platform 1) 记录、关键 ID 齐全（含 8/9/10/11/12/19/21/22）、11/12 为 https、21/22 与 16/17 一致、ID7 为空、ID0 含上游版权
 13. OTS（OpenType Sanitizer）能通过     —— 浏览器按同一套检查决定要不要加载
 14. 四个 face 的纵向指标与码点覆盖完全一致
 15. emoji 序列能合成成单个字形（可选）  —— 需要 uharfbuzz

用法：``python3 tools/verify.py [dist 目录]``，全部通过时退出码 0。
"""
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
import unicodedata
from fontTools.ttLib import TTFont
from fontTools.merge.unicode import is_Default_Ignorable
from fontTools.pens.boundsPen import BoundsPen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'dist')
FACES = ['Regular', 'Bold', 'Italic', 'BoldItalic']
ALLOWED_WIDTHS = {0, 550, 1100}
# 每个 face 必须完整覆盖的源字体（本字体 = 基底 ∪ JuliaMono ∪ NotoEmoji）
CJK_SUBSET = 'NotoSansCJKsc-Symbols5.ttf'   # tools/make_cjk_symbol_subset.py 生成
SUPERSET = {
    'Regular':    ['ComicR.ttf', 'julia/JuliaMonoNerdFontMono-Regular.ttf'],
    'Bold':       ['ComicB.ttf', 'julia/JuliaMonoNerdFontMono-Bold.ttf'],
    'Italic':     ['SShI.ttf', 'julia/JuliaMonoNerdFontMono-Italic.ttf'],
    'BoldItalic': ['SShBI.ttf', 'julia/JuliaMonoNerdFontMono-BoldItalic.ttf'],
}
# 这些码点故意不收：
#   · Noto 内部私用区/未分配码点（见 docs/emoji-presentation.md）
#   · C0/C1 控制字符（build.py 的 drop_control_cmap() 主动删除，控制码不该有字形）
CONTROL_DROPPED = set(range(0x00, 0x20)) | {0x7F} | set(range(0x80, 0xA0))
DROPPED = ({0xFE82C} | set(range(0xFE4E5, 0xFE4EF)) | set(range(0xFE82E, 0xFE838))
           | CONTROL_DROPPED)

# 四个 face 必须完全一致的纵向指标（family/vertical_metrics）
FAMILY_METRICS = ('sTypoAscender', 'sTypoDescender', 'usWinAscent', 'usWinDescent')

# 组合标记区块（与 build.py 的 JULIA_COMBINING_RANGES 保持一致）。
# 不能只靠 unicodedata.category：Python 3.13 的 Unicode 数据(15.1)较旧，会把
# U+1ACF..U+1ADD、U+1AE0..U+1AE5 这批 Unicode 16 的新组合符判成未分配(Cn)。
COMBINING_RANGES = [(0x0300, 0x036F), (0x1AB0, 0x1AFF), (0x1DC0, 0x1DFF),
                    (0x20D0, 0x20FF), (0xFE20, 0xFE2F)]


def is_combining_mark(cp):
    return unicodedata.category(chr(cp)) in ('Mn', 'Me') or any(
        a <= cp <= b for a, b in COMBINING_RANGES)

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


def _ots_runner():
    """返回一个 ``run(src, dst) -> (returncode, stderr_text)`` 的执行器，找不到就返回 None。

    优先用 PyPI 的 ``opentype-sanitizer``（内含 ots 模块与可执行文件），
    其次找 PATH 上的 ``ots-sanitize``。
    """
    try:
        import ots as _ots  # type: ignore

        def run(src, dst):
            p = _ots.sanitize(src, dst, capture_output=True)
            return p.returncode, (p.stderr or b'').decode('utf-8', 'replace')
        return run
    except Exception:
        pass
    exe = shutil.which('ots-sanitize')
    if exe:
        def run(src, dst):
            p = subprocess.run([exe, src, dst], capture_output=True)
            return p.returncode, (p.stderr or b'').decode('utf-8', 'replace')
        return run
    return None


# emoji 序列：都应该被 ccmp 连字合成成**一个**字形
def emoji_presentation_set():
    """Emoji_Presentation=Yes 的码点（读 data/emoji-data.txt，与 build.py 同源）。"""
    path = os.path.join(ROOT, 'data', 'emoji-data.txt')
    out = set()
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.split('#')[0].strip()
            if not line:
                continue
            rng, prop = (x.strip() for x in line.split(';'))
            if prop != 'Emoji_Presentation':
                continue
            a, b = ((int(x, 16) for x in rng.split('..')) if '..' in rng
                    else (int(rng, 16),) * 2)
            out.update(range(a, b + 1))
    return out


EMOJI_SEQUENCES = {
    'keycap 1\u20e3': '1\u20e3',
    'keycap 1\ufe0f\u20e3': '1\ufe0f\u20e3',          # RGI 正规写法（带 VS16）
    'keycap #\ufe0f\u20e3': '#\ufe0f\u20e3',
    'flag \U0001F1E8\U0001F1F3': '\U0001F1E8\U0001F1F3',
    'ZWJ family': '\U0001F468\u200d\U0001F469\u200d\U0001F467',
    'tag flag': '\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F',
    # 下列序列的**首字符是"文本默认"emoji**（cmap 里是单色字形，VS16 才切彩色），
    # 而 GSUB 连字是按单色字形写的 —— 不补彩色变体时它们会散成 3~4 个字形
    # （见 build.py::add_colour_ligature_variants）。RGI 正规写法都带 VS16。
    'heart on fire': '\u2764\ufe0f\u200d\U0001F525',
    'eye in speech bubble': '\U0001F441\ufe0f\u200d\U0001F5E8\ufe0f',
    'pirate flag': '\U0001F3F4\ufe0f\u200d\u2620\ufe0f',
    'rainbow flag': '\U0001F3F3\ufe0f\u200d\U0001F308',
    'health worker': '\U0001F9D1\u200d\u2695\ufe0f',
    'emoji + VS16': '\U0001F600\ufe0f',
}

# 键盘帽基字符 + VS16 必须留在**默认（单色、1 格）**字形：若 cmap14 把它换成
# Noto 的彩色数字字形，ccmp 键盘帽连字就会失配（踩过的坑，见 docs/merge-renaming.md）。
KEYCAP_BASE_VS16 = ['1\ufe0f', '#\ufe0f', '*\ufe0f']


def check_emoji_sequences(face, path):
    """用 HarfBuzz 实测 emoji 序列是否合成成单个字形（需要 uharfbuzz）。"""
    try:
        import uharfbuzz as hb  # type: ignore
    except ImportError:
        notes.append('未安装 uharfbuzz，跳过 emoji 序列 shaping 校验'
                     '（pip install uharfbuzz）')
        return
    order = TTFont(path, lazy=True).getGlyphOrder()
    blob = hb.Blob.from_file_path(path)
    font = hb.Font(hb.Face(blob))
    for label, text in EMOJI_SEQUENCES.items():
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {'kern': True, 'liga': True, 'ccmp': True, 'rlig': True})
        if len(buf.glyph_infos) != 1:
            glyphs = ', '.join(order[i.codepoint] for i in buf.glyph_infos)
            fail(f'{face}: emoji 序列「{label}」没有合成成单字形（得到 {len(buf.glyph_infos)} 个：{glyphs}）')

    for text in KEYCAP_BASE_VS16:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {'kern': True, 'liga': True, 'ccmp': True, 'rlig': True})
        adv = [p.x_advance for p in buf.glyph_positions]
        if len(buf.glyph_infos) != 1 or adv != [550]:
            glyphs = ', '.join(order[i.codepoint] for i in buf.glyph_infos)
            fail(f'{face}: 键盘帽基字符 {text!r} 的 VS16 没有保持默认单色字形'
                 f'（cmap14 若换成彩色数字，ccmp 键盘帽连字会失配）：得到 {glyphs} adv={adv}')

    # 全量连字回归：把 GSUB 里每条 ligature 还原成字符序列（按 RGI 规则给"文本默认"
    # 字符补 VS16），要求都能合成单个字形。任何一条散开都说明 cmap14 选中的字形
    # 和连字要匹配的字形又对不上了（本次审计就靠它发现 ❤️‍🔥 / 🏳️‍🌈 / 🏴‍☠️ 全坏）。
    f = TTFont(path, lazy=False)
    cmap = f.getBestCmap()
    rev = {}
    for cp, g in cmap.items():
        rev.setdefault(g, cp)
    vs16 = set()
    for t in f['cmap'].tables:
        if t.format == 14:
            for cp, g in (t.uvsDict.get(0xFE0F) or []):
                if g is not None:
                    vs16.add(cp)
    pres = emoji_presentation_set()
    total, broken = 0, []
    for lk in f['GSUB'].table.LookupList.Lookup:
        if lk.LookupType != 4:
            continue
        for sub in lk.SubTable:
            for first, ligs in sub.ligatures.items():
                for lig in ligs:
                    comps = [first] + list(lig.Component)
                    if len(comps) < 2:
                        continue
                    cps = [rev.get(c) for c in comps]
                    if any(c is None for c in cps):
                        continue
                    total += 1
                    text = ''.join(chr(cp) + ('\ufe0f' if (cp not in pres and cp in vs16) else '')
                                   for cp in cps)
                    buf = hb.Buffer()
                    buf.add_str(text)
                    buf.guess_segment_properties()
                    hb.shape(font, buf, {'kern': True, 'liga': True, 'ccmp': True, 'rlig': True})
                    if len(buf.glyph_infos) != 1:
                        broken.append('+'.join(f'U+{ord(c):04X}' for c in text))
    if broken:
        fail(f'{face}: {len(broken)}/{total} 条 emoji 连字在 RGI 形式下没有合成单字形'
             f'（例：{broken[:3]}）')
    elif total:
        notes.append(f'{face}: emoji 连字 {total} 条全部合成单字形')


def check_mark_stacking(face, path):
    """两个组合符必须**叠加**（mark-to-mark），而不是重叠。"""
    try:
        import uharfbuzz as hb  # type: ignore
    except ImportError:
        notes.append('未安装 uharfbuzz，跳过组合符叠加校验')
        return
    blob = hb.Blob.from_file_path(path)
    font = hb.Font(hb.Face(blob))
    # x 没有预组合的 acute/macron 字形，所以两个标记都会留在流里
    buf = hb.Buffer()
    buf.add_str('\u0078\u0301\u0304')
    buf.guess_segment_properties()
    hb.shape(font, buf, {'kern': True, 'liga': True, 'ccmp': True, 'rlig': True})
    if len(buf.glyph_infos) != 3:
        fail(f'{face}: x + U+0301 + U+0304 期望 3 个字形，实际 {len(buf.glyph_infos)}')
        return
    y = buf.glyph_positions[-1].y_offset
    if y <= 0:
        fail(f'{face}: 第二个组合符没有叠加（y_offset={y}，应为正：叠到前一个标记上方）')


def gsub_outputs(gsub):
    """GSUB 里**产出**的字形（只算输出，不算输入 mapping 的 key）。"""
    out = set()

    def add(lookup_type, sub):
        try:
            if lookup_type == 1:
                out.update(sub.mapping.values())
            elif lookup_type == 2:
                for slot in sub.mapping.values():
                    out.update(slot)
            elif lookup_type == 3:
                for alts in sub.alternates.values():
                    out.update(alts)
            elif lookup_type == 4:
                for ligs in sub.ligatures.values():
                    for lig in ligs:
                        out.add(lig.LigGlyph)
            elif lookup_type == 7:
                add(sub.ExtensionLookupType, sub.ExtSubTable)
            elif lookup_type == 8:
                out.update(sub.Substitute)
        except AttributeError:
            pass

    if getattr(gsub, 'LookupList', None):
        for lk in gsub.LookupList.Lookup:
            for sub in lk.SubTable:
                add(lk.LookupType, sub)
    return out


def check_face(name, pres):
    path = os.path.join(DIST, f'ComicMathMono-{name}.ttf')
    if not os.path.exists(path):
        fail(f'{name}: 缺少产物 {path}')
        return
    f = TTFont(path, lazy=False)
    cmap = f.getBestCmap()
    glyf = f['glyf']
    hmtx = f['hmtx']
    o = f['OS/2']
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

    # 4. GPOS mark：mark-to-base（按 above/below 分成多个 subtable）+ mark-to-mark
    base_marks = set()
    has_mkmk = False
    if 'GPOS' in f:
        for lk in f['GPOS'].table.LookupList.Lookup:
            if lk.LookupType == 4:
                for st in lk.SubTable:
                    base_marks.update(st.MarkCoverage.glyphs)
            elif lk.LookupType == 6:
                has_mkmk = True
    n_marks = len(base_marks)
    if n_marks < 300:
        fail(f'{name}: GPOS mark 定位缺失或过少（{n_marks} 个标记）')
    if not has_mkmk:
        fail(f'{name}: 缺少 mark-to-mark（GPOS LookupType 6），两个组合符会重叠而不是叠加')

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

    # 7. 上游源字体的超集（含从 Noto Sans CJK 抠出来的 5 字形子集）
    for rel in SUPERSET[name] + [CJK_SUBSET]:
        sp = os.path.join(ROOT, 'sources', rel)
        if not os.path.exists(sp):
            notes.append(f'{name}: 源字体 {rel} 缺失，跳过超集检查')
            continue
        gap = set(TTFont(sp, lazy=True).getBestCmap()) - set(cmap) - DROPPED
        if gap:
            fail(f'{name}: 不是 {rel} 的超集，缺 {len(gap)} 个码点：'
                 f'{["U+%04X" % c for c in sorted(gap)[:5]]}')

    # 8. glyf 结构：简单字形的 flag 保留位 bit7 必须为 0。
    #    用 TTGlyphPen 直接吃 CFF 三次曲线时，fontTools 会写出 flagCubic=0x80，
    #    OTS / 浏览器会报 "Bad glyph flag, reserved bit 7 must be set to zero" 并拒收整份字体。
    bad_flags = 0
    for g in glyf.glyphs.values():
        if getattr(g, 'numberOfContours', 0) < 0:      # 复合字形跳过
            continue
        flags = getattr(g, 'flags', None)
        if flags and any(b & 0x80 for b in flags):
            bad_flags += 1
    if bad_flags:
        fail(f'{name}: {bad_flags} 个简单字形的 glyf flag 置了保留位 bit7（OTS 会拒收整份字体）')

    # 9. GSUB 必须存在且含 ccmp —— 键盘帽/旗帜/ZWJ/Tag flag 全靠它。
    #    （踩过的坑：加 GPOS mark 时 feaLib 默认重建整份 GSUB，把 Noto 的 ccmp 删掉了。）
    if 'GSUB' not in f:
        fail(f'{name}: 缺 GSUB（emoji 序列的 ccmp 连字会全部失效）')
    else:
        feats = [fr.FeatureTag for fr in f['GSUB'].table.FeatureList.FeatureRecord]
        if 'ccmp' not in feats:
            fail(f'{name}: GSUB 里没有 ccmp（键盘帽/旗帜/ZWJ 等 emoji 序列不会合成）')

    # 10. 隐形字符必须 0 宽：组合标记 + Default_Ignorable
    #     （坑：U+20E3 是在 zero_width_marks() 之后才补进来的；Noto 的 ZWJ/Tag 字符
    #      带着 1100 的单位漏进来，会变成 2 格；Unicode 16 的新组合符被旧
    #      unicodedata 判成 Cn 也会漏掉）
    wide = []
    for cp, g in cmap.items():
        if is_combining_mark(cp) or is_Default_Ignorable(cp):
            w = hmtx.metrics.get(g, (0,))[0]
            if w:
                wide.append((cp, w))
    if wide:
        fail(f'{name}: {len(wide)} 个组合标记/Default_Ignorable 不是 0 宽：'
             f'{[f"U+{cp:04X}({w})" for cp, w in wide[:5]]}')

    # 10b. 组合标记必须进 GDEF mark 类（否则 HarfBuzz 不做 mark 定位）
    mark_class = set()
    if 'GDEF' in f:
        gc = getattr(f['GDEF'].table, 'GlyphClassDef', None)
        if gc is not None:
            mark_class = {g for g, cl in gc.classDefs.items() if cl == 3}
    not_marked = [cp for cp, g in cmap.items() if is_combining_mark(cp) and g not in mark_class]
    if not_marked:
        fail(f'{name}: {len(not_marked)} 个组合标记不在 GDEF mark 类：'
             f'{["U+%04X" % c for c in not_marked[:5]]}')

    # 11. 控制字符不该映射到字形
    ctl = [cp for cp in cmap if unicodedata.category(chr(cp)) == 'Cc']
    if ctl:
        fail(f'{name}: cmap 里仍有 {len(ctl)} 个控制字符：{["U+%04X" % c for c in ctl[:5]]}')

    # 12. win 指标必须覆盖字形 bbox，否则 Windows/GDI 会裁掉高字形
    if o.usWinAscent < f['head'].yMax or o.usWinDescent < -f['head'].yMin:
        fail(f'{name}: usWinAscent/Descent={o.usWinAscent}/{o.usWinDescent} 小于字形 bbox '
             f'(yMax={f["head"].yMax} yMin={f["head"].yMin})，会被裁剪；'
             f'请更新 build.py 的 WIN_ASCENT/WIN_DESCENT')

    # 13. 等宽 / 嵌入 / 版本 / 斜体元数据自洽
    post = f['post']
    if not post.isFixedPitch:
        fail(f'{name}: post.isFixedPitch=0（等宽字体应为非 0）')
    if o.xAvgCharWidth != 550:
        fail(f'{name}: OS/2.xAvgCharWidth={o.xAvgCharWidth}（等宽字体应为 550）')
    if o.fsType != 0:
        fail(f'{name}: OS/2.fsType={o.fsType}（应为 0=可安装）')
    if not (o.fsSelection & 0x80):
        fail(f'{name}: fsSelection 未设 USE_TYPO_METRICS(bit7)，行距会被 win 指标撑大')
    ver_name = f['name'].getDebugName(5) or ''
    mv = re.search(r'(\d+(?:\.\d+)?)', ver_name)
    if not mv or abs(float(mv.group(1)) - f['head'].fontRevision) > 1e-4:
        fail(f'{name}: head.fontRevision={f["head"].fontRevision} 与 name 版本 {ver_name!r} 不一致')
    uid = f['name'].getDebugName(3) or ''
    if any(s in uid for s in ('Nerd Font', 'ComicShanns', 'SeriousShanns', 'JuliaMono', 'Noto')):
        fail(f'{name}: name ID3(Unique ID) 仍是上游字体名：{uid!r}')
    if post.italicAngle:
        expect = round(math.tan(math.radians(-post.italicAngle)) * f['head'].unitsPerEm)
        if (f['hhea'].caretSlopeRise, f['hhea'].caretSlopeRun) != (f['head'].unitsPerEm, expect):
            fail(f'{name}: caretSlope 与 italicAngle 不匹配：'
                 f'({f["hhea"].caretSlopeRise},{f["hhea"].caretSlopeRun})，'
                 f'应为 ({f["head"].unitsPerEm},{expect})')

    # 13b. name 表：不留 Mac(platform 1) 记录；关键 ID 必须齐全（且只走 Windows 平台）
    mac = [r.nameID for r in f['name'].names if r.platformID == 1]
    if mac:
        fail(f'{name}: name 表里仍有 {len(mac)} 条 Mac(platform 1) 记录：{sorted(set(mac))}')
    need_ids = {0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 22}
    win_ids = {r.nameID for r in f['name'].names if r.platformID == 3}
    miss = need_ids - win_ids
    if miss:
        fail(f'{name}: name 表缺少 ID {sorted(miss)}（Windows 平台）')

    # 13b-2. 补全出来的元数据要自洽：URL 必须 https、WWS 与 typographic 命名一致
    nm = f['name']
    for nid in (11, 12):
        v = nm.getDebugName(nid) or ''
        if not v.startswith('https://'):
            fail(f'{name}: name ID{nid} 不是 https URL：{v!r}')
    if (nm.getDebugName(21) or '') != (nm.getDebugName(16) or ''):
        fail(f'{name}: name ID21(WWS Family) 与 ID16(Typographic Family) 不一致')
    if (nm.getDebugName(22) or '') != (nm.getDebugName(17) or ''):
        fail(f'{name}: name ID22(WWS Subfamily) 与 ID17(Typographic Subfamily) 不一致')
    if nm.getDebugName(7):
        fail(f'{name}: name ID7 应为空（未注册任何商标）')
    # ID0 里要带上游版权声明（OFL 要求），不能只是「derived from …」
    id0 = f['name'].getDebugName(0) or ''
    if 'Copyright' not in id0:
        fail(f'{name}: name ID0 未包含上游版权声明（OFL 要求）')

    # 13c. hmtx「尾部等宽段」必须真的被压掉：最常见的 advance（emoji 段）应排在字序尾部。
    #      否则 numberOfHMetrics 从 ~21k 涨到 ~64k，每 face 白涨 ~85 KB
    #      —— 见 build.py::compact_hmtx() 的字形重排。
    advs = [hmtx.metrics[g][0] for g in f.getGlyphOrder()]
    common_adv, common_n = Counter(advs).most_common(1)[0]
    trimmed = len(advs) - f['hhea'].numberOfHMetrics
    if trimmed < common_n - 64:
        fail(f'{name}: hmtx 尾部等宽段没被压掉（numberOfHMetrics={f["hhea"].numberOfHMetrics}，'
             f'只 trim 了 {trimmed} 个字形，而常见 advance {common_adv} 有 {common_n} 个）'
             f'—— build.py::compact_hmtx() 的字形重排可能失效')

    # 13d. STAT（样式菜单）：四 face 都要有，wght + ital，ital 在最后，每轴 1 条
    #      —— 对应 fontbakery 的 opentype/STAT/ital_axis、STAT_in_statics、STAT_strings
    is_italic = bool(post.italicAngle)
    if 'STAT' not in f:
        fail(f'{name}: 缺少 STAT 表（fontbakery opentype/STAT/ital_axis 会 FAIL）')
    else:
        stat = f['STAT'].table
        tags = [a.AxisTag for a in stat.DesignAxisRecord.Axis]
        if 'ital' not in tags:
            fail(f'{name}: STAT 缺少 ital 轴（现有 {tags}）')
        elif tags[-1] != 'ital':
            fail(f'{name}: STAT 的 ital 轴必须排在最后（现有顺序 {tags}）')
        per_axis = {}
        for av in (stat.AxisValueArray.AxisValue if stat.AxisValueArray else []):
            if av.Format in (1, 2, 3):
                per_axis.setdefault(tags[av.AxisIndex], []).append(av)
            else:
                fail(f'{name}: STAT 出现 Format {av.Format} 的 AxisValue（本项目只用 1/3）')
        for tag, avs in per_axis.items():
            if len(avs) > 1:
                fail(f'{name}: STAT 的 {tag} 轴有 {len(avs)} 条记录；静态字体每轴只能 1 条'
                     f'（把变量字体的 STAT 塞进静态字体，Windows 会把所有字重显示成同一个名字）')
        w = per_axis.get('wght') or []
        if len(w) == 1:
            if getattr(w[0], 'Value', None) != o.usWeightClass:
                fail(f'{name}: STAT wght={getattr(w[0], "Value", None)} '
                     f'与 OS/2.usWeightClass={o.usWeightClass} 不一致')
        ital = per_axis.get('ital') or []
        if len(ital) == 1:
            av = ital[0]
            val = getattr(av, 'Value', None)
            flags = av.Flags
            linked = getattr(av, 'LinkedValue', None)
            if is_italic:
                if (val, flags) != (1.0, 0):
                    fail(f'{name}: STAT ital 应为 (值 1.0, flags 0)，实际 ({val}, {flags:#06x})')
            else:
                if (val, flags, linked) != (0.0, 0x0002, 1.0):
                    fail(f'{name}: STAT ital 应为 (值 0.0, flags 0x0002(elidable), '
                         f'linked 1.0)，实际 ({val}, {flags:#06x}, {linked})')

    # 13e. 未 hinting 的字体必须带 smart dropout 开关
    #      PUSHW 511 / SCANCTRL / PUSHB 4 / SCANTYPE —— fontbakery 的 smart_dropout 找这 7 字节
    SMART_DROPOUT = bytes.fromhex('b801ff85b0048d')
    if 'prep' not in f:
        fail(f'{name}: 缺少 prep 表（未 hinting 字体应带 smart dropout 开关）')
    elif SMART_DROPOUT not in f['prep'].program.getBytecode():
        fail(f'{name}: prep 里没有 smart dropout 指令（应为 b8 01 ff 85 b0 04 8d）')

    # 13f. 有大小写映射的码点，其 swapcase 对应码点也必须在 cmap 里
    #      —— 对应 fontbakery 的 case_mapping（含它自己豁免的那批码点）
    #      Coptic 的两个大写就是缺在这个点上（见 build.py::add_coptic_capitals）
    CASE_EXCEPTIONS = {0x0192, 0x00B5, 0x03C0, 0x2126, 0x03BC, 0x03A9, 0x0394,
                       0x0251, 0x0261, 0x00FF, 0x0250, 0x025C, 0x0252, 0x0271,
                       0x0282, 0x029E, 0x0287, 0x0127, 0x0140, 0x023F, 0x0240, 0x026B}
    no_pair = []
    for cp in cmap:
        if cp in CASE_EXCEPTIONS or unicodedata.category(chr(cp))[0] != 'L':
            continue
        sw = chr(cp).swapcase()
        if len(sw) == 1 and sw != chr(cp) and ord(sw) not in cmap:
            no_pair.append((cp, ord(sw)))
    if no_pair:
        fail(f'{name}: {len(no_pair)} 个码点缺少大小写对应：'
             f'{[f"U+{a:04X}->U+{b:04X}" for a, b in no_pair[:5]]}')

    # 13g. 我们合成的 Coptic 大写（build.py::add_coptic_capitals）：advance 一格、墨迹不越界
    #      （防「以后换成 Noto 那种比例字形」：Noto 大写 psi 宽 738，会溢出 550 的格子）
    cgs = f.getGlyphSet()
    for cap_cp, small_cp in ((0x2CAE, 0x2CAF), (0x2CDE, 0x2CDF)):
        if cap_cp not in cmap or small_cp not in cmap:
            continue
        g = cmap[cap_cp]
        if hmtx.metrics[g][0] != 550:
            fail(f'{name}: U+{cap_cp:04X} 的 advance={hmtx.metrics[g][0]}，应为 550')
        bp = BoundsPen(cgs)
        cgs[g].draw(bp)
        if bp.bounds and (bp.bounds[0] < -1 or bp.bounds[2] > 551):
            fail(f'{name}: U+{cap_cp:04X} 墨迹越出格子：'
                 f'x=[{bp.bounds[0]:.0f}, {bp.bounds[2]:.0f}]（应落在 0..550）')

    # 13h. 不应有「从任何 cmap / UVS / GSUB / GPOS / GDEF / COLR 都到不了」的字形
    #      —— 对应 fontbakery 的 unreachable_glyphs，但这里把 format 14（UVS）也算上；
    #         fontbakery 只查 best cmap，所以它会误报 VS 变体字形。
    reach = set()
    for t in f['cmap'].tables:
        if getattr(t, 'cmap', None):
            reach.update(t.cmap.values())
        if getattr(t, 'format', None) == 14:
            for entries in (getattr(t, 'uvsDict', None) or {}).values():
                for _cp, gname in entries:
                    if gname:
                        reach.add(gname)
    known = set(f.getGlyphOrder())
    seen = set()

    def walk(obj, skip_attrs=()):
        if id(obj) in seen:
            return
        seen.add(id(obj))
        if isinstance(obj, str):
            if obj in known:
                reach.add(obj)
            return
        if isinstance(obj, (int, float, bytes, type(None), bool)):
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(k, skip_attrs)
                walk(v, skip_attrs)
            return
        if isinstance(obj, (list, tuple, set)):
            for x in obj:
                walk(x, skip_attrs)
            return
        for k, v in getattr(obj, '__dict__', {}).items():
            if k in skip_attrs:
                continue
            walk(v, skip_attrs)

    # 只算**会保留**的表：GPOS/GDEF 的覆盖范围由 cmap 派生，不额外引入字形。
    # COLR 的 BaseGlyphPaintRecord.BaseGlyph 是"定义"不是"引用"，必须跳过。
    if 'GSUB' in f:
        reach |= {g for g in gsub_outputs(f['GSUB'].table) if g in known}
    if 'COLR' in f:
        walk(f['COLR'].table, skip_attrs=('BaseGlyph', 'clips'))
    dead = [g for g in known if g != '.notdef' and g not in reach]
    if dead:
        fail(f'{name}: {len(dead)} 个字形不可达（无 cmap/UVS/GSUB/GPOS/GDEF/COLR 引用）：'
             f'{dead[:5]}')

    # 13i. sTypoAscender 必须 >= Agrave 的 yMax（否则 macOS 可能改用更大的行高）
    if 0x00C0 in cmap:
        bp = BoundsPen(cgs)
        cgs[cmap[0x00C0]].draw(bp)
        if bp.bounds and o.sTypoAscender < bp.bounds[3]:
            fail(f'{name}: sTypoAscender={o.sTypoAscender} '
                 f'< Agrave yMax={bp.bounds[3]:.0f}（macOS 可能撑大行高）')

    notes.append(f'{name}: cmap={len(cmap)} width={sorted(widths)} '
                 f'UVS={ {hex(k): v for k, v in sorted(n_uvs.items())} } '
                 f'marks={n_marks} colour-default={n_colr} size={size_mb:.2f}MB')


def main():
    pres = load_presentation()
    for face in FACES:
        check_face(face, pres)

    # 14. family 一致性：四个 face 的纵向指标与码点覆盖必须完全一样
    #     （否则切换字重/斜体时行距会跳；README 也宣称四个 face 覆盖相同）
    ref = None
    for face in FACES:
        path = os.path.join(DIST, f'ComicMathMono-{face}.ttf')
        if not os.path.exists(path):
            continue
        ff = TTFont(path, lazy=True)
        oo, hh = ff['OS/2'], ff['hhea']
        metrics = {k: getattr(oo, k) for k in FAMILY_METRICS}
        metrics['hhea.ascent'] = hh.ascent
        metrics['hhea.descent'] = hh.descent
        cm = set(ff.getBestCmap())
        if ref is None:
            ref = (face, metrics, cm)
        else:
            rface, rmetrics, rcm = ref
            if metrics != rmetrics:
                diff = {k: (rmetrics[k], metrics[k]) for k in rmetrics if rmetrics[k] != metrics[k]}
                fail(f'family 纵向指标不一致（{rface} vs {face}）：{diff}')
            if cm != rcm:
                a = ['U+%04X' % c for c in sorted(rcm - cm)[:4]]
                b = ['U+%04X' % c for c in sorted(cm - rcm)[:4]]
                fail(f'family 码点覆盖不一致（{rface} vs {face}）：'
                     f'仅 {rface} 有 {a}；仅 {face} 有 {b}')

    # 15. OTS：浏览器按同一套检查决定要不要加载字体
    ots = _ots_runner()
    if ots is None:
        notes.append('未找到 ots-sanitize / opentype-sanitizer，跳过 OTS 校验'
                     '（pip install opentype-sanitizer）')
    else:
        with tempfile.TemporaryDirectory() as td:
            for face in FACES:
                path = os.path.join(DIST, f'ComicMathMono-{face}.ttf')
                if not os.path.exists(path):
                    continue
                rc, err = ots(path, os.path.join(td, f'{face}.ots.ttf'))
                if rc != 0:
                    head = ' / '.join(line.strip() for line in err.strip().splitlines()[:2])
                    fail(f'{face}: OTS 拒收（浏览器会拒绝加载）：{head}')

    # 11. emoji 序列合成（可选，需要 uharfbuzz）
    for face in FACES:
        path = os.path.join(DIST, f'ComicMathMono-{face}.ttf')
        if os.path.exists(path):
            check_emoji_sequences(face, path)
            check_mark_stacking(face, path)

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
