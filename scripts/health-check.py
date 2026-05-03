#!/usr/bin/env python3
"""
记忆系统健康检查脚本
每天验证系统状态，发现问题及时报告。

用法：
  python3 health-check.py
"""

import os
import json
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
SCRIPTS_DIR = Path.home() / ".openclaw" / "workspace" / "scripts"
WORKSPACE_DIR = Path.home() / ".openclaw" / "workspace"

MAX_STORAGE_MB = 3000  # 3GB 阈值
WARNINGS = []
ERRORS = []


def check_file_exists(filepath, name):
    """检查文件是否存在"""
    if not filepath.exists():
        ERRORS.append(f"❌ {name} 不存在: {filepath}")
        return False
    return True


def check_checkpoint():
    """检查 checkpoint 文件完整性"""
    cp_file = MEMORY_DIR / ".chat-log-checkpoint.json"
    if not check_file_exists(cp_file, "Checkpoint"):
        return
    
    try:
        with open(cp_file, 'r') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            ERRORS.append("❌ Checkpoint 格式错误：不是 JSON 对象")
        else:
            print(f"  ✅ Checkpoint: {len(data)} 个会话位置已记录")
    except json.JSONDecodeError:
        ERRORS.append("❌ Checkpoint 文件损坏（JSON 解析失败）")


def check_scripts():
    """检查关键脚本是否存在"""
    scripts = [
        'export-chat-log.py',
        'auto-move-chat-logs.py',
        'auto-archive.py',
        'auto-backup.py',
    ]
    
    for name in scripts:
        filepath = SCRIPTS_DIR / name
        if check_file_exists(filepath, f"脚本 {name}"):
            size = filepath.stat().st_size
            if size < 100:
                WARNINGS.append(f"⚠️  脚本 {name} 可能为空（{size} bytes）")
            else:
                print(f"  ✅ 脚本 {name}: {size} bytes")


def check_storage_size():
    """检查存储大小"""
    total_size = 0
    for root, dirs, files in os.walk(MEMORY_DIR):
        # 排除隐藏目录和备份
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            try:
                total_size += (Path(root) / f).stat().st_size
            except:
                pass
    
    size_mb = total_size / 1024 / 1024
    
    if size_mb > MAX_STORAGE_MB:
        ERRORS.append(f"❌ 存储超过 {MAX_STORAGE_MB}MB（当前 {size_mb:.0f}MB），请清理旧文件")
    elif size_mb > MAX_STORAGE_MB * 0.8:
        WARNINGS.append(f"⚠️  存储接近上限（{size_mb:.0f}MB / {MAX_STORAGE_MB}MB）")
    else:
        print(f"  ✅ 存储大小: {size_mb:.1f}MB / {MAX_STORAGE_MB}MB")


def check_symlinks():
    """检查死链接"""
    dead_links = 0
    for root, dirs, files in os.walk(MEMORY_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            filepath = Path(root) / f
            if filepath.is_symlink() and not filepath.exists():
                dead_links += 1
                WARNINGS.append(f"⚠️  死链接: {filepath}")
    
    if dead_links == 0:
        print(f"  ✅ 无死链接")


def check_recent_activity():
    """检查最近是否有活动"""
    recent_files = []
    cutoff = datetime.now()
    
    for root, dirs, files in os.walk(MEMORY_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            filepath = Path(root) / f
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            if (cutoff - mtime).days <= 1:
                recent_files.append(filepath)
    
    if recent_files:
        print(f"  ✅ 最近 24 小时有 {len(recent_files)} 个文件更新")
    else:
        WARNINGS.append("⚠️  最近 24 小时没有文件更新（可能系统未运行）")


def check_backup():
    """检查备份状态"""
    backup_dir = WORKSPACE_DIR / ".backups"
    if not backup_dir.exists():
        WARNINGS.append("⚠️  备份目录不存在（可能还未执行过备份）")
        return
    
    # 检查最近 2 天是否有备份
    recent_backups = 0
    for item in backup_dir.iterdir():
        if item.is_dir():
            try:
                dir_date = datetime.strptime(item.name, '%Y-%m-%d')
                if (datetime.now() - dir_date).days <= 2:
                    recent_backups += 1
            except:
                pass
    
    if recent_backups > 0:
        print(f"  ✅ 最近有备份（{recent_backups} 个）")
    else:
        WARNINGS.append("⚠️  最近 2 天没有备份记录")


def main():
    print(f"🏥 记忆系统健康检查（{datetime.now().strftime('%Y-%m-%d %H:%M')}）\n")
    
    check_checkpoint()
    check_scripts()
    check_storage_size()
    check_symlinks()
    check_recent_activity()
    check_backup()
    
    print("\n" + "=" * 50)
    if ERRORS:
        print("❌ 错误:")
        for e in ERRORS:
            print(f"  {e}")
    if WARNINGS:
        print("\n⚠️  警告:")
        for w in WARNINGS:
            print(f"  {w}")
    if not ERRORS and not WARNINGS:
        print("✅ 系统健康，没有问题")
    print("=" * 50)
    
    return len(ERRORS)


if __name__ == '__main__':
    exit(main())
