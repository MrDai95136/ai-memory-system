#!/usr/bin/env python3
"""
记忆系统每日状态报告
检查所有记忆相关组件是否正常运行，生成统一报告。

用法：
  python3 memory-status.py
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
SCRIPTS_DIR = Path.home() / ".openclaw" / "workspace" / "scripts"
SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"

REPORT = []

def section(title):
    REPORT.append(f"\n{'='*20} {title} {'='*20}")

def ok(msg):
    REPORT.append(f"  ✅ {msg}")

def warn(msg):
    REPORT.append(f"  ⚠️  {msg}")

def error(msg):
    REPORT.append(f"  ❌ {msg}")


def check_memory_dir():
    """检查目录结构"""
    section("目录结构")
    checks = {
        "memory/active": MEMORY_DIR / "active",
        "memory/chat-log": MEMORY_DIR / "chat-log",
        "memory/archive": MEMORY_DIR / "archive",
        ".checkpoint": MEMORY_DIR / ".chat-log-checkpoint.json",
        "INDEX.md": MEMORY_DIR / "INDEX.md",
    }
    for name, path in checks.items():
        if path.exists():
            ok(f"{name}")
        else:
            error(f"{name} 不存在")


def check_daily_files():
    """检查今天的记忆文件"""
    section("今日记忆")
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 查找今天的 daily 文件
    daily_dir = MEMORY_DIR / "2026"
    found = False
    if daily_dir.exists():
        for month_dir in daily_dir.iterdir():
            if not month_dir.is_dir():
                continue
            daily_path = month_dir / "daily" / f"{today}.md"
            if daily_path.exists():
                size = daily_path.stat().st_size
                ok(f"今日日记存在 ({size} bytes)")
                found = True
            chat_path = month_dir / "chat-log" / f"{today}.md"
            if chat_path.exists():
                size = chat_path.stat().st_size
                ok(f"今日对话记录存在 ({size} bytes)")
    
    if not found:
        warn(f"今日日记文件未找到（可能还没到写入时间）")


def check_chat_log():
    """检查 chat-log"""
    section("对话历史")
    chat_dir = MEMORY_DIR / "chat-log"
    if chat_dir.exists():
        files = list(chat_dir.glob("*.md"))
        ok(f"chat-log 目录有 {len(files)} 个文件")
        # 检查最新文件
        if files:
            latest = max(files, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest.stat().st_mtime)
            hours_ago = (datetime.now() - mtime).total_seconds() / 3600
            ok(f"最新: {latest.name} ({hours_ago:.1f}小时前)")
    else:
        error("chat-log 目录不存在")


def check_scripts():
    """检查脚本"""
    section("脚本文件")
    scripts = [
        "export-chat-log.py",
        "auto-move-chat-logs.py",
        "auto-archive.py",
        "auto-backup.py",
        "health-check.py",
    ]
    for name in scripts:
        path = SCRIPTS_DIR / name
        if path.exists():
            ok(f"{name}")
        else:
            error(f"{name} 缺失")


def check_cron():
    """检查 cron 任务状态"""
    section("定时任务")
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        jobs = data.get("jobs", []) if isinstance(data, dict) else data
        
        memory_jobs = [
            "记忆每日增量备份",
            "自动搬运聊天记录",
            "对话历史每日提取",
            "记忆系统健康检查",
            "记忆每周全量备份",
            "记忆文件自动归档",
        ]
        
        for job in jobs:
            name = job.get("name", "")
            if name not in memory_jobs:
                continue
                state = job.get("state", {})
                last_status = state.get("lastStatus", "从未执行")
                last_run = state.get("lastRunAtMs")
                enabled = job.get("enabled", False)
                
                status_icon = "✅" if last_status == "ok" else ("❌" if last_status == "error" else "⏳")
                status_text = f"{name}: {status_icon} {last_status}"
                
                if last_run:
                    last_dt = datetime.fromtimestamp(last_run / 1000)
                    status_text += f" (上次: {last_dt.strftime('%m-%d %H:%M')})"
                
                if not enabled:
                    status_text += " [已禁用]"
                
                if last_status == "ok":
                    ok(status_text)
                elif last_status == "error":
                    error(status_text)
                else:
                    warn(status_text)
    except Exception as e:
        warn(f"无法获取 cron 状态: {e}")


def check_mempalace():
    """检查 MemPalace"""
    section("MemPalace")
    mempalace = Path.home() / ".mempalace" / "palace"
    if mempalace.exists():
        ok("MemPalace 数据库存在")
        db = mempalace / "chroma.sqlite3"
        if db.exists():
            size = db.stat().st_size
            ok(f"向量数据库: {size // 1024} KB")
    else:
        error("MemPalace 未安装")


def check_sessions():
    """检查会话文件"""
    section("会话文件")
    if SESSIONS_DIR.exists():
        files = list(SESSIONS_DIR.glob("*.jsonl"))
        files = [f for f in files if "trajectory" not in f.name]
        ok(f"会话文件: {len(files)} 个")
        
        # 最新会话
        if files:
            latest = max(files, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest.stat().st_mtime)
            hours_ago = (datetime.now() - mtime).total_seconds() / 3600
            ok(f"最新会话: {latest.name} ({hours_ago:.1f}小时前)")


def check_disk():
    """检查磁盘占用"""
    section("磁盘占用")
    try:
        result = subprocess.run(
            ["du", "-sh", str(MEMORY_DIR)],
            capture_output=True, text=True, timeout=10
        )
        size = result.stdout.strip().split()[0]
        ok(f"memory/ 目录: {size}")
        
        # 文件总数
        count = sum(1 for _ in MEMORY_DIR.rglob("*"))
        ok(f"总文件数: {count}")
    except:
        pass


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    REPORT.append(f"🧠 记忆系统状态报告")
    REPORT.append(f"生成时间: {now}")
    
    check_memory_dir()
    check_daily_files()
    check_chat_log()
    check_scripts()
    check_cron()
    check_mempalace()
    check_sessions()
    check_disk()
    
    report = "\n".join(REPORT)
    print(report)


if __name__ == "__main__":
    main()
