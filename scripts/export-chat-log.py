#!/usr/bin/env python3
"""
对话历史增量提取脚本
从 OpenClaw .jsonl 会话文件中提取用户和 AI 的对话，转成 Markdown 格式。
支持增量提取：记录上次提取位置，只提取新内容并追加到当日文件。

用法：
  python3 ~/.openclaw/workspace/scripts/export-chat-log.py              # 提取所有新会话
  python3 ~/.openclaw/workspace/scripts/export-chat-log.py --today      # 只提取今天的
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
MEMORY_DIR = Path.home() / ".openclaw" / "workspace" / "memory"
CHAT_LOG_DIR = MEMORY_DIR / "chat-log"
CHECKPOINT_FILE = MEMORY_DIR / ".chat-log-checkpoint.json"

# 确保目录存在
CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_checkpoint():
    """加载检查点，记录每个会话上次提取的位置（含格式验证）"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            else:
                print("⚠️  Checkpoint 格式错误，使用空检查点")
        except json.JSONDecodeError:
            print("⚠️  Checkpoint 文件损坏，使用空检查点")
            # 尝试从备份恢复
            backup = CHECKPOINT_FILE.with_suffix('.json.bak')
            if backup.exists():
                try:
                    with open(backup, 'r') as f:
                        return json.load(f)
                    print("  ✅ 从备份恢复成功")
                except:
                    pass
    return {}


def save_checkpoint(checkpoint):
    """保存检查点（原子写入 + 备份，解决 6）"""
    # 先备份旧的 checkpoint
    if CHECKPOINT_FILE.exists():
        backup = CHECKPOINT_FILE.with_suffix('.json.bak')
        import shutil
        shutil.copy2(str(CHECKPOINT_FILE), str(backup))
    
    # 原子写入：先写临时文件，再 rename
    temp_file = CHECKPOINT_FILE.with_suffix('.json.tmp')
    with open(temp_file, 'w') as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)
    temp_file.replace(CHECKPOINT_FILE)


def get_session_files(today_only=False):
    """获取会话文件列表"""
    files = []
    for f in SESSIONS_DIR.glob("*.jsonl"):
        if "trajectory" in f.name:
            continue
        if today_only:
            # 只处理今天修改过的文件
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime.date() != datetime.now().date():
                continue
        files.append(f)
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)


def parse_session(filepath, start_line=0):
    """解析会话文件，提取用户和 AI 的对话"""
    messages = []
    current_tool_calls = []
    current_tool_result = None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"读取文件失败 {filepath}: {e}")
        return messages, len(lines) if 'lines' in dir() else 0
    
    for i, line in enumerate(lines):
        if i < start_line:
            continue
        
        try:
            data = json.loads(line.strip())
        except:
            continue
        
        msg = data.get('message', {})
        role = msg.get('role', '')
        content = msg.get('content', '')
        timestamp = data.get('timestamp', '')
        
        if role == 'user':
            if isinstance(content, list):
                text = ''
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text += item.get('text', '')
                        elif item.get('type') == 'image_url':
                            text += '\n[图片]'
            else:
                text = str(content) if content else ''
            
            if text.strip():
                messages.append({
                    'role': 'user',
                    'text': text.strip(),
                    'time': timestamp
                })
        
        elif role == 'assistant':
            if isinstance(content, list):
                text = ''
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text += item.get('text', '')
                        elif item.get('type') == 'tool_use':
                            tool_name = item.get('name', '')
                            tool_input = item.get('input', {})
                            text += f'\n[工具调用: {tool_name}]'
            else:
                text = str(content) if content else ''
            
            if text.strip():
                messages.append({
                    'role': 'assistant',
                    'text': text.strip(),
                    'time': timestamp
                })
    
    return messages, len(lines)


def format_messages(messages):
    """格式化消息为 Markdown"""
    lines = []
    for msg in messages:
        time_str = ''
        if msg['time']:
            try:
                dt = datetime.fromisoformat(msg['time'].replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M')
            except:
                pass
        
        role_label = '👤 用户' if msg['role'] == 'user' else '🦁 七十八'
        
        # 清理文本，限制过长内容
        text = msg['text']
        if len(text) > 2000:
            text = text[:2000] + '\n\n...（内容已截断）'
        
        lines.append(f"\n### {role_label} ({time_str})\n\n{text}\n")
    
    return '\n'.join(lines)


def get_session_summary(filepath, messages):
    """从对话内容生成会话摘要（用于文件名）"""
    # 提取前几条用户消息的关键词
    user_msgs = [m['text'] for m in messages if m['role'] == 'user']
    if not user_msgs:
        return 'empty'
    
    # 取第一条用户消息的前50字作为摘要
    first_msg = user_msgs[0][:50]
    # 清理特殊字符
    summary = ''.join(c for c in first_msg if c.isalnum() or c in ' -_.')
    return summary[:30] if summary else 'chat'


def main():
    today_only = '--today' in sys.argv
    
    print("📋 开始提取对话历史...")
    
    checkpoint = load_checkpoint()
    session_files = get_session_files(today_only=today_only)
    
    if not session_files:
        print("✅ 没有新的会话需要提取")
        return
    
    # 按日期分组
    daily_content = {}
    
    for filepath in session_files:
        session_id = filepath.stem
        last_line = checkpoint.get(session_id, 0)
        
        messages, total_lines = parse_session(filepath, start_line=last_line)
        
        if not messages:
            # 更新检查点即使没有新消息
            checkpoint[session_id] = total_lines
            continue
        
        # 获取文件修改日期作为对话日期
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        date_key = mtime.strftime('%Y-%m-%d')
        
        if date_key not in daily_content:
            daily_content[date_key] = []
        
        daily_content[date_key].extend(messages)
        checkpoint[session_id] = total_lines
        
        print(f"  📝 {filepath.name}: 提取了 {len(messages)} 条新消息")
    
    # 写入每日文件
    for date_key, messages in daily_content.items():
        chat_file = CHAT_LOG_DIR / f"{date_key}.md"
        
        # 如果是新文件，添加标题和"今日要点"占位符
        if not chat_file.exists():
            with open(chat_file, 'w', encoding='utf-8') as f:
                f.write(f"# {date_key} 对话记录\n\n")
                f.write("## 今日要点\n")
                f.write("> （待补充：一句话总结今天最重要的事）\n\n")
                f.write("---\n\n")
        
        # 追加新内容
        formatted = format_messages(messages)
        with open(chat_file, 'a', encoding='utf-8') as f:
            f.write(f"\n---\n## 会话增量更新 ({datetime.now().strftime('%H:%M')})\n")
            f.write(formatted)
            f.write(f"\n\n_更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")
        
        print(f"  ✅ 已写入: {chat_file.name} ({len(messages)} 条)")
    
    # 保存检查点
    save_checkpoint(checkpoint)
    print("✅ 提取完成")


if __name__ == '__main__':
    main()
