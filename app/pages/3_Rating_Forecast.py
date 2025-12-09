# pages/3_Rating_Forecast.py

import streamlit as st
import pandas as pd
import altair as alt

from lib.snowflake_utils import get_sf_connection

st.set_page_config(page_title="Rating Forecast", layout="wide")
st.title("📈 Previsione del Rating")

st.sidebar.header("Impostazioni previsione")

# --- Modo di selezione dei giorni futuri ---
selection_mode = st.sidebar.radio(
    "Come vuoi scegliere i giorni futuri?",
    ["Slider", "Input numerico"],
    index=0,
)

if selection_mode == "Slider":
    periods = st.sidebar.slider(
        "Giorni futuri da prevedere",
        min_value=1,
        max_value=180,
        value=30,
        step=1,
    )
else:
    periods = st.sidebar.number_input(
        "Giorni futuri da prevedere",
        min_value=1,
        max_value=180,
        value=30,
        step=1,
    )

st.sidebar.markdown(f"Prevediamo i prossimi **{periods}** giorni")

st.write(
    "Il grafico mostra il tuo rating storico su Lichess (utente `spellbind`) "
    "e la previsione calcolata con `SNOWFLAKE.ML.FORECAST`."
)

conn = get_sf_connection()

# ---------------- Storico ----------------
with st.spinner("Carico dati storici..."):
    df_hist = pd.read_sql(
        """
        SELECT ts, rating
        FROM CHESS_DB.ANALYTICS.V_RATING_DAILY
        ORDER BY ts
        """,
        conn,
    )

if df_hist.empty:
    st.warning("Non ci sono dati storici disponibili per il rating.")
    st.stop()

# ---------------- Forecast ----------------
with st.spinner("Calcolo la previsione dal modello Snowflake..."):
    df_fore = pd.read_sql(
        f"""
        SELECT
            ts,
            forecast,
            lower_bound,
            upper_bound
        FROM TABLE(
            CHESS_DB.ANALYTICS.RATING_FORECAST_MODEL!FORECAST(
                FORECASTING_PERIODS => {periods}
            )
        )
        ORDER BY ts
        """,
        conn,
    )

# --------- Preparazione dati per il grafico ---------

# storico
df_hist_plot = df_hist.copy()
df_hist_plot["VALUE"] = df_hist_plot["RATING"]
df_hist_plot["LOWER_BOUND"] = None
df_hist_plot["UPPER_BOUND"] = None
df_hist_plot["SERIES"] = "Storico"
df_hist_plot = df_hist_plot[["TS", "VALUE", "LOWER_BOUND", "UPPER_BOUND", "SERIES"]]

# forecast
df_fore_plot = df_fore.rename(
    columns={
        "FORECAST": "VALUE",
        "LOWER_BOUND": "LOWER_BOUND",
        "UPPER_BOUND": "UPPER_BOUND",
    }
)
df_fore_plot["SERIES"] = "Forecast"
df_fore_plot = df_fore_plot[["TS", "VALUE", "LOWER_BOUND", "UPPER_BOUND", "SERIES"]]

# --- trucco per togliere il “gap” visivo tra storico e forecast ---
last_hist_ts = df_hist_plot["TS"].max()
first_fore_ts = df_fore_plot["TS"].min()

if pd.notna(last_hist_ts) and pd.notna(first_fore_ts):
    first_fore_row = df_fore_plot.iloc[0].copy()
    first_fore_row["TS"] = last_hist_ts
    df_fore_plot = pd.concat(
        [pd.DataFrame([first_fore_row]), df_fore_plot],
        ignore_index=True
    ).sort_values("TS")

# uniamo storia + forecast
df_all = pd.concat([df_hist_plot, df_fore_plot], ignore_index=True)

# ---------------- Grafico Altair ----------------

base = alt.Chart(df_all).encode(
    x=alt.X("TS:T", title="Data"),
    tooltip=["TS:T", "VALUE:Q", "SERIES:N", "LOWER_BOUND:Q", "UPPER_BOUND:Q"],
)

line = base.mark_line().encode(
    y=alt.Y("VALUE:Q", title="Rating"),
    color=alt.Color("SERIES:N", title="Serie"),
)

band = (
    base
    .transform_filter(alt.datum.SERIES == "Forecast")
    .mark_area(opacity=0.2)
    .encode(
        y="LOWER_BOUND:Q",
        y2="UPPER_BOUND:Q",
    )
)

chart = (band + line).interactive()

st.altair_chart(chart, use_container_width=True)
