
# app.py

import streamlit as st
import pandas as pd

from lib.games_service import load_games
from lib.ui_chess import render_lichess_board

st.set_page_config(
    page_title="Chess Game Explorer",
    layout="wide",
)

st.title("♟️ Chess Game Explorer")


st.sidebar.header("Filtri")

speed_filter = st.sidebar.selectbox(
    "Tipo di partita (speed)",
    options=["Tutti", "blitz", "bullet"],
    index=1,
)

result_filter = st.sidebar.selectbox(
    "Risultato (dal tuo punto di vista)",
    options=["Tutti", "win", "loss", "draw"],
    index=0,
)

color_filter = st.sidebar.selectbox(
    "Colore (tuo)",
    options=["Tutti", "white", "black"],
    index=0,
)

rating_min, rating_max = st.sidebar.slider(
    "Rating avversario",
    min_value=800,
    max_value=2600,
    value=(1200, 2300),
    step=50,
)

limit = st.sidebar.slider(
    "Numero massimo di partite da caricare",
    min_value=20,
    max_value=500,
    value=100,
    step=20,
)


with st.spinner("Carico le partite da Snowflake..."):
    try:
        df_games = load_games(
            speed_filter=speed_filter,
            result_filter=result_filter,
            color_filter=color_filter,
            rating_range=(rating_min, rating_max),
            limit=limit,
        )
    except Exception as e:
        st.error(f"Errore durante il caricamento delle partite: {e}")
        st.stop()

if df_games.empty:
    st.warning("Nessuna partita trovata con i filtri selezionati.")
    st.stop()


if "selected_game_id" not in st.session_state and not df_games.empty:
    st.session_state.selected_game_id = df_games.iloc[0]["GAME_ID"]


board_container = st.container()

st.subheader("Storico dell partite")


df_display = df_games.rename(
    columns={
        "GAME_ID": "Game ID",
        "GAME_DATE": "Data",
        "SPEED": "Formato",
        "MY_COLOR": "Mio Colore",
        "MY_RESULT": "Risultato",
        "OPENING_NAME": "Apertura",
        "OPPONENT_NAME": "Avversario",
        "OPPONENT_RATING": "Rating avv.",
    }
)

event = st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",           
    selection_mode="single-row", 
    key="games_table",
)

try:
    selected_rows = event.selection.rows
except AttributeError:
    selected_rows = []

if selected_rows:
    idx = selected_rows[0]
    st.session_state.selected_game_id = df_games.iloc[idx]["GAME_ID"]

current_game_id = st.session_state.get("selected_game_id")


with board_container:
    st.subheader("Scacchiera Lichess")
    render_lichess_board(current_game_id, height=500)




