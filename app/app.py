

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

# Inizializza il game_id selezionato (default: prima partita)
if "selected_game_id" not in st.session_state and not df_games.empty:
    st.session_state.selected_game_id = df_games.iloc[0]["GAME_ID"]

# Placeholder per la scacchiera (lo creiamo qui per tenerla sopra)
board_container = st.container()

st.subheader("Partite")

# Prepara la tabella da mostrare all'utente
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
    on_select="rerun",           # abilita la selezione come input
    selection_mode="single-row", # una riga alla volta
    key="games_table",
)

# Se l'utente ha selezionato una riga, aggiorniamo il game_id
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






























# import os                       # serve per gestire le variabili d'ambiente. (os.environ)
# from dotenv import load_dotenv  # serve per caricare le variabili d'ambiente da .env
# import pandas as pd
# import streamlit as st
# import streamlit.components.v1 as components # per embed iframe
# import snowflake.connector

# st.set_page_config(
#     page_title="Chess Game Explorer",
#     layout="wide",
# )

# load_dotenv()


# def get_sf_connection():
#     """Crea una connessione a Snowflake usando le env vars."""
#     try:
#         conn = snowflake.connector.connect(
#             account=os.environ["SNOWFLAKE_ACCOUNT"],
#             user=os.environ["SNOWFLAKE_USER"],
#             password=os.environ["SNOWFLAKE_PASSWORD"],
#             warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "CHESS_WH"),
#             database=os.environ.get("SNOWFLAKE_DATABASE", "CHESS_DB"),
#             schema=os.environ.get("SNOWFLAKE_SCHEMA", "ANALYTICS"),
#         )
#         return conn
#     except KeyError as ke:
#         st.error(
#             f"Manca una variabile d'ambiente per Snowflake: {ke}. "
#             "Controlla il file .env (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, ...)."
#         )
#         st.stop()
#     except Exception as e:
#         st.error(f"Errore di connessione a Snowflake: {e}")
#         st.stop()


# @st.cache_data(show_spinner=False)
# def load_games(speed_filter: str, result_filter: str, limit: int) -> pd.DataFrame:
#     """
#     Carica le partite dalla view V_PARTITE_ANALISI applicando i filtri base.
#     Restituisce un DataFrame pandas.
#     """
#     query = """
#     SELECT
#         id            AS GAME_ID,
#         game_date     AS GAME_DATE,
#         speed         AS SPEED,
#         my_color      AS MY_COLOR,
#         my_result     AS MY_RESULT,
#         opening_name  AS OPENING_NAME,
#         opponent_name AS OPPONENT_NAME,
#         opponent_rating AS OPPONENT_RATING
#     FROM CHESS_DB.ANALYTICS.V_PARTITE_ANALISI
#     WHERE my_color IS NOT NULL
#     """

#     params = {}

#     if speed_filter != "Tutti":
#         query += " AND speed = %(speed)s"
#         params["speed"] = speed_filter

#     if result_filter != "Tutti":
#         query += " AND my_result = %(result)s"
#         params["result"] = result_filter

#     query += " ORDER BY game_date DESC LIMIT %(limit)s"
#     params["limit"] = limit

#     with get_sf_connection() as conn:
#         cur = conn.cursor()
#         cur.execute(query, params)
#         df = cur.fetch_pandas_all()

#     return df


# # MAIN

# st.title("♟️ Chess Game Explorer")

# st.markdown(
#     "Esplora le tue partite Lichess salvate in Snowflake e rivedile "
#     "su una scacchiera 2D embedded da Lichess."
# )

# # Sidebar per i filtri
# st.sidebar.header("Filtri")

# speed_filter = st.sidebar.selectbox(
#     "Tipo di partita (speed)",
#     options=["Tutti", "blitz", "bullet"],
#     index=1,
# )

# result_filter = st.sidebar.selectbox(
#     "Risultato (dal tuo punto di vista)",
#     options=["Tutti", "win", "loss", "draw"],
#     index=0,
# )

# limit = st.sidebar.slider(
#     "Numero massimo di partite da caricare",
#     min_value=20,
#     max_value=500,
#     value=100,
#     step=20,
# )

# # Carica dati
# with st.spinner("Carico le partite da Snowflake..."):
#     try:
#         df_games = load_games(speed_filter, result_filter, limit)
#     except Exception as e:
#         st.error(f"Errore durante il caricamento delle partite: {e}")
#         st.stop()

# if df_games.empty:
#     st.warning("Nessuna partita trovata con i filtri selezionati.")
#     st.stop()

# # Layout: tabella a sinistra, scacchiera a destra
# col_table, col_board = st.columns([3, 2])

# with col_table:
#     st.subheader("Partite")

#     df_display = df_games.rename(
#         columns={
#             "GAME_ID": "Game ID",
#             "GAME_DATE": "Data",
#             "SPEED": "Speed",
#             "MY_COLOR": "Colore",
#             "MY_RESULT": "Risultato",
#             "OPENING_NAME": "Apertura",
#             "OPPONENT_NAME": "Avversario",
#             "OPPONENT_RATING": "Rating avv.",
#         }
#     )

#     st.dataframe(
#         df_display,
#         use_container_width=True,
#         hide_index=True,
#     )

#     game_id = st.selectbox(
#         "Scegli una partita da visualizzare sulla scacchiera:",
#         options=df_games["GAME_ID"].tolist(),
#     )

# with col_board:
#     st.subheader("Scacchiera Lichess")

#     if game_id:
#         embed_url = f"https://lichess.org/embed/{game_id}?theme=auto&bg=auto"

#         components.iframe(
#             src=embed_url,
#             height=400,
#             scrolling=True,
#         )
#     else:
#         st.info("Seleziona una partita per vederla sulla scacchiera.")
