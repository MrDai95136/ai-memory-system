# AI Memory System — OpenClaw 记忆系统

基于 OpenClaw 的四层 AI 记忆系统架构，参考人类记忆真实工作机制设计。

## 功能

- 🧠 **四层记忆架构**：长期记忆 + 项目文件 + 每日日记 + 对话历史
- 🔍 **语义搜索**：MemPalace 向量索引，跨会话快速召回
- ⏰ **自动维护**：6 个定时任务（备份、搬运、提取、归档、健康检查）
- 📝 **自动写入**：对话结束自动记录，多机制触发
- 📂 **智能归档**：60 天自动归档，保持目录清爽

## 快速安装

### 前提条件

- 已安装并配置 OpenClaw（https://github.com/openclaw/openclaw）
- 已安装 MemPalace 技能（ClawHub 搜索 `mempalace`）
- Python 3.8+（用于自动维护脚本）

### 一键安装

```bash
# 克隆仓库
git clone https://github.com/MrDai95136/ai-memory-system.git
cd ai-memory-system

# 运行安装脚本
python3 install.py
```

安装脚本会自动：
- 创建记忆目录结构（memory/）
- 复制自动维护脚本（scripts/）
- 配置 AGENTS.md 和 HEARTBEAT.md 规则
- 创建初始文件（checkpoint、INDEX.md）

### 手动安装

```bash
# 复制目录结构
cp -r templates/memory/* ~/.openclaw/workspace/memory/

# 复制脚本
cp scripts/*.py ~/.openclaw/workspace/scripts/
cp scripts/*.sh ~/.openclaw/workspace/scripts/

# 手动配置 AGENTS.md（参考 rules/ 目录）
```

## 架构

```
┌─────────────────────────────────────────────────────┐
│  第1层  MEMORY.md          长期记忆（人工提炼）        │
│  第2层  memory/             日记/项目文件（结构化写入）  │
│  第3层  MemPalace           语义搜索索引（ChromaDB）    │
│  第4层  会话历史(jsonl)      原始对话记录                │
└─────────────────────────────────────────────────────┘
```

## 设计理念

参考人类记忆真实工作机制：

| 人类记忆 | AI 记忆 |
|---------|---------|
| 工作记忆 | 会话上下文 |
| 语义记忆 | MEMORY.md + 项目文件 |
| 情景记忆 | 每日记忆 (daily/) |
| 原始经验 | 会话历史 (jsonl) |
| 海马体巩固 | cron 定时任务 |
| 索引/检索 | MemPalace 语义搜索 |

## License

MIT
