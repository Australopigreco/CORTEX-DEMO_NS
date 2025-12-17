USE DATABASE CHESS_DB;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE STAGE CHESS_DB.ANALYTICS.CHESS_OPENINGS_STAGE
    DIRECTORY = (ENABLE = TRUE)
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

CREATE OR REPLACE TABLE CHESS_DB.ANALYTICS.CHESS_OPENING_RAW AS
SELECT
    RELATIVE_PATH,
    TO_VARCHAR (
        SNOWFLAKE.CORTEX.PARSE_DOCUMENT (
            '@CHESS_DB.ANALYTICS.CHESS_OPENINGS_STAGE',
            RELATIVE_PATH,
            {'mode': 'LAYOUT'} ):content
        ) AS EXTRACTED_LAYOUT
FROM
    DIRECTORY('@CHESS_DB.ANALYTICS.CHESS_OPENINGS_STAGE')
WHERE
    RELATIVE_PATH ILIKE '%.pdf'
    OR RELATIVE_PATH ILIKE '%.docx';

select * from CHESS_DB.ANALYTICS.CHESS_OPENING_RAW;

CREATE OR REPLACE TABLE CHESS_DB.ANALYTICS.CHESS_OPENING_RAW_CHUNK AS
SELECT
    relative_path,
    BUILD_SCOPED_FILE_URL(@CHESS_DB.ANALYTICS.CHESS_OPENINGS_STAGE, relative_path) AS file_url,
    (
        relative_path || ':\n'
        || coalesce('Header 1: ' || c.value['headers']['header_1'] || '\n', '')
        || coalesce('Header 2: ' || c.value['headers']['header_2'] || '\n', '')
        || c.value['chunk']
    ) AS chunk,
    'English' AS language
FROM
    CHESS_DB.ANALYTICS.CHESS_OPENING_RAW,
    LATERAL FLATTEN(SNOWFLAKE.CORTEX.SPLIT_TEXT_MARKDOWN_HEADER(
        EXTRACTED_LAYOUT,
        OBJECT_CONSTRUCT('#', 'header_1', '##', 'header_2'),
        2000, -- chunks of 2000 characters
        300 -- 300 character overlap
    )) c;

select * from CHESS_DB.ANALYTICS.CHESS_OPENING_RAW_CHUNK;

CREATE OR REPLACE CORTEX SEARCH SERVICE CHESS_DB.ANALYTICS.CHESS_OPENINGS_SEARCH
    ON chunk
    ATTRIBUTES language
    WAREHOUSE = CHESS_WH
    TARGET_LAG = '1 hour'
    AS (
    SELECT
        chunk,
        relative_path,
        file_url,
        language
    FROM CHESS_DB.ANALYTICS.CHESS_OPENING_RAW_CHUNK
    );

