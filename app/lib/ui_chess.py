# lib/ui_chess.py

import streamlit as st
import streamlit.components.v1 as components


def render_lichess_board(game_id: str | None, height: int = 450):
    """Mostra la scacchiera Lichess per una partita specifica."""
    if not game_id:
        st.info("Seleziona una partita per vederla sulla scacchiera.")
        return

    embed_url = f"https://lichess.org/embed/{game_id}?theme=auto&bg=auto"

    components.iframe(
        src=embed_url,
        height=height,
        scrolling=True,
    )
