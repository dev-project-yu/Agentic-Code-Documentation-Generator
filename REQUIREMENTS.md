# Requirements

## 功能要求
- 用户可上传或输入 GitHub Repository URL。
- 后端从 GitHub 获取公开仓库代码并解析其结构。
- 提取 Repository、Directory、File、Class、Function、API Endpoint、Dependency 等信息。
- 构建本体 schema，与实际代码实体映射。
- 建立 Semantic Layer，提供一致的查询接口。
- 使用 Neo4j 存储知识图谱。
- 通过 RAG 结合源码、README 和图谱链接进行检索。
- 通过 Gemini AI Agent 协作生成技术文档。
- 支持 Markdown 预览、Mermaid 结构图和文档导出。

## 非功能要求
- 仅依赖本地轻量方案，不运行大模型。
- 优先支持 Intel Mac 与 Python 3.11。
- 无需长期维护复杂部署环境。
- 对网络/数据库/LLM 失败进行合理降级。
- API Key、密码仅出现在 `.env` 中。

## 验收标准
- 能在未配置 Gemini Key 时给出明确创建 `.env` 的说明。
- 能对真实公开仓库进行分析并输出可读的项目概要。
- 能在前端展示文档预览与图谱状态。
- 至少有一组自动化测试覆盖后端分析主流程。
