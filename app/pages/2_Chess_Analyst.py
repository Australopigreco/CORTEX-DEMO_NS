# pages/2_Chess_Analyst.py

import streamlit as st
import requests
import pandas as pd

from typing import Any, Dict, List, Optional

from lib.snowflake_utils import get_sf_connection
from lib.ui_chess import render_lichess_board


# =========================
# Config pagina + stile
# =========================
st.set_page_config(
    page_title="Chess Analyst",
    page_icon="♟️",
    layout="wide",
)

st.markdown(
    """
    <style>
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
    .section-spacer {
        margin-top: 2.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Chess Analyst")



# =========================
# Costanti
# =========================
FILE_MODELLO_SEMANTICO = "@CHESS_DB.ANALYTICS.SEMANTIC_MODELS/scacchi_semantica.yaml"


# =========================
# Traduzione generica EN->IT via Snowflake Cortex
# =========================
@st.cache_data(show_spinner=False, ttl=3600)
def traduci_in_italiano(testo: str) -> str:
    """
    Traduce un testo in italiano usando SNOWFLAKE.CORTEX.TRANSLATE.
    - Usa autodetect lingua sorgente ('') e target 'it'
    - Cache per evitare costi/latency ai rerun
    """
    testo = (testo or "").strip()
    if not testo:
        return testo

    # Evita costi/latency su testi enormi (opzionale)
    if len(testo) > 2000:
        return testo

    conn = get_sf_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT SNOWFLAKE.CORTEX.TRANSLATE(%(t)s, '', 'it')",
            {"t": testo},
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else testo
    except Exception as e:
        # Non bloccare la UI: fallback al testo originale
        # Mostra un warning UNA sola volta per sessione
        if not st.session_state.get("_warn_traduzione_cortex", False):
            st.session_state["_warn_traduzione_cortex"] = True
            st.warning(
                "Nota: non riesco a tradurre automaticamente alcuni testi (Cortex Translate non disponibile o non autorizzato per questo ruolo). "
                "In quei casi vedrai l'originale."
            )
        return testo
    finally:
        try:
            cur.close()
        except Exception:
            pass


def formatta_e_traduci_testo_analyst(testo_raw: str) -> str:
    """
    Gestisce solo il caso speciale 'interpretation' (titolo in italiano),
    e per tutto il resto fa traduzione generica in italiano.
    """
    testo_raw = testo_raw or ""

    prefisso = "This is our interpretation of your question:"
    if testo_raw.startswith(prefisso):
        resto = testo_raw[len(prefisso):].lstrip()
        resto_it = traduci_in_italiano(resto)
        return f"**Questa è la nostra interpretazione della tua domanda:**\n\n{resto_it}"

    return traduci_in_italiano(testo_raw)


# =========================
# Chiamata Cortex Analyst (REST)
# =========================
def chiama_cortex_analyst(domanda: str) -> Dict[str, Any]:
    """
    Chiama il REST API di Cortex Analyst usando:
    - il file YAML sullo stage (FILE_MODELLO_SEMANTICO)
    - il token di sessione della connessione Snowflake
    """
    domanda = (domanda or "").strip()
    if not domanda:
        raise ValueError("La domanda è vuota.")

    conn = get_sf_connection()

    host = conn.host
    session_token = conn.rest.token
    url = f"https://{host}/api/v2/cortex/analyst/message"

    body = {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": domanda}],
            }
        ],
        "semantic_model_file": FILE_MODELLO_SEMANTICO,
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


# =========================
# Rendering contenuti Analyst
# =========================
def mostra_contenuto(blocchi: List[Dict[str, Any]]):
    """
    Mostra il contenuto restituito da Cortex Analyst:
    - text: tradotto in italiano
    - suggestions/follow-up: tradotti in italiano
    - sql: mostrata come SQL (NON tradotta) + risultati
    - se nei risultati c'è una colonna partita (id/game_id/partita_id), riga selezionabile
      e aggiorna la scacchiera in basso.
    """
    conn = get_sf_connection()
    indice_blocco = 0

    for item in (blocchi or []):
        item_type = item.get("type")
        indice_blocco += 1

        if item_type == "text":
            testo_raw = item.get("text", "")
            st.markdown(formatta_e_traduci_testo_analyst(testo_raw))

        elif item_type in ("suggestions", "suggestion"):
            suggerimenti = item.get("suggestions", []) or []
            if suggerimenti:
                with st.expander("Suggerimenti di follow-up", expanded=False):
                    for s in suggerimenti:
                        st.markdown(f"- {traduci_in_italiano(str(s))}")

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
                    continue

                # Cerco una colonna ID partita
                candidate_cols = [
                    c for c in df.columns if c.lower() in ("id", "game_id", "partita_id")
                ]
                col_partita = candidate_cols[0] if candidate_cols else None

                if col_partita:
                    evento = st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="single-row",
                        key=f"risultati_analyst_{indice_blocco}",
                    )

                    try:
                        righe_selezionate = evento.selection.rows
                    except AttributeError:
                        righe_selezionate = []

                    if righe_selezionate:
                        idx = righe_selezionate[0]
                        partita_id = df.iloc[idx][col_partita]
                        st.session_state.analyst_selected_game_id = str(partita_id)
                        st.success(f"Partita selezionata: {partita_id}")
                else:
                    st.dataframe(df, use_container_width=True)

        else:
            # Blocchi non previsti: li ignoriamo silenziosamente
            pass


# =========================
# Stato sessione
# =========================
if "analyst_history" not in st.session_state:
    st.session_state.analyst_history = []


# =========================
# UI: input domanda
# =========================
st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
st.subheader("Fai una domanda sulle tue partite")

domanda = st.text_area(
    "Domanda:",
    placeholder='Esempio: "Quali sono le 10 aperture con cui ho il win rate peggiore nel blitz?"',
    height=140,
)

st.write("")
col1, col2 = st.columns([1, 3])

with col1:
    bottone_chiedi = st.button("Chiedi a Cortex Analyst", use_container_width=True)

with col2:
    st.write("")

if bottone_chiedi:
    if not domanda.strip():
        st.warning("Scrivi prima una domanda.")
    else:
        with st.spinner("Interrogo Cortex Analyst..."):
            try:
                risposta_json = chiama_cortex_analyst(domanda)
            except Exception as e:
                st.error(f"Errore nella chiamata a Cortex Analyst:\n\n{e}")
            else:
                st.session_state.analyst_history.append(
                    {"question": domanda, "response": risposta_json}
                )


# =========================
# UI: cronologia
# =========================
st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
st.subheader("Cronologia conversazione")

if not st.session_state.analyst_history:
    st.info("Fai una prima domanda per vedere qui le risposte.")
else:
    for item in reversed(st.session_state.analyst_history):
        q = item.get("question", "")
        resp = item.get("response", {}) or {}

        st.markdown(f"**Tu:** {q}")

        msg = resp.get("message", {}) or {}
        content_blocks = msg.get("content", []) or []

        mostra_contenuto(content_blocks)
        st.markdown("---")


# =========================
# UI: scacchiera selezionata dai risultati
# =========================
st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
st.subheader("Scacchiera dalla risposta di Analyst")

game_id = st.session_state.get("analyst_selected_game_id")

if game_id:
    render_lichess_board(game_id, height=480)
else:
    st.info("Seleziona una partita da una delle tabelle dei risultati per vederla qui.")
