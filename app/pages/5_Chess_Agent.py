# pages/5_Chess_Agent.py
import json
import re
import requests
import streamlit as st

from lib.ui_chess import render_lichess_board
from lib.snowflake_utils import get_sf_connection

DB = "CHESS_DB"
SCHEMA = "ANALYTICS"
AGENT = "CHESS_COPILOT"

st.set_page_config(page_title="Chess Copilot Agent", layout="wide")
st.title("🤖 Chess Copilot (Cortex Agent)")

def to_msg(role: str, text: str) -> dict:
    return {"role": role, "content": [{"type": "text", "text": text}]}


def sse_events(resp):
    event = None
    data_lines = []

    # decode_unicode=False => ottieni bytes, decodifichi tu in UTF-8 (zero mojibake)
    for raw in resp.iter_lines(decode_unicode=False):
        if not raw:
            if event is not None:
                yield event, "\n".join(data_lines)
            event, data_lines = None, []
            continue

        line = raw.decode("utf-8", errors="replace").strip()

        if line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())

def call_agent(messages):
    conn = get_sf_connection()
    host = conn.host
    pat = st.secrets["SNOWFLAKE_PAT"]

    url = f"https://{host}/api/v2/databases/{DB}/schemas/{SCHEMA}/agents/{AGENT}:run"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
        "X-Snowflake-Role": "ACCOUNTADMIN",
        "X-Snowflake-Warehouse": "CHESS_WH",
    }
    body = {"messages": messages, "tool_choice": {"type": "auto"}}

    # ✅ stream=True per SSE reale
    # ✅ timeout tuple: (connect_timeout, read_timeout)
    r = requests.post(url, headers=headers, json=body, stream=True, timeout=(10, 900))
    if r.status_code >= 400:
        st.error(f"HTTP {r.status_code} | request_id={r.headers.get('X-Snowflake-Request-Id')}")
        st.code(r.content.decode("utf-8", errors="replace"))
        st.stop()

    r.raise_for_status()
    return r


# Stato chat
if "agent_api_messages" not in st.session_state:
    st.session_state.agent_api_messages = []
if "chat_ui" not in st.session_state:
    st.session_state.chat_ui = []
if "agent_selected_game_id" not in st.session_state:
    st.session_state.agent_selected_game_id = None

# Render cronologia UI
for m in st.session_state.chat_ui:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_q = st.chat_input("Chiedimi di partite, rating o aperture…")
if user_q:
    st.session_state.chat_ui.append({"role": "user", "content": user_q})
    st.session_state.agent_api_messages.append(to_msg("user", user_q))

    with st.chat_message("assistant"):
        placeholder = st.empty()
        out = ""

        resp = call_agent(st.session_state.agent_api_messages)

        # Stream: mostriamo i delta e poi teniamo il testo finale
        final_text = None
        for ev, data in sse_events(resp):
            if ev == "response.text.delta":
                payload = json.loads(data)
                out += payload.get("text", "")
                placeholder.markdown(out)
            elif ev == "response":
                payload = json.loads(data)
                # fallback: prova a estrarre testo finale dalla risposta aggregata
                content = payload.get("response", {}).get("content", [])
                texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                if texts:
                    final_text = "\n".join(texts)

        if final_text:
            out = final_text
            placeholder.markdown(out)

    st.session_state.chat_ui.append({"role": "assistant", "content": out})
    st.session_state.agent_api_messages.append(to_msg("assistant", out))

    m = re.search(r"GAME_ID\s*[:=]\s*([A-Za-z0-9]+)", out)
    if m:
        st.session_state.agent_selected_game_id = m.group(1)

# Scacchiera se trovata
gid = st.session_state.agent_selected_game_id
if gid:
    st.subheader("♟️ Scacchiera")
    render_lichess_board(gid, height=480)
