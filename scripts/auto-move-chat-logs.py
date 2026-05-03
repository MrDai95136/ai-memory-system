#!/usr/bin/env python3
"""
自动搬运下载的聊天记录文件
从 ~/Downloads/ 检测 chat-*.md 文件，移动到 memory/chat-log/ 目录

用法：
  python3 ~/.openclaw/workspace/scripts/auto-move-chat-logs.py
"""

import shutil
from pathlib import Path

DOWNLOADS_DIR = Path.home() / "Downloads"
STAGING_DIR = Path.home() / ".openclaw" / "workspace" / "memory" / "chat-log" / "staging"
CHAT_LOG_DIR = STAGING_DIR

CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)


def main():
    pattern = "chat-*.md"
    files = list(DOWNLOADS_DIR.glob(pattern))
    
    if not files:
        print("✅ Downloads 中没有发现聊天记录文件")
        return
    
    moved = 0
    for f in files:
        # 如果目标已存在同名文件，跳过（避免重复）
        dest = CHAT_LOG_DIR / f.name
        if dest.exists():
            print(f"⏭️ {f.name} 已存在，跳过")
            continue
        
        shutil.move(str(f), str(dest))
        print(f"✅ {f.name} → memory/chat-log/")
        moved += 1
    
    print(f"\n共搬运 {moved} 个文件")


if __name__ == '__main__':
    main()
