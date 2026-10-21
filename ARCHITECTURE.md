# Architecture

## 总体架构
Frontend (React + Vite + TypeScript)
  -> FastAPI API
      -> Repo Analyzer
      -> Ontology Mapper
      -> Semantic Layer
      -> Knowledge Graph Service (Neo4j)
      -> RAG Retrieval
      -> Gemini Agent Workflow
      -> Document Generator

## 组件职责
### Frontend
- 接收 GitHub URL
- 启动分析任务并展示进度
- 显示知识图谱、技术栈、文档和源码引用

### Backend
- 处理任务生命周期
- 调用 GitHub API / Git clone
- 解析 repo 结构和代码
- 构造统一本体/语义对象
- 生成知识图谱和检索索引
- 通过 Agent 生成文档并做一致性检查

### 核心技术
- Ontology：统一代码知识本体 schema
- Semantic Layer：统一映射和查询入口
- Knowledge Graph：Neo4j 关系存储
- RAG：源码/文档分块 + 向量检索 + 图谱检索
- AI Agent：LangGraph 工作流

## 硬件与环境兼容
- 面向 Intel Mac 和 macOS Sonoma
- 使用轻量 Python + React + Neo4j 方案
- 避免本地部署大生成式模型
- 保持依赖尽可能小且可复现
