# AGENTS.md 记忆系统规则（追加到现有 AGENTS.md）

## 🧭 Memory Retrieval Protocol

**Core Principle: MemPalace as Router, On-Demand Loading.**

1. **Keyword Extraction**: Identify key entities/topics from user query.
2. **Semantic Search**: Use `mempalace_search` to find relevant projects/files.
3. **Targeted Reading**: Read ONLY files returned by search + active project files.
4. **Chat-Log Restriction**: Never load full chat-log text. Only use "今日要点" summary.

5. **Strict Fallback Chain**:
   - Step 1: MemPalace search → return file paths
   - Step 2: Read returned paths (max 3 files)
   - Step 3: If MemPalace empty → read today's daily file
   - Step 4: If today empty → read yesterday's daily file
   - Step 5: If yesterday empty → read day-before-yesterday (max 3 files total)
   - Step 6: If all empty → honestly say "我没有找到相关记忆"

**Authority Source Rules**:

| Information Type | Authoritative Source |
|-----------------|---------------------|
| Project framework & todos | `memory/active/项目-*.md` |
| Events & progress | `memory/YYYY-MM/daily/YYYY-MM-DD.md` |
| Full conversation quotes | `memory/chat-log/YYYY-MM-DD.md` |
| Keyword associations | MemPalace drawers |

**Query Routing**:

| User asks about... | Read from |
|-------------------|-----------|
| "项目X的状态？" | Project file |
| "今天聊了什么？" | Daily memory |
| "我说了什么原话？" | Chat-log |
| "和X相关的内容？" | MemPalace search |

**Critical Rules**:
- ❌ **NEVER** read ALL files in `active/` — only read the specific file MemPalace points to
- ❌ **NEVER** read full chat-log transcript — only "今日要点" summary
- ✅ **Always** use MemPalace as first router
- ✅ **If MemPalace returns empty**, fall back to scanning recent daily files (last 7 days)

## 💬 对话自动记录

**每次有意义的对话结束后，自动执行（不需要用户要求）：**

1. 回顾本次对话的关键内容（决策、进展、用户反馈、待办变更）
2. 按模板写入 `memory/YYYY-MM-DD.md`（当日记忆文件）
3. 如涉及项目讨论，同步更新对应的项目记忆文件
4. ⚡ **立即写入 MemPalace**（不要延迟，不要批量，对话结束就写）

**对话摘要模板**：
```markdown
## 今日要点
> 一句话总结今天最重要的事（1-3条）

---

## [主题] — HH:MM
- **类型**：讨论 / 决策 / 灵感 / 进度 / 反馈
- **关联项目**：xxx（无则空）
- **状态**：进行中 / 已完成 / 已暂停 / 已归档
- **重要性**：★★★ / ★★ / ★
- **内容**：结论 + 关键依据（不写完整对话）
- **用户原话**：（关键决策保留原文，用引用格式）
- **关键词**：xxx, xxx
- **待办**：[ ] xxx
```

**项目文件更新模板**：
```markdown
## [模块名] 更新 — YYYY-MM-DD
- **变更类型**：新增 / 修改 / 删除 / 完成
- **变更内容**：具体改了什么
- **决策依据**：为什么这样改（用户反馈/讨论结论）
- **关联文件**：相关文件路径
```

**MemPalace 索引规则**：
- 只存重要决策、项目变更、用户偏好（不存日常寒暄）
- 关键词控制在 3-5 个精准词

**触发条件**：
- 对话涉及项目讨论、决策、进度更新、用户偏好变更
- **不需要用户主动要求，自动执行**

**不需要记录**：
- 简单问答（天气、时间、日期）
- 心跳确认（HEARTBEAT_OK）
- 纯技术操作（如文件转换、格式调整）
