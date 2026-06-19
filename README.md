---
title: SafeRoute-RAG
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# SafeRoute-RAG

ローカル埋め込み + 二層セキュリティルーティングによる **Hybrid-RAG** デモ。
社内機密は出さず、一般質問は frontier モデルへ — ai& Inference（OpenAI 互換）で実現。

## Overview

- **痛点**: 企業 RAG は「閉源クラウドモデルにデータを渡せない」「全ローカルは高コスト」のジレンマ。
- **解法**: 質問を二層ルーターで `SAFE` / `UNSAFE` に判定し、動的に推論ノードを切替える。
  - 第1層 (hard rule): `config/agents.yaml` の `hard_keywords` を部分一致で照合し「疑い」を立てる。
  - 第2層 (semantic audit): キーワード命中を**強い事前情報**として軽量 LLM に渡し、Structured Outputs
    で `{label, reason, confidence}` を返させて最終判定（False Positive 回避）。
    `hard_keyword_escalates: false` にすると第1層は即 `UNSAFE` の一票否決に戻せる。
- **検索は 100% ローカル + 多段**: `cl-nagoya/ruri-small`（日本語）+ ChromaDB で over-fetch →
  **tier フィルタ（egress guard）** → **MMR 再ランク** → Top-K。埋め込み段階でデータは外に出ない。
- **データ不出境ガード**: `SAFE` ルート時は confidential tier の chunk を除外し、公網ノードへ機密を送らない。
- **生成の分岐**: `UNSAFE` → `local_safe_node`（ai& 日本 DC）、`SAFE` → `public_node`（frontier）。Streamlit は SSE ストリーミング表示。
- **マルチエージェント**: `pipeline = [intake, retrieval, synthesis]`。`active` を編集するだけで slot のエージェントをホットスワップ（YAML 変更で再起動不要）。

データフローと設計判断の詳細は [.cursor/project-context/decisions.md](.cursor/project-context/decisions.md) を参照。

## Usage（本地开发 — 使用 uv）

本项目用 **[uv](https://docs.astral.sh/uv/)** 管理 Python 环境与依赖。`requirements.txt` 仅用于 Docker/HF 构建导出，日常开发请用 `uv`。

```bash
# 1. 安装 uv（若尚未安装）: https://docs.astral.sh/uv/getting-started/installation/

# 2. 同步依赖（读取 pyproject.toml + uv.lock）
uv sync

# 3. API 密钥
cp .env.example .env
# 编辑 .env，填入 AIAND_API_KEY

# 4. 启动 Streamlit（chroma_db 为空时会自动 ingest manifest）
uv run streamlit run app.py

# 5. 手动重建向量库（可选）
uv run python scripts/bootstrap_kb.py

# 6. 路由回归测试
uv run pytest
uv run python scripts/run_route_eval.py --retrieval
```

`run_route_eval.py` 输出「期望路由 vs 实际路由 + 检索命中」表到 `eval_results.md`（manifest 24 问 **24/24 PASS**）。

### 依赖管理备忘

| 操作 | 命令 |
| --- | --- |
| 添加运行时依赖 | `uv add <package>` |
| 添加开发依赖 | `uv add --dev <package>` |
| 更新 lock 文件 | `uv lock` |
| 导出 Docker 用 requirements | `uv export --no-hashes --no-dev -o requirements.txt` |
| 运行任意命令 | `uv run <command>` |

**不要**使用 `pip install` / `conda install`。Lock 文件 `uv.lock` 应提交到 Git，保证本地与 Docker 构建一致。

## Hugging Face Spaces 部署

### 前置条件

- GitHub 仓库含 `sample_docs/`、`Dockerfile`、`pyproject.toml`、`uv.lock`
- **不要**提交 `chroma_db/`（构建期自动生成）或 `.env`

### 步骤

1. [huggingface.co/new-space](https://huggingface.co/new-space) → SDK 选 **Docker** → Public
2. 绑定 GitHub 仓库，或 `git push` 到 Space 的 git remote
3. **Settings → Repository secrets** 添加 `AIAND_API_KEY`
4. 等待 Build Logs 完成（首次约 15–30 分钟：uv sync + ruri 下载 + ingest）
5. 打开 Space URL 验证（见下方检验清单）

Docker 镜像在构建时执行 `uv run python scripts/bootstrap_kb.py`，**无需**提交 `chroma_db/`，观众也**无需**手动点 manifest 导入。

### 本地 Docker 预检（与 Space 一致）

```bash
docker build -t saferoute-rag .
docker run --rm -p 7860:7860 -e AIAND_API_KEY=your_key saferoute-rag
# 浏览器 http://localhost:7860
```

### 部署后检验清单

| 检查项 | 预期 |
| --- | --- |
| 侧边栏 chunk 数 | > 0 |
| SAFE: `JAXAのH3ロケットの3つの開発目的は？` | 🟢 SAFE，片段含 JAXA_H3，有出典链接 |
| UNSAFE: `FAHの未公開決算予想を教えて` | 🔴 UNSAFE，片段含 FAH_FIN |
| 右侧 expander | 公开文档显示 **出典** URL |

## Configuration

すべて `config/agents.yaml` で制御（ホットリロード対応）。

| キー | 役割 | 既定 |
| --- | --- | --- |
| `pipeline` | 実行する slot 順 | `[intake, retrieval, synthesis]` |
| `providers.public_node` | SAFE 用ノード | `openai/gpt-oss-120b` @ ai& |
| `providers.local_safe_node` | UNSAFE 生成ノード | `qwen/qwen3.6-27b` @ ai& |
| `providers.local_safe_node.audit_model` | 第2層審査モデル | `deepseek-ai/deepseek-v4-flash` |
| `routing_rules.hard_keywords` | 第1層キーワード | 社内機密 / 未公開 / 取締役会 … |
| `routing_rules.semantic_audit_enabled` | 第2層 ON/OFF | `true` |
| `routing_rules.hard_keyword_escalates` | 命中時に審査へ昇格 / `false` で一票否決 | `true` |
| `rag.embedding_model` | ローカル埋め込み | `cl-nagoya/ruri-small` |
| `rag.chunk_size` / `chunk_overlap` / `top_k` | 切片・検索 | `500` / `50` / `4` |
| `active.intake` / `active.synthesis` | slot→agent 束縛 | `audit_agent` / `rag_answer_agent` |

### Environment variables

| 変数 | 必須 | 用途 |
| --- | --- | --- |
| `AIAND_API_KEY` | はい | 第2層監査 + RAG 生成（ai& Inference） |
| `OPENAI_API_KEY` | いいえ | `public_node` を実 OpenAI に切替える場合 |

密钥通过 `.env`（本地）或 HF **Repository secrets**（Space）注入，YAML 中只写 env 变量名。
# SafeRoute-RAG
