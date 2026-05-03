#!/usr/bin/env python3
"""
AI Memory System 安装脚本
将记忆系统模板安装到 OpenClaw workspace。
"""

import os
import sys
import shutil
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
SCRIPTS_DIR = WORKSPACE / "scripts"
MEMORY_DIR = WORKSPACE / "memory"
BASE_DIR = Path(__file__).parent


def check_openclaw():
    if not WORKSPACE.exists():
        print("❌ 未找到 OpenClaw workspace，请先安装 OpenClaw")
        print("   https://github.com/openclaw/openclaw")
        return False
    return True


def check_mempalace():
    mempalace = Path.home() / ".mempalace" / "palace"
    if not mempalace.exists():
        print("⚠️  MemPalace 未检测到，建议先安装")
        print("   在 OpenClaw 中: 搜索技能 mempalace 并安装")
        return False
    return True


def create_memory_structure():
    dirs = [
        MEMORY_DIR / "active",
        MEMORY_DIR / "chat-log",
        MEMORY_DIR / "archive" / "by-date",
        MEMORY_DIR / "archive" / "by-project",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {d.relative_to(WORKSPACE)}")


def copy_scripts():
    src = BASE_DIR / "scripts"
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    for script in src.glob("*.py"):
        dst = SCRIPTS_DIR / script.name
        shutil.copy2(script, dst)
        os.chmod(dst, 0o755)
        print(f"  ✅ {script.name}")


def setup_rules():
    agents_rules = BASE_DIR / "rules" / "AGENTS-memory-rules.md"
    heartbeat_rules = BASE_DIR / "rules" / "HEARTBEAT-memory-rules.md"

    if agents_rules.exists():
        dst = WORKSPACE / "AGENTS.md"
        if not dst.exists():
            shutil.copy2(agents_rules, dst)
            print("  ✅ AGENTS.md 已创建")
        else:
            content = dst.read_text()
            if "对话自动记录" not in content:
                rules = agents_rules.read_text()
                with open(dst, "a") as f:
                    f.write("\n\n" + rules)
                print("  ✅ AGENTS.md 已追加规则")
            else:
                print("  ⏭️ AGENTS.md 已有规则")

    if heartbeat_rules.exists():
        dst = WORKSPACE / "HEARTBEAT.md"
        if not dst.exists():
            shutil.copy2(heartbeat_rules, dst)
            print("  ✅ HEARTBEAT.md 已创建")
        else:
            content = dst.read_text()
            if "对话自动记录" not in content:
                rules = heartbeat_rules.read_text()
                with open(dst, "a") as f:
                    f.write("\n\n" + rules)
                print("  ✅ HEARTBEAT.md 已追加规则")
            else:
                print("  ⏭️ HEARTBEAT.md 已有规则")


def create_init_files():
    checkpoint = MEMORY_DIR / ".chat-log-checkpoint.json"
    if not checkpoint.exists():
        checkpoint.write_text("{}")
        print("  ✅ .chat-log-checkpoint.json")

    index = MEMORY_DIR / "INDEX.md"
    if not index.exists():
        index.write_text("# 记忆系统索引\n\n> 此文件由 auto-archive.py 自动生成。\n")
        print("  ✅ INDEX.md")


def verify():
    print("\n🔍 验证...")
    checks = [
        MEMORY_DIR / "active",
        MEMORY_DIR / "chat-log",
        MEMORY_DIR / "archive" / "by-date",
        MEMORY_DIR / ".chat-log-checkpoint.json",
        MEMORY_DIR / "INDEX.md",
        SCRIPTS_DIR / "export-chat-log.py",
        SCRIPTS_DIR / "auto-backup.py",
        SCRIPTS_DIR / "auto-archive.py",
        SCRIPTS_DIR / "health-check.py",
    ]
    ok = sum(1 for p in checks if p.exists())
    for p in checks:
        status = "✅" if p.exists() else "❌"
        print(f"  {status} {p.relative_to(WORKSPACE) if p.exists() else p.name}")
    return ok == len(checks)


def main():
    print("=" * 50)
    print("  AI Memory System 安装")
    print("=" * 50)
    print()

    if not check_openclaw():
        sys.exit(1)
    check_mempalace()

    print("\n📂 创建目录结构...")
    create_memory_structure()

    print("\n🔧 复制脚本...")
    copy_scripts()

    print("\n📝 配置规则...")
    setup_rules()

    print("\n📄 创建初始文件...")
    create_init_files()

    ok = verify()
    print(f"\n{'✅ 安装完成！' if ok else '⚠️  部分文件缺失'}")
    print("\n🎉 下一步：在 OpenClaw 主会话中设置定时任务")


if __name__ == "__main__":
    main()
