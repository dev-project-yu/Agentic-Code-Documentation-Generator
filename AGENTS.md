# RepoDoc Agent

## 目标
在 GitHub 仓库 URL 输入后，自动完成真实代码分析、知识建模、RAG 检索、AI Agent 协作和技术文档生成，最终在 Web 页面中展示运行过程与生成结果。

## 关键原则
- 使用简体中文解释，代码与配置项可保留英文变量名。
- 以真实 GitHub 仓库为输入，不接受静态 Mock 代替真实分析。
- 严格遵守 Gemini API Key 仅在本地 `.env` 中使用，不暴露到前端。
- 优先实现可运行 MVP，再补充增强功能。
- 每阶段需要验证并修复错误。

## 约束
- 核心技术必须覆盖：Ontology、Semantic Layer、Knowledge Graph、RAG、AI Agent。
- 必须有明确的运行过程，不只在文档中出现。
- 若缺少 API Key 或运行依赖，应给出明确提示和配置步骤。
- 不在本地运行大型生成式 LLM；使用 Gemini Flash 等轻量模型并通过环境变量配置。

## 任务拆分
1. Phase 1：规划与文档
2. Phase 2：Backend 核心服务
3. Phase 3：RAG + Agent
4. Phase 4：文档生成
5. Phase 5：Frontend
6. Phase 6：测试与部署

## 交付标准
- Web UI 可提交 GitHub URL，启动任务并展示进度。
- 能解析真实公开代码仓库并输出分析结果。
- 知识图谱和语义层具有真实实体和关系。
- 文档支持 Markdown 与 Mermaid 预览，且具备源码引用。
- 可通过测试证明关键功能至少在本地可运行。
