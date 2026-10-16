#!/usr/bin/env bash
#
# 把 dist/ 里的字体安装到用户字体目录。
#
# 两个刻意的设计（都是踩过坑换来的）：
#
#  1. 用 cp + mv 做**原子替换**。直接 cp 覆盖正在使用的字体文件时，
#     正在运行的终端可能读到写了一半的文件。
#  2. **不执行 fc-cache**。fc-cache 会截断重写 fontconfig 的缓存文件，
#     而缓存是 mmap 进进程的 —— 正在使用它的程序会收到 SIGBUS 直接崩溃。
#     fontconfig 本来就会按目录 mtime 自动失效缓存，不需要手动预热。
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/ComicMathMono"

mkdir -p "$DEST"

shopt -s nullglob
files=("$ROOT"/dist/ComicMathMono-*.ttf)
if [ ${#files[@]} -eq 0 ]; then
    echo "dist/ 里没有字体，请先跑：python3 build.py" >&2
    exit 1
fi

for f in "${files[@]}"; do
    base="$(basename "$f")"
    tmp="$DEST/.${base}.tmp"
    cp "$f" "$tmp"
    mv -f "$tmp" "$DEST/$base"          # rename 是原子操作
    echo "  installed $base"
done

echo
echo "已安装到 $DEST"
echo "不需要跑 fc-cache。已开的终端要重启才会用上新字体。"
