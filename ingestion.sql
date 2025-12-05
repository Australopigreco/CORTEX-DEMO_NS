
CREATE OR REPLACE WAREHOUSE CHESS_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

USE WAREHOUSE CHESS_WH;

CREATE OR REPLACE DATABASE CHESS_DB;
CREATE OR REPLACE SCHEMA CHESS_DB.RAW;

USE DATABASE CHESS_DB;
USE SCHEMA RAW;


CREATE OR REPLACE TABLE LICHESS_GAMES (
    ID              STRING,
    RATED           BOOLEAN,
    VARIANT         STRING,
    SPEED           STRING,
    PERF            STRING,
    CREATED_AT_MS   NUMBER,
    LAST_MOVE_AT_MS NUMBER,
    STATUS          STRING,
    WINNER          STRING,
    MOVES           STRING,
    TURNS           NUMBER,
    OPENING_NAME    STRING,
    OPENING_ECO     STRING,
    WHITE_NAME      STRING,
    WHITE_ID        STRING,
    WHITE_RATING    NUMBER,
    BLACK_NAME      STRING,
    BLACK_ID        STRING,
    BLACK_RATING    NUMBER,
    CREATED_AT      TIMESTAMP_LTZ,
    LAST_MOVE_AT    TIMESTAMP_LTZ
);




CREATE OR REPLACE VIEW V_GAMES_ANALYST AS
SELECT
    id,
    rated,
    variant,
    speed,
    perf,

    created_at,
    CAST(created_at AS DATE) AS game_date,
    last_move_at,
    DATEDIFF('second', created_at, last_move_at) AS game_duration_seconds,

    status,
    winner,

    moves,
    ARRAY_SIZE(SPLIT(moves, ' ')) AS ply_count, 

    opening_name,
    opening_eco,

    white_name,
    white_rating,
    black_name,
    black_rating,

    CASE
        WHEN white_name = 'spellbind' THEN 'white'
        WHEN black_name = 'spellbind' THEN 'black'
        ELSE NULL
    END AS my_color,

    CASE
        WHEN white_name = 'spellbind' AND winner = 'white' THEN 'win'
        WHEN black_name = 'spellbind' AND winner = 'black' THEN 'win'
        WHEN winner IS NULL OR winner = '' THEN 'draw'
        WHEN (white_name = 'spellbind' OR black_name = 'spellbind') THEN 'loss'
        ELSE NULL
    END AS my_result,

    CASE
        WHEN white_name = 'spellbind' THEN black_name
        WHEN black_name = 'spellbind' THEN white_name
        ELSE NULL
    END AS opponent_name,

    CASE
        WHEN white_name = 'spellbind' THEN black_rating
        WHEN black_name = 'spellbind' THEN white_rating
        ELSE NULL
    END AS opponent_rating,

    CASE
        WHEN
            CASE
                WHEN white_name = 'spellbind' THEN black_rating
                WHEN black_name = 'spellbind' THEN white_rating
                ELSE NULL
            END IS NULL THEN NULL
        WHEN
            CASE
                WHEN white_name = 'spellbind' THEN black_rating
                WHEN black_name = 'spellbind' THEN white_rating
                ELSE NULL
            END < 1800 THEN '<1800'
        WHEN
            CASE
                WHEN white_name = 'spellbind' THEN black_rating
                WHEN black_name = 'spellbind' THEN white_rating
                ELSE NULL
            END < 2000 THEN '1800-1999'
        WHEN
            CASE
                WHEN white_name = 'spellbind' THEN black_rating
                WHEN black_name = 'spellbind' THEN white_rating
                ELSE NULL
            END < 2200 THEN '2000-2199'
        ELSE '>=2200'
    END AS opponent_rating_bucket

FROM LICHESS_GAMES;