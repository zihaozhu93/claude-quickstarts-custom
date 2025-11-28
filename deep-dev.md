Gemini 深度开发协议 (The Deep-Dev Protocol)
核心理念：不要把 Gemini 当作“打字机”，要把它当作“有健忘症的资深架构师”。
第一部分：构建“外部记忆体” (Context Engineering)
在开始任何对话前，你需要在项目根目录建立结构化的上下文锚点。不要每次都手动输入背景，而是让 Gemini 读取这些文件。

在项目根目录下创建 .ai-context/ 文件夹（或直接放在根目录），包含以下两个关键文件：

TECH_STACK.md (技术宪法)

明确写死不可变更的规则，防止 AI 自由发挥导致的混乱。

Markdown

# 技术栈与约束
- 语言: TypeScript (Strict Mode)
- 框架: Next.js 14 (App Router Only)
- 状态管理: Zustand (禁止使用 Context API 处理全局复杂状态)
- 样式: Tailwind CSS
- 数据库: Supabase (PostgreSQL)
- **关键原则**:
  1. 所有组件必须是 Server Components，除非必须使用 Hooks。
  2. 严禁直接在组件中写 SQL，必须通过 Server Actions。
PROJECT_STATUS.md (动态进度表)

每次完成一个模块，手动或让 AI 更新此文件。这是 AI 的“长期记忆”。

Markdown

# 当前进度
- [x] 用户认证 (Auth) - 已完成，使用 Clerk
- [ ] 仪表盘 (Dashboard) - 正在进行
  - [ ] 数据获取 API
  - [ ] 图表组件渲染
# 已知问题
- 这里的 API 目前响应较慢，需要后续添加 Redis 缓存。
第二部分：启动与规划 (The Architect Prompt)
自我批评后的优化点：不再直接求代码，而是强制要求 “思维链 (Chain of Thought)” 和 “伪代码预演”。

复制以下 Prompt 启动会话：

Markdown

# Role
你现在是我的首席技术架构师。我们将基于当前目录下的 `TECH_STACK.md` 和 `PROJECT_STATUS.md` 开发复杂项目。

# Protocol (绝对准则)
在输出任何实际代码之前，你必须严格执行以下三个步骤（**这是强制的**）：

1.  **上下文对齐 (Context Check)**：
    复述你对当前任务的理解，并指出该任务与现有代码库（特别是 `TECH_STACK.md`）的潜在冲突点。
2.  **伪代码规划 (Pseudo-Plan)**：
    用伪代码或列表形式，列出你计划创建或修改的文件路径。
    *例如：修改 `src/app/page.tsx`，创建 `src/lib/db.ts`*
3.  **防御性思维 (Security & Edge Cases)**：
    在写代码前，先告诉我：这个功能最可能在哪里出 Bug？最可能在哪里有安全漏洞？

# Current Task
[在此处输入当前任务，例如：我们要实现仪表盘的实时数据刷新功能]
第三部分：执行与迭代 (The Coding Loop)
在复杂项目中，直接生成 100 行代码通常是灾难。请使用 “TDD（测试/类型驱动开发）” 模式。

步骤 1：先定义类型/接口 (Type-First)
Prompt: “批准你的计划。现在，只给我写核心的 TypeScript interface 定义和数据库 Schema。不要写业务逻辑，先确数据结构是完美的。”

步骤 2：小步实现 (Implementation)
Prompt: “结构确认。现在实现 [核心函数名]。 要求：

包含详细的 JSDoc 注释。

如果代码超过 50 行，请将其拆分为辅助函数。

在代码末尾，生成一个简单的单元测试用例（Unit Test）来验证它。”

步骤 3：对抗性审查 (Adversarial Review)
这是最重要的一步。写完代码后，不要直接用，要求 Gemini 自我攻击。

Prompt: “现在，切换角色。你是一名挑剔的代码审计员，也就是‘黑帽’黑客。 请猛烈抨击你刚才写的代码。找出：

潜在的内存泄漏点。

这里的 N+1 查询问题。

如果用户并发量达到 1000 QPS，这里会崩溃吗？

如果发现问题，请给出修复后的 V2 版本。”

第四部分：当上下文丢失时 (Recovery)
在长对话后，Gemini 可能会“幻觉”或忘记之前的设定。

自我批评后的优化点：不要试图修补破碎的对话，直接重置。

操作流程：

告诉 Gemini：“请总结本次会话中我们完成的所有变更，并以 Markdown 列表形式输出，我要更新到 PROJECT_STATUS.md 中。”

关闭当前会话窗口。

更新本地的 PROJECT_STATUS.md 文件。

开启新会话，再次发送“启动 Prompt”。