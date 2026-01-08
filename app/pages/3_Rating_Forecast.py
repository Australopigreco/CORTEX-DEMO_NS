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
    "Previsioni per i giorni futuri: ",
    ["Slider", "Input numerico"],
    index=0,
)

if selection_mode == "Slider":
    periods = st.sidebar.slider(
        "Giorni futuri da prevedere",
        min_value=1,
        max_value=250,
        value=180,
        step=1,
    )
else:
    periods = st.sidebar.number_input(
        "Giorni futuri da prevedere",
        min_value=1,
        max_value=250,
        value=180,
        step=1,
    )

st.sidebar.markdown(f"Prevediamo i prossimi **{periods}** giorni")

st.write(
    "Il grafico mostra il tuo rating storico su Lichess (utente `spellbind`) "
    "e la previsione calcolata con `SNOWFLAKE.ML.FORECAST`."
)

st.markdown("<br>", unsafe_allow_html=True) 

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

# ---------- Quanto storico mostrare ----------

total_points = len(df_hist)

# di default: ultimi 120 giorni, oppure tutti se ne hai meno di 120
default_hist_points = min(total_points, 120)


# piccolo spazio visivo tra parte forecast e parte storico
st.sidebar.markdown("")
st.sidebar.markdown("")

hist_selection_mode = st.sidebar.radio(
    "Come vuoi scegliere i giorni storici da mostrare?",
    ["Slider", "Input numerico"],
    index=0,
)

if hist_selection_mode == "Slider":
    hist_points = st.sidebar.slider(
        "Giorni storici da mostrare prima del forecast",
        min_value=1,
        max_value=int(total_points),
        value=int(default_hist_points),
        step=1,
    )
else:
    hist_points = st.sidebar.number_input(
        "Giorni storici da mostrare prima del forecast",
        min_value=1,
        max_value=int(total_points),
        value=int(default_hist_points),
        step=1,
    )

hist_points = int(hist_points)

st.sidebar.markdown(
    f"Mostriamo gli **ultimi {hist_points}** giorni di storico."
)

# tieni solo gli ultimi `hist_points` record
df_hist = df_hist.tail(hist_points)

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

# --- Calcola automaticamente il range dell'asse Y con un po' di margine ---
min_val = df_all["VALUE"].min()
max_val = df_all["VALUE"].max()

padding = 100
y_min = max(min_val - padding, 0)
y_max = max_val + padding

y_scale = alt.Scale(
    domain=[float(y_min), float(y_max)],
    nice=False,
    zero=False,   # <-- non forzare lo zero
)

# ---------------- Grafico Altair ----------------

# linea (storico + forecast)
line = (
    alt.Chart(df_all)
    .mark_line()
    .encode(
        x=alt.X("TS:T", title="Data"),
        y=alt.Y("VALUE:Q", title="Rating", scale=y_scale),
        color=alt.Color("SERIES:N", title="Serie"),
        tooltip=["TS:T", "VALUE:Q", "SERIES:N", "LOWER_BOUND:Q", "UPPER_BOUND:Q"],
    )
)

# banda di confidenza solo sul forecast
band = (
    alt.Chart(df_all)
    .transform_filter(alt.datum.SERIES == "Forecast")
    .mark_area(opacity=0.2)
    .encode(
        x="TS:T",
        y=alt.Y("LOWER_BOUND:Q", scale=y_scale),
        y2="UPPER_BOUND:Q",
    )
)

chart = (band + line).interactive()

st.altair_chart(chart, use_container_width=True)
