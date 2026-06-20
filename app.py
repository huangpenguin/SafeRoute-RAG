"""SafeRoute-RAG Streamlit app: chat + document upload + live routing dashboard."""

from __future__ import annotations

import streamlit as st

from src.database import LocalKnowledgeBase
from src.demo_limits import demo_mode_enabled, max_queries_per_session, max_query_chars
from src.orchestrator import Orchestrator

st.set_page_config(page_title="SafeRoute-RAG", page_icon="🛡️", layout="wide")


@st.cache_resource
def get_orchestrator() -> Orchestrator:
    """Create orchestrator; auto-ingest manifest when chroma_db is empty (local / HF fallback)."""
    orch = Orchestrator()
    if orch.kb.count() == 0:
        orch.kb.ingest_manifest(reset=False)
    return orch


def _mask_url(url: str) -> str:
    return url.replace("https://", "").split("/")[0]


def _check_demo_query_limit() -> bool:
    """Return True if the query is allowed; show UI error otherwise."""
    if not demo_mode_enabled():
        return True
    limit = max_queries_per_session()
    used = st.session_state.setdefault("demo_query_count", 0)
    if used >= limit:
        st.error(f"デモの質問上限（{limit} 回/セッション）に達しました。ページを再読み込みしてください。")
        return False
    return True


def _validate_query(query: str) -> str | None:
    """Return an error message if the query is invalid."""
    if not query.strip():
        return "質問を入力してください。"
    if demo_mode_enabled() and len(query) > max_query_chars():
        return f"質問は {max_query_chars()} 文字以内にしてください。"
    return None


def main() -> None:
    orch = get_orchestrator()
    kb: LocalKnowledgeBase = orch.kb

    st.title("🛡️ SafeRoute-RAG")
    st.caption("ローカル埋め込み + 二層セキュリティルーティングの Hybrid-RAG（ai& Inference）")

    with st.sidebar:
        st.header("📚 ナレッジベース")
        st.metric("登録チャンク数", kb.count())
        if demo_mode_enabled():
            limit = max_queries_per_session()
            used = st.session_state.get("demo_query_count", 0)
            st.caption(f"デモモード: 残り {max(limit - used, 0)}/{limit} 回")
        else:
            if st.button("manifest を一括取り込み", use_container_width=True):
                with st.spinner("ingest 中..."):
                    n = kb.ingest_manifest(reset=True)
                st.success(f"{n} チャンクを取り込みました")
                st.rerun()

            uploaded = st.file_uploader("文書をアップロード (.md / .txt)", type=["md", "txt"])
            if uploaded is not None and st.button("アップロードを取り込み", use_container_width=True):
                text = uploaded.read().decode("utf-8", errors="ignore")
                n = kb.ingest_text(text, doc_id=uploaded.name, tier="uploaded")
                st.success(f"{uploaded.name}: {n} チャンク取り込み")
                st.rerun()

        st.divider()
        st.subheader("⚙️ アクティブ Pipeline")
        st.json(dict(orch.config.active))

    col_chat, col_dash = st.columns([3, 2])

    with col_chat:
        st.subheader("💬 チャット")
        query = st.chat_input("質問を入力してください")
        if query:
            err = _validate_query(query)
            if err:
                st.warning(err)
            elif _check_demo_query_limit():
                st.chat_message("user").write(query)
                with st.spinner("ルーティング + 検索..."):
                    result = orch.run(query, stream=True)
                with st.chat_message("assistant"):
                    if result.answer_stream is not None:
                        st.write_stream(result.answer_stream)
                    else:
                        st.write(result.answer or "（回答なし）")
                st.session_state["last_result"] = result
                if demo_mode_enabled():
                    st.session_state["demo_query_count"] = st.session_state.get("demo_query_count", 0) + 1

    with col_dash:
        st.subheader("📊 ルーティング監視ダッシュボード")
        result = st.session_state.get("last_result")
        if result is None:
            st.info("質問するとここに経路が表示されます。")
        else:
            route = result.route
            badge = "🔴 UNSAFE" if route.label == "UNSAFE" else "🟢 SAFE"
            st.markdown(f"### {badge}")
            cfg = orch.config
            provider = cfg.providers[route.target_provider]
            conf = f"{route.confidence:.2f}" if route.confidence is not None else "-"
            st.table(
                {
                    "判定": [route.label],
                    "発火レイヤー": [route.layer],
                    "命中キーワード": [", ".join(route.matched_keywords) or "-"],
                    "判定理由": [route.reason or "-"],
                    "確信度": [conf],
                    "ルーティング先": [f"{provider.name}"],
                    "モデル": [route.target_model],
                    "エンドポイント": [_mask_url(provider.base_url)],
                    "ルーティング遅延(ms)": [route.latency_ms],
                }
            )
            st.markdown("#### 🔎 検索スニペット (Top-K)")
            for c in result.chunks:
                lock = "🔒" if c.tier == "confidential" else "🌐"
                with st.expander(f"{lock} {c.doc_id}  score={c.score}"):
                    if c.source_url:
                        st.markdown(f"**出典:** [{c.source_url}]({c.source_url})")
                    elif c.tier == "confidential":
                        st.caption("合成 Demo 機密文書（外部 URL なし）")
                    st.write(c.text[:400])


if __name__ == "__main__":
    main()
