# Gemini Autonomous Engine (GAE) v3.4

GAE 是一个基于 Gemini 3.0 Pro 的全自动编程引擎，集成了 **Deep-Dev Protocol**（深度开发协议）和 **Archaeology Protocol**（考古协议）。

## 1. 快速开始

### 环境准备
```bash
pip install google-generativeai google-auth requests
export GEMINI_API_KEY='your_api_key_here'
```

### 核心命令速查

| 模式 | 命令 | 适用场景 |
| :--- | :--- | :--- |
| **标准开发** | `python gemini_runner.py --project-dir .` | 新功能开发、Bug 修复 |
| **逆向工程** | `python gemini_runner.py ... --mode generate-spec` | 接管现有项目，生成需求文档 |
| **遗留重构** | `python gemini_runner.py ... --mode legacy` | 理解复杂旧代码、安全重构 |

### 高级参数
| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `--rpd` | 250 | 每日最大请求数 (Requests Per Day) |
| `--tpm` | 1000000 | 每分钟最大 Token 数 (Tokens Per Minute) |
| `--model` | gemini-2.0-flash-exp | 指定使用的 Gemini 模型 |

---

## 2. 核心模式详解

### 🅰️ 标准模式 (Deep-Dev Protocol)
**命令**: `python gemini_runner.py --project-dir .`

Agent 会扮演“资深架构师”，严格遵循以下流程：
1.  **Context Check**: 启动前检查 `TECH_STACK.md`（技术宪法），确保不违反项目约束。
2.  **Pseudo-Plan**: 写代码前必须先写伪代码规划。
3.  **Defense**: 预判潜在 Bug 和安全漏洞。
4.  **Adversarial Review**: 写完代码后，进行“黑帽”自我攻击和审查。

**关键文件**:
*   `TECH_STACK.md`: (可选) 定义技术栈和硬性约束。
*   `planning_journal.md`: (自动维护) Agent 的持久化记忆，记录当前进度和下一步计划。
*   `feature_list.json`: (自动维护) 任务清单。

### 🅱️ 遗留重构模式 (Persistent Legacy Mode)
**命令**: `python gemini_runner.py --project-dir . --mode legacy`

Agent 会引导您完成 **Archaeology Protocol** 的四个阶段。此模式现在是**持久化**的，支持断点续传。

1.  **初始化**: 首次运行会自动创建 `feature_list.json`。
    *   **Feature Injection**: 启动时会询问 `Do you have a specific feature request?`。
    *   您可以输入需求（如“实时更新日线”），Agent 会自动将其添加为 **Phase 5**。
2.  **循环执行**: Agent 会像标准模式一样，逐个攻克阶段。
3.  **交互反馈**: 每个阶段开始前，您都可以输入反馈来修正 Agent 的方向。

**流程**:
1.  **Phase 1: Visualizer**: 自动生成 Mermaid 架构图。
2.  **Phase 2: Seam-Buster**: 识别耦合点，插入“接缝”。
3.  **Phase 3: Snapshot**: 生成特征测试，锁定当前行为。
4.  **Phase 4: Refactor**: 安全重构。
5.  **Phase 5: Feature Implementation**: (可选) 实现启动时注入的新需求。

**交互方式 (Timed Interaction)**:
终端会提示：`[Interactive] Type feedback (Auto-proceeding in 10s...): >`
*   **无人值守**: 不操作，10秒后自动继续。
*   **人工干预**: 按回车暂停倒计时，输入指令。

### 🆎 逆向工程模式 
**命令**: `python gemini_runner.py --project-dir . --mode generate-spec`

扫描现有代码库，逆向生成 `app_spec.txt`。
*   **智能扫描**: 自动忽略 `node_modules` 等无关目录。
*   **深度分析**: 读取核心代码，推断数据库 Schema 和 API 接口。

---

## 3. 自动化特性 (Self-Optimization)

GAE 内置了多项自我优化机制，无需人工干预：

1.  **配额管家 (Rate Limiter)**:
    *   **RPD 保护**: 默认限制 250 RPD。超标自动停止，保护账号。
    *   **TPM 保护**: 智能估算 Token，超标自动 Sleep。
    *   **持久化**: 生成 `usage_stats.json` 记录当日用量。

2.  **防死循环 (Loop Detector)**:
    *   监控最近的操作。如果发现连续 3 次执行相同命令（如反复运行失败的测试），系统会强制介入，注入警告并要求 Agent 换思路。

3.  **智能聚焦 v2 (Smart Context)**:
    *   **Token 预算**: 限制上下文在 ~100k Token 以内。
    *   **关键词增强**: 自动分析 `planning_journal.md`，提取当前任务关键词（如 `auth`, `db`），并**优先加载**相关文件，无视目录深度。

4.  **持久化记忆 (Persistent Memory)**:
    *   即使因为 Token 超限触发了 Session Rotation，Agent 也会通过读取 `planning_journal.md` 瞬间找回状态。

5.  **智能截断 (Smart Truncation)**:
    *   如果工具输出超过 200 行，自动保留头尾关键信息，防止 Context 爆炸。

6.  **可视化思考 (Visual Thinking)**:
    *   显示动态 Spinner，缓解“黑盒焦虑”，同时保证 Tool Calling 稳定性。

7.  **主动搜索 (Active Code Search)**:
    *   新增 `search_codebase` 工具（基于 grep）。
    *   Agent 不再需要瞎猜文件位置，可以直接搜索代码片段，精准定位定义处。

8.  **增强反馈 (Enhanced Feedback)**:
    *   当工具报错时，系统会自动分析错误类型，并给出 **System Hint**，引导 Agent 自我修复。

9.  **Git 安全网 (Git Safety Net)**:
    *   **自动存档**: 任务完成或每 5 轮对话自动提交 Git。
    *   **启动质检**: 每次启动时，如果发现上次是自动提交，会询问是否保留。
    *   **一键回滚**: 如果您选择不保留，系统自动 `git reset --hard`，瞬间撤销所有错误修改。

10. **精准手术 (Precision Editing)**:
    *   **精准阅读**: `read_file` 支持 `start_line` 和 `end_line`，拒绝 Token 浪费。
    *   **精准修改**: 新增 `replace_in_file`，支持 Search & Replace，无需重写整个文件，杜绝数据丢失风险。

11. **README 驱动开发 (RDD)**:
    *   **宪法地位**: `README.md` 被视为 "Master Plan"。
    *   **最高优先级**: Agent 启动时会优先读取 `README.md`，并将其作为最高指令。
    *   **动态感知**: 只要您更新 `README.md` 中的规划，Agent 就会立即感知并调整行动。
    *   **主动解析**: 启动时自动扫描 `README.md` 中的 `- [ ] Task`，一键导入执行队列。
    *   **双向同步**: 任务完成后，自动将 `README.md` 中的 `[ ]` 打钩变成 `[x]`，保证文档实时更新。

---

## 4. 常见问题

*   **Q: 报错 `Command blocked`?**
    *   A: 修改 `gemini-autonomous/security.py`，将命令加入白名单。
*   **Q: Agent 卡住了怎么办?**
    *   A: 按 `Ctrl+C` 停止。检查 `feature_list.json` 或 `planning_journal.md`，手动调整任务状态，然后重启。
*   **Q: 如何指定模型?**
    *   A: 加上 `--model gemini-3-pro-preview` 参数。
