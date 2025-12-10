Links 
 
time-series: https://docs.snowflake.com/en/user-guide/ml-functions/forecasting

CREATE OR REPLACE SNOWFLAKE.ML.FORECAST my_fc(
  INPUT_DATA => TABLE(my_view),
  SERIES_COLNAME => 'series_id',         -- optional
  TIMESTAMP_COLNAME => 'ts',
  TARGET_COLNAME => 'y',
  CONFIG_OBJECT => { 'method': 'fast', 'evaluate': FALSE }
);