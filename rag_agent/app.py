"""Single-question chat UI over the finance cockpit gold schema.

v1 is deliberately single-shot: every question re-runs agent.ask() from scratch with no
carried-over conversation history. Run with: streamlit run app.py
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agent import ask  # noqa: E402 - import after load_dotenv() so env vars are set first

st.set_page_config(page_title="Finance Cockpit Q&A", page_icon="📊")
st.title("Finance Cockpit Q&A")
st.caption(
    "Ask a question about the gold-layer finance/procurement data. Each question is answered "
    "independently - follow-ups don't carry over prior context yet."
)

question = st.text_input("Your question", placeholder="Which department has the worst procurement savings this year?")

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Thinking..."):
        try:
            result = ask(question)
        except Exception as e:  # noqa: BLE001 - surface any failure in the UI, don't crash the app
            st.error(f"Something went wrong: {e}")
        else:
            st.markdown(result["answer"])
            if result["sources"]:
                with st.expander("Sourced from"):
                    for tool_name, detail in result["sources"]:
                        if tool_name == "run_sql":
                            st.code(detail, language="sql")
                        else:
                            st.write(f"Schema lookup: `{detail}`")
