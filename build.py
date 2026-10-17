#!/usr/bin/env python3
"""ComicMathMono —— 面向终端的合并等宽字体，构建脚本。

四个 face：
  Regular    = ComicShannsMono NFM Regular + Julia Regular 数学层 + Noto COLRv1 emoji(全量)
  Bold       = ComicShannsMono NFM Bold    + Julia Bold    数学层 + Noto COLRv1 emoji(全量)
  Italic     = SeriousShanns  NFM Italic   + Julia Italic  补缺(拉丁扩展+数学) + Noto COLRv1 emoji(全量)
  BoldItalic = SeriousShanns  NFM BoldItalic + Julia BoldItalic 补缺 + Noto COLRv1 emoji(全量)

advance 规范：单格 550/1000upem；emoji 1100（两格）。CJK 不烤，走 fontconfig fallback。

用法：
    python3 build.py          # 依赖见 requirements.txt；源字体见 sources/
产物输出到 dist/。
"""
import copy
import math
import os
import re
import sys
import unicodedata
from collections import Counter

from fontTools.ttLib import TTFont, newTable
from fontTools.misc import timeTools
from fontTools.misc.transform import Transform
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.merge import Merger
from fontTools.merge.unicode import is_Default_Ignorable
import fontTools.ttLib as ttLib
from fontTools.ttLib.tables.C_O_L_R_ import table_C_O_L_R_
from fontTools.ttLib.tables.C_P_A_L_ import table_C_P_A_L_
from fontTools.ttLib.tables.ttProgram import Program

# ---------- 路径 ----------

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(ROOT, 'sources')
DIST = os.path.join(ROOT, 'dist')
TMP = os.path.join(ROOT, '.build')          # 中间产物，不入库

FAMILY = 'ComicMathMono'
CELL = 550        # 单格宽度
WIDE = 1100       # emoji 宽度（两格）

# 键盘帽基字符：U+0023 '#'、U+002A '*'、U+0030..U+0039 '0'..'9'。
# 它们的 VS16 必须写成 DefaultUVS（沿用默认字形），不能换成 Noto 的彩色数字 ——
# 原因见 apply_emoji_presentation() 里的注释。
KEYCAP_BASES = frozenset([0x23, 0x2A] + list(range(0x30, 0x3A)))

# ---------- 版本与纵向指标 ----------
# 四个 face 必须共用同一套纵向指标（fontbakery family/vertical_metrics），否则切换字重/斜体时行距会跳。
VERSION = '1.0'                 # head.fontRevision 与 name ID5/ID3 共用
# 行高 = ASCENT - DESCENT = 1278（保持不变）。之所以从 928/−350 挪成 1030/−248：
# Agrave 的重音顶到 988（斜体 1026，倾斜让 bbox 更高）—— 声明 ascent 装不下最高字形时，
# macOS 可能改用更大的行高（fontbakery `typoascender_exceeds_Agrave`）。挪动只是把单位从
# descent 移到 ascent：行高不变，文字在行框内下移 102/1278 ≈ 8%（14px 字号约 1.1px）。
ASCENT = 1030                   # hhea.ascent = OS/2.sTypoAscender（控制行距）
DESCENT = -248                  # hhea.descent = OS/2.sTypoDescender（控制行距）
# usWinAscent/Descent 要覆盖**全家族**字形 bbox，否则 Windows/GDI 会裁掉高字形
# （斜体面实测 yMax=1317 / yMin=-1029）。行距交给上面的 typo 值 + fsSelection bit7。
# 若换源字体后字形更高，tools/verify.py 的 win_ascent 断言会失败，届时更新这两个常量。
WIN_ASCENT = 1317
WIN_DESCENT = 1029
ITALIC_ANGLE = -12.7            # 取自 SeriousShanns 的 post.italicAngle（原值 -12.5 是拍脑袋的）
UNDERLINE_POSITION = -100       # 取自 JuliaMono（-200/100 @2000upem）
UNDERLINE_THICKNESS = 50
# OS/2 的上下标 / 删除线度量必须四个 face 一致，否则在 Word/LibreOffice 等
# 依赖这些值的软件里切换字重/斜体会跳。Canonical 值取自 ComicShanns（650/600，
# 上标 0/350、下标 0/75）。删除线厚度不能是 0（当前上游 Comic/Serious 都是 0，
# 结果为“删除线不可见”），统一为 50/300。
SUBSCRIPT_METRICS = (650, 600, 0, 75)      # XSize, YSize, XOffset, YOffset
SUPERSCRIPT_METRICS = (650, 600, 0, 350)
STRIKEOUT_METRICS = (50, 300)             # Size, Position

# Julia 优先用 sources/julia/ 下的本地副本；没有则回退系统已安装的 Nerd Font 版本
SYSTEM_JULIA_DIRS = [
    '/usr/share/fonts/TTF/juliamono-nerd/mono',
    os.path.expanduser('~/.local/share/fonts/juliamono-nerd/mono'),
]


EMOJI_DATA = os.path.join(ROOT, 'data', 'emoji-data.txt')   # Unicode emoji 属性表


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
    'notosym2': os.path.join(SOURCES, 'NotoSansSymbols2-Regular.ttf'),
    'notosym': os.path.join(SOURCES, 'NotoSansSymbols-Regular.ttf'),
    'cjk5': os.path.join(SOURCES, 'NotoSansCJKsc-Symbols5.ttf'),
}

# 成品字体里写入的许可信息（便于再分发时满足上游要求）。
# OFL-1.1 要求「版权声明随字体分发」，所以这里把各上游的 copyright 一并列出，
# 而不是只写「derived from …」。完整许可文本见 NOTICE.md / LICENSE-OFL-1.1.txt。
COPYRIGHT = (
    'ComicMathMono, a merged terminal monospace font. '
    'Derived from: ComicShannsMono Nerd Font (Copyright (c) 2018 Shannon Miwa, '
    '(c) 2023 Jesus Gonzalez, (c) 2023 Rodrigo Batista de Moraes, (c) 2024 Fini Jastrow; MIT); '
    'SeriousShanns Nerd Font (Copyright (c) 2018 Shannon Miwa, (c) 2019 dtinth, '
    '(c) 2023-2024 Kyle Beechly; MIT); '
    'JuliaMono (Copyright (c) 2020-2026 The JuliaMono Project Authors; OFL-1.1); '
    'Noto Color Emoji, Noto Sans Symbols/Symbols 2, Noto Sans CJK '
    '(Copyright Google Inc. / The Noto Project Authors / Adobe; OFL-1.1). '
    'Distributed under the SIL Open Font License, Version 1.1.'
)
LICENSE_DESC = 'This Font Software is licensed under the SIL Open Font License, Version 1.1.'
LICENSE_URL = 'https://scripts.sil.org/OFL'

# ---------- name 表里其余字段（ID 8/9/10/11/12/19/21/22） ----------
# ID 7（Trademark）**有意留空**：没有注册过商标就不做商标声明。
# ID 18（Compatible Full）只有 Mac 平台会读，而我们已经删掉全部 Mac 记录，故不加。
# ID 23/24（CPAL light/dark）与 ID 25（可变字体前缀）对本字体不适用。
VENDOR_NAME = 'ATMxsp01'                       # ID 8 Manufacturer
DESIGNER_NAME = 'ATMxsp01'                     # ID 9 Designer
DESCRIPTION = ('A comic-style monospace terminal font with Latin, Greek, Cyrillic, '
               'mathematical symbols and full-colour emoji.')   # ID 10
VENDOR_URL = 'https://github.com/ATMxsp01/ComicMathMono'        # ID 11
DESIGNER_URL = 'https://github.com/ATMxsp01'                    # ID 12
SAMPLE_TEXT = ('The quick brown fox jumps over the lazy dog. '
               '0123456789 \u2211 \u222b \u221a \u03c0 \u2260 \u2264 \u2265 \U0001f600')  # ID 19

# ---------- 可复现构建 ----------
# head.created/modified 每次构建都变 → 文件不 byte-identical。用 SOURCE_DATE_EPOCH
# 固定（默认 2000-01-01 UTC）；head 里的时间戳是「1904 起算的秒」，所以要减 epoch_diff。
SOURCE_DATE_EPOCH = int(os.environ.get('SOURCE_DATE_EPOCH', '946684800'))
BUILD_TIME = SOURCE_DATE_EPOCH - timeTools.epoch_diff


def ensure_reproducible_hash_seed():
    """强制 PYTHONHASHSEED=0，否则 GPOS 的二进制每次构建都不同。

    fontTools 编译 OT 表时按「子表共享顺序」排布，而那个顺序受 Python 字符串哈希
    随机化影响（实测两次构建 GPOS 字节不同、CMAP/GLYF 相同）。解释器启动后再改
    ``os.environ`` 已经无效，只能带 seed 自重启一次；只在走 ``main()`` 时做。
    """
    if os.environ.get('PYTHONHASHSEED') != '0':
        os.environ['PYTHONHASHSEED'] = '0'
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__), *sys.argv[1:]])

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


def is_combining_mark(cp):
    """判定某个码点是否要当组合标记处理（0 宽 + 进 GPOS mark 定位）。

    **不能只用 ``unicodedata.category``**：本机 Python 3.13 的 Unicode 数据是 15.1，
    而 JuliaMono 快照已经到 Unicode 16 —— U+1ACF..U+1ADD、U+1AE0..U+1AE5 这 21 个
    新组合符会被 Python 判成 Cn（未分配），于是既没 0 宽化、也没进 GPOS mark
    （fontbakery 的 ``gdef_mark_chars`` 会报）。既然这些区块就是我们拷贝组合符的范围，
    直接按区块判定：区块内 + 类别为 Mn/Me，二者取并集。
    """
    if unicodedata.category(chr(cp)) in ('Mn', 'Me'):
        return True
    return any(a <= cp <= b for a, b in JULIA_COMBINING_RANGES)


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

def decompose_glyph(font, name, cubic=False):
    """把字形分解成一个 glyf 简单字形。

    ``cubic=True`` 用于 CFF/OTTO 源（三次曲线）：必须先经 ``Cu2QuPen`` 转成二次
    曲线。否则 ``TTGlyphPen`` 会把三次段用 fontTools 内部的 ``flagCubic=0x80``
    标记写进 glyf 的 flag 字节 —— 那是 OpenType 的保留位，OTS / 浏览器会判定
    "Bad glyph flag" 并**拒收整份字体**（本项目的 5 个 CJK 类 emoji 就踩了这个坑）。
    """
    glyph_set = font.getGlyphSet()
    rec = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(rec)
    pen = TTGlyphPen(None)
    out_pen = Cu2QuPen(pen, max_err=1.0, reverse_direction=True) if cubic else pen
    rec.replay(out_pen)
    return pen.glyph()


def scale_glyph(g, factor):
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    g.coordinates = GlyphCoordinates([(x * factor, y * factor) for x, y in g.coordinates])
    return g


def flatten_scale_font(font, factor, upem_factor=None, uniform_advance=None):
    if upem_factor is None:
        upem_factor = factor
    # CFF/OTTO 源没有 glyf：先把三次曲线转成二次曲线（见 decompose_glyph），
    # 并在建好 glyf 之后丢弃 CFF，避免留下一个"半转换"的字体对象。
    cubic = 'CFF ' in font or 'CFF2' in font
    order = font.getGlyphOrder()
    new_glyphs = {}
    for name in order:
        try:
            g = decompose_glyph(font, name, cubic=cubic)
        except Exception:
            continue
        if factor != 1.0:
            g = scale_glyph(g, factor)
        new_glyphs[name] = g
    glyf = newTable('glyf')
    glyf.glyphOrder = order
    glyf.glyphs = new_glyphs
    font['glyf'] = glyf
    for tag in ('CFF ', 'CFF2', 'VORG'):
        if tag in font:
            del font[tag]
    # 关键：decompose_glyph() 已经把源字体的 lsb 烘进坐标（fontTools 的
    # getGlyphSet() 会按 lsb - xMin 平移轮廓），所以缩放后必须 recalcBounds 并
    # 令 hmtx.lsb = 新 xMin。否则 FreeType/HarfBuzz 会按“lsb - xMin”再次平移轮廓，
    # 把 Julia/Noto/SeriousShanns 的字形整体推到格子左边（实测 ∫ 左移 99 单位）。
    for name, m in list(font['hmtx'].metrics.items()):
        m = list(m)
        m[0] = round(m[0] * factor)
        g = new_glyphs.get(name)
        if g is not None:
            if g.numberOfContours != 0:
                try:
                    g.recalcBounds(glyf)
                except Exception:
                    pass
            m[1] = round(g.xMin) if hasattr(g, 'xMin') else 0
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


def copy_julia_into(base, julia, ranges, extra, overwrite, skip=None, suffix='.julia',
                    advance=CELL):
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
                dst_name = src_name + suffix
        if dst_name not in order:
            order.append(dst_name)
        glyfs[dst_name] = copy.deepcopy(g)
        # 不能用 0：Julia/Noto 的字形不是贴着格子左边设计的，lsb=0 会让
        # FreeType 把轮廓整体左移 xMin 个单位。用复制过来字形的 xMin 保持原设计位置。
        lsb = round(g.xMin) if getattr(g, 'numberOfContours', 0) != 0 and hasattr(g, 'xMin') else 0
        hmtx[dst_name] = [advance, lsb]
        set_cmap_entry(base, cp, dst_name)
        copied += 1
    base.setGlyphOrder(order)
    return copied


# ---------- emoji 呈现：默认文本 / 默认彩色 / VS15 / VS16 ----------

def load_emoji_presentation(path=EMOJI_DATA):
    """Emoji_Presentation=Yes 的码点集合（来自 Unicode emoji-data.txt）。"""
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
            a, b = (int(x, 16) for x in rng.split('..')) if '..' in rng else (int(rng, 16),) * 2
            out.update(range(a, b + 1))
    return out


def normalize_symbol_font(font):
    """把任意 upem 的符号字体缩放到 1000 upem、单格 advance。

    只改 advance 不够：Noto Sans Symbols 2 是比例符号字体，很多字形本身按
    1000~1370 单位宽设计（world map 1269、racing car 1155…）。如果只把
    advance 强制成 550，墨迹仍会横跨 2~2.5 格并压到相邻字符上。这里对
    超过格宽的轮廓做**水平**压缩（保持垂直设计/基线），使其真正落进 550 格。
    """
    factor = 1000.0 / font['head'].unitsPerEm
    font = flatten_scale_font(font, factor, upem_factor=factor, uniform_advance=CELL)
    glyf = font['glyf']
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    for name, g in glyf.glyphs.items():
        if getattr(g, 'numberOfContours', 0) == 0 or not hasattr(g, 'coordinates'):
            continue
        xs = [x for x, y in g.coordinates]
        if not xs:
            continue
        xmin, xmax = min(xs), max(xs)
        w = xmax - xmin
        if w > CELL:
            s = CELL / w
            cx = (xmin + xmax) / 2.0
            # 缩放后把墨迹中心放回格子中心（源字体的比例符号是居中设计的，
            # 但 Noto Symbols 的 advance 比格子宽，中心在 685 而不是 275）。
            g.coordinates = GlyphCoordinates(
                [(CELL / 2.0 + (x - cx) * s, y) for x, y in g.coordinates])
            g.recalcBounds(glyf)
            m = font['hmtx'].metrics[name]
            font['hmtx'].metrics[name] = (m[0], round(g.xMin))
    return font


def fit_glyphs_in_cells(font, ranges):
    """把指定区间的**字母**字形收进自己的 advance 格子。

    JuliaMono 的希腊多调号大写（如 U+1F5B）在 2000upem/1200 格中靠左伸出的
    重音设计，缩放到 550 格后墨迹仍有 877 单位宽，直接排会压到相邻字母上。
    这里只对 ranges 内的 Letter 类别、非零 advance 字形做水平压缩/居中：
    宽度超过 advance 时按比例压缩，最后把墨迹 bbox 居中到格内。
    """
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    glyf = font['glyf']
    hmtx = font['hmtx']
    cmap = font.getBestCmap()
    seen = set()
    fitted = 0
    for cp, g in cmap.items():
        if g in seen or not any(a <= cp <= b for a, b in ranges):
            continue
        if unicodedata.category(chr(cp))[0] != 'L':
            continue
        gl = glyf.glyphs.get(g)
        if gl is None or getattr(gl, 'numberOfContours', 0) == 0 or not hasattr(gl, 'coordinates'):
            continue
        adv, _ = hmtx.metrics[g]
        if adv <= 0:
            continue
        xs = [x for x, y in gl.coordinates]
        if not xs:
            continue
        xmin, xmax = min(xs), max(xs)
        w = xmax - xmin
        if w <= adv and xmin >= -2 and xmax <= adv + 2:
            seen.add(g)
            continue
        # 留 30 单位侧边距：即使 bbox 收进 0..550，贴着格子边也会让
        # 下一个字母的左侧重音与前一个字母的右缘相碰。
        margin = 30
        max_w = max(1, adv - 2 * margin)
        s = min(1.0, max_w / w) if w > max_w else 1.0
        cx = (xmin + xmax) / 2.0
        gl.coordinates = GlyphCoordinates(
            [(adv / 2.0 + (x - cx) * s, y) for x, y in gl.coordinates])
        gl.recalcBounds(glyf)
        hmtx.metrics[g] = (adv, round(gl.xMin))
        seen.add(g)
        fitted += 1
    return fitted


def drop_cmap_entry(font, cp):
    """从所有普通 cmap 子表里删掉一个码点（UVS 子表不动）。"""
    for t in font['cmap'].tables:
        if t.format == 14 or not hasattr(t, 'cmap'):
            continue
        t.cmap.pop(cp, None)


def fill_mono_symbols(base, julia, need_mono):
    """依次从 JuliaMono → Noto Sans Symbols 2 → Noto Sans Symbols → CJK 子集补单色轮廓。

    最后一个来源是 `sources/NotoSansCJKsc-Symbols5.ttf`：5 个「CJK 类 emoji」
    （U+3030 U+303D U+3297 U+3299 U+1F237）的单色轮廓。它们默认是文本呈现，
    但只有 CJK 字体带单色轮廓，所以单独从 Noto Sans CJK 抠出来做成几 KB 的子集
    （重生成见 tools/make_cjk_symbol_subset.py）。这几个是全角字形，按 2 格（WIDE）给。
    """
    copy_julia_into(base, julia, [], need_mono, False)
    base_cmap = base.getBestCmap()
    for key, suffix in (('notosym2', '.sym2'), ('notosym', '.sym')):
        rest = [cp for cp in need_mono if cp not in base_cmap]
        if not rest:
            break
        if os.path.exists(SRC[key]):
            sym = normalize_symbol_font(TTFont(SRC[key]))
            copy_julia_into(base, sym, [], rest, False, suffix=suffix)
            base_cmap = base.getBestCmap()
    rest = [cp for cp in need_mono if cp not in base_cmap]
    if rest and os.path.exists(SRC['cjk5']):
        cjk = TTFont(SRC['cjk5'])
        upem = cjk['head'].unitsPerEm
        cjk = flatten_scale_font(cjk, WIDE / upem, upem_factor=1000 / upem,
                                 uniform_advance=WIDE)
        copy_julia_into(base, cjk, [], rest, False, suffix='.cjk', advance=WIDE)
        base_cmap = base.getBestCmap()
    return base_cmap


def prepare_emoji_presentation(base, julia, noto_cmap):
    """按 Unicode 的默认呈现规则整理 emoji 码点（必须在合并 Noto 之前跑）。

    · 默认**文本**呈现（Emoji_Presentation != Yes）：必须提供单色轮廓，否则
      文本渲染只会画出空轮廓 —— 表现为"字符整个消失"。轮廓依次取
      JuliaMono → Noto Sans Symbols 2；都取不到的（都是 CJK 相关圈字）直接丢弃。
    · 默认**彩色**呈现：把 base 的 cmap 让出来，让 Noto 的彩色字形占住；
      base 原有的单色字形留给 VS15 使用。
    """
    pres = load_emoji_presentation()
    # 不可见字符（Tag 字符、变体选择符等）不能丢：标签序列旗帜要靠它们合成
    need_mono = sorted(cp for cp in noto_cmap
                       if cp not in pres and not is_Default_Ignorable(cp))

    base_cmap = fill_mono_symbols(base, julia, need_mono)
    mono = {cp: base_cmap[cp] for cp in sorted(noto_cmap) if cp in pres and cp in base_cmap}
    drop = [cp for cp in need_mono if cp not in base_cmap]
    for cp in list(mono) + drop:
        drop_cmap_entry(base, cp)
    print(f'  emoji 呈现：默认彩色 {len(mono)} 个交还 Noto；无单色源丢弃 {len(drop)} 个')
    return {'text': need_mono, 'mono': mono, 'drop': drop}


def _set_uvs(font, fe0f, fe0e):
    """写入 cmap format 14（Unicode 变体序列）表。

    列表元素是 ``(码点, 字形名)``；字形名为 ``None`` 表示 **DefaultUVS** ——
    即「这条变体序列沿用 cmap 的默认字形，不换」。
    """
    uvs = {}
    if fe0f:
        uvs[0xFE0F] = fe0f
    if fe0e:
        uvs[0xFE0E] = fe0e
    if not uvs:
        return
    for t in font['cmap'].tables:
        if t.format == 14:
            t.uvsDict = uvs
            return
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
    t = CmapSubtable.newSubtable(14)
    t.platformID, t.platEncID, t.language = 0, 5, 0
    t.cmap, t.uvsDict = {}, uvs
    font['cmap'].tables.append(t)


def apply_emoji_presentation(font, noto, plan, noto_rename):
    """合并之后：丢弃无单色源的码点，并生成真正的 UVS（VS15/VS16）表。"""
    for cp in plan['drop']:
        drop_cmap_entry(font, cp)
    noto_cmap = noto.getBestCmap()
    colr_base = set(r.BaseGlyph for r in font['COLR'].table.BaseGlyphList.BaseGlyphPaintRecord)

    def find_colour(cp):
        n = noto_cmap.get(cp)
        if n is None:
            return None
        # 必须用 Merger 的实际改名结果：Noto 的 heart 在斜体面可能被改名成
        # heart.5（因为 SShI 本身已有 heart.1/2/3 的 Nerd Font 图标），
        # 只猜 .1/.2/.3 会漏掉「❤ + VS16」的彩色变体。
        merged = noto_rename.get(n, n)
        if merged in colr_base:
            return merged
        if n in colr_base:
            return n
        # 防御性兜底：找出所有 n.<数字> 形式的 COLR 基字形。
        cands = [g for g in colr_base
                 if g.startswith(n + '.') and g[len(n) + 1:].isdigit()]
        if cands:
            return sorted(cands, key=lambda g: int(g.rsplit('.', 1)[1]))[0]
        return None

    cmap = font.getBestCmap()
    pairs = {}
    for cp in plan['text']:
        mono, colr = cmap.get(cp), find_colour(cp)
        if mono and colr and mono != colr:
            pairs[cp] = (mono, colr)
    for cp, mono in plan['mono'].items():
        colr = cmap.get(cp)
        if colr and mono != colr:
            pairs[cp] = (mono, colr)

    # 键盘帽基字符（0-9 # *）的变体序列走 DefaultUVS：沿用 cmap 里的默认（单色）字形。
    # 不能像其它「文本默认」emoji 那样把 VS16 换成 Noto 的彩色数字，因为 ccmp 键盘帽
    # 连字的输入是单色字形（sub one uni20E3 -> keycap）；一旦 cmap14 把 U+0031+FE0F
    # 指向彩色的 one.1，`0031 FE0F 20E3` 就永远匹配不上连字，会散成「彩色数字 + 帽框」。
    # 这也正是成熟字体的做法：Noto Color Emoji 的 371 条 FE0F 全是 DefaultUVS ——
    # 原则是「cmap14 选中的字形，必须和后续连字要匹配的字形一致」。
    default_uvs = {cp for cp in pairs if cp in KEYCAP_BASES}
    for cp in default_uvs:
        del pairs[cp]

    fe0f = {cp: None for cp in default_uvs}
    fe0f.update({cp: colr for cp, (mono, colr) in pairs.items()})
    fe0e = {cp: None for cp in default_uvs}
    fe0e.update({cp: mono for cp, (mono, colr) in pairs.items()})

    # 默认**彩色**呈现的 emoji（cmap 已经指向 COLR 基字形）：FE0F 也走 DefaultUVS。
    # 它们是合法的 `cp + FE0F` 序列，但字形不变；不登记的话 FE0F 会以"不可见字形"
    # 残留下来 —— 实测 `🏴 + FE0F + ZWJ + ☠ + FE0F` 会散成 2 个字形。
    # Noto Color Emoji 的 371 条 FE0F 全是 DefaultUVS，就是同一个道理。
    colour_default = sorted(cp for cp, g in cmap.items()
                            if g in colr_base and cp not in pairs)
    fe0f.update({cp: None for cp in colour_default})

    _set_uvs(font, sorted(fe0f.items(), key=lambda kv: kv[0]),
             sorted(fe0e.items(), key=lambda kv: kv[0]))
    print(f'  UVS：VS16 {len(fe0f)} 条'
          f'（DefaultUVS {len(default_uvs) + len(colour_default)}：键盘帽 {len(default_uvs)}'
          f' + 默认彩色 {len(colour_default)}），VS15 {len(fe0e)} 条')


def add_colour_ligature_variants(font):
    """让 emoji ZWJ 连字同时接受「彩色变体」字形。返回新增的连字条数。

    文本默认的 emoji（Emoji_Presentation=No，如 ❤ 🏳 👁 ⚖ ☠ ♀ ♂ ⚕）在 cmap 里是**单色**
    字形，只有 VS16 之后才换成彩色字形；而 Noto 的 ZWJ 连字是按单色字形名写的。
    于是标准写法 `cp + FE0F + ZWJ + …` 匹配不上，实测 ❤️‍🔥 🏳️‍🌈 🏴‍☠️ 👁️‍🗨️ 🧑‍⚕️ 全部散成 3~4 个字形。

    这里为每条连字补一个「把单色组件替换成对应彩色组件」的变体（组件里有多处时取所有组合）。
    单色写法（`cp + ZWJ + …`，文本呈现）仍然由原连字匹配，两种都能用。
    """
    from fontTools.ttLib.tables.otTables import Ligature
    if 'GSUB' not in font:
        return 0
    cmap = font.getBestCmap()
    to_colour = {}
    for t in font['cmap'].tables:
        if t.format == 14:
            for cp, g in (getattr(t, 'uvsDict', {}) or {}).get(0xFE0F, []):
                if g and cp in cmap and g != cmap[cp]:
                    to_colour[cmap[cp]] = g       # 单色 → 彩色
    if not to_colour:
        return 0
    added = 0
    for lk in font['GSUB'].table.LookupList.Lookup:
        if lk.LookupType != 4:                    # 只处理 Ligature 查找
            continue
        for sub in lk.SubTable:
            for first, ligs in list(sub.ligatures.items()):
                for lig in list(ligs):
                    comps = list(lig.Component)
                    slots = [i for i, g in enumerate([first] + comps) if g in to_colour]
                    for mask in range(1, 1 << len(slots)):
                        new_first, new_comps = first, list(comps)
                        for bit, idx in enumerate(slots):
                            if not (mask >> bit) & 1:
                                continue
                            if idx == 0:
                                new_first = to_colour[first]
                            else:
                                new_comps[idx - 1] = to_colour[comps[idx - 1]]
                        same = sub.ligatures.get(new_first, [])
                        if any(list(l.Component) == new_comps for l in same):
                            continue
                        dup = Ligature()
                        dup.Component = new_comps
                        dup.LigGlyph = lig.LigGlyph
                        dup.CompCount = len(new_comps) + 1
                        sub.ligatures.setdefault(new_first, []).append(dup)
                        added += 1
            # 变体是**追加**到 LigatureSet 末尾的，而 HarfBuzz 按集合顺序取第一个匹配 ——
            # 不排序的话短连字（如「跑步+肤色」）会抢在长连字变体前面，序列又散开。
            # OpenType 规范本来就要求 ligature 按组件数从长到短排列。
            for ligs in sub.ligatures.values():
                ligs.sort(key=lambda l: -len(l.Component))
    return added


def decompose_precomposed_for_stacking(font):
    """预组合字母 + 后续组合符时，先拆回「基字母 + 组合符」再让 GPOS 叠。

    HarfBuzz 会在 GSUB 前把 ``a + U+0301`` 规范合成 ``aacute``；若文本是
    ``a + U+0301 + U+0304``，第一个重音变成预组合字形，第二个重音只能走
    mark-to-base，落在基线附近并与第一个重音重叠（实测 y_offset=0）。

    这里加一条 **contextual** GSUB 规则：当预组合字母**后面还跟着组合符**时，
    把预组合字形拆成基字母 + 组合符（MultipleSubst），于是 GPOS 能看到
    「基字母 + 第一个组合符 + 第二个组合符」，mark-to-mark 正常叠高。
    单独的 ``á`` 不拆，仍走预组合字形；只有多标记场景才拆。
    """
    if 'GSUB' not in font:
        return 0
    from fontTools.ttLib.tables import otTables
    cmap = font.getBestCmap()
    order = font.getGlyphOrder()
    gid = {g: i for i, g in enumerate(order)}
    hmtx = font['hmtx']
    marks = []
    for cp, g in cmap.items():
        if is_combining_mark(cp):
            marks.append(g)
    if not marks:
        return 0
    mapping = {}
    for cp, g in cmap.items():
        if is_combining_mark(cp):
            continue
        if unicodedata.category(chr(cp))[0] != 'L':
            continue
        nfd = unicodedata.normalize('NFD', chr(cp))
        if len(nfd) <= 1 or not any(is_combining_mark(ord(ch)) for ch in nfd[1:]):
            continue
        parts = [cmap.get(ord(ch)) for ch in nfd]
        if any(p is None for p in parts) or parts[0] == g:
            continue
        # 只拆 advance 能对上的（预组合 1 格 = 基字母 1 格 + 0 宽组合符）；
        # Hangul 等分解成多个有宽度的 jamo 时 sum 对不上，自动跳过。
        if sum(hmtx.metrics[p][0] for p in parts) != hmtx.metrics[g][0]:
            continue
        mapping[g] = parts
    if not mapping:
        return 0

    gsub = font['GSUB'].table
    msub = otTables.MultipleSubst()
    msub.Format = 1
    msub.mapping = {g: mapping[g] for g in sorted(mapping, key=gid.get)}
    mlk = otTables.Lookup()
    mlk.LookupType = 2
    mlk.LookupFlag = 0
    mlk.SubTable = [msub]
    mlk.SubTableCount = 1
    midx = len(gsub.LookupList.Lookup)
    gsub.LookupList.Lookup.append(mlk)
    gsub.LookupList.LookupCount = midx + 1

    ctx = otTables.ChainContextSubst()
    ctx.Format = 3
    ctx.BacktrackCoverage = []
    ctx.BacktrackGlyphCount = 0
    cov_in = otTables.Coverage()
    cov_in.glyphs = sorted(mapping, key=gid.get)
    ctx.InputCoverage = [cov_in]
    ctx.InputGlyphCount = 1
    cov_la = otTables.Coverage()
    cov_la.glyphs = sorted(set(marks), key=gid.get)
    ctx.LookAheadCoverage = [cov_la]
    ctx.LookAheadGlyphCount = 1
    rec = otTables.SubstLookupRecord()
    rec.SequenceIndex = 0
    rec.LookupListIndex = midx
    ctx.SubstLookupRecord = [rec]
    ctx.SubstCount = 1
    clk = otTables.Lookup()
    clk.LookupType = 6
    clk.LookupFlag = 0
    clk.SubTable = [ctx]
    clk.SubTableCount = 1
    cidx = len(gsub.LookupList.Lookup)
    gsub.LookupList.Lookup.append(clk)
    gsub.LookupList.LookupCount = cidx + 1
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag == 'ccmp':
            fr.Feature.LookupListIndex.append(cidx)
    return len(mapping)


def zero_width_marks(font):
    """把 Mn/Me 组合标记的 advance 设为 0（它们默认要叠加在前一个字符上）。"""
    cmap = font.getBestCmap()
    n = 0
    for cp, gname in cmap.items():
        if not is_combining_mark(cp):
            continue
        if gname not in font['hmtx'].metrics:
            continue
        m = list(font['hmtx'].metrics[gname])
        if m[0] != 0:
            m[0] = 0
            font['hmtx'].metrics[gname] = tuple(m)
            n += 1
    return n


def zero_invisible_widths(font):
    """把「组合标记（Mn/Me）」和「Default_Ignorable」字符的 advance 都设为 0。

    两类都不该占格子：
      · 组合标记要叠在前一个字符上 —— Julia 层拷进来的已经在 ``zero_width_marks()``
        里 0 宽化，但 emoji 呈现阶段后补的 U+20E3 会漏掉；
      · Default_Ignorable（ZWJ / ZWNJ / ZWSP / 双向控制符 / Tag 字符…）按 Unicode
        规定不应产生可见宽度。HarfBuzz 会自己隐藏它们，但其它渲染器与测量 API 会按
        hmtx 算宽 —— Noto Color Emoji 的 1100 会漏进来（ZWJ、Tag 字符会变成 **2 格**）。
        参考 Noto Sans Mono：一律 0。
    """
    cmap = font.getBestCmap()
    n_mark = n_ign = 0
    for cp, gname in cmap.items():
        if gname not in font['hmtx'].metrics:
            continue
        is_mark = is_combining_mark(cp)
        if not (is_mark or is_Default_Ignorable(cp)):
            continue
        m = list(font['hmtx'].metrics[gname])
        if m[0] != 0:
            m[0] = 0
            font['hmtx'].metrics[gname] = tuple(m)
            if is_mark:
                n_mark += 1
            else:
                n_ign += 1
    return n_mark, n_ign


def drop_control_cmap(font):
    """删掉 C0/C1 控制字符（Cc）的 cmap 映射。

    斜体基底 SeriousShanns 把 U+0016–U+001F、U+0080–U+0088 映射到了空白字形，
    部分渲染器会把控制码画成一个空盒子（fontbakery 的 `control_chars` 也会报）。
    控制字符本就不该有字形。
    """
    n = 0
    for cp in list(font.getBestCmap()):
        if unicodedata.category(chr(cp)) == 'Cc':
            drop_cmap_entry(font, cp)
            n += 1
    return n


def compact_hmtx(font):
    """按 advance 重排字形，把最常见 advance 的字形集中到字序**尾部**。

    这样 hmtx 的「尾部等宽段」最长、``hhea.numberOfHMetrics`` 最小。为什么需要：
    0 宽化 `Default_Ignorable`（ZWJ / Tag 字符）之后，这些 0 宽字形插在尾部 Noto 的
    1100 段中间，把等宽段打断 —— numberOfHMetrics 从 21321 涨到 63591，hmtx 从
    166 KB 涨到 254 KB，而两种编码的字形 advance 完全等价（纯浪费）。

    **两个前提**：
      · 必须在**保存前**、字形还带真实名字时做。成品是 post format 3，重新载入后 glyph
        name 是按 GID 合成的（``glyphNNNNN``），那时再重排会让 GSUB/COLR 的 name→GID
        解析全部错位。
      · 必须在 ``add_mark_feature()`` **之前**做：GPOS 的 Coverage 与 MarkArray/BaseArray
        是按 GID 对齐的平行数组，而 feaLib 的 buildCoverage 按「当前 GID」排序，所以
        GPOS 要用重排后的字序来建。GSUB（来自 Merger）不受影响：它的 Coverage 在
        preWrite 时从 ``ligatures`` 字典按 GID 重新生成。

    返回尾部等宽段的长度（0 表示没做重排）。
    """
    order = font.getGlyphOrder()
    if not order or order[0] != '.notdef':
        return 0
    metrics = font['hmtx'].metrics
    tail_adv = Counter(metrics[g][0] for g in order).most_common(1)[0][0]
    head = [g for g in order[1:] if metrics[g][0] != tail_adv]
    tail = [g for g in order[1:] if metrics[g][0] == tail_adv]
    font.setGlyphOrder(['.notdef'] + head + tail)   # 会同步更新 glyf.glyphOrder
    return len(tail)


def gsub_outputs(gsub):
    """GSUB 里**产出**的字形（只算输出，不算输入）。

    输入字形如果没有 cmap 映射、也没有任何 lookup 产出它，就等于不可达 —— fontbakery 的
    ``unreachable_glyphs`` 也是这个口径。注意 mapping 的 **key 是输入**，不能算。
    """
    out = set()

    def add(lookup_type, sub):
        try:
            if lookup_type == 1:                    # Single
                out.update(sub.mapping.values())
            elif lookup_type == 2:                  # Multiple
                for slot in sub.mapping.values():
                    out.update(slot)
            elif lookup_type == 3:                  # Alternate
                for alts in sub.alternates.values():
                    out.update(alts)
            elif lookup_type == 4:                  # Ligature
                for ligs in sub.ligatures.values():
                    for lig in ligs:
                        out.add(lig.LigGlyph)
            elif lookup_type == 7:                  # Extension
                add(sub.ExtensionLookupType, sub.ExtSubTable)
            elif lookup_type == 8:                  # Reverse chaining single
                out.update(sub.Substitute)
            # 5/6 上下文查找本身不产出字形，只调度别的 lookup（那些 lookup 也在列表里）
        except AttributeError:
            pass

    if getattr(gsub, 'LookupList', None):
        for lk in gsub.LookupList.Lookup:
            for sub in lk.SubTable:
                add(lk.LookupType, sub)
    return out


def _drop_unreachable_once(font):
    """删掉从任何 cmap 子表 / UVS / GSUB / GPOS / GDEF / COLR 都到不了的字形（保留 .notdef）。

    这些字形在源字体里就没有访问路径：ComicShanns 有 4 个未编码字形（Ucaseircumflex /
    lowercasearon / ccommaaccent / idotaccent），另外还有合并时被改名的各源 ``.null``、
    Noto Color Emoji 的 ``.notdef`` 副本 —— 改名后就没人引用了。共 ~1.3 KB 死代码。

    **必须建 GPOS 之前调用**：删字形会改变 GID。
    """
    order = font.getGlyphOrder()
    known = set(order)
    reach = set()
    for t in font['cmap'].tables:
        cm = getattr(t, 'cmap', None)
        if cm:
            reach.update(cm.values())
        if getattr(t, 'format', None) == 14:
            for entries in (getattr(t, 'uvsDict', None) or {}).values():
                for _cp, gname in entries:
                    if gname:
                        reach.add(gname)
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

    # 只看**会保留**的表：GPOS/GDEF 随后会被 add_mark_feature() 整个重建，
    # 它们对旧字形的引用不算数（斜体基底就有只被旧 GPOS 引用的空字形）。
    if 'GSUB' in font:
        reach |= {g for g in gsub_outputs(font['GSUB'].table) if g in known}
    # COLR 里 BaseGlyphPaintRecord.BaseGlyph 是"定义"不是"引用"：一个彩色基字形记录
    # 如果既不在 cmap、也不是 GSUB 输出、也没被别的 paint 引用，它就是不可达的
    # （Noto 有 12 个这样的空基字形记录，fontbakery 能检出，我们沿用同一判据）。
    if 'COLR' in font:
        # BaseGlyph = 基字形记录（定义）；clips = 裁剪框（字形属性）—— 都不是"引用"
        walk(font['COLR'].table, skip_attrs=('BaseGlyph', 'clips'))
    drop = [g for g in order if g != '.notdef' and g not in reach]
    if drop:
        drop_set = set(drop)
        # 删字形前先摘掉 COLR 里指向它们的基字形记录，否则 COLR 会引用不存在的字形
        if 'COLR' in font:
            colr = font['COLR']
            if colr.version == 0:
                for g in drop:
                    colr.ColorLayers.pop(g, None)
            else:
                bl = colr.table.BaseGlyphList
                if bl is not None:
                    bl.BaseGlyphPaintRecord = [r for r in bl.BaseGlyphPaintRecord
                                               if r.BaseGlyph not in drop_set]
                    bl.BaseGlyphCount = len(bl.BaseGlyphPaintRecord)
                cl = getattr(colr.table, 'ClipList', None)
                if cl is not None and getattr(cl, 'clips', None):
                    for g in drop:
                        cl.clips.pop(g, None)
        for g in drop:
            del font['glyf'].glyphs[g]
            del font['hmtx'].metrics[g]
        font.setGlyphOrder([g for g in order if g not in drop_set])
    return len(drop)


def drop_unreachable_glyphs(font, max_rounds=5):
    """反复删不可达字形直到不动点。

    删掉一个 COLR 基字形记录后，它引用的图层字形可能也变成孤儿（Noto 的 emoji 就有这种
    链式结构），所以要迭代。
    """
    total = 0
    for _ in range(max_rounds):
        n = _drop_unreachable_once(font)
        total += n
        if not n:
            break
    return total


# JuliaMono 快照里只有科普特**小写**（U+2CAF psi、U+2CDF Old Nubian NGI，另有 2CB2/2CB3），
# 没有对应大写，fontbakery 的 case_mapping 会 FAIL。这两对按「大写 = 小写统一缩放到
# cap height、水平居中、advance 仍是一格」合成：与本字体自己的 cap/x 高度体系一致，
# 也避免把比例字体（Noto Sans Coptic 的大写 psi adv=834）硬塞进 550 的等宽格子。
COPTIC_CASE_PAIRS = [(0x2CAE, 0x2CAF), (0x2CDE, 0x2CDF)]

# 设计上的 cap height（upem=1000，实测 roman 面 'H' 的 yMax）。
# **不能用 'H' 的 bbox 现算**：斜体面的 'H' 是倾斜的，轴对齐 bbox 会被放大
# （italic H yMax=776，而真实 cap 仍是 668，多出来的 ≈ 450×tan(12.7°)）。
# 用常量还能保证四个 face 合成出来的大写高度一致。
CAP_HEIGHT = 668


def add_coptic_capitals(font):
    """从本 face 的科普特小写合成缺的大写。返回合成个数。

    缩放规则（可复现）：``s = min(cap_height / h, (CELL-10) / w)``，然后水平居中、
    基线对齐（``y0 -> 0``）。psi 的小写本来就画到 cap height，所以 s≈1.00；
    NGI 是 x-height，会放大到约 1.46 倍。
    """
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    cap = CAP_HEIGHT
    max_ink = CELL - 10                     # 左右各留 5 单位余量
    n = 0
    for cap_cp, small_cp in COPTIC_CASE_PAIRS:
        if cap_cp in cmap or small_cp not in cmap:
            continue
        bp = BoundsPen(gs)
        gs[cmap[small_cp]].draw(bp)
        if not bp.bounds:
            continue
        x0, y0, x1, y1 = bp.bounds
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            continue
        s = min(cap / h, max_ink / w)
        dx, dy = (CELL - w * s) / 2 - x0 * s, -y0 * s
        rec = DecomposingRecordingPen(gs)
        gs[cmap[small_cp]].draw(rec)
        pen = TTGlyphPen(None)
        rec.replay(TransformPen(pen, Transform(s, 0, 0, s, dx, dy)))
        glyph = pen.glyph()
        name = 'uni%04X' % cap_cp
        font.setGlyphOrder(font.getGlyphOrder() + [name])
        font['glyf'].glyphs[name] = glyph
        glyph.recalcBounds(font['glyf'])
        font['hmtx'].metrics[name] = (CELL, glyph.xMin)
        for sub in font['cmap'].tables:
            if sub.isUnicode() and sub.format in (4, 12):
                sub.cmap[cap_cp] = name
        n += 1
    return n


def finalize_widths_and_order(font, n_ctl=0):
    """0 宽化隐形字形 →（可选）删控制码映射 → 重排字形。返回各项计数。

    顺序很重要：先 0 宽化，重排才知道哪些字形是 0 宽；重排又必须在建 GPOS 之前。
    调用方随后用新字序建 GPOS（见 ``compact_hmtx`` 的说明）。
    ``n_ctl`` 允许调用方已经提前删过控制码（可达性判断需要最终的 cmap）。
    """
    n_mark, n_ign = zero_invisible_widths(font)
    if not n_ctl:
        n_ctl = drop_control_cmap(font)
    n_tail = compact_hmtx(font)
    return n_mark, n_ign, n_ctl, n_tail


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


def _remap_gsub_inputs(gsub, mapping):
    """只改 GSUB 的**输入**字形，绝不改替换输出。

    ``revive_renamed_rules`` 的映射是为了让按 Noto 彩色字形写的连字重新匹配
    cmap 里的单色字形；如果连 ``LigGlyph`` / SingleSubst 输出也一起改掉，彩色
    emoji 会被换成单色字形。输出必须保持 Noto 的彩色字形。
    """
    if not mapping:
        return 0
    changed = 0

    def remap_list(lst):
        nonlocal changed
        for i, g in enumerate(lst):
            if g in mapping:
                lst[i] = mapping[g]
                changed += 1

    def remap_coverage(cov):
        if cov is not None and hasattr(cov, 'glyphs'):
            remap_list(cov.glyphs)

    def remap_subtable(lookup_type, sub):
        nonlocal changed
        if lookup_type == 7:                      # Extension
            remap_subtable(sub.ExtensionLookupType, sub.ExtSubTable)
            return
        if lookup_type == 1:                      # Single：key 是输入
            for k in list(sub.mapping):
                if k in mapping:
                    sub.mapping[mapping[k]] = sub.mapping.pop(k)
                    changed += 1
        elif lookup_type == 2:                    # Multiple：key 是输入
            for k in list(sub.mapping):
                if k in mapping:
                    sub.mapping[mapping[k]] = sub.mapping.pop(k)
                    changed += 1
        elif lookup_type == 3:                    # Alternate：key 是输入
            for k in list(sub.alternates):
                if k in mapping:
                    sub.alternates[mapping[k]] = sub.alternates.pop(k)
                    changed += 1
        elif lookup_type == 4:                    # Ligature：first/Component 是输入
            for first in list(sub.ligatures):
                if first in mapping:
                    sub.ligatures[mapping[first]] = sub.ligatures.pop(first)
                    changed += 1
            for ligs in sub.ligatures.values():
                for lig in ligs:
                    remap_list(lig.Component)
        elif lookup_type in (5, 6):               # Context / ChainContext
            remap_coverage(getattr(sub, 'Coverage', None))
            for attr in ('BacktrackCoverage', 'InputCoverage', 'LookAheadCoverage'):
                covs = getattr(sub, attr, None)
                if covs:
                    for cov in covs:
                        remap_coverage(cov)
        elif lookup_type == 8:                    # ReverseChainSingle：Coverage 是输入
            remap_coverage(getattr(sub, 'Coverage', None))
            # sub.Substitute 是**输出**，不动。

    for lk in gsub.LookupList.Lookup:
        for sub in lk.SubTable:
            remap_subtable(lk.LookupType, sub)
    return changed


def revive_renamed_rules(font, noto, noto_rename):
    """修复因 Merger 重命名字形而失效的 GSUB/GPOS 规则。

    Merger 合并时，若 base 与 Noto 都有同名但轮廓不同的字形（如 ``one``），会把
    后一个（Noto）的改名成 ``one.1``（若 ``one.1`` 已被 base 的 Nerd Font 图标
    占用，则可能是 ``one.2``、``one.5``……）；同时把引用它的 ``ccmp`` 连字规则
    也改成改名后的字形。但最终 ``cmap`` 仍指向 base 的 ``one``，于是这些规则永远
    无法触发 —— 典型受害者是键盘帽 emoji：``1️⃣(0031 FE0F 20E3)`` 本该由
    ``one + uni20E3 -> 彩色键盘帽`` 合成，结果只剩「数字 + 帽框」两个字形。

    这里用 **Merger 的实际改名表** ``noto_rename``（原 Noto 名 → 合并后名）把
    规则输入里指向被改名副本的引用，改回 cmap 里同码点、可达的字形。

    不能再用「任何以 .数字 结尾的名字」去猜：R 正规的 ``SShI.ttf`` 本身就有
    ``heart.1``/``heart.2``/``heart.3`` 等 Nerd Font 图标，Noto 的彩色 heart
    实际被改名成 ``heart.5``；靠后缀猜会把 base 的图标误当成 Noto 副本。
    """
    rev = {}
    for cp, gname in noto.getBestCmap().items():
        rev.setdefault(gname, cp)
    cmap = font.getBestCmap()
    mapping = {}
    for old_name, new_name in noto_rename.items():
        cp = rev.get(old_name)
        if cp is None:
            continue
        target = cmap.get(cp)
        if target is not None and target != new_name:
            mapping[new_name] = target
    if not mapping:
        return 0
    if 'GSUB' in font:
        _remap_gsub_inputs(font['GSUB'].table, mapping)
    if 'GPOS' in font:
        # GPOS 里没有“替换输出”，Coverage/锚点引用的字形都是输入，全部映射。
        _remap_names(font['GPOS'].table, mapping)
    return len(mapping)


def fix_colr_renames(font, noto_rename):
    """把 COLR 里残留的「Noto 原名」改成 Merger 改名后的名字。

    Merger 的 COLR 合并通常已经按改名后的字序解析 GID，所以这里多数情况下
    是空操作；保留它是为了防止 fontTools 版本差异下 COLR 仍按原名字引用。
    映射方向是 Noto 原名 → 合并后名，不能再用 base 名 → ``.1`` 的猜测
    （R 的 base 本身有 ``heart.1``…，Noto 的 heart 可能是 ``heart.5``）。
    """
    if 'COLR' not in font:
        return 0
    changed = 0
    # 只在确有原名残留在 COLR 里时才交给 _remap_names；否则直接跳过，
    # 避免把 base 的同名图标误连到 Noto 的彩色字形。
    strings = set()

    def collect(obj, seen=None):
        if seen is None:
            seen = set()
        if isinstance(obj, str):
            strings.add(obj)
            return
        if isinstance(obj, (int, float, bool, type(None))):
            return
        oid = id(obj)
        if oid in seen:
            return
        seen.add(oid)
        if isinstance(obj, list):
            for x in obj:
                collect(x, seen)
        elif isinstance(obj, tuple):
            for x in obj:
                collect(x, seen)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                collect(k, seen)
                collect(v, seen)
        elif hasattr(obj, '__dict__'):
            for v in vars(obj).values():
                collect(v, seen)

    collect(font['COLR'].table)
    mapping = {a: b for a, b in noto_rename.items() if a in strings and a != b}
    if mapping:
        changed = len(mapping)
        _remap_names(font['COLR'].table, mapping)
    return changed



def merge_noto_emoji(base, noto, base_names=None):
    """把 Noto COLRv1 整字体合并进 base（base 已有码点优先，Noto 填 emoji）。

    返回 ``(font, noto_rename)``；``noto_rename`` 是 Merger **实际**做的
    「Noto 原字形名 → 合并后字形名」映射（如 ``heart -> heart.5``）。后续修复
    GSUB/COLR 引用、查彩色变体都必须用它，不能假设后缀一定是 ``.1``——base 的
    Nerd Font 图标本身就可能叫 ``heart.1``/``heart.2``/``heart.3``。
    """
    base_order = list(base.getGlyphOrder())
    noto_order = list(noto.getGlyphOrder())
    base_path = os.path.join(TMP, '_base_tmp.ttf')
    noto_path = os.path.join(TMP, '_noto_tmp.ttf')
    base.save(base_path)
    noto.save(noto_path)
    merger = Merger()
    font = merger.merge([base_path, noto_path])

    merged_order = font.getGlyphOrder()
    if merged_order[:len(base_order)] == base_order and len(merged_order) == len(base_order) + len(noto_order):
        noto_rename = {old: merged_order[len(base_order) + i]
                       for i, old in enumerate(noto_order) if old != merged_order[len(base_order) + i]}
    else:
        # 防御：若 Merger 改变顺序，按它的算法重算改名表。
        from fontTools.merge.cmap import computeMegaGlyphOrder
        class _M:
            pass
        m = _M()
        bo, no = list(base_order), list(noto_order)
        computeMegaGlyphOrder(m, [bo, no])
        noto_rename = {a: b for a, b in zip(noto_order, no) if a != b}

    n = revive_renamed_rules(font, noto, noto_rename)
    c = fix_colr_renames(font, noto_rename)
    strip_locl(font)
    print(f'  修复改名失效的引用：排版规则 {n} 个，COLR 图层 {c} 个（Noto 改名 {len(noto_rename)} 个）')
    return font, noto_rename



def add_mark_feature(font):
    """补 GPOS `mark` 特性：把组合标记定位回它所属的格子。

    组合标记来自 JuliaMono，是按「550 宽格子居中 + 基线对齐」设计的
    （例如 acutecomb 自身墨迹 x=[182,367]，中心正好是格子中心 275）。
    因此在等宽字体里正确的定位就是**把标记原点挪回基准字形原点**（左移一格）。

    没有 GPOS 时 HarfBuzz 会用自己的启发式，把标记推到格子右半边
    （实测 q+U+0301 的墨迹中心偏 +182），所以这个特性是必需的。

    锚点取 (275, 0)：x=格子中心，y=基线（标记自己已按基线设计好高度，
    所以 y 不做偏移；这样上下加符、希伯来元音点等都能保持设计位置）。
    """
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    cmap = font.getBestCmap()
    marks, bases = [], []
    seen_m, seen_b = set(), set()
    for cp, g in cmap.items():
        # 名字里有 '-' 等字符的字形不能写进 fea（`A-B` 会被当成字形范围），直接跳过：
        # 这些多是 Nerd Font 图标字形，不需要当组合符的基准
        if g.startswith('.') or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', g):
            continue
        if is_combining_mark(cp):
            if g not in seen_m:
                seen_m.add(g); marks.append(g)
        elif g not in seen_b:
            seen_b.add(g); bases.append(g)
    if not marks or not bases:
        return 0

    # ---- mark-to-mark（组合符叠加）----
    # 只做 mark-to-base 时，第二个组合符会和第一个**完全重叠**。
    # 正确做法：第一个标记的锚点放在它的墨迹顶（above）/底（below），第二个标记的
    # 锚点放在它自己的墨迹底（above）/顶（below），这样第二个标记的墨迹正好贴住第一个：
    #   y_offset = yMax(first) - yMin(second)   （above）
    #   y_offset = yMin(first) - yMax(second)   （below）
    # 以前把第二个标记的锚点写成 0（基线），会把标记整体再抬高一个自身高度
    # （实测 x + U+0301 + U+0304 的 macron 被推到 y≈1325，几乎飞出字面）。
    # 每个标记的 yMin/yMax 不同，所以用 MarkMarkPosBuilder 生成**逐字形**锚点，
    # 而不是把高度量化成类（类无法表达“第二个标记用自己的 yMin”）。
    gs = font.getGlyphSet()
    rev = {}
    for cp, g in cmap.items():
        rev.setdefault(g, cp)
    BELOW_CC = {202, 216, 218, 220, 224, 226, 240}
    above_bounds, below_bounds = {}, {}
    for g in marks:
        bp = BoundsPen(gs)
        gs[g].draw(bp)
        if not bp.bounds:
            continue
        ymin, ymax = bp.bounds[1], bp.bounds[3]
        cc = unicodedata.combining(chr(rev[g])) if g in rev else 0
        is_below = (ymin + ymax) < 0 or (cc in BELOW_CC and ymax < 600)
        if is_below:
            below_bounds[g] = (ymin, ymax)
        else:
            above_bounds[g] = (ymin, ymax)
    above_marks = sorted(above_bounds)
    below_marks = sorted(below_bounds)

    # 预组合字母（á、alphatonos、U+1F5B…）本身也要能当 mark-to-mark 的
    # **第一个标记**。HarfBuzz 会先把「a + U+0301」规范合成 aacute；如果只在
    # Mark2Array 里放组合符，第二个组合符仍会走 mark-to-base 落到基线，
    # 与预组合重音重叠。这里把 NFD 含组合符的字母加入 Mark1Array：
    # 第二个 above/below 标记分别贴到它的墨迹顶/底。
    precomposed = {}
    for cp, g in cmap.items():
        if is_combining_mark(cp) or g in above_bounds or g in below_bounds:
            continue
        nfd = unicodedata.normalize('NFD', chr(cp))
        if len(nfd) > 1 and any(is_combining_mark(ord(ch)) for ch in nfd[1:]):
            bp = BoundsPen(gs)
            gs[g].draw(bp)
            if bp.bounds:
                precomposed[g] = (bp.bounds[1], bp.bounds[3])

    cx = CELL // 2
    lines = []
    mcls = []
    if above_marks:
        mcls.append(f'markClass [{" ".join(above_marks)}] <anchor {cx} 0> @MC_ABOVE;')
    if below_marks:
        mcls.append(f'markClass [{" ".join(below_marks)}] <anchor {cx} 0> @MC_BELOW;')
    lines.append('languagesystem DFLT dflt;')
    # 只注册字体实际覆盖的脚本（含 Inherited 组合符被这些脚本借用的情况）。
    # 不注册的话 HarfBuzz 在 hebr/arab 等脚本下找不到 mark 特性（实测希伯来文会退回
    # 启发式定位），而 DFLA 回退并不可靠。
    for tag in ('latn', 'grek', 'cyrl', 'hebr', 'arab', 'armn', 'geor'):
        lines.append(f'languagesystem {tag} dflt;')
    lines.append('feature mark {')
    if above_marks:
        lines.append(f'  position base [{" ".join(bases)}] <anchor {cx} 0> mark @MC_ABOVE;')
    if below_marks:
        lines.append(f'  position base [{" ".join(bases)}] <anchor {cx} 0> mark @MC_BELOW;')
    lines.append('} mark;')
    fea = '\n'.join(mcls + lines) + '\n'
    # 只重建 GPOS/GDEF！feaLib 默认 tables=None 会把 GSUB 也一起重建，而这段 fea
    # 里没有任何 GSUB 特性 —— 结果它先建出一个空 GSUB，再 del font["GSUB"]，
    # 把 Merger 合并进来的 Noto ccmp（键盘帽/旗帜/ZWJ/Tag flag 的连字）整表删掉。
    addOpenTypeFeaturesFromString(font, fea, tables=['GPOS', 'GDEF'])

    # ---- mark-to-mark：逐字形 yMin/yMax 锚点 ----
    from fontTools.otlLib.builder import MarkMarkPosBuilder, buildAnchor
    b = MarkMarkPosBuilder(font, 'mark-to-mark')
    for g in above_marks:
        ymin, ymax = above_bounds[g]
        b.marks[g] = (0, buildAnchor(cx, round(ymin)))       # 第二个：墨迹底
        b.baseMarks[g] = {0: buildAnchor(cx, round(ymax))}   # 第一个：墨迹顶
    for g in below_marks:
        ymin, ymax = below_bounds[g]
        b.marks[g] = (1, buildAnchor(cx, round(ymax)))       # 第二个：墨迹顶
        b.baseMarks[g] = {1: buildAnchor(cx, round(ymin))}   # 第一个：墨迹底
    for g, (ymin, ymax) in precomposed.items():
        b.baseMarks[g] = {0: buildAnchor(cx, round(ymax)),
                          1: buildAnchor(cx, round(ymin))}
    lookup = b.build()
    gpos = font['GPOS'].table
    idx = len(gpos.LookupList.Lookup)
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == 'mark':
            fr.Feature.LookupListIndex.append(idx)
    return len(marks)



def add_stat_table(font, weight, italic):
    """写入 STAT（Style Attributes）表：``wght`` + ``ital`` 两个轴，每个 face 每轴只写 1 条。

    两个轴都写的原因：
      · ``ital`` 是现代应用/新系统读斜体的标准入口：正体 0、斜体 1，且必须排在**最后一个轴**；
        正体还要 elidable(0x0002) + ``LinkedValue = 1.0``（正体 ↔ 斜体互指），斜体 flags=0。
      · ``wght`` 让 STAT 里带上重量信息（400/700），而不是只靠 ``OS/2.usWeightClass`` 去猜。

    **静态字体每个轴只能有 1 条 AxisValue**（fontbakery 的 ``STAT_in_statics``）。把变量字体的
    STAT 原样塞进静态字体会让 Windows 只读第一条记录 —— 于是所有字重都显示成同一个名字。

    ``macNames=False``：本项目已删除全部 Mac(platform 1) name 记录（fontbakery 的
    ``no_mac_entries``），而 buildStatTable 默认会把这些记录重新加回来。
    """
    is_bold = weight >= 700
    axes = [
        dict(tag='wght', name='Weight', ordering=0,
             values=[dict(value=weight, name='Bold' if is_bold else 'Regular',
                          flags=0 if is_bold else 0x0002)]),
        # ital 必须最后；正体带 elidable + linkedValue，斜体两个都不带
        dict(tag='ital', name='Italic', ordering=1,
             values=[dict(value=1, name='Italic')] if italic else
                    [dict(value=0, name='Regular', flags=0x0002, linkedValue=1.0)]),
    ]
    buildStatTable(font, axes, elidedFallbackName='Regular', macNames=False)


# smart dropout：PUSHW 511 / SCANCTRL（无条件打开 dropout control）/ PUSHB 4 / SCANTYPE
# （smart 规则）。fontbakery 的 `smart_dropout` 就是在 prep 里找这 7 个字节，这也是
# gftools fix-nonhinting 对「未 hinting 字体」的标准处理。
SMART_DROPOUT = bytes.fromhex('b801ff85b0048d')


def add_smart_dropout_prep(font):
    """给未 hinting 的字体补一个只含 smart dropout 开关的 ``prep`` 表。

    本字体完全没有 hinting（无 cvt/fpgm，0 个字形带指令），此时各渲染器对
    「dropout control」的默认值不一致：小字号下 1px 细线可能整段消失
    （我们的 `|` 只有 88/1000 em，@12px ≈ 1.06 px，正好在这个区间）。
    这 7 个字节不调整任何轮廓点，只把这个开关显式打开；不会把字体变成 hinted。
    """
    asm = 'PUSHW[1] 511\nSCANCTRL[]\nPUSHB[1] 4\nSCANTYPE[]'
    prog = Program()
    prog.fromAssembly(asm)
    assert prog.getBytecode() == SMART_DROPOUT      # 防止 fontTools 汇编器行为变化
    if 'prep' in font:
        old = font['prep'].program.getBytecode()
        if SMART_DROPOUT in old:
            return False
        prog = Program()
        prog.fromBytecode(old + SMART_DROPOUT)      # 保留已有 prep，追加我们的片段
    prep = newTable('prep')
    prep.program = prog
    font['prep'] = prep
    return True


def recalc_hhea_metrics(font):
    """按最终 hmtx/glyf 重算 hhea 的 minLSB/minRSB/xMaxExtent/advanceWidthMax。

    hmtx.lsb 修正后这些值会变；fontTools 的 save() 只重算 glyf/head bbox，
    不会重算 hhea，留着上游的旧值会让部分渲染器（尤其 GDI/旧 macOS）用错
    side bearing / 裁切范围。
    """
    glyf = font['glyf']
    hmtx = font['hmtx']
    order = font.getGlyphOrder()
    adv_max = 0
    min_lsb = None
    min_rsb = None
    max_extent = None
    for name in order:
        adv, lsb = hmtx[name]
        adv_max = max(adv_max, adv)
        g = glyf[name]
        if g.numberOfContours == 0:
            continue
        width = g.xMax - g.xMin
        rsb = adv - lsb - width
        extent = lsb + width
        min_lsb = lsb if min_lsb is None else min(min_lsb, lsb)
        min_rsb = rsb if min_rsb is None else min(min_rsb, rsb)
        max_extent = extent if max_extent is None else max(max_extent, extent)
    hhea = font['hhea']
    hhea.advanceWidthMax = adv_max
    hhea.minLeftSideBearing = min_lsb if min_lsb is not None else 0
    hhea.minRightSideBearing = min_rsb if min_rsb is not None else 0
    hhea.xMaxExtent = max_extent if max_extent is not None else 0
    return (adv_max, hhea.minLeftSideBearing, hhea.minRightSideBearing, hhea.xMaxExtent)


def set_face_meta(font, subfamily, weight, bold, italic):
    psname = f'{FAMILY}-{subfamily.replace(" ", "")}'
    name = font['name']
    # 删掉所有 Mac(platform 1) name 记录：OpenType 现代实践已不再需要（Apple 自己
    # 的 SF 系列也不带），fontbakery 的 `no_mac_entries` 会报。上游基底带的那些遗留
    # 记录（如 ID0=ComicShanns 的版权）也正是从这儿来的，会被一并清掉。
    name.names = [r for r in name.names if r.platformID != 1]
    # name ID3（Unique ID）以前完全没人管，一直是上游的 "ComicShannsMono Nerd Font Mono 3.5.1"。
    # 按惯例写成 "<version>;<vendor>;<psname>"。
    unique_id = f'Version {VERSION};NONE;{psname}'
    for nid, val in ((0, COPYRIGHT), (1, FAMILY), (2, subfamily),
                     (3, unique_id), (4, f'{FAMILY} {subfamily}'),
                     (5, f'Version {VERSION}'), (6, psname),
                     (16, FAMILY), (17, subfamily),
                     (13, LICENSE_DESC), (14, LICENSE_URL),
                     # 元数据补全：厂商/设计者/简介/两个 URL/样文/WWS 命名
                     (8, VENDOR_NAME), (9, DESIGNER_NAME), (10, DESCRIPTION),
                     (11, VENDOR_URL), (12, DESIGNER_URL), (19, SAMPLE_TEXT),
                     (21, FAMILY), (22, subfamily)):
        for rec in list(name.names):
            if rec.nameID == nid:
                rec.string = val
        name.setName(val, nid, 3, 1, 0x409)

    os2 = font['OS/2']
    head = font['head']
    hhea = font['hhea']

    # ---- 版本：head.fontRevision 必须和 name ID5 一致（Regular/Bold 原来继承 Noto 的 2.057、
    #      斜体继承 SeriousShanns 的 4.0，而 name 写的是 1.0）----
    head.fontRevision = float(VERSION)

    # ---- 时间戳固定，保证 byte-identical 构建 ----
    #      TTFont.save() 默认 recalcTimestamp=True 会用「当前时间」覆盖 modified，
    #      所以必须同时关掉，否则每次构建 head 都不同。
    head.created = head.modified = BUILD_TIME
    font.recalcTimestamp = False

    # ---- 字重 / 斜体标记 ----
    os2.usWeightClass = weight
    fs = 0
    if bold:
        fs |= 0x20
    if italic:
        fs |= 0x01
    if not bold and not italic:
        fs = 0x40
    fs |= 0x80           # USE_TYPO_METRICS：行距用 typo 值，win 值只管不裁剪
    os2.fsSelection = fs
    head.macStyle = (0x01 if bold else 0) | (0x02 if italic else 0)

    # ---- 纵向指标：四 face 必须完全一致 ----
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = ASCENT, DESCENT, 0
    os2.usWinAscent, os2.usWinDescent = WIN_ASCENT, WIN_DESCENT
    hhea.ascent, hhea.descent, hhea.lineGap = ASCENT, DESCENT, 0

    # ---- 等宽元数据 ----
    os2.xAvgCharWidth = CELL
    os2.fsType = 0                      # 统一为可安装（斜体面原来继承 SeriousShanns 的 4=Preview&Print）
    # 上下标 / 删除线：四 face 统一，且删除线厚度绝不能为 0（否则不可见）。
    (os2.ySubscriptXSize, os2.ySubscriptYSize,
     os2.ySubscriptXOffset, os2.ySubscriptYOffset) = SUBSCRIPT_METRICS
    (os2.ySuperscriptXSize, os2.ySuperscriptYSize,
     os2.ySuperscriptXOffset, os2.ySuperscriptYOffset) = SUPERSCRIPT_METRICS
    os2.yStrikeoutSize, os2.yStrikeoutPosition = STRIKEOUT_METRICS
    os2.panose.bWeight = 8 if bold else 5
    post = font['post']
    post.isFixedPitch = 1               # 等宽字体必须非 0（原来被 Merger 弄成 0）
    post.underlinePosition = UNDERLINE_POSITION
    post.underlineThickness = UNDERLINE_THICKNESS
    post.italicAngle = ITALIC_ANGLE if italic else 0.0
    hhea.caretSlopeRise = 1000 if italic else 1
    hhea.caretSlopeRun = round(math.tan(math.radians(-ITALIC_ANGLE)) * 1000) if italic else 0

    # ---- hhea 的 side-bearing 统计：必须按修正后的 lsb 重算 ----
    recalc_hhea_metrics(font)

    # ---- STAT：样式菜单（wght + ital），每个 face 每轴 1 条 ----
    add_stat_table(font, weight, italic)

    # ---- 未 hinting 字体：补 smart dropout 开关（prep，7 字节） ----
    add_smart_dropout_prep(font)

    # ---- 收尾：重算 Unicode/代码页范围 ----
    #      （0 宽化 / 删控制码 / 重排字形已在 build_face 里、建 GPOS 之前做完）
    os2.recalcUnicodeRanges(font)
    os2.recalcCodePageRanges(font)
    print(f'  元数据：v{VERSION}，typo {ASCENT}/{DESCENT}，win {WIN_ASCENT}/{WIN_DESCENT}')
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
    # 全量吸收 JuliaMono 剩下的码点（跳过 Noto 覆盖的彩色 emoji）：
    # 这样本字体就是 ComicShanns ∪ JuliaMono ∪ NotoEmoji，fallback 链里不需要 JuliaMono 了
    julia_all = [cp for cp in julia.getBestCmap() if cp not in noto_cmap]
    n += copy_julia_into(base, julia, [], julia_all, False, skip=noto_cmap)

    # 覆盖率对齐：斜体基底 SeriousShanns（NF 3.2.1）缺一批 Nerd Font 3.5.1 的 PUA 图标，
    # 而 JuliaMono 快照也是更旧的 3.4.0，补不上 → 斜体面会比正体少 215 个图标码点。
    # 从**同字重**的 ComicShanns 基底补（只补 PUA，避免把直立拉丁混进斜体）。
    if base_key.startswith('ssh'):
        ref = flatten_scale_font(TTFont(SRC['comic_r' if base_key == 'ssh_i' else 'comic_b']), 1.0)
        ref_cmap = ref.getBestCmap()
        cur = base.getBestCmap()
        gap = sorted(cp for cp in ref_cmap
                     if cp not in cur and (0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0x10FFFD))
        if gap:
            filled = copy_julia_into(base, ref, [], gap, False, suffix='.comic')
            print(f'  覆盖率对齐：从 Comic 补入 {filled} 个 PUA 图标')

    n_fit = fit_glyphs_in_cells(base, [(0x0370, 0x03FF), (0x1F00, 0x1FFF)])
    if n_fit:
        print(f'  希腊多调号：{n_fit} 个字母收进 {CELL} 格（原墨迹越界）')

    z = zero_width_marks(base)
    print(f'  Julia 层拷入 {n} 个码点（其中组合标记 0 宽化 {z} 个）')

    if emoji:
        plan = prepare_emoji_presentation(base, julia, noto_cmap)
        noto = TTFont(SRC['noto'])
        noto = flatten_scale_font(noto, WIDE / 1024, upem_factor=1000 / 1024, uniform_advance=WIDE)
        for tag in ('vhea', 'vmtx'):
            if tag in noto:
                del noto[tag]
        font, noto_rename = merge_noto_emoji(base, noto)
        apply_emoji_presentation(font, noto, plan, noto_rename)
        # ZWJ 连字要同时接受 VS16 选中的彩色字形（否则 ❤️‍🔥 🏳️‍🌈 这类标准写法会散开）
        n_var = add_colour_ligature_variants(font)
        if n_var:
            print(f'  ZWJ 连字彩色变体：+{n_var} 条')
        print(f'  emoji 层合并完成，glyph 数: {len(font.getGlyphOrder())}')
    else:
        # 非 emoji 的 face 没有彩色字形，但同样需要「默认文本呈现」符号的单色轮廓；
        # 否则粗体/斜体里的 © ® ▪ ☀ ❤ … 会回退到别的字体，风格不一致
        pres = load_emoji_presentation()
        need_mono = sorted(cp for cp in noto_cmap
                           if cp not in pres and not is_Default_Ignorable(cp))
        fill_mono_symbols(base, julia, need_mono)
        font = base

    # Coptic 大写缺失：从本 face 的小写合成（要在 GPOS/重排之前，新字形才会被算进去）
    n_coptic = add_coptic_capitals(font)
    if n_coptic:
        print(f'  Coptic 大写：从对应小写合成 {n_coptic} 个（缩放到 cap，advance {CELL}）')

    # 先删控制码映射：可达性判断要基于**最终**的 cmap（否则 CR 这类字形会被算成可达）
    n_ctl = drop_control_cmap(font)

    # 删掉上游未编码字形 + 合并改名后的 .null/.notdef 副本（删字形会改 GID，必须在 GPOS 前）
    n_dead = drop_unreachable_glyphs(font)
    if n_dead:
        print(f'  清理不可达字形：{n_dead} 个（上游未编码 / 合并改名副本）')

    # 0 宽化 / 重排字形也必须在建 GPOS **之前**（见 compact_hmtx 的说明）
    n_mark, n_ign, n_ctl, n_tail = finalize_widths_and_order(font, n_ctl)
    # GSUB 的 contextual 分解必须放在重排之后：Coverage 要按最终 GID 排序，
    # 否则 OTS 会报 "Coverage is not sorted by glyph ids"。
    n_dec = decompose_precomposed_for_stacking(font)
    if n_dec:
        print(f'  预组合字母分解：{n_dec} 个（仅当后面跟组合符时）')
    m = add_mark_feature(font)
    print(f'  GPOS mark 锚定：{m} 个组合标记；0 宽化 标记 {n_mark} + 隐形 {n_ign}，'
          f'删控制码 {n_ctl}，等宽尾段 {n_tail} 个字形')

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
    ensure_reproducible_hash_seed()   # 不满足则带着 PYTHONHASHSEED=0 重启，保证可复现
    if not check_sources():
        return 1
    os.makedirs(DIST, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    # 四个 face 都带彩色 emoji：否则粗体/斜体里的 emoji 要靠系统 Noto Color Emoji 兜底，
    # 而且粗体里 VS15/VS16 切换会失效（Bold 面没有彩色字形也没有 UVS）
    build_face('Regular', 'comic_r', 'julia_r', emoji=True, overwrite=True)
    build_face('Bold', 'comic_b', 'julia_b', emoji=True, overwrite=True)
    build_face('Italic', 'ssh_i', 'julia_i', emoji=True, overwrite=False)
    build_face('Bold Italic', 'ssh_bi', 'julia_bi', emoji=True, overwrite=False)
    print(f'全部完成 → {DIST}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
