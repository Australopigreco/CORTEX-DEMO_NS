# lib/snowflake_utils.py

import os

import streamlit as st
import snowflake.connector
from dotenv import load_dotenv

# Carica le variabili dal .env una volta sola
load_dotenv()


@st.cache_resource(show_spinner=False)
def get_sf_connection():
    """
    Crea (e cache-a) una connessione a Snowflake usando le env vars.

    Env richieste:
    - SNOWFLAKE_ACCOUNT
    - SNOWFLAKE_USER
    - SNOWFLAKE_PASSWORD
    - opzionali: SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA
    """
    try:
        conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "CHESS_WH"),
            database=os.environ.get("SNOWFLAKE_DATABASE", "CHESS_DB"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA", "RAW"),
        )
        return conn
    except KeyError as ke:
        st.error(
            f"Manca una variabile d'ambiente per Snowflake: {ke}. "
            "Controlla il file .env (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, ...)."
        )
        st.stop()
    except Exception as e:
        st.error(f"Errore di connessione a Snowflake: {e}")
        st.stop()
