CREATE OR REPLACE SCHEMA CHESS_DB.ANALYTICS;

CREATE OR REPLACE VIEW CHESS_DB.ANALYTICS.V_PARTITE_ANALISI AS
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

    -- tuo colore
    CASE
        WHEN white_name = 'spellbind' THEN 'white'
        WHEN black_name = 'spellbind' THEN 'black'
        ELSE NULL
    END AS my_color,

    -- esito dal tuo punto di vista
    CASE
        WHEN white_name = 'spellbind' AND winner = 'white' THEN 'win'
        WHEN black_name = 'spellbind' AND winner = 'black' THEN 'win'
        WHEN winner IS NULL OR winner = '' THEN 'draw'
        WHEN (white_name = 'spellbind' OR black_name = 'spellbind') THEN 'loss'
        ELSE NULL
    END AS my_result,

    -- tuo rating
    CASE
        WHEN white_name = 'spellbind' THEN white_rating
        WHEN black_name = 'spellbind' THEN black_rating
        ELSE NULL
    END AS my_rating,

    -- avversario & rating avversario
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

    -- differenza rating (tu - avversario)
    (CASE
        WHEN white_name = 'spellbind' THEN white_rating
        WHEN black_name = 'spellbind' THEN black_rating
        ELSE NULL
     END)
     -
    (CASE
        WHEN white_name = 'spellbind' THEN black_rating
        WHEN black_name = 'spellbind' THEN white_rating
        ELSE NULL
     END) AS rating_diff,

    -- bucket rating avversario
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
    END AS opponent_rating_bucket,

    -- flag comodi per metriche
    CASE WHEN
        (white_name = 'spellbind' AND winner = 'white') OR
        (black_name = 'spellbind' AND winner = 'black')
    THEN 1 ELSE 0 END AS is_win,

    CASE WHEN
        winner IS NULL OR winner = ''
    THEN 1 ELSE 0 END AS is_draw

FROM CHESS_DB.RAW.V_GAMES_ANALYST
WHERE (white_name = 'spellbind' OR black_name = 'spellbind');

select * from v_partite_analisi;

CREATE OR REPLACE VIEW CHESS_DB.ANALYTICS.V_RATING_DAILY AS
SELECT
    CAST(game_date AS TIMESTAMP_NTZ) AS ts,
    my_rating AS rating
FROM (
    SELECT
        game_date,
        created_at,
        my_rating,
        ROW_NUMBER() OVER (
            PARTITION BY game_date
            ORDER BY created_at DESC
        ) AS rn
    FROM CHESS_DB.ANALYTICS.V_PARTITE_ANALISI
    WHERE my_rating IS NOT NULL
)
WHERE rn = 1
ORDER BY ts;

select * from CHESS_DB.ANALYTICS.V_RATING_DAILY;


USE WAREHOUSE CHESS_WH;
USE DATABASE CHESS_DB;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE SNOWFLAKE.ML.FORECAST RATING_FORECAST_MODEL(
  INPUT_DATA        => TABLE(CHESS_DB.ANALYTICS.V_RATING_DAILY),
  TIMESTAMP_COLNAME => 'TS',
  TARGET_COLNAME    => 'RATING',
  CONFIG_OBJECT     => {'frequency': '1 day'}
);

SELECT *
FROM TABLE(
    CHESS_DB.ANALYTICS.RATING_FORECAST_MODEL!FORECAST(
        FORECASTING_PERIODS => 90
    )
);

