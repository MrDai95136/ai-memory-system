#!/usr/bin/env python3
"""
记忆系统自动备份脚本
- 每天增量备份（只备份今天修改的文件）
- 每周全量备份
- 备份保留 30 天

用法：
  python3 auto-backup.py --incremental    # 增量备份（默认）
  python3 auto-backup.py --full           # 全量备份
  python3 auto-backup.py --dry-run        # 预览
"""

import os
import shutil
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
WORKSPACE_DIR = Path.home() / ".openclaw" / "workspace"
BACKUP_BASE = Path.home() / ".openclaw" / "workspace" / ".backups"
STATE_FILE = BACKUP_BASE / "backup-state.json"
MAX_BACKUP_DAYS = 30
DRY_RUN = '--dry-run' in __import__('sys').argv
FULL_BACKUP = '--full' in __import__('sys').argv


def get_backup_dir():
    """获取今天的备份目录"""
    today = datetime.now().strftime('%Y-%m-%d')
    return BACKUP_BASE / today


def file_hash(filepath):
    """计算文件 MD5"""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def load_state():
    """加载备份状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'last_hashes': {}, 'last_full_backup': None}


def save_state(state):
    """保存备份状态"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_files_to_backup():
    """获取需要备份的文件"""
    files = []
    
    # 扫描 memory/ 目录（排除 .dreams 和 .backups）
    for root, dirs, filenames in os.walk(MEMORY_DIR):
        # 排除隐藏目录和备份目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.backups']
        
        for filename in filenames:
            filepath = Path(root) / filename
            if filepath.suffix in ['.md', '.json', '.txt', '.py']:
                files.append(filepath)
    
    # 扫描 AGENTS.md, SOUL.md, USER.md, HEARTBEAT.md
    for name in ['AGENTS.md', 'SOUL.md', 'USER.md', 'HEARTBEAT.md', 'TOOLS.md', 'IDENTITY.md', 'MEMORY.md']:
        filepath = WORKSPACE_DIR / name
        if filepath.exists():
            files.append(filepath)
    
    return files


def incremental_backup():
    """增量备份：只备份修改过的文件"""
    state = load_state()
    backup_dir = get_backup_dir()
    backed_up = 0
    
    for filepath in get_files_to_backup():
        current_hash = file_hash(filepath)
        last_hash = state['last_hashes'].get(str(filepath))
        
        # 如果文件没变，跳过
        if current_hash == last_hash:
            continue
        
        # 计算相对路径
        try:
            rel_path = filepath.relative_to(WORKSPACE_DIR)
        except ValueError:
            rel_path = filepath.relative_to(MEMORY_DIR.parent / "memory")
        
        dest = backup_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        if DRY_RUN:
            print(f"  [预览] {filepath.name} → backup/")
        else:
            shutil.copy2(str(filepath), str(dest))
        
        state['last_hashes'][str(filepath)] = current_hash
        backed_up += 1
    
    if not DRY_RUN:
        save_state(state)
    
    return backed_up


def full_backup():
    """全量备份"""
    backup_dir = get_backup_dir() / "full"
    
    if DRY_RUN:
        print(f"  [预览] 全量备份到 {backup_dir}")
        return len(list(get_files_to_backup()))
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 备份 memory/
    memory_backup = backup_dir / "memory"
    if MEMORY_DIR.exists():
        shutil.copytree(str(MEMORY_DIR), str(memory_backup), 
                       ignore=shutil.ignore_patterns('.dreams', '.backups', '__pycache__'))
    
    # 备份关键配置文件
    config_backup = backup_dir / "config"
    config_backup.mkdir(parents=True, exist_ok=True)
    for name in ['AGENTS.md', 'SOUL.md', 'USER.md', 'HEARTBEAT.md', 'TOOLS.md', 'IDENTITY.md', 'MEMORY.md']:
        src = WORKSPACE_DIR / name
        if src.exists():
            shutil.copy2(str(src), str(config_backup / name))
    
    # 更新状态
    state = load_state()
    state['last_full_backup'] = datetime.now().isoformat()
    for filepath in get_files_to_backup():
        state['last_hashes'][str(filepath)] = file_hash(filepath)
    save_state(state)
    
    return len(list(get_files_to_backup()))


def cleanup_old_backups():
    """清理超过 30 天的备份"""
    if not BACKUP_BASE.exists():
        return
    
    cutoff = datetime.now() - timedelta(days=MAX_BACKUP_DAYS)
    cleaned = 0
    
    for item in BACKUP_BASE.iterdir():
        if item.is_dir() and item.name != 'backup-state.json':
            try:
                dir_date = datetime.strptime(item.name, '%Y-%m-%d')
                if dir_date < cutoff:
                    if DRY_RUN:
                        print(f"  [预览] 删除旧备份: {item.name}")
                    else:
                        shutil.rmtree(str(item))
                    cleaned += 1
            except ValueError:
                pass
    
    return cleaned


def main():
    print(f"📋 记忆系统备份（{datetime.now().strftime('%Y-%m-%d %H:%M')}）")
    if DRY_RUN:
        print("⚠️  预览模式\n")
    
    BACKUP_BASE.mkdir(parents=True, exist_ok=True)
    
    if FULL_BACKUP:
        count = full_backup()
        print(f"{'[预览] ' if DRY_RUN else ''}全量备份: {count} 个文件 → {get_backup_dir() / 'full'}")
    else:
        count = incremental_backup()
        print(f"{'[预览] ' if DRY_RUN else ''}增量备份: {count} 个文件已备份")
    
    cleaned = cleanup_old_backups()
    if cleaned > 0:
        print(f"🗑️  清理了 {cleaned} 个过期备份（超过{MAX_BACKUP_DAYS}天）")
    
    # 计算备份目录总大小
    total_size = sum(f.stat().st_size for f in BACKUP_BASE.rglob('*') if f.is_file())
    print(f"💾 备份总大小: {total_size / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    main()
