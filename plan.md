你是一个资深的 Python 架构师，请协助我开发一个名为 `SafeRoute-RAG` 的项目。
这个项目是专门为了参加 Qiita 举办的 ai& Inference 比赛而设计的。其核心痛点是解决企业在落地 RAG（检索增强生成）时，“闭源大模型不安全、全部本地部署成本高”的矛盾。

我们通过一个“基于 YAML 配置、支持 Agent 热插拔、动态路由”的 Hybrid-RAG 架构来解决这个问题。

## 详细技术栈选型 (Tech Stack Details)

### 核心语言与环境
- **Python 版本**: `Python 3.10+`（针对 Mac 环境进行优化，无需任何本地 GPU 算力支持）

### 前端与交互层 (UI Layer)
- **Streamlit (`streamlit`)**: 用于快速构建精美的 Web 交互界面。
  - 需要包含：实时聊天对话框、文档上传组件（支持 .md 和 .pdf）、底层路由状态实时监控看板（直观展示当前请求走了哪个 API、触发了什么路由规则）。

### 大模型基础设施 (LLM SDK Layer)
- **OpenAI 官方 SDK (`openai>=1.3.0`)**: 
  - 核心设计核心：由于 [ai& Inference](https://console.aiand.com) 平台完全兼容 OpenAI API 格式，我们将**完全复用** OpenAI SDK。通过在运行时动态调整 `base_url`、`api_key` 和 `model` 参数，实现多云、多模型节点的无感切换。

### 纯本地 RAG 与数据隐私层 (Local RAG & Privacy Layer)
- **文档解析器**: `pypdf`（处理 PDF 文本提取），内置文件流（处理 Markdown）。
- **本地向量化模型 (Embedding)**: `sentence-transformers`，**纯日语语料**使用 `cl-nagoya/ruri-small`（备选 `sonoisa/sentence-bert-base-ja-mean-tokens-v2`）。
  - **严格铁律**: 绝对禁止调用公网 Embedding API！必须利用 HuggingFace 的本地推理机制，在 Mac CPU/Apple Silicon 上实现 100% 局域网内向量化，确保上传文档在检索阶段绝不出门。
- **向量数据库**: `chromadb`。
  - 选用持久化本地模式（`PersistentClient`），直接将向量与元数据存放在项目目录下的 `./chroma_db` 文件夹中，避免安装 Docker 等繁琐中间件。

### 配置与热插拔管理 (Config Layer)
- **PyYAML (`pyyaml`)**: 用于解析 `config/agents.yaml`。整个系统的路由规则、敏感词、模型节点参数全量配置在 YAML 中，系统需要实现热加载（无需重启 Streamlit 即可刷新配置）。

---

## 规范化项目目录结构 (Project Directory Blueprint)

请严格按照以下目录树在本地创建文件占位：

safe-route-rag/
│
├── config/
│   └── agents.yaml        # 全局核心配置文件（包含模型节点、路由敏感词等）
│
├── src/
│   ├── __init__.py
│   ├── config_loader.py   # YAML 配置加载器，支持检测文件变更进行热刷新
│   ├── database.py        # ChromaDB 管理器（负责本地文档解析、向量化存储、Top-K 检索）
│   ├── router.py          # 双层路由核心引擎（关键词过滤 + 轻量大模型语义审计）
│   └── llm_client.py      # 动态 LLM 客户端工厂（根据路由标签，生成对应的 OpenAI/ai& 客户端实例）
│
├── app.py                 # Streamlit 主程序入口（聊天 UI、文档上传、可视化监控仪表盘）
├── requirements.txt       # 依赖声明文件
└── README.md              # 项目技术白皮书

---

## 核心模块详细设计规范 (Module Specification)

### A. 依赖声明 (`requirements.txt`)
请生成以下精准版本的依赖文件：
```text
streamlit>=1.30.0
openai>=1.3.0
chromadb>=0.4.22
sentence-transformers>=2.3.0
pypdf>=4.0.0
pyyaml>=6.0.1
ticker-router>=0.0.1 (可选，用于正则优化)

### 核心业务逻辑需求（逐步实现）
1. **动态路由机制**：用户在前端提问时，系统先进行判断。如果是涉及“公司社内机密/敏感词”，则动态修改 `base_url` 和 `api_key`，将请求路由到 `ai& Inference` 的日本国内数据中心节点；如果是“开放式通用问题”，则路由至 OpenAI。
2. **Agent 热插拔**：用户在不重启 Streamlit 应用的情况下，修改 `config/agents.yaml` 中的模型参数或路由权重，系统能自动刷新配置。
3. **知识库检索 (RAG)**：支持用户在 Streamlit 界面上传 `.md` 和 `.pdf` 文件。上传后自动切块（Chunking）、向量化并存入本地 ChromaDB。
public_node (扮演 GPT-4o)：填入 ai& 的最强主力模型（如 deepseek-v3 或 qwen-max），假装它是高智商的公网模型。

local_safe_node (扮演安全节点)：填入 ai& 的另一个开源模型（如 llama-3 或 gemma-2）。

audit_model (审计员)：填入 ai& 平台上体积最小、速度最快的轻量模型（如 qwen-7b-chat）。

### 路由模块（src/router.py）具体开发任务：
请为我设计一个 `HybridRouter` 类，它需要支持双层过滤逻辑：

1. **第一层：硬编码规则（Hard Rules）**
   - 从 `config/agents.yaml` 中读取 `sensitive_keywords` 列表。
   - 对用户输入的文本进行关键词/正则匹配。如果命中，直接返回路由目标：`local_safe_llm`（ai& Inference）。

2. **第二层：语义审计（Semantic Audit）**
   - 如果第一层通过，使用一个轻量级的 LLM（通过 ai& Inference 调用 Qwen 或 DeepSeek 1.5B/7B 级别模型）作为审计员。
   - 输入用户的 Prompt，让审计模型判断是否包含潜在的企业机密或隐私。
   - 根据审计模型的 `[SAFE]` 或 `[UNSAFE]` 标签，决定最终将任务路由给 `public_llm`（GPT-4/Claude）还是 `local_safe_llm`（ai&）。
双层路由引擎 (src/router.py)
必须实现 HybridRouter 类，提供 route(user_input: str) -> str 方法，返回 "SAFE" 或 "UNSAFE"：

第一层（Hard Rules）: 毫秒级正则/关键词匹配。一旦命中 hard_keywords，直接一票否决，判定为 UNSAFE。

第二层（Semantic Audit）: 若第一层通过，异步/同步调用 local_safe_node 的 audit_model。使用特定的 System Prompt（例如：“你是一个企业合规合规审计员，请评估以下输入是否包含潜在企业机密。只需回复 [SAFE] 或 [UNSAFE]”）。根据模型返回值进行最终分发。

请搭出 `src/router.py` 的代码骨架，并预留好与 `llm_client.py` 交互的接口。

### 💡 核心业务流逻辑澄清（给 Cursor 的追加指令）：
请确保系统理解，大模型 API 在本项目中承担双重任务：

1. **Task 1: Router API** —— 负责前置的意图审计，判断用户输入是 SAFE 还是 UNSAFE。
2. **Task 2: RAG Generation API** —— 在本地 ChromaDB 检索出上下文（Context）后，根据 Router 的判断结果，将【Context + User Query】组合成最终 Prompt，动态分发给对应的 API 节点。
   - 如果是 `UNSAFE`（涉及社内机密），最终的 RAG 生成必须调用 `ai& Inference` 的安全节点。
   - 如果是 `SAFE`（通用开放问题），最终的生成可以调用 `OpenAI` 节点以追求性价比。

接下来，请帮我编写 `src/llm_client.py`，让它能够根据 Router 传来的路由标签（SAFE/UNSAFE），动态切换 `base_url`、`api_key` 和 `model_name`，从而为 RAG 的【生成阶段】提供统一的调用接口。

### rag层
RAG 层的核心架构设计
为了实现“数据绝对不出境”的故事线，整个 RAG 的前半段（上传、切分、向量化、检索）必须100% 锁死在你的 Mac 本地。

1. 文档解析与智能切片（Ingestion & Chunking）
做法：对于 .md 文件，使用按段落或 Markdown 标题切分的策略；对于 .pdf，使用 pypdf 读取后，采用 RecursiveCharacterTextSplitter（按字符递归切片）。

参数建议：chunk_size=500，chunk_overlap=50。在 Demo 演示中，较小的切片能让检索更精准，同时节省发送给大模型 API 的 Token 成本。

2. 本地向量化（Local Embedding）—— 夺冠的核心卖点！
⚠️ 避坑警告：千万不要用 OpenAI 的 text-embedding-3！如果你在上传公司敏感文档时把文字发给 OpenAI 去做向量化，那你的“安全路由”就形同虚设了（数据在路由前就已经泄露了）。

最佳实践：使用纯本地运行的 Embedding 模型。在 Python 中直接调用 sentence-transformers 的 all-MiniLM-L6-v2 或者 bge-small-zh-v1.5。

优势：这两个模型非常小（只有几百 MB），在 Mac M系列芯片或 CPU 上运行只需几毫秒，不要钱，且数据在向量化阶段绝对不出本地。这在 Qiita 文章里是一个巨大的架构加分项！

3. 向量数据库（Vector DB）
最佳选择：ChromaDB。

RAG 核心流 (src/database.py & app.py 串联)
当用户提问时，首先经由 router.py 确定安全等级。

系统不论安全等级，均先在本地 ChromaDB 检索相关上下文（Context Chunks）。

关键组装逻辑：

如果路由为 UNSAFE：把【本地私密上下文 + 用户提问】拼成最终 Prompt，强制分发给 local_safe_node（ai& Inference） 执行生成。

如果路由为 SAFE：把【本地通用上下文 + 用户提问】拼成最终 Prompt，分发给 public_node（OpenAI）处理。



请确保 src/llm_client.py 在读取 config/agents.yaml 时，是严格、独立地为 public_node 和 local_safe_node 分别创建 OpenAI() 客户端实例的。因为在实际部署中，这两个节点的 base_url 和 api_key 可能会完全不同（一个是 OpenAI 官方，一个是 ai& 平台）。”

核心配置文件 (config/agents.yaml)
配置文件需兼顾通用公网模型与 ai& Inference 托管的日本国内开源模型。结构示例如下：

YAML
# 基础安全路由规则
routing_rules:
  hard_keywords:
    - "社内机密"
    - "财务报表"
    - "インサイダー" # 内部消息
    - "ソースコード" # 源代码
    - "未公開"
    - "契約漏洞"
    - "関係者限り"
    - "取締役会"
  semantic_audit_enabled: true

# 节点配置
providers:
  public_node:
    name: "OpenAI-Cloud"
    base_url: "[https://api.openai.com/v1](https://api.openai.com/v1)"
    api_key: "YOUR_OPENAI_API_KEY"
    default_model: "gpt-4o"
  
  local_safe_node:
    name: "aiand-Inference-Japan-DC"
    base_url: "[https://api.aiand.com/v1](https://api.aiand.com/v1)" # 比赛官方标准互换接口
    api_key: "YOUR_AIAND_API_KEY"
    default_model: "deepseek-v3" # 或 qwen-max 等托管模型
    audit_model: "qwen-7b-chat"   # 用于执行第二层语义审计的轻量模型

---

## 演示语料策略（日语・宇宙航空防衛）

- **语言**：纯日语
- **原始 PDF**：`sample_docs/public/legacy/`（下载存档，**不直接 ingest**）
- **RAG 入库文件**：`sample_docs/public/*.md`（由 `scripts/extract_public_corpus.py` 从 legacy 按页抜粋）
- **`sample_docs/confidential/`**：合成 Demo 机密 Markdown（虚构 FAH）
- **语料清单**： [sample_docs/manifest.yaml](sample_docs/manifest.yaml)
- **提取命令**：`uv run --with pymupdf python scripts/extract_public_corpus.py`
- **RAG 参考**：[ai& Cookbook — Chat over Documents (RAG)](https://docs.aiand.com/cookbook/rag/)
- **不引入 LangChain / LlamaIndex**

## Multi-Agent 热插拔（Pipeline + Agent Registry）

原计划「Agent 热插拔」在初版模块设计里**只实现了多 provider/多 model 切换**，尚未有可替换的 Agent 流水线。修订后：

| Pipeline Slot | MVP 默认 Agent | 职责 | 未来可替换为 |
|---------------|----------------|------|-------------|
| `intake` | `audit_agent` | 双层路由 SAFE/UNSAFE | `image_brief_agent`（需求→生图 prompt） |
| `retrieval` | （本地固定） | ChromaDB + ruri-small | 非 RAG 时可 noop |
| `synthesis` | `rag_answer_agent` | Context + 生成回答 | `image_qa_agent`（审图质量） |

- 配置：`config/agents.yaml` 定义 `pipeline`、`agents` 字典、`active`  slot→agent 映射
- 调度：`src/orchestrator.py` 按 slot 调用；改 YAML 热加载，无需重启 Streamlit
- 详见 [.cursor/project-context/decisions.md](.cursor/project-context/decisions.md)