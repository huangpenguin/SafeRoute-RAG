# SafeRoute-RAG 演示语料搜集 — Gemini 提示词

> 用法：按顺序复制下方各 Prompt 到 Gemini（建议开启 Google Search / 联网）。  
> **公开资料**：Gemini 只负责找来源与摘要，PDF/页面由你本人下载后放入 `sample_docs/public/`。  
> **机密资料**：全部为**合成 Demo 文档**，由 Gemini 起草 Markdown，你审阅后存入 `sample_docs/confidential/`。

---

## Prompt 0：设定上下文（先发这一条）

```text
你是日本企业 IT / 合规 / RAG 系统方面的调研助手。我要做一个名为 SafeRoute-RAG 的 Demo，参加 Qiita 的 ai& Inference 比赛。

架构要点：
- 知识库分两类：① 公开情报（public）② 社内机密（confidential，全部为合成 Demo，非真实泄露）
- 用户提问时，系统用日语敏感词 + LLM 审计决定走「公网 frontier 模型」还是「日本国内 ai& 安全节点」
- 语料主题：日本の宇宙・航空・防衛産業（JAXA、三菱重工、IHI、川崎重工、スカイPerfect JSAT 等）
- 语言：文档正文以日语为主；文件名可用英数字

请在整个对话中：
1. 公开资料必须给出**可验证的官方或一手来源 URL**（优先 .go.jp、企业 IR、JAXA 官网）
2. 不要编造下载链接；找不到官方 PDF 就明确说「需自行在官网检索」
3. 机密层文档必须标注「【合成デモ・非公開】」，数字与公司内部决策均为虚构
4. 输出格式用 Markdown 表格，便于我复制

确认理解后回复「了解しました」，不要开始搜集。
```

---

## Prompt 1：公开资料清单（你来下载）

```text
【任务】为 SafeRoute-RAG 的 `sample_docs/public/` 搜集 **4～6 份** 日语公开资料。

主题范围（每主题 1 份即可）：
1. JAXA — H3 ロケットまたは SLIM 月面着陸ミッションの公開概要
2. 三菱重工 — 宇宙事業または H-IIA/H3 関連の公開 IR/ニュース
3. IHI または 川崎重工 — 航空エンジン/宇宙関連の公開事業説明
4. スカイパーフェクト JSAT または 宇宙ビジネス — 商用衛星の公開サービス説明
5. （可选）防衛省 / 宇宙開発戦略本部 — 宇宙政策の公開白書・概要ページ

对每个主题，输出表格，列如下：
| # | 建议文件名 | 文档类型 | 来源机构 | 直接 URL | 页数/篇幅估计 | 建议截取章节 | 为何适合「SAFE 路由」演示 | 推荐 Demo 提问（日语） |

要求：
- URL 必须是截至今日仍可访问的官方页面或 PDF 直链
- 若只有 HTML 无 PDF，说明「保存为 PDF 或复制为 Markdown」的操作建议
- 每份资料预估入库后 800～3000 日语字即可（不必整本下载）
- Demo 提问必须是**不含** 社内機密/未公開/インサイダー/ソースコード 等敏感词的普通业务问题

额外输出一节「下载检查清单」，列出我需要手动完成的步骤（勾选框格式）。
```

---

## Prompt 2：合成机密文档（Gemini 直接写 Markdown）

```text
【任务】为 `sample_docs/confidential/` 起草 **4 份合成机密 Markdown**，用于触发 UNSAFE 路由。

虚构设定：某日本航空航天 conglomerate「極東航空宇宙ホールディングス（FAH）」的内部文档。可影射但不使用真实未公开数据。

每份文档要求：
- 长度：600～1200 日语字
- 顶部 YAML front matter：
  ---
  classification: "社内機密・関係者限り"
  synthetic: true
  demo_only: true
  ---
- 正文必须自然出现以下路由敏感词中的 **至少 2 个**（分散在不同段落）：
  社内機密、財務報表、インサイダー、ソースコード、未公開、契約漏洞
- 内容类型（各 1 份）：
  1. `fah_unreleased_financial_forecast.md` — 未公開の次期決算予想・M&A 評価
  2. `fah_launch_contract_draft.md` — 打ち上げ契約の未公開条項と「契約漏洞」リスクメモ
  3. `fah_insider_roadmap.md` — インサイダー向け製品ロードマップ（ソースコード模块名を含む）
  4. `fah_board_minutes_confidential.md` — 取締役会議事録（未公開の提携交渉）

输出格式：
- 先给 4 个文件的完整 Markdown（用 `### 文件名` 分隔）
- 再给表格：| 文件名 | 触发的敏感词 | 推荐 Demo 提问（日语，应判 UNSAFE）| 期望命中层（hard_rule / semantic_audit）|

注意：所有数字、公司名、日期均为虚构；文末加一行「※本ドキュメントは SafeRoute-RAG デモ用の合成データです」
```

---

## Prompt 3：Demo 问答对（路由测试用）

```text
【任务】基于 Prompt 1 的公开资料 + Prompt 2 的合成机密文档，生成 **路由测试用问答对**。

输出两个表格：

### 表 A：期望 SAFE → public_node（12 问）
列：| ID | 用户提问（日语） | 期望检索文档 | 期望路由 | 不应命中的敏感词 |

### 表 B：期望 UNSAFE → local_safe_node（12 问）
列：| ID | 用户提问（日语） | 期望检索文档 | 期望路由 | 预期触发机制（关键词名 / 语义审计）|

要求：
- SAFE 问题：关于 JAXA 任务概要、公开卫星服务、企业官网上的事业说明等
- UNSAFE 问题：涉及未公開财务、内部源码、インサイダー情報、合同漏洞等
- 各有一半问题**不**明显含敏感词，需依赖第二层语义审计（用于证明双层路由价值）
- 附加「边界用例」3 问：措辞模糊，说明系统可能判 SAFE 或 UNSAFE，供我人工验证

最后给一节「Qiita 記事用ワンライナー」：各 3 条，用于 GIF 演示时的字幕文案（日语）。
```

---

## Prompt 4：敏感词与 Embedding 校验

```text
【任务】审查 SafeRoute-RAG 的日语路由配置是否与语料匹配。

当前 hard_keywords 计划列表：
社内機密、財務報表、インサイダー、ソースコード、未公開、契約漏洞

请完成：
1. 建议补充的日语 hard_keywords（5～10 个），附「为何需要」与「误报风险」
2. 建议**不要**加入的词（易误报日常用语）
3. 针对纯日语语料，比较 embedding 模型（仅 CPU Mac 场景）：
   - cl-nagoya/ruri-small
   - sonoisa/sentence-bert-base-ja-mean-tokens-v2
   - intfloat/multilingual-e5-small
   从日语检索精度、模型体积、首次下载大小、推理速度给出推荐排序
4. 若 public 用官方 PDF（日语）、confidential 用合成 MD，入库前是否需要统一预处理（给出 checklist）

输出简洁，表格优先。
```

---

## Prompt 5（可选）：单份公开 PDF 精读摘要

下载某份 PDF 后，若只想入库其中几页，用此 Prompt：

```text
我将粘贴一份日语航空航天公开文档的目录或节选文本（来自 [来源 URL]）。

请帮我：
1. 推荐最适合 RAG Demo 的 2～3 个章节（说明理由）
2. 为每个章节写一段 200～400 字的日语摘要（仅基于我提供的内容，不要 hallucinate 数字）
3. 给出 3 个基于该摘要的 SAFE 路由 Demo 提问（日语）
4. 若摘要中 accidentally 出现「未公開」等词，指出并改写为中性表述

【在此粘贴目录或正文节选】
```

---

## 本地目录约定

```text
sample_docs/
├── public/
│   ├── legacy/              # 原始 PDF（下载存档，不 ingest）
│   │   ├── JAXA_H3_PressKit.pdf.pdf
│   │   └── ...
│   ├── jaxa_h3_overview.md  # 脚本提取后的 RAG 入库文件
│   └── ...
├── confidential/
└── manifest.yaml
```

**清洗流程：**

1. PDF 放入 `public/legacy/`
2. 运行 `uv run --with pymupdf python scripts/extract_public_corpus.py`
3. 检查 `public/*.md`，必要时在脚本 `ExtractSpec.pages` 调整页码后重跑
4. 更新 `manifest.yaml` 的 `path` / `status: ready`

## 合规提醒

- 公开 PDF：保留来源 URL，Demo /README 中注明出处；仅截取必要章节。
- 机密 MD：必须带 `synthetic: true`；勿使用真实企业泄露文件或真实 insider 信息。
- 比赛文章：明确写「機密文書はデモ用合成データ」以免误解。
