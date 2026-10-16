#!/usr/bin/env python3
"""ComicMathMono —— 面向终端的合并等宽字体，构建脚本。

四个 face：
  Regular    = ComicShannsMono NFM Regular + Julia Regular 数学层 + Noto COLRv1 emoji(全量)
  Bold       = ComicShannsMono NFM Bold    + Julia Bold    数学层（emoji 回退到 Regular）
  Italic     = SeriousShanns  NFM Italic   + Julia Italic  补缺(拉丁扩展+数学)（emoji 回退到 Regular）
  BoldItalic = SeriousShanns  NFM BoldItalic + Julia BoldItalic 补缺（emoji 回退到 Regular）

advance 规范：单格 550/1000upem；emoji 1100（两格）。CJK 不烤，走 fontconfig fallback。

用法：
    python3 build.py          # 依赖见 requirements.txt；源字体见 sources/
产物输出到 dist/。
"""
import copy
import os
import sys
import unicodedata

from fontTools.ttLib import TTFont, newTable
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.merge import Merger
import fontTools.ttLib as ttLib
from fontTools.ttLib.tables.C_O_L_R_ import table_C_O_L_R_
from fontTools.ttLib.tables.C_P_A_L_ import table_C_P_A_L_

# ---------- 路径 ----------

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(ROOT, 'sources')
DIST = os.path.join(ROOT, 'dist')
TMP = os.path.join(ROOT, '.build')          # 中间产物，不入库

FAMILY = 'ComicMathMono'
CELL = 550        # 单格宽度
WIDE = 1100       # emoji 宽度（两格）

# Julia 优先用 sources/julia/ 下的本地副本；没有则回退系统已安装的 Nerd Font 版本
SYSTEM_JULIA_DIRS = [
    '/usr/share/fonts/TTF/juliamono-nerd/mono',
    os.path.expanduser('~/.local/share/fonts/juliamono-nerd/mono'),
]


def _julia(name):
    local = os.path.join(SOURCES, 'julia', name)
    if os.path.exists(local):
        return local
    for d in SYSTEM_JULIA_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return local


SRC = {
    'comic_r': os.path.join(SOURCES, 'ComicR.ttf'),
    'comic_b': os.path.join(SOURCES, 'ComicB.ttf'),
    'ssh_i': os.path.join(SOURCES, 'SShI.ttf'),
    'ssh_bi': os.path.join(SOURCES, 'SShBI.ttf'),
    'julia_r': _julia('JuliaMonoNerdFontMono-Regular.ttf'),
    'julia_b': _julia('JuliaMonoNerdFontMono-Bold.ttf'),
    'julia_i': _julia('JuliaMonoNerdFontMono-Italic.ttf'),
    'julia_bi': _julia('JuliaMonoNerdFontMono-BoldItalic.ttf'),
    'noto': os.path.join(SOURCES, 'Noto-COLRv1.ttf'),
}

# 成品字体里写入的许可信息（便于再分发时满足上游要求）
COPYRIGHT = (
    'ComicMathMono: a merged terminal monospace font. Glyphs derived from '
    'ComicShannsMono Nerd Font (MIT), SeriousShanns Nerd Font (MIT), '
    'JuliaMono (OFL-1.1) and Noto Color Emoji (OFL-1.1). '
    'Distributed under the SIL Open Font License, Version 1.1.'
)
LICENSE_DESC = 'This Font Software is licensed under the SIL Open Font License, Version 1.1.'
LICENSE_URL = 'https://scripts.sil.org/OFL'

# ---------- Julia 层码点范围 ----------
# Julia 优先（可覆盖 base 已有字形）：数学/符号区，保证技术符号风格统一
JULIA_WIN_RANGES = [
    (0x0370, 0x03FF), (0x1F00, 0x1FFF), (0x2100, 0x214F), (0x2190, 0x21FF),
    (0x2200, 0x22FF), (0x2300, 0x23FF), (0x2500, 0x259F), (0x27C0, 0x27EF),
    (0x2800, 0x28FF), (0x2980, 0x29FF), (0x2A00, 0x2AFF),
]
JULIA_WIN_EXTRA = [0x25CC, 0x2605, 0x2713, 0x2714, 0x2715, 0x2716, 0x2717, 0x279C]

# 只补 base 缺失的码点（不覆盖 base 已有字形）：拉丁扩展 / 标点 / 其他字母文字
JULIA_FILL_RANGES = [
    # 拉丁 / 注音 / 修饰符
    (0x00A0, 0x00FF), (0x0100, 0x024F), (0x0250, 0x02AF), (0x02B0, 0x02FF),
    (0x1D00, 0x1D7F), (0x1D80, 0x1DBF), (0x1E00, 0x1EFF),
    (0x2C60, 0x2C7F), (0xA720, 0xA7FF), (0xAB30, 0xAB6F), (0x10780, 0x107BF),
    # 标点 / 上下标 / 货币 / 数字形式 / 控制图
    (0x2000, 0x206F), (0x2070, 0x209F), (0x20A0, 0x20CF), (0x2150, 0x218F), (0x2400, 0x243F),
    # 符号 / 几何 / 圈号 / 补充箭头 / 遗留计算 / 数学字母
    (0x2460, 0x24FF), (0x25A0, 0x25FF), (0x2600, 0x26FF), (0x2700, 0x27BF),
    (0x27F0, 0x27FF), (0x2900, 0x297F), (0x2B00, 0x2BFF), (0x2E00, 0x2E7F),
    (0x1D400, 0x1D7FF), (0x1F100, 0x1F1FF), (0x1F650, 0x1F67F),
    (0x1F780, 0x1F7FF), (0x1F800, 0x1F8FF), (0x1FB00, 0x1FBFF),
    # Tier 2：其他字母文字
    (0x0400, 0x052F), (0x1C80, 0x1C8F), (0x2DE0, 0x2DFF), (0xA640, 0xA69F),
    (0x0530, 0x058F), (0x0590, 0x05FF), (0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
    (0x10A0, 0x10FF), (0x1C90, 0x1CBF), (0x16A0, 0x16FF), (0x10C80, 0x10CFF),
    (0x13A0, 0x13FF), (0xAB70, 0xABBF),
]

# 强制换成 Julia 版（覆盖 Comic/SeriousShanns）的数学/标点符号
JULIA_FORCE = [0x00AC, 0x00B0, 0x00B1, 0x00D7, 0x00F7, 0x2020, 0x2021, 0x2026]

# 组合重音符号：收录为 0 宽（advance=0）。
# 说明：HarfBuzz 会先把「基字母 + 标记」合成预组合字形（有的话），只有无预组合形式的
# 序列（如 q+U+0301）才会用到独立标记字形；此时 HarfBuzz 自带回退定位，会把标记挪回
# 基字符所在格子，因此终端与浏览器都能正确叠加。详见 docs/combining-marks.md。
JULIA_COMBINING_RANGES = [
    (0x0300, 0x036F),   # Combining Diacritical Marks
    (0x1AB0, 0x1AFF),   # Combining Diacritical Marks Extended
    (0x1DC0, 0x1DFF),   # Combining Diacritical Marks Supplement
    (0x20D0, 0x20FF),   # Combining Diacritical Marks for Symbols
    (0xFE20, 0xFE2F),   # Combining Half Marks
]


# ---------- COLR/CPAL 合并支持 ----------

def _remap_names(obj, mapping, seen=None):
    if seen is None:
        seen = set()
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    if isinstance(obj, (int, float, bool, type(None))):
        return obj
    oid = id(obj)
    if oid in seen:
        return obj
    seen.add(oid)
    if isinstance(obj, list):
        return [_remap_names(x, mapping, seen) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_remap_names(x, mapping, seen) for x in obj)
    if isinstance(obj, dict):
        return {_remap_names(k, mapping, seen): _remap_names(v, mapping, seen) for k, v in obj.items()}
    if hasattr(obj, '__dict__'):
        for k, v in list(vars(obj).items()):
            try:
                setattr(obj, k, _remap_names(v, mapping, seen))
            except AttributeError:
                pass
        return obj
    return obj


class MergingCOLR(table_C_O_L_R_):
    def merge(self, merger, tables):
        idx = next((i for i, t in enumerate(tables) if t is not NotImplemented), None)
        if idx is None:
            return NotImplemented
        table = tables[idx]
        mapping = merger.duplicateGlyphsPerFont[idx]
        if mapping:
            table = copy.deepcopy(table)
            table = _remap_names(table, mapping)
        return table


class MergingCPAL(table_C_P_A_L_):
    def merge(self, merger, tables):
        for t in tables:
            if t is not NotImplemented:
                return t
        return NotImplemented


_orig_getTableClass = ttLib.getTableClass


def _getTableClass(tag):
    if tag == 'COLR':
        return MergingCOLR
    if tag == 'CPAL':
        return MergingCPAL
    return _orig_getTableClass(tag)


ttLib.getTableClass = _getTableClass


# ---------- 基础工具 ----------

def decompose_glyph(font, name):
    glyph_set = font.getGlyphSet()
    rec = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(rec)
    pen = TTGlyphPen(None)
    rec.replay(pen)
    return pen.glyph()


def scale_glyph(g, factor):
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    g.coordinates = GlyphCoordinates([(x * factor, y * factor) for x, y in g.coordinates])
    return g


def flatten_scale_font(font, factor, upem_factor=None, uniform_advance=None):
    if upem_factor is None:
        upem_factor = factor
    order = font.getGlyphOrder()
    new_glyphs = {}
    for name in order:
        try:
            g = decompose_glyph(font, name)
        except Exception:
            continue
        if factor != 1.0:
            g = scale_glyph(g, factor)
        new_glyphs[name] = g
    glyf = newTable('glyf')
    glyf.glyphOrder = order
    glyf.glyphs = new_glyphs
    font['glyf'] = glyf
    for name, m in list(font['hmtx'].metrics.items()):
        m = list(m)
        m[0] = round(m[0] * factor)
        font['hmtx'].metrics[name] = tuple(m)
    if 'hhea' in font:
        t = font['hhea']
        for a in ('ascent', 'descent', 'lineGap'):
            if hasattr(t, a):
                setattr(t, a, round(getattr(t, a) * upem_factor))
    if 'OS/2' in font:
        os2 = font['OS/2']
        for a in ('sTypoAscender', 'sTypoDescender', 'sTypoLineGap',
                  'usWinAscent', 'usWinDescent', 'sxHeight', 'sCapHeight'):
            if hasattr(os2, a) and getattr(os2, a) is not None:
                setattr(os2, a, round(getattr(os2, a) * upem_factor))
    if uniform_advance is not None:
        for name, m in list(font['hmtx'].metrics.items()):
            m = list(m)
            m[0] = uniform_advance
            font['hmtx'].metrics[name] = tuple(m)
    font['head'].unitsPerEm = round(font['head'].unitsPerEm * upem_factor)
    return font


def set_cmap_entry(font, cp, name):
    for t in font['cmap'].tables:
        if not hasattr(t, 'cmap'):
            continue
        if t.platformID not in (0, 3):
            continue
        if t.format in (0, 6) and cp > 0xFF:
            continue
        if t.format == 4 and cp > 0xFFFF:
            continue
        t.cmap[cp] = name


def copy_julia_into(base, julia, ranges, extra, overwrite, skip=None):
    jcmap = julia.getBestCmap()
    jglyf = julia['glyf']
    order = list(base.getGlyphOrder())
    glyfs = base['glyf'].glyphs
    hmtx = base['hmtx'].metrics
    base_cmap = base.getBestCmap()
    want = set()
    for a, b in ranges:
        want.update(range(a, b + 1))
    want.update(extra)
    copied = 0
    for cp in sorted(want):
        if skip and cp in skip:
            continue
        src_name = jcmap.get(cp)
        if src_name is None or src_name not in jglyf.glyphs:
            continue
        if not overwrite and cp in base_cmap:
            continue
        g = jglyf.glyphs[src_name]
        if not hasattr(g, 'coordinates') and getattr(g, 'numberOfContours', 0) != 0:
            continue
        if cp in base_cmap:
            dst_name = base_cmap[cp]
        else:
            dst_name = src_name
            if dst_name in glyfs:
                dst_name = src_name + '.julia'
        if dst_name not in order:
            order.append(dst_name)
        glyfs[dst_name] = copy.deepcopy(g)
        hmtx[dst_name] = [CELL, 0]
        set_cmap_entry(base, cp, dst_name)
        copied += 1
    base.setGlyphOrder(order)
    return copied


def zero_width_marks(font):
    """把 Mn/Me 组合标记的 advance 设为 0（它们默认要叠加在前一个字符上）。"""
    cmap = font.getBestCmap()
    n = 0
    for cp, gname in cmap.items():
        if unicodedata.category(chr(cp)) not in ('Mn', 'Me'):
            continue
        if gname not in font['hmtx'].metrics:
            continue
        m = list(font['hmtx'].metrics[gname])
        if m[0] != 0:
            m[0] = 0
            font['hmtx'].metrics[gname] = tuple(m)
            n += 1
    return n


def strip_locl(font):
    """删除 fontTools Merger 自动合成的 locl 特性。

    Merger 在合并时，会对"两个字体都覆盖同一码点、但字形不同"的情况自动合成一条
    locl 规则（注册在 latn 下），映射形如 nine -> nine.1。由于本字体的 base 原本
    没有任何合法的 locl，这条规则只会在拉丁文片段里把 ASCII 数字/符号替换成 Noto
    的字形（表现为空白/双宽），故整条删除。详见 docs/locl-issue.md。
    """
    if 'GSUB' not in font:
        return
    gsub = font['GSUB'].table
    frs = gsub.FeatureList.FeatureRecord
    drop_feat = [i for i, fr in enumerate(frs) if fr.FeatureTag == 'locl']
    if not drop_feat:
        return
    drop_lk = set()
    for i in drop_feat:
        drop_lk.update(frs[i].Feature.LookupListIndex)

    # 1) 删除 locl feature，并重映射 langsys 里的 feature 索引
    keep = [fr for i, fr in enumerate(frs) if i not in drop_feat]
    fidx = {i: j for j, i in enumerate(i for i in range(len(frs)) if i not in drop_feat)}
    gsub.FeatureList.FeatureRecord = keep
    gsub.FeatureList.FeatureCount = len(keep)
    for sr in gsub.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [l.LangSys for l in sr.Script.LangSysRecord]:
            if ls is not None:
                ls.FeatureIndex = [fidx[i] for i in ls.FeatureIndex if i in fidx]

    # 2) 删除不再被任何 feature / 上下文规则引用的孤儿 lookup
    used = set()
    for fr in keep:
        used.update(fr.Feature.LookupListIndex)
    for lk in gsub.LookupList.Lookup:
        for sub in lk.SubTable:
            for rec in getattr(sub, 'SubstLookupRecord', None) or ():
                used.add(rec.LookupListIndex)
    drop_lk -= used
    if drop_lk:
        lkidx = {i: j for j, i in enumerate(i for i in range(len(gsub.LookupList.Lookup)) if i not in drop_lk)}
        gsub.LookupList.Lookup = [lk for i, lk in enumerate(gsub.LookupList.Lookup) if i not in drop_lk]
        gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
        for fr in keep:
            fr.Feature.LookupListIndex = [lkidx[i] for i in fr.Feature.LookupListIndex]
        for lk in gsub.LookupList.Lookup:
            for sub in lk.SubTable:
                for rec in getattr(sub, 'SubstLookupRecord', None) or ():
                    rec.LookupListIndex = lkidx[rec.LookupListIndex]


def merge_noto_emoji(base, noto):
    """把 Noto COLRv1 整字体合并进 base（base 已有码点优先，Noto 填 emoji）。"""
    base_path = os.path.join(TMP, '_base_tmp.ttf')
    noto_path = os.path.join(TMP, '_noto_tmp.ttf')
    base.save(base_path)
    noto.save(noto_path)
    merger = Merger()
    font = merger.merge([base_path, noto_path])
    strip_locl(font)
    return font


def set_face_meta(font, subfamily, weight, bold, italic):
    psname = f'{FAMILY}-{subfamily.replace(" ", "")}'
    name = font['name']
    for nid, val in ((0, COPYRIGHT), (1, FAMILY), (2, subfamily),
                     (4, f'{FAMILY} {subfamily}'), (5, 'Version 1.0'),
                     (6, psname), (13, LICENSE_DESC), (14, LICENSE_URL)):
        for rec in list(name.names):
            if rec.nameID == nid:
                rec.string = val
        name.setName(val, nid, 3, 1, 0x409)
        name.setName(val, nid, 1, 0, 0)
    os2 = font['OS/2']
    os2.usWeightClass = weight
    fs = 0
    if bold:
        fs |= 0x20
    if italic:
        fs |= 0x01
    if not bold and not italic:
        fs = 0x40
    os2.fsSelection = fs
    font['head'].macStyle = (0x01 if bold else 0) | (0x02 if italic else 0)
    if 'post' in font:
        font['post'].italicAngle = -12.5 if italic else 0.0
    return font


# ---------- 主流程 ----------

def build_face(style, base_key, julia_key, emoji, overwrite):
    print(f'── 构建 {style} ──')
    base = TTFont(SRC[base_key])
    julia = TTFont(SRC[julia_key])

    # Julia: 2000upem/adv1200 → 1000upem/adv550
    julia = flatten_scale_font(julia, CELL / 1200, upem_factor=0.5, uniform_advance=CELL)

    # 基底：Comic 已是 550；Serious Shanns 按实测 advance 归一化到 550
    if base_key.startswith('ssh'):
        adv_a = base.getGlyphSet()['A'].width
        base = flatten_scale_font(base, CELL / adv_a, upem_factor=1.0, uniform_advance=CELL)

    # Noto(emoji) 已有的码点不要用 Julia 覆盖，否则会把彩色 emoji 变成单色符号
    noto_cmap = set(TTFont(SRC['noto']).getBestCmap().keys())

    n = copy_julia_into(base, julia, JULIA_WIN_RANGES, JULIA_WIN_EXTRA, overwrite)
    n += copy_julia_into(base, julia, JULIA_FILL_RANGES, [], False, skip=noto_cmap)
    n += copy_julia_into(base, julia, JULIA_COMBINING_RANGES, [], False, skip=noto_cmap)
    n += copy_julia_into(base, julia, [], JULIA_FORCE, True)
    z = zero_width_marks(base)
    print(f'  Julia 层拷入 {n} 个码点（其中组合标记 0 宽化 {z} 个）')

    if emoji:
        noto = TTFont(SRC['noto'])
        noto = flatten_scale_font(noto, WIDE / 1024, upem_factor=1000 / 1024, uniform_advance=WIDE)
        for tag in ('vhea', 'vmtx'):
            if tag in noto:
                del noto[tag]
        font = merge_noto_emoji(base, noto)
        print(f'  emoji 层合并完成，glyph 数: {len(font.getGlyphOrder())}')
    else:
        font = base

    weight = 700 if style in ('Bold', 'Bold Italic') else 400
    bold = style in ('Bold', 'Bold Italic')
    italic = style in ('Italic', 'Bold Italic')
    set_face_meta(font, style, weight, bold, italic)
    out = os.path.join(DIST, f'{FAMILY}-{style.replace(" ", "")}.ttf')
    font.save(out)
    print(f'  写出 {out}')
    return out


def check_sources():
    missing = [p for p in SRC.values() if not os.path.exists(p)]
    if missing:
        print('缺少源字体文件：', file=sys.stderr)
        for p in missing:
            print('  ' + p, file=sys.stderr)
        print('获取方式见 sources/README.md', file=sys.stderr)
        return False
    return True


def main():
    if not check_sources():
        return 1
    os.makedirs(DIST, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    build_face('Regular', 'comic_r', 'julia_r', emoji=True, overwrite=True)
    build_face('Bold', 'comic_b', 'julia_b', emoji=False, overwrite=True)
    build_face('Italic', 'ssh_i', 'julia_i', emoji=False, overwrite=False)
    build_face('Bold Italic', 'ssh_bi', 'julia_bi', emoji=False, overwrite=False)
    print(f'全部完成 → {DIST}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
