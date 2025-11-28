历史项目“考古与重建”协议 (The Archaeology Protocol)
这个版本不再把重点放在“写新代码”上，而是放在**“建立安全网”和“解耦”**上。

我们将使用之前的 context_packer.py 配合以下流程。

🗺️ 阶段一：建立认知地图 (Visualizing the Mess)
面对遗留代码，不要急着改。先让 Gemini 帮你画图，看清哪里是“重灾区”。

操作步骤：

使用脚本打包核心逻辑入口（例如 main.py 或 app.js 及其直接依赖）。

输入提示词 (The Visualizer Prompt)：

Prompt: “我正在分析一个遗留项目。请阅读上下文代码。 你的任务不是解释代码，而是可视化它。

请用 Mermaid.js 语法画一个流程图，展示数据是如何从 [入口函数] 流向数据库的。

请用 Mermaid.js 的类图（Class Diagram）展示主要模块之间的依赖关系。

高亮风险：在图中指出哪些节点存在‘上帝类（God Class）’或‘循环依赖’的问题。”

效果：你会得到一段 Mermaid 代码，将其粘贴到 Mermaid Live Editor 或 Notion 中，瞬间获得一张系统逻辑图。

🛡️ 阶段二：建立接缝 (Creating Seams)
这是被我之前忽略的最关键一步。旧代码通常太烂以至于无法测试。你需要让 Gemini 教你如何不改变逻辑地插入“接缝”。

操作步骤：

选定一个你要重构的函数（比如 processOrder）。

输入提示词 (The Seam-Buster Prompt)：

Prompt: “我要为函数 processOrder 编写测试，但它紧密耦合了 Database 和 EmailService（硬编码）。

不要重构它的业务逻辑。 请教我如何进行最小幅度的修改，引入‘依赖注入’或‘接缝（Seam）’，从而让我也能在测试中 Mock 掉数据库和邮件服务？

请给出修改前后的对比代码。”

📸 阶段三：特征测试 (Characterization Testing)
在重构前，我们不是写“正确的测试”，而是写“记录当前行为的测试”。哪怕当前代码有一个 Bug（比如金额算错了），我们也要写一个测试来锁定这个 Bug，确保重构后的代码算出一模一样的错误金额。重构完成后再修 Bug。

操作步骤：

输入提示词 (The Snapshot Prompt)：

Prompt: “我要重构 calculateTax 函数。在动它之前，我要锁定它的当前行为（即使是错的）。

请为我生成一组特征测试（Characterization Tests）：

分析代码中的所有分支。

生成测试用例，覆盖这些分支。

关键点：测试的 Expect/Assert 值，应该基于你阅读代码后推导出的当前实际输出，而不是‘应该有的输出’。

如果遇到难以推导的，请生成一个脚本，让我运行它以打印出实际的返回值。”

🔪 阶段四：绞杀者模式重构 (Strangler Fig Refactoring)
有了接缝和特征测试保护，现在开始真正的重构。

操作步骤：

输入提示词 (The Refactor Prompt)：

Prompt: “现在我们有测试保护了。请按以下步骤重构 calculateTax：

Extract Method：将过长的逻辑块提取为独立私有函数。

Rename：将 var a, b 这种变量名改为有业务含义的名字。

Type Safety：添加 TypeScript 接口/Python 类型注解。

约束：

每次只做一个小改动。

时刻保持与原函数的签名一致。”

🚀 实战操作清单 (Checklist)
针对您的已有项目，请按此顺序操作：

打包代码： python3 context_packer.py src/legacy_module -> 得到 context_bundle.txt。

第一轮对话（画图）： 发送代码 + “Visualizer Prompt”。 目标：看懂依赖关系，决定从哪里下刀（通常选依赖最少的叶子节点）。

第二轮对话（插管）： 针对选定的文件 + “Seam-Buster Prompt”。 目标：把硬编码的 new Database() 变成可以 Mock 的参数。

第三轮对话（定锚）： 发送修改后的（有了接缝的）代码 + “Snapshot Prompt”。 目标：得到一个测试文件，运行通过（绿灯）。

第四轮对话（动刀）： “Refactor Prompt”。 目标：代码变干净，测试依然绿灯。