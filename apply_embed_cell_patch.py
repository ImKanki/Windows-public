# -*- coding: utf-8 -*-
"""将 embed_cell.py 的最小尺寸从 120x90 改为 46x40。"""
from pathlib import Path
import sys


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("embed_cell.py")
    if not target.exists():
        raise SystemExit(f"找不到文件: {target}")

    text = target.read_text(encoding="utf-8")
    old = "        self.setMinimumSize(120, 90)"
    new = "        self.setMinimumSize(46, 40)"

    if new in text:
        print(f"无需修改，已经是目标值: {target}")
        return
    if old not in text:
        raise SystemExit(
            "未找到目标行：self.setMinimumSize(120, 90)\n"
            "请手动将它改为 self.setMinimumSize(46, 40)"
        )

    backup = target.with_suffix(target.suffix + ".bak")
    backup.write_text(text, encoding="utf-8")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"修改完成: {target}")
    print(f"备份文件: {backup}")


if __name__ == "__main__":
    main()
