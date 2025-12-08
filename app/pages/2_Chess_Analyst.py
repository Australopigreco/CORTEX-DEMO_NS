# pages/2_Chess_Analyst.py

import streamlit as st
import requests
import pandas as pd

from lib.snowflake_utils import get_sf_connection
from lib.ui_chess import render_lichess_board

# -----------------------
# Stile globale (spaziatura + eventuale background)
# -----------------------

st.markdown(
    """
    <style>
    /* Più spazio verticale tra i blocchi principali */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        margin-bottom: 1.2rem;
    }
    .stTextArea label {
        margin-bottom: 0.5rem;
    }
    /* Margine sopra la sezione cronologia */
    .section-spacer {
        margin-top: 2.5rem;
        margin-bottom: 1rem;
    }

    /* ESEMPIO di background; sostituisci l'URL con una tua GIF se vuoi.
       Se non vuoi il background animato, commenta o cancella questo blocco.
    .stApp {
        background-image: url("https://media.tenor.com/4k3Z9l9M1D4AAAAC/chess.gif");
        background-size: cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
        background-position: center;
    }
    */
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("😄 Chess Analyst")


# 👉 Adatta questo path al tuo stage reale e al nome del file YAML
SEMANTIC_MODEL_FILE = "@CHESS_DB.ANALYTICS.SEMANTIC_MODELS/scacchi_semantica.yaml"


def call_cortex_analyst(question: str) -> dict:
    """
    Chiama il REST API di Cortex Analyst usando:
    - il file YAML sullo stage (SEMANTIC_MODEL_FILE)
    - il token di sessione della connessione Snowflake
    """
    question = question.strip()
    if not question:
        raise ValueError("La domanda è vuota.")

    conn = get_sf_connection()

    host = conn.host
    session_token = conn.rest.token

    url = f"https://{host}/api/v2/cortex/analyst/message"

    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question}
                ],
            }
        ],
        "semantic_model_file": SEMANTIC_MODEL_FILE,
    }

    headers = {
        "Authorization": f'Snowflake Token="{session_token}"',
        "Content-Type": "application/json",
    }

    resp = requests.post(url, json=body, headers=headers, timeout=60)

    request_id = resp.headers.get("X-Snowflake-Request-Id")

    if resp.status_code >= 400:
        raise RuntimeError(
            f"Errore Cortex Analyst {resp.status_code} (request_id={request_id}):\n{resp.text}"
        )

    resp_json = resp.json()
    resp_json["request_id"] = request_id
    return resp_json


def display_content(content: list[dict]):
    """
    Mostra il contenuto restituito da Cortex Analyst:
    - testo (interpretazione / spiegazione)
    - suggerimenti
    - SQL + risultati (in expander)
    - se i risultati contengono una colonna partita (id/game_id), la riga è cliccabile
      e aggiorna la scacchiera in basso.
    """
    conn = get_sf_connection()

    # per dare chiavi diverse agli eventuali dataframe multipli
    block_index = 0

    for item in content:
        item_type = item.get("type")
        block_index += 1

        if item_type == "text":
            st.markdown(item.get("text", ""))

        elif item_type == "suggestions":
            suggestions = item.get("suggestions", [])
            if suggestions:
                with st.expander("Suggerimenti di follow-up", expanded=False):
                    for s in suggestions:
                        st.markdown(f"- {s}")

        elif item_type == "sql":
            statement = item.get("statement", "")
            if not statement:
                continue

            with st.expander("SQL generato", expanded=False):
                st.code(statement, language="sql")

            with st.expander("Risultati", expanded=True):
                try:
                    df = pd.read_sql(statement, conn)
                except Exception as e:
                    st.error(f"Errore eseguendo la query SQL:\n{e}")
                    continue

                if df.empty:
                    st.info("La query non ha restituito risultati.")
                else:
                    # cerchiamo una possibile colonna con l'id partita
                    candidate_cols = [c for c in df.columns if c.lower() in ("id", "game_id", "partita_id")]
                    game_col = candidate_cols[0] if candidate_cols else None

                    # se trovo una colonna partita, rendo la tabella selezionabile
                    if game_col:
                        df_show = df.copy()
                        event = st.dataframe(
                            df_show,
                            use_container_width=True,
                            hide_index=True,
                            on_select="rerun",
                            selection_mode="single-row",
                            key=f"analyst_result_{block_index}",
                        )

                        # se l'utente seleziona una riga, salvo il game_id in session_state
                        try:
                            selected_rows = event.selection.rows
                        except AttributeError:
                            selected_rows = []

                        if selected_rows:
                            idx = selected_rows[0]
                            game_id = df.iloc[idx][game_col]
                            st.session_state.analyst_selected_game_id = str(game_id)
                            st.success(f"Partita selezionata: {game_id}")
                    else:
                        # nessuna colonna partita: tabella normale
                        st.dataframe(df, use_container_width=True)




if "analyst_history" not in st.session_state:
    st.session_state.analyst_history = []

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

st.subheader("Fai una domanda sulle tue partite")

question = st.text_area(
    "Domanda:",
    placeholder='Esempio: "Quali sono le 10 aperture con cui ho il win rate peggiore nel blitz?"',
    height=140,
)

st.write("")  

col1, col2 = st.columns([1, 3])

with col1:
    ask = st.button("Chiedi a Cortex Analyst", use_container_width=True)

with col2:
    st.write("")

if ask:
    if not question.strip():
        st.warning("Scrivi prima una domanda.")
    else:
        with st.spinner("Interrogo Cortex Analyst..."):
            try:
                response_json = call_cortex_analyst(question)
            except Exception as e:
                st.error(f"Errore nella chiamata a Cortex Analyst:\n\n{e}")
            else:
                st.session_state.analyst_history.append(
                    {
                        "question": question,
                        "response": response_json,
                    }
                )

st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
st.subheader("Cronologia conversazione")

if not st.session_state.analyst_history:
    st.info("Fai una prima domanda per vedere qui le risposte.")
else:
    for item in reversed(st.session_state.analyst_history):
        q = item["question"]
        resp = item["response"]

        st.markdown(f"**Tu:** {q}")
        msg = resp.get("message", {})
        content_blocks = msg.get("content", [])

        display_content(content_blocks)

        st.markdown("---")



st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
st.subheader("Scacchiera dalla risposta di Analyst")

game_id = st.session_state.get("analyst_selected_game_id")

if game_id:
    render_lichess_board(game_id, height=480)
else:
    st.info("Seleziona una partita da una delle tabelle dei risultati per vederla qui.")
