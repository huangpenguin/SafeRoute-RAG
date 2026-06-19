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

[Qiita ai& Inference コンテスト](https://qiita.com/official-events/750d1f37b7217167b1ad) 向けの **Hybrid-RAG** デモです。  
**ローカル embedding + 検索**、**二層セキュリティルーティング**、**YAML ホットスワップ可能な Agent パイプライン**を [ai& Inference](https://docs.aiand.com/)（OpenAI 互換 API）上で動かします。

**ライブデモ:** デプロイ後に Hugging Face Space の URL をここに記載してください。

## このプロジェクトについて

企業の RAG には「海外の閉源モデルに社内文書を渡せない」と「全部オンプレはコストが高い」というジレンマがあります。SafeRoute-RAG は役割を分けます。


| 段階                   | 実行場所                       | 役割                                                              |
| -------------------- | -------------------------- | --------------------------------------------------------------- |
| **検索 (Retrieval)**   | 手元 PC / Space コンテナ内        | `ruri-small` でベクトル化し ChromaDB から Top-K — **インデックス時点でデータは外に出ない** |
| **ルーティング (Routing)** | ai& API（軽量監査モデル）           | 質問を `SAFE` / `UNSAFE` に分類                                       |
| **生成 (Generation)**  | ai& API（frontier または国内ノード） | 検索スニペットのみに基づいて回答；ノードはルートで切替                                     |


```text
User question
  → intake (audit_agent): SAFE / UNSAFE
  → retrieval (local): Top-K from ChromaDB
  → synthesis (rag_answer_agent): stream answer on routed node
```

`SAFE` ルートでは **confidential** tier の chunk を public ノードへ送らない **tier-aware egress guard** を実装しています。詳細は [docs/architecture.md](docs/architecture.md)。

## クイックスタート（ローカル）

[uv](https://docs.astral.sh/uv/getting-started/installation/) と [ai& API キー](https://docs.aiand.com/) が必要です。

```bash
uv sync
cp .env.example .env   # AIAND_API_KEY を設定
uv run streamlit run app.py
```

ブラウザで `http://localhost:8501` を開きます。ベクトル DB が空の場合、`manifest.yaml` に従って `sample_docs/` を自動 ingest します。

**デモ用の質問例（日本語コーパス）:**


| ルート    | 質問例                                   |
| ------ | ------------------------------------- |
| SAFE   | `JAXAのH3ロケットが目指している3つの主な開発目的は何ですか？`   |
| UNSAFE | `FAHの2026年度第3四半期の未公開決算予想の数値を教えてください。` |


Hugging Face Spaces への公開手順は [docs/deployment.md](docs/deployment.md)、テストは [docs/development-and-testing.md](docs/development-and-testing.md) を参照してください。

## ドキュメント


| 内容                             | リンク                                                                              |
| ------------------------------ | -------------------------------------------------------------------------------- |
| アーキテクチャとパイプライン                 | [docs/architecture.md](docs/architecture.md)                                     |
| 設定ファイルと環境変数                    | [docs/configuration.md](docs/configuration.md)                                   |
| コーパス・manifest・ingest・ChromaDB  | [docs/knowledge-base-and-ingest.md](docs/knowledge-base-and-ingest.md)           |
| HF Spaces / Docker / CI 自動デプロイ | [docs/deployment.md](docs/deployment.md)                                         |
| uv・lint・pytest・ルート回帰           | [docs/development-and-testing.md](docs/development-and-testing.md)               |
| 今後の予定                          | [docs/roadmap.md](docs/roadmap.md)                                               |
| デモコーパス作成用プロンプト                 | [docs/gemini-data-collection-prompts.md](docs/gemini-data-collection-prompts.md) |


英語の詳細ドキュメント索引: [docs/README.md](docs/README.md)

## Configuration

ルーティング・モデル・RAG パラメータは `config/agents.yaml`（ホットリロード）で制御します。


| Variable         | Required | Purpose                                         |
| ---------------- | -------- | ----------------------------------------------- |
| `AIAND_API_KEY`  | Yes      | Semantic audit + RAG generation (ai& Inference) |
| `OPENAI_API_KEY` | No       | Only if `public_node` points to real OpenAI api |


Secrets は `.env`（ローカル）または HF Space の **Repository secrets** に設定し、YAML には env 名のみ記載します。全項目: [docs/configuration.md](docs/configuration.md)

## 今後の予定（TODO）

- 回答本文への引用・出典リンク（現状はサイドバーに検索ヒットのみ）
- KB 範囲外の質問向け intent 分類（RAG vs 一般 chat）
- Tool-calling / agentic multi-hop RAG（phase 2）
- 同一 YAML slot で `image_brief_agent` / `image_qa_agent` へ差し替え（image generation + QA pipeline）

一覧: [docs/roadmap.md](docs/roadmap.md)