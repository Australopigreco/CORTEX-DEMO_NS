# lib/games_service.py

import streamlit as st
import pandas as pd

from .snowflake_utils import get_sf_connection


@st.cache_data(show_spinner=False)
def load_games(
    speed_filter: str,
    result_filter: str,
    color_filter: str,
    rating_range: tuple[int, int],
    limit: int,
) -> pd.DataFrame:
    """
    Carica le partite da V_GAMES_ANALYST applicando i filtri base.

    Filtri:
    - speed_filter: "Tutti" | "blitz" | "bullet" | ecc.
    - result_filter: "Tutti" | "win" | "loss" | "draw"
    - color_filter: "Tutti" | "white" | "black"
    - rating_range: (min_rating, max_rating)
    - limit: numero massimo di partite
    """
    min_rating, max_rating = rating_range

    query = """
    SELECT
        id              AS GAME_ID,
        game_date       AS GAME_DATE,
        speed           AS SPEED,
        my_color        AS MY_COLOR,
        my_result       AS MY_RESULT,
        opening_name    AS OPENING_NAME,
        opponent_name   AS OPPONENT_NAME,
        opponent_rating AS OPPONENT_RATING
    FROM CHESS_DB.ANALYTICS.V_PARTITE_ANALISI
    WHERE my_color IS NOT NULL
    """

    params: dict = {}

    if speed_filter != "Tutti":
        query += " AND speed = %(speed)s"
        params["speed"] = speed_filter

    if result_filter != "Tutti":
        query += " AND my_result = %(result)s"
        params["result"] = result_filter

    if color_filter != "Tutti":
        query += " AND my_color = %(my_color)s"
        params["my_color"] = color_filter

    if min_rating is not None:
        query += " AND opponent_rating >= %(min_rating)s"
        params["min_rating"] = int(min_rating)

    if max_rating is not None:
        query += " AND opponent_rating <= %(max_rating)s"
        params["max_rating"] = int(max_rating)

    query += " ORDER BY game_date DESC LIMIT %(limit)s"
    params["limit"] = int(limit)

    conn = get_sf_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    df = cur.fetch_pandas_all()

    return df
