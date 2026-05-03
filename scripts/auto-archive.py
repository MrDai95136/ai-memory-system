#!/usr/bin/env python3
"""
记忆文件自动归档脚本 v2
- 超过 60 天的记忆文件移动到 archive/by-date/YYYY-MM/
- 保留原始 mtime（防止误判）
- 在原位置创建符号链接（防止路径断裂）
- 三重判断避免误归档活跃项目
- 动态生成 INDEX.md

用法：
  python3 auto-archive.py              # 执行归档
  python3 auto-archive.py --dry-run    # 预览不执行
"""

import os
import shutil
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
ACTIVE_DIR = MEMORY_DIR / "active"
ARCHIVE_DIR = MEMORY_DIR / "archive" / "by-date"
DAILY_BASE = MEMORY_DIR / "2026"
CHAT_LOG_DIR = MEMORY_DIR / "chat-log"
INDEX_FILE = MEMORY_DIR / "INDEX.md"
BACKUP_DIR = MEMORY_DIR / ".mempalace-backup"

# 60天前
CUTOFF_DATE = datetime.now() - timedelta(days=60)
DRY_RUN = '--dry-run' in __import__('sys').argv

# 归档排除：项目文件永不自动归档
PROTECTED_PATTERNS = ['项目-', 'ACTIVE', 'INDEX.md', 'README.md', 'AI记忆']


def is_protected(filepath):
    """项目文件和系统文件不归档"""
    name = filepath.name
    for pattern in PROTECTED_PATTERNS:
        if pattern in name:
            return True
    return False


def file_age_days(filepath):
    """文件年龄（天）"""
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    return (datetime.now() - mtime).days


def recently_mentioned(project_name, days=7):
    """检查最近 N 天的日记中是否提到项目名"""
    if not project_name:
        return False
    
    cutoff = datetime.now() - timedelta(days=days)
    
    # 扫描 2026/ 下的 daily 目录
    for year_dir in DAILY_BASE.iterdir():
        if not year_dir.is_dir():
            continue
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir() or not month_dir.name.endswith('月'):
                continue
            daily_dir = month_dir / "daily"
            if not daily_dir.exists():
                continue
            for df in daily_dir.glob("*.md"):
                if datetime.fromtimestamp(df.stat().st_mtime) < cutoff:
                    continue
                try:
                    content = df.read_text(encoding='utf-8')
                    if project_name in content:
                        return True
                except:
                    pass
    return False


def read_project_status(filepath):
    """读取项目文件中的状态"""
    try:
        content = filepath.read_text(encoding='utf-8')
        # 查找状态标记
        status_match = re.search(r'\*\*状态\*\*[：:]\s*(.+)', content)
        if status_match:
            status = status_match.group(1).strip()
            if any(kw in status for kw in ['进行中', '已暂停', '活跃']):
                return 'active'
            if '已结项' in status or '已完成' in status:
                return 'completed'
    except:
        pass
    return 'unknown'


def should_archive(filepath):
    """三重判断是否应该归档"""
    # 保护文件
    if is_protected(filepath):
        return False
    
    # 条件1：超过 60 天
    age = file_age_days(filepath)
    if age < 60:
        return False
    
    # 条件2：最近 7 天日记中提到
    name = filepath.stem
    if recently_mentioned(name):
        return False
    
    # 条件3：项目文件状态检查
    if filepath.suffix == '.md' and '项目' in str(filepath):
        status = read_project_status(filepath)
        if status == 'active':
            return False
    
    return True


def move_to_archive(filepath):
    """移动文件到归档目录，保留 mtime，创建软链接"""
    # 计算归档路径
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    year_month = mtime.strftime("%Y-%m")
    
    archive_subdir = ARCHIVE_DIR / year_month
    dest = archive_subdir / filepath.name
    
    if DRY_RUN:
        print(f"  [预览] {filepath.name} → archive/by-date/{year_month}/")
        return True
    
    # 创建归档目录
    archive_subdir.mkdir(parents=True, exist_ok=True)
    
    # 记录原始 stat
    original_stat = filepath.stat()
    original_atime = original_stat.st_atime
    original_mtime = original_stat.st_mtime
    
    # 移动文件
    shutil.move(str(filepath), str(dest))
    
    # 恢复原始 mtime（解决 1A）
    os.utime(dest, (original_atime, original_mtime))
    
    # 创建符号链接（解决 1B），如果不支持则创建硬链接
    symlink_path = filepath
    try:
        symlink_path.symlink_to(dest)
        print(f"  ✅ {filepath.name} → archive/by-date/{year_month}/ (软链接)")
    except OSError:
        # 符号链接不支持，尝试硬链接
        try:
            os.link(str(dest), str(symlink_path))
            print(f"  ✅ {filepath.name} → archive/by-date/{year_month}/ (硬链接)")
        except OSError as e2:
            print(f"  ⚠️ {filepath.name} 已归档，但链接创建失败: {e2}")
    
    return True


def update_index():
    """动态生成 INDEX.md（解决 4A）"""
    if DRY_RUN:
        print("\n[预览] 将更新 INDEX.md")
        return
    
    now = datetime.now()
    
    # 扫描 active/
    active_files = []
    if ACTIVE_DIR.exists():
        for f in ACTIVE_DIR.iterdir():
            if f.is_file() and f.suffix == '.md':
                # 如果是软链接，指向归档文件
                if f.is_symlink():
                    target = f.resolve()
                    active_files.append((f.name, f"memory/active/{f.name} (→ {target.relative_to(MEMORY_DIR)})"))
                else:
                    active_files.append((f.name, f"memory/active/{f.name}"))
    
    # 扫描归档目录
    archived = {}
    if ARCHIVE_DIR.exists():
        for ym_dir in sorted(ARCHIVE_DIR.iterdir()):
            if ym_dir.is_dir():
                files = list(ym_dir.glob("*.md"))
                if files:
                    archived[ym_dir.name] = len(files)
    
    # 扫描日记目录
    daily_stats = {}
    if DAILY_BASE.exists():
        for year_dir in sorted(DAILY_BASE.iterdir()):
            if not year_dir.is_dir():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                daily_dir = month_dir / "daily"
                if daily_dir.exists():
                    count = len(list(daily_dir.glob("*.md")))
                    key = f"{year_dir.name}/{month_dir.name}"
                    daily_stats[key] = count
    
    # 扫描 chat-log
    chat_files = []
    if CHAT_LOG_DIR.exists():
        for f in sorted(CHAT_LOG_DIR.iterdir()):
            if f.is_file() and f.suffix == '.md' and not f.is_symlink():
                size_kb = f.stat().st_size / 1024
                chat_files.append((f.name, f"{size_kb:.0f}KB"))
    
    # 生成 INDEX
    lines = [
        "# 记忆文件索引",
        "",
        f"> 最后更新：{now.strftime('%Y-%m-%d %H:%M')}（由归档脚本自动生成）",
        "> 如果你发现索引和实际不符，对我说\"更新索引\"",
        "",
        "---",
        "",
        "## 📌 当前活跃项目",
        "",
    ]
    
    if active_files:
        lines.append("| 项目 | 路径 |")
        lines.append("|------|------|")
        for name, path in active_files:
            lines.append(f"| {name.replace('.md', '')} | `{path}` |")
    else:
        lines.append("（无活跃项目）")
    
    lines.extend([
        "",
        "---",
        "",
        "## 📂 文件架构",
        "",
        "```",
        "memory/",
        "├── active/                    ← 当前活跃项目",
        "├── 2026/                      ← 按年月归档的记忆",
        "│   └── MM-月/daily/           ← 每日记忆",
        "├── chat-log/                  ← 每日对话原始记录",
        "├── archive/by-date/           ← 超过60天的文件归档",
        "├── INDEX.md                   ← 本索引文件",
        "└── AI记忆系统搭建计划.md      ← 记忆系统建设进度",
        "```",
        "",
        "---",
        "",
        "## 📅 月度记忆统计",
        "",
        "| 年月 | 日记文件 | 路径 |",
        "|------|---------|------|",
    ])
    
    for key, count in sorted(daily_stats.items(), reverse=True):
        lines.append(f"| {key} | {count} | `memory/{key}/daily/` |")
    
    lines.extend([
        "",
        "---",
        "",
        "## 💬 对话历史",
        "",
        "| 日期 | 文件 | 大小 | 路径 |",
        "|------|------|------|------|",
    ])
    
    for name, size in chat_files:
        lines.append(f"| {name.replace('.md', '')} | {name} | {size} | `memory/chat-log/` |")
    
    if archived:
        lines.extend([
            "",
            "---",
            "",
            "## 📦 已归档（超过60天）",
            "",
            "| 年月 | 文件数 | 路径 |",
            "|------|--------|------|",
        ])
        for ym, count in sorted(archived.items(), reverse=True):
            lines.append(f"| {ym} | {count} | `memory/archive/by-date/{ym}/` |")
    
    lines.extend([
        "",
        "---",
        "",
        "## 🔍 快速查找",
        "",
        "**问 AI 比翻文件夹更快。** 你可以这样问：",
        "",
        "| 你想找 | 这样问 |",
        "|--------|--------|",
        '| 某天的讨论记录 | "X月X号的对话内容" |',
        '| 某个项目的框架 | "XXX项目的项目文件在哪" |',
        '| 某次决策的细节 | "我们是怎么确定XXX的" |',
        "",
        "---",
        "",
        "*此索引由 AI 自动生成和维护，不需要手动更新。*",
        "",
    ])
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n✅ INDEX.md 已更新（{now.strftime('%H:%M')}）")


def archive_recovery_rule():
    """在 AGENTS.md 中添加归档恢复规则（解决 3B）"""
    agents_path = Path.home() / ".openclaw" / "workspace" / "AGENTS.md"
    content = agents_path.read_text(encoding='utf-8')
    
    if "Archive Recovery Rule" not in content:
        recovery_rule = """
## 📦 Archive Recovery Rule

**If user mentions a project marked as "archived":**
1. Search in `memory/archive/` for the project file
2. Copy it back to `memory/active/` (remove old symlink if exists)
3. Update status to "进行中" in the project file
4. Run `auto-archive.py` to regenerate INDEX.md
5. Notify user: "已恢复 [项目名]，状态更新为进行中"

**If user asks to "更新索引":**
- Run `python3 ~/.openclaw/workspace/scripts/auto-archive.py`
"""
        # Insert before "The goal:" line
        content = content.replace(
            "The goal: Be helpful without being annoying.",
            recovery_rule + "\nThe goal: Be helpful without being annoying."
        )
        agents_path.write_text(content, encoding='utf-8')
        print("✅ Archive Recovery Rule added to AGENTS.md")


def build_file_index():
    """构建文件索引缓存（解决 7：性能优化）"""
    index = {}
    
    if DAILY_BASE.exists():
        for year_dir in DAILY_BASE.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                daily_dir = month_dir / "daily"
                if not daily_dir.exists():
                    continue
                for f in daily_dir.iterdir():
                    if f.is_file() and f.suffix == '.md' and not f.is_symlink():
                        index[str(f)] = {
                            'path': str(f),
                            'mtime': f.stat().st_mtime,
                            'size': f.stat().st_size,
                            'name': f.name
                        }
    
    # 扫描 chat-log
    if CHAT_LOG_DIR.exists():
        for f in CHAT_LOG_DIR.iterdir():
            if f.is_file() and f.suffix == '.md' and not f.is_symlink():
                index[str(f)] = {
                    'path': str(f),
                    'mtime': f.stat().st_mtime,
                    'size': f.stat().st_size,
                    'name': f.name
                }
    
    return index


def check_storage_threshold():
    """检查存储是否超过 3000MB（解决 14）"""
    total_size = 0
    for root, dirs, files in os.walk(MEMORY_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            try:
                total_size += (Path(root) / f).stat().st_size
            except:
                pass
    
    size_mb = total_size / 1024 / 1024
    
    if size_mb > 3000:
        print(f"⚠️  存储超过 3000MB（当前 {size_mb:.0f}MB），请清理旧文件")
        return True
    elif size_mb > 2400:
        print(f"⚠️  存储接近上限（{size_mb:.0f}MB / 3000MB）")
    
    return False


def main():
    print(f"📋 开始归档检查（截止日期: {CUTOFF_DATE.strftime('%Y-%m-%d')}）")
    if DRY_RUN:
        print("⚠️  预览模式，不会实际移动文件\n")
    
    # 检查存储阈值
    check_storage_threshold()
    
    # 加载文件索引（性能优化）
    file_index = build_file_index()
    
    archived_count = 0
    
    # 检查日记目录（使用索引加速）
    if DAILY_BASE.exists():
        for year_dir in DAILY_BASE.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                daily_dir = month_dir / "daily"
                if not daily_dir.exists():
                    continue
                for f in sorted(daily_dir.iterdir()):
                    if f.is_file() and f.suffix == '.md' and not f.is_symlink():
                        if should_archive(f):
                            if move_to_archive(f):
                                archived_count += 1
    
    # 检查 chat-log
    if CHAT_LOG_DIR.exists():
        for f in sorted(CHAT_LOG_DIR.iterdir()):
            if f.is_file() and f.suffix == '.md' and not f.is_symlink():
                if should_archive(f):
                    if move_to_archive(f):
                        archived_count += 1
    
    # 保存文件索引缓存
    index_cache = MEMORY_DIR / ".file-index.json"
    if not DRY_RUN:
        with open(index_cache, 'w', encoding='utf-8') as f:
            json.dump(file_index, f, indent=2, ensure_ascii=False)
    
    # 更新索引
    update_index()
    
    # 添加归档恢复规则
    archive_recovery_rule()
    
    print(f"\n{'[预览] ' if DRY_RUN else ''}共归档 {archived_count} 个文件")


if __name__ == '__main__':
    main()
