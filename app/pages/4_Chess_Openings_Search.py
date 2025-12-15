# pages/4_Chess_Openings_Chat.py

import streamlit as st
import pandas as pd


import requests
from lib.snowflake_utils import get_sf_connection

st.set_page_config(
    page_title="Chess Openings Chat",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Chess Openings Chat (Najdorf & QGD)")

st.write(
    "Fai domande sulle aperture (Siciliana Najdorf). "
    "Useremo Cortex Search sui PDF caricati in Snowflake per trovare i passaggi rilevanti, "
    "e un modello LLM di Snowflake per riassumerli in italiano."
)

# ---- Config semplice nella sidebar ----

st.sidebar.header("Impostazioni")

model_name = st.sidebar.selectbox(
    "Modello LLM",
    options=["mistral-large2", "llama3.1-70b", "llama3.1-8b"],
    index=0,
)

num_chunks = st.sidebar.slider(
    "Numero di chunk di contesto da recuperare",
    min_value=1,
    max_value=10,
    value=5,
)

debug = st.sidebar.toggle("Mostra contesto (debug)", value=False)

# ---- Stato della chat ----

if "openings_chat_messages" not in st.session_state:
    st.session_state.openings_chat_messages = []


def query_cortex_search(query: str, limit: int | None = None) -> list[dict]:
    """
    Chiama il servizio CHESS_OPENINGS_SEARCH via REST API e restituisce
    una lista di risultati (chunk, file_url, relative_path, language, ecc.).
    Se 'limit' è None, usa il valore scelto nella sidebar (num_chunks) oppure 5.
    """
    from streamlit import session_state as ss  # per sicurezza

    if limit is None:
        # prova a prendere il valore che usi nello slider; se non c’è, default 5
        limit = ss.get("num_chunks", 5)

    conn = get_sf_connection()

    host = conn.host
    session_token = conn.rest.token

    url = (
        f"https://{host}/api/v2/databases/CHESS_DB/"
        f"schemas/ANALYTICS/cortex-search-services/CHESS_OPENINGS_SEARCH:query"
    )

    body = {
        "query": query,
        "limit": limit,
        "columns": ["chunk", "file_url", "relative_path", "language"],
        "filter": {"@and": [{"@eq": {"language": "English"}}]},
    }

    headers = {
        "Authorization": f'Snowflake Token="{session_token}"',
        "Content-Type": "application/json",
    }

    resp = requests.post(url, json=body, headers=headers, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Errore Cortex Search {resp.status_code}:\n{resp.text}"
        )

    resp_json = resp.json()
    return resp_json.get("results", [])



def call_cortex_complete(model: str, prompt: str) -> str:
    """
    Chiama SNOWFLAKE.CORTEX.COMPLETE via SQL usando la stessa connessione
    che usi per tutto il resto.
    """
    conn = get_sf_connection()
    # IMPORTANTE: usa parametri per evitare injection
    df = pd.read_sql(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s) AS RESULT",
        conn,
        params=[model, prompt],
    )
    return df["RESULT"].iloc[0]


def build_prompt(question: str, chunks: list[dict]) -> str:
    """
    Costruisce il prompt per il modello LLM:
    - include contesto estratto dai PDF (chunks)
    - istruisce il modello a rispondere in italiano e solo se il contesto basta
    """
    context_parts = []
    for i, r in enumerate(chunks):
        context_parts.append(
            f"Documento {i+1} ({r['relative_path']}):\n{r['chunk']}"
        )
    context_str = "\n\n".join(context_parts)

    prompt = f"""
[INST]
Sei un assistente di scacchi specializzato in aperture, soprattutto Siciliana Najdorf
e Gambetto di Donna rifiutato. Ti viene fornito un contesto estratto da libri PDF
e appunti caricati in Snowflake.

Usa **solo** le informazioni nel contesto per rispondere alla domanda dell'utente.
Se le informazioni non sono sufficienti, rispondi soltanto:
"Non so rispondere a questa domanda con i dati che ho."

Rispondi sempre in italiano, in modo chiaro e comprensibile per un giocatore
tra 1700 e 2300 Elo.

<context>
{context_str}
</context>

<question>
{question}
</question>
[/INST]
Risposta (in italiano):
"""
    return prompt, context_str


# ---- UI chat: mostra la cronologia ----

icons = {"assistant": "❄️", "user": "👤"}

for msg in st.session_state.openings_chat_messages:
    with st.chat_message(msg["role"], avatar=icons[msg["role"]]):
        st.markdown(msg["content"])

# ---- Input utente ----

user_q = st.chat_input("Fai una domanda sulle aperture...")

if user_q:
    # aggiungi messaggio utente alla cronologia
    st.session_state.openings_chat_messages.append(
        {"role": "user", "content": user_q}
    )

    # mostra subito il messaggio utente
    with st.chat_message("user", avatar=icons["user"]):
        st.markdown(user_q)

    # risposta assistente
    with st.chat_message("assistant", avatar=icons["assistant"]):
        placeholder = st.empty()
        with st.spinner("Sto pensando e cercando nei PDF..."):
            # 1) Cerca nei PDF con Cortex Search
            results = query_cortex_search(user_q)

            if not results:
                answer = "Non ho trovato passaggi rilevanti nei PDF per rispondere a questa domanda."
                placeholder.markdown(answer)
                st.session_state.openings_chat_messages.append(
                    {"role": "assistant", "content": answer}
                )
            else:
                # 2) Costruisci il prompt per l'LLM
                prompt, context_str = build_prompt(user_q, results)

                # Debug: mostra il contesto
                if debug:
                    st.sidebar.text_area("Contesto usato per la risposta", context_str, height=300)

                # 3) Chiama SNOWFLAKE.CORTEX.COMPLETE
                raw_answer = call_cortex_complete(model_name, prompt)

                # 4) Costruisci tabella dei riferimenti
                markdown_table = "###### Riferimenti\n\n| PDF | URL |\n|-----|-----|\n"
                for r in results:
                    markdown_table += f"| {r['relative_path']} | [Link]({r['file_url']}) |\n"

                full_answer = raw_answer + "\n\n" + markdown_table

                placeholder.markdown(full_answer)

                st.session_state.openings_chat_messages.append(
                    {"role": "assistant", "content": full_answer}
                )
