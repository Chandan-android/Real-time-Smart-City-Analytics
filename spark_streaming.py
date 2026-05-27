import logging
import os
import time
import traceback
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg') # non-interactive backend — saves plots as PNG files
import matplotlib.pyplot as plt
import seaborn as sns

from pyspark.storagelevel import StorageLevel
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType, IntegerType, FloatType, StringType, StructField, StructType, NumericType
)
from pyspark.sql.functions import (
    col, trim, lower, when, count, isnan, hour, dayofmonth, dayofweek, month, year, to_timestamp
    )

from pyspark.ml.feature import Imputer, VectorAssembler
from pyspark.ml import PipelineModel

# ── Logging Setup ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("SmartCityStreaming")

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════
KAFKA_BROKER = 'localhost:9092'
MODELS_DIR = 'saved_models'
OUTPUT_DIR = 'output'
PLOT_DIR = 'output/plots'
PARQUET_DIR = 'output/parquet'

# Per-dataset subdirectories
PLOT_DIRS = {
    'traffic'  : 'output/plots/traffic',
    'energy'   : 'output/plots/energy',
    'pollution': 'output/plots/pollution',
}
PARQUET_DIRS = {
    'traffic'  : 'output/parquet/traffic',
    'energy'   : 'output/parquet/energy',
    'pollution': 'output/parquet/pollution',
}
COLLECT_SECS = 60  # Time in seconds to collect streaming data before processing
STREAM_STATE_FILE = "stream_state.txt"  # Resume file written by Generate_data.py
TRIGGER_SECS = "15 seconds"

# Create output directories if they don't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs(PARQUET_DIR, exist_ok=True)
for _d in list(PLOT_DIRS.values()) + list(PARQUET_DIRS.values()):
    os.makedirs(_d, exist_ok=True)

# ══════════════════════════════════════════════════════════════════
#  CREATE SPARK SESSION
# ══════════════════════════════════════════════════════════════════
spark = (
    SparkSession.builder
    .appName("SmartCityAnalytics")
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2")
    .config("spark.driver.memory", "3g")
    .config("spark.executor.memory", "3g")
    .config("spark.driver.maxResultSize", "1g")
    .config("spark.sql.shuffle.partitions", "2")
    .config("spark.default.parallelism", "2")
    .config("spark.python.worker.reuse", "true")
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.network.timeout", "800s")
    .config("spark.executor.heartbeatInterval", "60s")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")
print("Spark session started.")

# ══════════════════════════════════════════════════════════════════
#  LOAD SAVED MODELS — BEST MODEL + PREPROCESSORS
# ══════════════════════════════════════════════════════════════════
print("Loading pre-trained models and preprocessors...")

traffic_metadata = joblib.load(f'{MODELS_DIR}/traffic_metadata.pkl')
energy_metadata = joblib.load(f'{MODELS_DIR}/energy_metadata.pkl')
pollution_metadata = joblib.load(f'{MODELS_DIR}/pollution_metadata.pkl')

# Traffic model components
best_model_t   = PipelineModel.load(traffic_metadata['best_model_path'])
scaler_t       = PipelineModel.load(traffic_metadata['scaler_model_path'])
encoder_t      = PipelineModel.load(traffic_metadata['encoder_model_path'])
area_freq_pd_t = traffic_metadata['area_freq_t']
num_cols_t     = list(traffic_metadata['num_cols_t'])
cat_cols_t     = list(traffic_metadata['cat_cols_t'])
already_enc_t  = list(traffic_metadata['already_encoded_t'])
ohe_cols_t     = list(traffic_metadata['ohe_cols_t'])
final_feat_t   = list(traffic_metadata['final_feature_cols_t'])
mae_t          = traffic_metadata.get('mae_t')
rmse_t         = traffic_metadata.get('rmse_t')
r2_t           = traffic_metadata.get('r2_t')
trained_rows_t = traffic_metadata.get('trained_rows_t')

# Energy model components
best_model_e   = PipelineModel.load(energy_metadata['best_model_path'])
scaler_e       = PipelineModel.load(energy_metadata['scaler_model_path'])
encoder_e      = PipelineModel.load(energy_metadata['encoder_model_path'])
area_freq_pd_e = energy_metadata['area_freq_e']
num_cols_e     = list(energy_metadata['num_cols_e'])
cat_cols_e     = list(energy_metadata['cat_cols_e'])
already_enc_e  = list(energy_metadata['already_encoded_e'])
ohe_cols_e     = list(energy_metadata['ohe_cols_e'])
final_feat_e   = list(energy_metadata['final_feature_cols_e'])
mae_e          = energy_metadata.get('mae_e')
rmse_e         = energy_metadata.get('rmse_e')
r2_e           = energy_metadata.get('r2_e')
trained_rows_e = energy_metadata.get('trained_rows_e')

# Pollution model components
best_model_p   = PipelineModel.load(pollution_metadata['best_model_path'])
scaler_p       = PipelineModel.load(pollution_metadata['scaler_model_path'])
encoder_p      = PipelineModel.load(pollution_metadata['encoder_model_path'])
area_freq_pd_p = pollution_metadata['area_freq_p']
num_cols_p     = list(pollution_metadata['num_cols_p'])
cat_cols_p     = list(pollution_metadata['cat_cols_p'])
already_enc_p  = list(pollution_metadata['already_encoded_p'])
ohe_cols_p     = list(pollution_metadata['ohe_cols_p'])
final_feat_p   = list(pollution_metadata['final_feature_cols_p'])
mae_p          = pollution_metadata.get('mae_p')
rmse_p         = pollution_metadata.get('rmse_p')
r2_p           = pollution_metadata.get('r2_p')
trained_rows_p = pollution_metadata.get('trained_rows_p')

# Build Spark broadcast-friendly lookup DataFrames from area_freq pandas DataFrames
area_freq_sdf_t = spark.createDataFrame(area_freq_pd_t)  # cols: area, area_enc_t
area_freq_sdf_e = spark.createDataFrame(area_freq_pd_e)  # cols: area, area_enc_e
area_freq_sdf_p = spark.createDataFrame(area_freq_pd_p)  # cols: area, area_enc_p

log.info("Models and preprocessors loaded successfully.")

# ── Stream clock status ───────────────────────────────────────────
if os.path.exists(STREAM_STATE_FILE):
    with open(STREAM_STATE_FILE) as _f:
        _last = _f.read().strip()
    log.info(f"Stream clock: resuming after {_last}")
else:
    log.info("Stream clock: no state file — will start from 2026-01-01T00:00:00")

# ══════════════════════════════════════════════════════════════════
#  KAFKA SCHEMA DEFINITIONS
# ══════════════════════════════════════════════════════════════════

# Traffic schema
traffic_schema = StructType([
    StructField("timestamp",        StringType(),  True),
    StructField("area",             StringType(),  True),
    StructField("zone",             StringType(),  True),
    StructField("vehicle_count",    DoubleType(),  True),
    StructField("avg_speed",        DoubleType(),  True),
    StructField("congestion_level", StringType(),  True),
    StructField("road_type",        StringType(),  True),
    StructField("weather",          StringType(),  True),
    StructField("incident",         StringType(),  True),
    StructField("severity",         StringType(),  True),
    StructField("event",            StringType(),  True),
    StructField("signal_wait_time", DoubleType(),  True),
    StructField("is_weekend",       IntegerType(), True),
    StructField("is_it_hub",        IntegerType(), True),
    StructField("season",           StringType(),  True),
])

# Energy schema
energy_schema = StructType([
    StructField("timestamp",          StringType(),  True),
    StructField("area",               StringType(),  True),
    StructField("zone",               StringType(),  True),
    StructField("weather",            StringType(),  True),
    StructField("energy_consumption", DoubleType(),  True),
    StructField("temperature",        DoubleType(),  True),
    StructField("humidity",           DoubleType(),  True),
    StructField("demand_level",       StringType(),  True),
    StructField("renewable_usage",    DoubleType(),  True),
    StructField("load_type",          StringType(),  True),
    StructField("is_weekend",         IntegerType(), True),
    StructField("power_outage",       IntegerType(), True),
    StructField("is_it_hub",          IntegerType(), True),
    StructField("season",             StringType(),  True),
])

# Pollution schema
pollution_schema = StructType([
    StructField("timestamp",   StringType(),  True),
    StructField("area",        StringType(),  True),
    StructField("zone",        StringType(),  True),
    StructField("AQI",         DoubleType(),  True),
    StructField("PM2.5",       DoubleType(),  True),
    StructField("PM10",        DoubleType(),  True),
    StructField("NO2",         DoubleType(),  True),
    StructField("CO",          DoubleType(),  True),
    StructField("weather",     StringType(),  True),
    StructField("temperature", DoubleType(),  True),
    StructField("humidity",    DoubleType(),  True),
    StructField("is_weekend",  IntegerType(), True),
    StructField("is_it_hub",   IntegerType(), True),
    StructField("season",      StringType(),  True),
])

# ══════════════════════════════════════════════════════════════════
#  SHARED HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════

# Outlier capping function using IQR method for PySpark DataFrames
def cap_outliers_spark(df, col_name):
    """IQR-based outlier capping. Returns (capped_df, lower, upper) so
    the caller reuses the exact same bounds for post-cap outlier counting."""
    valid_count = df.filter(F.col(col_name).isNotNull()).count()
    if valid_count == 0:
        return df, None, None
 
    Q1, Q3 = df.approxQuantile(col_name, [0.25, 0.75], 0.01)  # exact quantiles
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    capped_df = df.withColumn(
        col_name,
        F.when(F.col(col_name) < lower, lower)
         .when(F.col(col_name) > upper, upper)
         .otherwise(F.col(col_name))
    )
    return capped_df, lower, upper

def count_outliers_with_bounds(df, col_name, lower, upper):
    """Count outliers using pre-computed bounds (avoids re-sampling drift)."""
    if lower is None or upper is None:
        return 0
    return df.filter(
        (F.col(col_name) < lower) | (F.col(col_name) > upper)
    ).count()

# Function to save matplotlib plots to disk
def save_plot(name, dataset=None):
    """Save current matplotlib figure to per-dataset subdir and close it."""
    if dataset is None:
        for key in PLOT_DIRS:
            if name.startswith(key):
                dataset = key
                break
    base = PLOT_DIRS.get(dataset, PLOT_DIR)
    path = f"{base}/{name}.png"
    plt.savefig(path, bbox_inches='tight', dpi=100)
    plt.close()
    log.info(f" Plot Saved -> {path}")

# Helper function to check if a field is numeric
def is_numeric(field):
    return isinstance(field.dataType, NumericType)

# Function to print missing value counts per column
_NULL_STRINGS = {"", "null", "None", "nan", "NaN", "NULL", "NA", "N/A"}

def null_counts(df, label=""):
    """Print missing value count per column."""
    log.info(f"\nMissing value counts {label}:")
    exprs = []
    for field in df.schema.fields:
        c = field.name
        dtype = field.dataType

        # Float / Double columns
        if isinstance(dtype, (DoubleType, FloatType)):
            condition = F.col(c).isNull() | F.isnan(F.col(c))

        # String columns
        elif isinstance(dtype, StringType):
            cleaned = F.lower(F.trim(F.col(c)))
            condition = F.col(c).isNull()
            for val in _NULL_STRINGS:
                condition = condition | (cleaned == val.lower())

        # Other datatypes
        else:
            condition = F.col(c).isNull()

        exprs.append(
            F.sum(F.when(condition, 1).otherwise(0)).alias(c)
        )
    df.select(exprs).show(truncate=False)

# Helper function to check if a column is null-like (SQL NULL or any string that represents missing)
def is_null_like(c):
    """
    Returns a PySpark Column expression that is True when the value is:
      - SQL NULL
      - Any string that represents missing: "", "null", "None", "nan", etc.
    This is needed because:
      - fillna() catches SQL NULL only
      - PySpark CSV reader may read empty cells as "" (not NULL)
      - Python str(None)="None" and str(float('nan'))="nan" become literal strings
    """
    condition = col(c).isNull()
    for s in _NULL_STRINGS:
        condition = condition | (lower(trim(col(c))) == s.lower())
    return condition

# Imputation function for numeric and categorical columns in PySpark DataFrames
def impute_df(df):
    """
    Impute missing values in a PySpark DataFrame.
    Numeric Columns:
        - Replace NULL and NaN using mean imputation
        - Uses Spark MLlib Imputer
    Categorical Columns:
        - Replace NULL and common missing strings
          using mode imputation
    """
    # Identify Numeric Columns
    num_cols = [
        f.name for f in df.schema.fields
        if isinstance(f.dataType, (DoubleType, FloatType))
    ]

    # Cast numeric columns to DoubleType
    for c in num_cols:
        df = df.withColumn(c, col(c).cast(DoubleType()))

    # Numeric Imputation (Mean)
    if num_cols:
        imputer = (
            Imputer(inputCols=num_cols, outputCols=num_cols)
            .setStrategy("mean")
            .setMissingValue(float('nan'))
        )
        df = imputer.fit(df).transform(df)

    # Identify Categorical Columns
    cat_cols = [
        f.name for f in df.schema.fields
        if str(f.dataType) == "StringType()"
    ]

    # Categorical Imputation (Mode)
    for c in cat_cols:
        # Compute mode excluding invalid missing strings
        mode_row = (
            df.filter(
                col(c).isNotNull() &
                (trim(col(c)) != "") &
                (~col(c).isin(list(_NULL_STRINGS)))
            )
            .groupBy(c)
            .count()
            .orderBy(F.desc("count"))
            .first()
        )
        if mode_row and mode_row[0] is not None:
            # Condition for all missing forms
            is_missing = col(c).isNull()
            for null_str in _NULL_STRINGS:
                is_missing = is_missing | (trim(col(c)) == null_str)

            # Replace missing values with mode
            df = df.withColumn(
                c,
                when(is_missing, mode_row[0]).otherwise(col(c))
            )
    return df

# Outlier counting function for a given column using IQR method
def count_outliers(df, col_name):
    """Return count of outlier rows for a given column using IQR."""
    valid_count = df.filter(F.col(col_name).isNotNull()).count()
    if valid_count == 0:
        return 0
    
    Q1, Q3 = df.approxQuantile(col_name, [0.25, 0.75], 0.01)
    IQR    = Q3 - Q1
    return df.filter(
        (F.col(col_name) < Q1 - 1.5*IQR) |
        (F.col(col_name) > Q3 + 1.5*IQR)
    ).count()

# ══════════════════════════════════════════════════════════════════
#  PREDICTION FUNCTIONS
# ══════════════════════════════════════════════════════════════════

# Traffic prediction function
def predict_traffic(sdf_t):
    """
    Apply Stage-2 Traffic feature engineering + preprocessing on a PySpark
    DataFrame, then return the DataFrame with a 'predicted_vehicle_count' column.
    Mirrors the feature engineering logic from model.ipynb (Traffic section).
    """
    # Feature Engineering
    # Peak hour flag 
    if "is_peak_hour" not in sdf_t.columns:
        sdf_t = sdf_t.withColumn(
            "is_peak_hour",
            F.when(
                ((F.col("hour") >= 8)  & (F.col("hour") <= 10)) |
                ((F.col("hour") >= 17) & (F.col("hour") <= 20)),
                1
            ).otherwise(0)
        )
    
    # Road capacity 
    if "road_capacity" not in sdf_t.columns:
        sdf_t = sdf_t.withColumn(
            "road_capacity",
            F.when(F.col("road_type") == "Highway",   1200.0)
            .when(F.col("road_type") == "Main Road",  750.0)
            .when(F.col("road_type") == "Street",     350.0)
            .otherwise(750.0)   # median fallback
        )
 
    # Core traffic interaction features
    if "speed_to_capacity_ratio" not in sdf_t.columns:
        sdf_t = sdf_t.withColumn(
            "speed_to_capacity_ratio", F.col("avg_speed") / F.col("road_capacity")
        )
    if "speed_x_peak" not in sdf_t.columns:
        sdf_t = sdf_t.withColumn(
            "speed_x_peak", F.col("avg_speed") * F.col("is_peak_hour")
        )
    if "hour_x_capacity" not in sdf_t.columns:
        sdf_t = sdf_t.withColumn(
            "hour_x_capacity", F.col("hour") * F.col("road_capacity")
        )

    # Lag features — no history in streaming; fill with 0
    if "vehicle_lag1" not in sdf_t.columns:
        sdf_t = sdf_t.withColumn("vehicle_lag1", F.lit(0.0))
    if "vehicle_lag2" not in sdf_t.columns:
        sdf_t = sdf_t.withColumn("vehicle_lag2", F.lit(0.0))

    # ── Add a surrogate row key so we can re-join context cols after prediction ──
    # The model pipeline drops timestamp / area / zone / vehicle_count (the target)
    # because they were not part of training features. We preserve them here and
    # join them back once the prediction column exists, so the final CSV written by
    # save_outputs contains all columns the Streamlit dashboard expects.
    sdf_t = sdf_t.withColumn("_row_id", F.monotonically_increasing_id())

    # Columns to restore after prediction (not model features, but needed in output)
    context_cols_t = [c for c in
                      ["_row_id", "timestamp", "area", "zone",
                       "vehicle_count", "congestion_level", "signal_wait_time"]
                      if c in sdf_t.columns]
    sdf_t_context = sdf_t.select(context_cols_t)
     
    # Area frequency encoding
    sdf_t = sdf_t.join(area_freq_sdf_t, on="area", how="left") \
                 .fillna({"area_enc_t": 0.0})
    
    # Drop columns not used in training
    drop_cols_t = ['timestamp', 'congestion_level', 'signal_wait_time', 'vehicle_count', 'area']
    sdf_t = sdf_t.drop(*[c for c in drop_cols_t if c in sdf_t.columns])

    # Apply saved Encoding pipeline
    sdf_t = encoder_t.transform(sdf_t)

    # Apply saved Scaling pipeline
    sdf_t = scaler_t.transform(sdf_t)

    # Assemble final feature vector
    missing_cols_t = [c for c in final_feat_t if c not in sdf_t.columns]
    if missing_cols_t:
        raise ValueError(f"Missing features for traffic model: {missing_cols_t}")
    assembler_t = VectorAssembler(
        inputCols=final_feat_t, outputCol="features", handleInvalid="keep")
    sdf_t = assembler_t.transform(sdf_t)

    # Run predictions with the loaded best model
    preds_sdf = best_model_t.transform(sdf_t) \
                            .withColumnRenamed("prediction", "predicted_vehicle_count")

    # Drop context cols from preds before re-joining to avoid duplicates
    cols_to_drop = [c for c in context_cols_t if c != "_row_id" and c in preds_sdf.columns]
    preds_sdf = preds_sdf.drop(*cols_to_drop)

    # Re-attach context columns (timestamp, area, zone, actual vehicle_count, etc.)
    preds_sdf = preds_sdf.join(sdf_t_context, on="_row_id", how="left").drop("_row_id")
    return preds_sdf
    
# Energy prediction function
def predict_energy(sdf_e):
    """
    Apply Stage-2 Energy feature engineering + preprocessing on a PySpark
    DataFrame, then return the DataFrame with a 'predicted_energy_consumption' column.
    Mirrors the feature engineering logic from model.ipynb (Energy section).
    """
    # Feature Engineering
    # Peak hour flag 
    if "is_peak_hour" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn(
            "is_peak_hour",
            F.when(
                ((F.col("hour") >= 6)  & (F.col("hour") <= 9))  |
                ((F.col("hour") >= 11) & (F.col("hour") <= 15)) |
                ((F.col("hour") >= 18) & (F.col("hour") <= 22)),
                1
            ).otherwise(0)
        )

    # Temperature-Humidity discomfort index
    if "temp_humidity_discomfort" not in sdf_e.columns: 
        sdf_e = sdf_e.withColumn(
            "temp_humidity_discomfort",
            F.col("temperature") - (
                F.lit(0.55) * (F.lit(1.0) - F.col("humidity") / F.lit(100.0)) *
                (F.col("temperature") - F.lit(14.5))
            )
        )

    # Temperature threshold flags
    if "high_temp_flag" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn("high_temp_flag",  (F.col("temperature") > 30).cast("int"))
    if "very_high_temp" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn("very_high_temp",  (F.col("temperature") > 34).cast("int"))
    if "is_extreme_cold" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn("is_extreme_cold", (F.col("temperature") < 18).cast("int"))
    if "temp_squared" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn("temp_squared",    F.col("temperature") * F.col("temperature"))

    # Interaction features
    if "temp_humidity_interaction" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn(
            "temp_humidity_interaction", F.col("temperature") * F.col("humidity")
        )
    if "peak_temp_interaction" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn(
            "peak_temp_interaction", F.col("is_peak_hour") * F.col("temperature")
        )

    # Lag features — no history in streaming; fill with 0
    if "lag_energy1" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn("lag_energy1", F.lit(0.0))
    if "lag_energy2" not in sdf_e.columns:
        sdf_e = sdf_e.withColumn("lag_energy2", F.lit(0.0))

     # ── Add surrogate row key to re-join context columns post-prediction ──
    sdf_e = sdf_e.withColumn("_row_id", F.monotonically_increasing_id())

    context_cols_e = [c for c in
                      ["_row_id", "timestamp", "area", "zone",
                       "energy_consumption", "demand_level"]
                      if c in sdf_e.columns]
    sdf_e_context = sdf_e.select(context_cols_e)

    # Area frequency encoding
    sdf_e = sdf_e.join(area_freq_sdf_e, on="area", how="left") \
                 .fillna({"area_enc_e": 0.0})
 
    # Drop columns not used in training
    drop_cols_e = ['timestamp', 'demand_level', 'energy_consumption', 'area']
    sdf_e = sdf_e.drop(*[c for c in drop_cols_e if c in sdf_e.columns])

    # Apply saved Encoding pipeline
    sdf_e = encoder_e.transform(sdf_e)

    # Apply saved Scaling pipeline
    sdf_e = scaler_e.transform(sdf_e)

    # Assemble final feature vector
    missing_cols_e = [c for c in final_feat_e if c not in sdf_e.columns]
    if missing_cols_e:
        raise ValueError(f"Missing features for energy model: {missing_cols_e}")
    assembler_e = VectorAssembler(
        inputCols=final_feat_e, outputCol="features", handleInvalid="keep")
    sdf_e = assembler_e.transform(sdf_e)

    # Run predictions with the loaded best model
    preds_sdf = best_model_e.transform(sdf_e) \
                            .withColumnRenamed("prediction", "predicted_energy_consumption")

    # Drop context cols from preds before re-joining to avoid duplicates
    cols_to_drop = [c for c in context_cols_e if c != "_row_id" and c in preds_sdf.columns]
    preds_sdf = preds_sdf.drop(*cols_to_drop)

    # Re-attach context columns (timestamp, area, zone, actual vehicle_count, etc.)
    preds_sdf = preds_sdf.join(sdf_e_context, on="_row_id", how="left").drop("_row_id")
    return preds_sdf

# Pollution prediction function
def predict_pollution(sdf_p):
    """
    Apply Stage-2 Pollution feature engineering + preprocessing on a PySpark
    DataFrame, then return the DataFrame with a 'predicted_AQI' column.
    Mirrors the feature engineering logic from model.ipynb (Pollution section).
    """
    # Feature Engineering
    # Temperature-Humidity interaction
    if "temp_humidity_interaction" not in sdf_p.columns:
        sdf_p = sdf_p.withColumn(
            "temp_humidity_interaction",
            F.col("temperature") * F.col("humidity")
        )

    # Temperature inversion risk
    if "temp_inversion_risk" not in sdf_p.columns:
        sdf_p = sdf_p.withColumn(
            "temp_inversion_risk",
            F.col("temperature") / (F.col("humidity") + F.lit(1.0))
        )

     # Peak hour indicator
    if "peak_hour" not in sdf_p.columns:
        sdf_p = sdf_p.withColumn(
            "peak_hour",
            F.when(
                ((F.col("hour") >= 7)  & (F.col("hour") <= 10)) |
                ((F.col("hour") >= 11) & (F.col("hour") <= 16)) |
                ((F.col("hour") >= 17) & (F.col("hour") <= 21)),
                1
            ).otherwise(0)
        )
    
    # Low humidity flag
    if "low_humidity_flag" not in sdf_p.columns:
        sdf_p = sdf_p.withColumn(
            "low_humidity_flag",
            (F.col("humidity") < 45).cast("int")
        )

    # Lag features — no history in streaming; fill with 0
    if "aqi_lag1" not in sdf_p.columns:
        sdf_p = sdf_p.withColumn("aqi_lag1", F.lit(0.0))
    if "aqi_lag2" not in sdf_p.columns:
        sdf_p = sdf_p.withColumn("aqi_lag2", F.lit(0.0))

    # Rename PM2.5 -> PM2_5 for consistency with training data
    if "PM2.5" in sdf_p.columns:
        sdf_p = sdf_p.withColumnRenamed("PM2.5", "PM2_5")

    # ── Add surrogate row key to re-join context columns post-prediction ──
    sdf_p = sdf_p.withColumn("_row_id", F.monotonically_increasing_id())

    context_cols_p = [c for c in
                      ["_row_id", "timestamp", "area", "zone",
                       "AQI", "PM2_5", "PM10", "NO2", "CO"]
                      if c in sdf_p.columns]
    sdf_p_context = sdf_p.select(context_cols_p)

    # Area frequency encoding - join against lookup DataFrame
    sdf_p = sdf_p.join(area_freq_sdf_p, on="area", how="left") \
                 .fillna({"area_enc_p": 0.0})

    # Drop columns not used in training
    drop_cols_p = ['timestamp', 'PM2_5', 'PM10', 'NO2', 'CO', 'AQI', 'area']
    sdf_p = sdf_p.drop(*[c for c in drop_cols_p if c in sdf_p.columns])

    # Apply saved Encoding pipeline
    sdf_p = encoder_p.transform(sdf_p)

    # Apply saved Scaling pipeline
    sdf_p = scaler_p.transform(sdf_p)

    # Assemble final feature vector
    missing_cols_p = [c for c in final_feat_p if c not in sdf_p.columns]
    if missing_cols_p:
        raise ValueError(f"Missing features for pollution model: {missing_cols_p}")
    assembler_p = VectorAssembler(
        inputCols=final_feat_p, outputCol="features", handleInvalid="keep")
    sdf_p = assembler_p.transform(sdf_p)

    # Run predictions with the loaded best model
    preds_sdf = best_model_p.transform(sdf_p) \
                            .withColumnRenamed("prediction", "predicted_AQI")

    # Drop context cols from preds before re-joining to avoid duplicates
    cols_to_drop = [c for c in context_cols_p if c != "_row_id" and c in preds_sdf.columns]
    preds_sdf = preds_sdf.drop(*cols_to_drop)

    # Re-attach context columns (timestamp, area, zone, actual vehicle_count, etc.)
    preds_sdf = preds_sdf.join(sdf_p_context, on="_row_id", how="left").drop("_row_id")
    return preds_sdf

# ══════════════════════════════════════════════════════════════════
#  TRAFFIC ETL + PREDICTION
# ══════════════════════════════════════════════════════════════════
def run_traffic_etl_predict(df_t):
    log.info("\n" + "="*60)
    log.info("  TRAFFIC — ETL + PREDICTION  ")
    log.info("="*60)

    # ── Data Inspection ───────────────────────────────────────────
    df_t.persist(StorageLevel.MEMORY_AND_DISK)
    rows_t = df_t.count()
    log.info(f"\nRows: {rows_t} | Columns: {len(df_t.columns)}")
    df_t.printSchema()
    df_t.show(5, truncate=False)

    # ── Preprocessing ─────────────────────────────────────────────
    log.info("\nNull counts (before):")
    null_counts(df_t)

    # Fill missing values for categorical columns
    known_default = {
        'incident': 'No Incident',
        'severity': 'No Severity',
        'event': 'No Event'
    }
    for col_name, default_value in known_default.items():
        df_t = df_t.withColumn(
            col_name,
            when(is_null_like(col_name), default_value)
            .otherwise(col(col_name))
        )

    # Duplicate count + drop
    total_before_t = df_t.count()
    df_t = df_t.dropDuplicates()
    log.info(f"Duplicates removed: {total_before_t - df_t.count()}")

    # Drop unused column from training
    if "generator_version" in df_t.columns:
        df_t = df_t.drop("generator_version")
        log.info("Dropped column: generator_version")

    # Timestamp parsing + time feature extraction
    df_t = df_t.withColumn(
        "timestamp",
        F.to_timestamp(col("timestamp"))
    ).filter(col("timestamp").isNotNull())

    if df_t.rdd.isEmpty():
        log.warning("Empty traffic batch after timestamp filtering")
        return df_t

    df_t = df_t \
        .withColumn('hour',      F.hour('timestamp')) \
        .withColumn('day',       F.dayofmonth('timestamp')) \
        .withColumn('dayofweek', ((F.dayofweek('timestamp') + 5) % 7)) \
        .withColumn('month',     F.month('timestamp')) \
        .withColumn('year',      F.year('timestamp'))
    
    log.info("\nAfter timestamp parsing:")
    df_t.printSchema()

    # ── Outlier Detection ─────────────────────────────────────────
    features_t = ['vehicle_count', 'avg_speed', 'signal_wait_time']
    df_t.select(features_t).describe().show()
 
    log.info("\nOutlier counts (before capping):")
    for c in features_t:
        log.info(f"  {c}: {count_outliers(df_t, c)}")

    # Boxplot before capping
    traffic_sample_pd = df_t.select(features_t).toPandas()
    plt.figure(figsize=(10, 8))
    for i, feat in enumerate(features_t, 1):
        plt.subplot(1, 3, i)
        sns.boxplot(x=traffic_sample_pd[feat])
        plt.title(f"{feat} Outliers")
    plt.tight_layout()
    save_plot("traffic_outliers_before")

    # ── Imputation ────────────────────────────────────────────────
    df_t = impute_df(df_t)

    log.info("\nNull counts (after imputation):")
    null_counts(df_t)

    # ── Consistency Checks ────────────────────────────────────────
    log.info("\nConsistency checks:")
    log.info(f"  Invalid vehicle_count (<0): {df_t.filter(F.col('vehicle_count') < 0).count()}")
    log.info(f"  Invalid avg_speed (<0 or >120): {df_t.filter((F.col('avg_speed') < 0) | (F.col('avg_speed') > 120)).count()}")
    log.info(f"  Invalid signal_wait_time (<0 or >300): {df_t.filter((F.col('signal_wait_time') < 0) | (F.col('signal_wait_time') > 300)).count()}")
    log.info(f"  Low congestion + high vehicles: {df_t.filter((F.col('congestion_level') == 'Low') & (F.col('vehicle_count') > 800)).count()}")
    log.info(f"  High speed during heavy rain: {df_t.filter((F.col('weather') == 'Heavy Rain') & (F.col('avg_speed') > 60)).count()}")
    log.info(f"  Low traffic + high wait: {df_t.filter((F.col('vehicle_count') < 100) & (F.col('signal_wait_time') > 200)).count()}")

    # ── Outlier Handling ──────────────────────────────────────────
    bounds_t = {}
    for c in features_t:
        df_t, lo, hi = cap_outliers_spark(df_t, c)
        bounds_t[c] = (lo, hi)
 
    log.info("\nOutlier counts (after capping):")
    for c in features_t:
        lo, hi = bounds_t[c]
        log.info(f" {c}: {count_outliers_with_bounds(df_t, c, lo, hi)}")
 
    df_t.printSchema()
    log.info(f"Final row count: {df_t.count()}")

    # ── Visualizations ────────────────────────────────────────────
    t_pd = df_t.toPandas()

    # DISTRIBUTION ANALYSIS
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, feat_col in zip(axes, ['vehicle_count', 'avg_speed', 'signal_wait_time']):
        sns.violinplot(y=t_pd[feat_col], ax=ax, inner='quartile', color='steelblue')
        ax.set_title(f"{feat_col} Distribution")
    plt.suptitle("Feature Distributions (Violin)")
    plt.tight_layout()
    save_plot("traffic_distribution")

    # CORRELATION HEATMAP
    plt.figure(figsize=(8,5))
    corr_t = t_pd[['vehicle_count','avg_speed','signal_wait_time','hour']].corr()
    sns.heatmap(corr_t, annot=True, fmt='.2f', annot_kws={"size": 11}, cmap='coolwarm')
    plt.title("Feature Correlation")
    save_plot("traffic_correlation")

    # TIME - BASED BEHAVIOR
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    pivot_hm = t_pd.pivot_table(
        values='vehicle_count', index='hour', columns='dayofweek', aggfunc='mean'
    )
    day_names = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    pivot_hm.columns = [day_names[c] for c in pivot_hm.columns]
    sns.heatmap(pivot_hm, cmap='YlOrRd', annot=False, fmt='.0f', linewidths=0.3, ax=axes[0,0])
    axes[0,0].set_title("Avg Vehicle Count — Hour × Day of Week")
    axes[0,0].set_xlabel("Day of Week")
    axes[0,0].set_ylabel("Hour of Day")

    daily_t = t_pd.groupby('dayofweek')[['vehicle_count','avg_speed']].mean()
    day_names = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    daily_t.index = [day_names[i] for i in daily_t.index]
    daily_t.plot(ax=axes[0,1], colormap='tab10')
    axes[0,1].set_title("Day-of-Week Traffic Behavior")
    axes[0,1].set_ylabel("Average Value")
    axes[0,1].tick_params(axis='x', rotation=0)

    yoy_t = t_pd.groupby('year')['vehicle_count'].mean()
    yoy_t.plot(ax=axes[1,0], color='steelblue')
    axes[1,0].set_title("Year-over-Year Average Vehicle Count (2% growth factor visible)")
    axes[1,0].set_ylabel("Avg Vehicle Count")
    axes[1,0].tick_params(axis='x', rotation=0)

    axes[1,1].axis('off')
    plt.tight_layout()
    save_plot("traffic_time_behavior")

    # WEATHER × SEASON IMPACT ANALYSIS
    season_weather = t_pd.groupby(
        ['season', 'weather'])['vehicle_count'].mean().reset_index()
    plt.figure(figsize=(12, 5))
    sns.barplot(x='season', y='vehicle_count', hue='weather', data=season_weather)
    plt.title("Vehicle Count by Season × Weather Interaction")
    plt.ylabel("Avg Vehicle Count")
    plt.legend(title='Weather', loc='upper right')
    save_plot("traffic_season_weather")

    # INCIDENT, ROAD TYPE AND ZONE IMPACT ANALYSIS
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    sns.boxplot(x='incident', y='avg_speed', data=t_pd, palette='Set2', ax=axes[0,0])
    axes[0,0].set_title("Incident Impact on Speed")
    axes[0,0].tick_params(axis='x', rotation=45)

    sns.barplot(x='road_type', y='avg_speed', data=t_pd, palette='Blues_d', ax=axes[0,1])
    axes[0,1].set_title("Road Type vs Speed")
    axes[0,1].tick_params(axis='x', rotation=45)

    sns.boxplot(x='zone', y='vehicle_count', data=t_pd,
               palette='Set3', order=['Central','East','South','West','North'], ax=axes[1,0])
    axes[1,0].set_title("Vehicle Count Spread by Zone")
    axes[1,0].set_ylabel("Vehicle Count")
    axes[1,0].tick_params(axis='x', rotation=45)

    axes[1,1].axis('off')
    plt.tight_layout()
    save_plot("traffic_incident_road_zone")

    # ── ML Prediction ─────────────────────────────────────────────
    log.info("\nRunning traffic predictions...")
    try:
        # Required columns check
        required_cols_t = [
            "vehicle_count",
            "avg_speed",
            "weather",
            "road_type",
            "zone",
            "incident",
            "season",
            "is_weekend",
            "is_it_hub",
            "event",
            "area",
            "hour",
            "day",
            "dayofweek",
            "month",
            "year"
        ]
        missing_cols_t = [c for c in required_cols_t if c not in df_t.columns]
        if missing_cols_t:
            log.error(f"Missing columns for prediction: {missing_cols_t}")
            return df_t

        df_t_pred = predict_traffic(df_t)
        sample_preds = (
            df_t_pred.select("predicted_vehicle_count")
            .limit(3).toPandas()["predicted_vehicle_count"].values
        )
        log.info(f"  Predictions done — sample: {sample_preds}")
        
        # Prediction vs Actual scatter (actual available in streaming batch)
        if "vehicle_count" in df_t_pred.columns and "predicted_vehicle_count" in df_t_pred.columns:
            scatter_pd = df_t_pred.select(
                "vehicle_count", "predicted_vehicle_count"
            ).toPandas()
            plt.figure(figsize=(7, 5))
            plt.scatter(scatter_pd["vehicle_count"],
                        scatter_pd["predicted_vehicle_count"],
                        alpha=0.3, s=10, color="steelblue")
            mn_t = scatter_pd["vehicle_count"].min()
            mx_t = scatter_pd["vehicle_count"].max()
            plt.plot([mn_t, mx_t], [mn_t, mx_t], "r--", lw=2)
            plt.xlabel("Actual Vehicle Count")
            plt.ylabel("Predicted Vehicle Count")
            plt.title("Traffic — Actual vs Predicted")
            plt.tight_layout()
            save_plot("traffic_actual_vs_predicted")

        df_t = df_t_pred
    except Exception as exc:
        log.error(f"  Traffic prediction error: {exc}")
        traceback.print_exc()
        
    log.info(f"\nFinal Traffic rows: {df_t.count()}")
    df_t.unpersist()
    return df_t

# ══════════════════════════════════════════════════════════════════
#  ENERGY ETL + PREDICTION
# ══════════════════════════════════════════════════════════════════
def run_energy_etl_predict(df_e):
    log.info("\n" + "="*60)
    log.info("  ENERGY — ETL + PREDICTION  ")
    log.info("="*60)

    # ── Data Inspection ───────────────────────────────────────────
    df_e.persist(StorageLevel.MEMORY_AND_DISK)
    rows_e = df_e.count()
    log.info(f"\nRows: {rows_e} | Columns: {len(df_e.columns)}")
    df_e.printSchema()
    df_e.show(5, truncate=False)

    # ── Preprocessing ─────────────────────────────────────────────
    log.info("\nNull counts (before):")
    null_counts(df_e)

    # Duplicate count + drop
    total_before_e = df_e.count()
    df_e  = df_e.dropDuplicates()
    log.info(f"Duplicates removed: {total_before_e - df_e.count()}")

    # Drop unused column from training
    if "generator_version" in df_e.columns:
        df_e = df_e.drop("generator_version")
        log.info("Dropped column: generator_version")

    # Timestamp parsing + time feature extraction
    df_e = df_e.withColumn(
        "timestamp",
        F.to_timestamp(col("timestamp"))
    ).filter(col("timestamp").isNotNull())

    if df_e.rdd.isEmpty():
        log.warning("Empty energy batch after timestamp filtering")
        return df_e

    df_e = df_e \
        .withColumn('hour',      F.hour('timestamp')) \
        .withColumn('day',       F.dayofmonth('timestamp')) \
        .withColumn('dayofweek', ((F.dayofweek('timestamp') + 5) % 7)) \
        .withColumn('month',     F.month('timestamp')) \
        .withColumn('year',      F.year('timestamp'))
    
    log.info("\nAfter timestamp parsing:")
    df_e.printSchema()

    # ── Outlier Detection ─────────────────────────────────────────
    features_e = ['energy_consumption','temperature','humidity','renewable_usage']
    df_e.select(features_e).describe().show()

    log.info("\nOutlier counts (before capping):")
    for c in features_e:
        log.info(f" {c}: {count_outliers(df_e, c)}")

    # Boxplot before capping
    e_before = df_e.select(features_e).toPandas()
    fig, axes = plt.subplots(1, len(features_e), figsize=(15, 5))
    for ax, c in zip(axes, features_e):
        sns.boxplot(x=e_before[c], ax=ax)
        ax.set_title(f"{c} — Before Capping")
    plt.tight_layout()
    save_plot("energy_outliers_before")

    # ── Imputation ────────────────────────────────────────────────
    df_e = impute_df(df_e)
    log.info("\nNull counts (after imputation):")
    null_counts(df_e)

    # ── Consistency Checks ────────────────────────────────────────
    log.info("\nConsistency checks:")
    log.info(f"  Invalid energy_consumption (<0): {df_e.filter(F.col('energy_consumption') < 0).count()}")
    log.info(f"  Invalid temperature (<-50 or >60): {df_e.filter((F.col('temperature') < -50) | (F.col('temperature') > 60)).count()}")
    log.info(f"  Invalid humidity (<0 or >100): {df_e.filter((F.col('humidity') < 0) | (F.col('humidity') > 100)).count()}")
    log.info(f"  Invalid renewable (<0 or >100): {df_e.filter((F.col('renewable_usage') < 0) | (F.col('renewable_usage') > 100)).count()}")
    log.info(f"  High demand but energy <3000: {df_e.filter((F.col('demand_level') == 'High') & (F.col('energy_consumption') < 3000)).count()}")
    log.info(f"  Low demand but energy >6500: {df_e.filter((F.col('demand_level') == 'Low') & (F.col('energy_consumption') > 6500)).count()}")
    log.info(f"  Night (0-5hr) but renewable >20: {df_e.filter(F.col('hour').isin([0, 1, 2, 3, 4, 5]) & (F.col('renewable_usage') > 20)).count()}")
    log.info(f"  Day (10-16hr) but renewable <1: {df_e.filter(F.col('hour').between(10, 16) & (F.col('renewable_usage') < 1)).count()}")

    # ── Outlier Handling ──────────────────────────────────────────
    bounds_e = {}
    for c in features_e:
        df_e, lo, hi = cap_outliers_spark(df_e, c)
        bounds_e[c] = (lo, hi)
 
    log.info("\nOutlier counts (after capping):")
    for c in features_e:
        lo, hi = bounds_e[c]
        log.info(f"{c}: {count_outliers_with_bounds(df_e, c, lo, hi)}")
 
    df_e.printSchema()
    log.info(f"Final row count: {df_e.count()}")

    # ── Visualizations ────────────────────────────────────────────
    e_pd = df_e.toPandas()

    # DISTRIBUTION ANALYSIS
    plt.figure(figsize=(15, 5))
    plt.subplot(1, 3, 1)
    for lt in e_pd['load_type'].unique():
        sns.kdeplot(e_pd[e_pd['load_type']==lt]['energy_consumption'],
                    label=lt, fill=True, alpha=0.3)
    plt.title("Energy Consumption KDE by Load Type")
    plt.legend()
    plt.subplot(1, 3, 2)
    for lt in e_pd['load_type'].unique():
        sns.kdeplot(e_pd[e_pd['load_type']==lt]['temperature'],
                    label=lt, fill=True, alpha=0.3)
    plt.title("Temperature KDE by Load Type")
    plt.legend()
    plt.subplot(1, 3, 3)
    for lt in e_pd['load_type'].unique():
        sns.kdeplot(e_pd[e_pd['load_type']==lt]['humidity'],
                    label=lt, fill=True, alpha=0.3)
    plt.title("Humidity KDE by Load Type")
    plt.legend()
    plt.tight_layout()
    save_plot("energy_kde_loadtype")

    # Weather × Load Type
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    sns.boxplot(x='weather', y='energy_consumption',
                data=e_pd, ax=axes[0], palette='Blues')
    axes[0].set_title("Energy Distribution by Weather")
    sns.boxplot(x='load_type', y='energy_consumption',
                data=e_pd, ax=axes[1], palette='Greens')
    axes[1].set_title("Energy Distribution by Load Type")
    plt.tight_layout()
    save_plot("energy_weather_loadtype")

    # TIME - BASED BEHAVIOUR
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    pivot_e = e_pd.pivot_table(
        values='energy_consumption', index='hour',
        columns='load_type', aggfunc='mean'
    )
    sns.heatmap(pivot_e, cmap='YlOrRd', annot=True, fmt='.0f',
                linewidths=0.3, annot_kws={'size': 9}, ax=axes[0,0])
    axes[0,0].set_title("Avg Energy Consumption — Hour × Load Type")
    axes[0,0].set_xlabel("Load Type")
    axes[0,0].set_ylabel("Hour of Day")

    hourly_e_wk = e_pd.groupby(
        ['hour','is_weekend'])['energy_consumption'].mean().reset_index()
    hourly_e_wk['Day type'] = hourly_e_wk['is_weekend'].map({0:'Weekday', 1:'Weekend'})
    sns.lineplot(x='hour', y='energy_consumption', hue='Day type',
                data=hourly_e_wk, palette=['steelblue','tomato'], ax=axes[0,1])
    axes[0,1].set_title("Hourly Energy — Weekday vs Weekend")
    axes[0,1].set_ylabel("Avg Energy Consumption")

    pivot_sz = e_pd.pivot_table(
        values='energy_consumption', index='season',
        columns='zone', aggfunc='mean'
    )
    sns.heatmap(pivot_sz, cmap='YlOrRd', annot=True, fmt='.0f',
                linewidths=0.3, annot_kws={'size': 10}, ax=axes[1,0])
    axes[1,0].set_title("Avg Energy Consumption — Season × Zone")
    axes[1,1].axis('off')
    plt.tight_layout()
    save_plot("energy_time_behavior")

    # ENVIRONMENT IMPACT
    plt.figure(figsize=(15,5))

    plt.subplot(1,2,1)
    sample_e = e_pd.sample(min(5000, len(e_pd)), random_state=42)
    sns.scatterplot(x='temperature', y='energy_consumption',
                    data=sample_e, alpha=0.2, color='steelblue')
    # regression line
    z = np.polyfit(sample_e['temperature'], sample_e['energy_consumption'], 2)
    p = np.poly1d(z)
    x_line = np.linspace(sample_e['temperature'].min(), sample_e['temperature'].max(), 100)
    plt.plot(x_line, p(x_line), 'r--', lw=2, label='Trend')
    plt.title("Temperature vs Energy (U-shaped relationship)")
    plt.legend()

    plt.subplot(1,2,2)
    sns.scatterplot(x='humidity', y='energy_consumption', data=sample_e, alpha=0.2, color='teal')
    plt.title("Humidity vs Energy")
    plt.tight_layout()
    save_plot("energy_environment")

    # SYSTEM BEHAVIOUR
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    sns.barplot(x='power_outage', y='energy_consumption',
                data=e_pd, palette='RdYlGn_r', ax=axes[0])
    axes[0].set_title("Power Outage Impact on Energy Consumption")
    axes[0].set_xticks([0, 1])
    axes[0].set_xticklabels(['No Outage', 'Outage'])

    sns.scatterplot(x='renewable_usage', y='energy_consumption',
                    hue='load_type', data=sample_e, alpha=0.3, palette='Set1', ax=axes[1])
    axes[1].set_title("Renewable Usage vs Energy — by Load Type")
    axes[1].legend(title='Load Type')

    sns.histplot(e_pd['renewable_usage'], bins=50, kde=True, ax=axes[2])
    axes[2].set_title("Renewable Distribution")
    plt.tight_layout()
    save_plot("energy_system")

    # YEAR OVER YEAR ENERGY GROWTH
    yoy_e = e_pd.groupby('year')['energy_consumption'].mean()
    yoy_e.plot(figsize=(10, 4), color='seagreen')
    plt.title("Year-over-Year Average Energy Consumption")
    plt.ylabel("Avg Energy Consumption")
    plt.xticks(rotation=0)
    plt.tight_layout()
    save_plot("energy_yoy_growth")

    # CORRELATION HEATMAP
    plt.figure(figsize=(6,5))
    corr_cols_e = ['energy_consumption', 'temperature', 'humidity', 'renewable_usage']
    sns.heatmap(e_pd[corr_cols_e].corr(), annot=True, cmap='coolwarm')
    plt.title("Energy — Correlation Matrix")
    plt.tight_layout()
    save_plot("energy_correlation")

    # ── ML Prediction ─────────────────────────────────────────────
    log.info("\nRunning energy predictions...")
    try:
        # Required columns check
        required_cols_e = [
            "energy_consumption",
            "temperature",
            "humidity",
            "renewable_usage",
            "load_type",
            "zone",
            "weather",
            "season",
            "is_weekend",
            "is_it_hub",
            "power_outage",
            "area",
            "demand_level",
            "hour",
            "day",
            "dayofweek",
            "month",
            "year"
        ]
        missing_cols_e = [c for c in required_cols_e if c not in df_e.columns]
        if missing_cols_e:
            log.error(f"Missing columns for prediction: {missing_cols_e}")
            return df_e

        df_e_pred = predict_energy(df_e)
        sample_preds = (
            df_e_pred.select("predicted_energy_consumption")
            .limit(3).toPandas()["predicted_energy_consumption"].values
        )
        log.info(f"  Predictions done — sample: {sample_preds}")

        # Prediction vs Actual scatter (actual available in streaming batch)
        if "energy_consumption" in df_e_pred.columns and "predicted_energy_consumption" in df_e_pred.columns:
            scatter_pd = df_e_pred.select(
                "energy_consumption", "predicted_energy_consumption"
            ).toPandas()
            plt.figure(figsize=(7, 5))
            plt.scatter(scatter_pd["energy_consumption"],
                        scatter_pd["predicted_energy_consumption"],
                        alpha=0.3, s=10, color="seagreen")
            mn_e = scatter_pd["energy_consumption"].min()
            mx_e = scatter_pd["energy_consumption"].max()
            plt.plot([mn_e, mx_e], [mn_e, mx_e], "r--", lw=2)
            plt.xlabel("Actual Energy Consumption")
            plt.ylabel("Predicted Energy Consumption")
            plt.title("Energy — Actual vs Predicted")
            plt.tight_layout()
            save_plot("energy_actual_vs_predicted")

        df_e = df_e_pred
    except Exception as exc:
        log.error(f"  Energy prediction error: {exc}")
        traceback.print_exc()

    log.info(f"\nFinal Energy rows: {df_e.count()}")
    df_e.unpersist()
    return df_e

# ══════════════════════════════════════════════════════════════════
#  POLLUTION ETL + PREDICT
# ══════════════════════════════════════════════════════════════════
def run_pollution_etl_predict(df_p):
    log.info("\n" + "="*60)
    log.info("  POLLUTION — ETL + PREDICTION  ")
    log.info("="*60)

    # ── Data Inspection ───────────────────────────────────────────
    df_p.persist(StorageLevel.MEMORY_AND_DISK)
    rows_p = df_p.count()
    log.info(f"\nRows: {rows_p} | Columns: {len(df_p.columns)}")
    df_p.printSchema()
    df_p.show(5, truncate=False)

    # Rename PM2.5 → PM2_5 to match data.ipynb and model training convention
    if "PM2.5" in df_p.columns:
        df_p = df_p.withColumnRenamed("PM2.5", "PM2_5")

    # ── Preprocessing ─────────────────────────────────────────────
    log.info("\nNull counts (before):")
    null_counts(df_p)

    # Duplicate count + drop
    total_before_p = df_p.count()
    df_p = df_p.dropDuplicates()
    log.info(f"Duplicates removed: {total_before_p - df_p.count()}")

    # Drop unused column from training
    if "generator_version" in df_p.columns:
        df_p = df_p.drop("generator_version")
        log.info("Dropped column: generator_version")

    # Timestamp parsing + time feature extraction
    df_p = df_p.withColumn(
        "timestamp",
        F.to_timestamp(col("timestamp"))
    ).filter(col("timestamp").isNotNull())

    if df_p.rdd.isEmpty():
        log.warning("Empty pollution batch after timestamp filtering")
        return df_p

    df_p = df_p \
        .withColumn('hour',      F.hour('timestamp')) \
        .withColumn('day',       F.dayofmonth('timestamp')) \
        .withColumn('dayofweek', ((F.dayofweek('timestamp') + 5) % 7)) \
        .withColumn('month',     F.month('timestamp')) \
        .withColumn('year',      F.year('timestamp'))
    
    log.info("\nAfter timestamp parsing:")
    df_p.printSchema()

    # ── Outlier Detection ─────────────────────────────────────────
    features_p = ['AQI','PM2_5','PM10','NO2','CO','temperature','humidity']
    df_p.select(features_p).describe().show()

    log.info("\nOutlier counts (before capping):")
    for c in features_p:
        log.info(f" {c}: {count_outliers(df_p, c)}")

    # Boxplot before capping
    p_before = df_p.select(features_p).toPandas()
    fig, axes = plt.subplots(3, 3, figsize=(15, 10))
    for ax, c in zip(axes.flat, features_p):
        sns.boxplot(x=p_before[c], ax=ax)
        ax.set_title(f"{c} — Before Capping")
    for ax in axes.flat[len(features_p):]:
        ax.set_visible(False)
    plt.tight_layout()
    save_plot("pollution_outliers_before")

    # ── Imputation ────────────────────────────────────────────────
    df_p = impute_df(df_p)
    log.info("\nNull counts (after imputation):")
    null_counts(df_p)

    # ── Consistency Checks ────────────────────────────────────────
    log.info("\nConsistency checks:")
    for c in ['AQI', 'PM2_5', 'PM10', 'NO2', 'CO']:
        log.info(f"  Invalid {c} (<0): {df_p.filter(F.col(c) < 0).count()}")
    log.info(f"  Invalid temperature (<-50): {df_p.filter(F.col('temperature') < -50).count()}")
    log.info(f"  Invalid humidity (<0): {df_p.filter(F.col('humidity') < 0).count()}")

    # ── Outlier Handling ──────────────────────────────────────────
    bounds_p = {}
    for c in features_p:
        df_p, lo, hi = cap_outliers_spark(df_p, c)
        bounds_p[c] = (lo, hi)
 
    log.info("\nOutlier counts (after capping):")
    for c in features_p:
        lo, hi = bounds_p[c]
        log.info(f" {c}: {count_outliers_with_bounds(df_p, c, lo, hi)}")
 
    df_p.printSchema()
    log.info(f"Final row count: {df_p.count()}")

    # ── Visualizations ────────────────────────────────────────────
    p_pd = df_p.toPandas()

    # Distribution overlays (PM2.5 vs PM10, NO2 vs CO, AQI)
    plt.figure(figsize=(15, 5))
    plt.subplot(1, 3, 1)
    sns.kdeplot(p_pd['PM2_5'], label='PM2_5', fill=True, alpha=0.4)
    sns.kdeplot(p_pd['PM10'],  label='PM10',  fill=True, alpha=0.4)
    plt.axvline(p_pd['PM2_5'].mean(), color='blue', ls='--', lw=1.2, label='PM2_5 mean')
    plt.axvline(p_pd['PM10'].mean(),  color='orange', ls='--', lw=1.2, label='PM10 mean')
    plt.title("PM2.5 vs PM10 Distribution")
    plt.xlabel("Concentration (µg/m³)") 
    plt.ylabel("Density")
    plt.legend()

    plt.subplot(1, 3, 2)
    sns.kdeplot(p_pd['NO2'], label='NO2', fill=True, alpha=0.4)
    sns.kdeplot(p_pd['CO'] * 10, label='CO×10', fill=True, alpha=0.4)
    plt.title("NO2 and CO Distribution")
    plt.xlabel("Concentration (µg/m³)")  
    plt.ylabel("Density")
    plt.legend()

    plt.subplot(1, 3, 3)
    sns.kdeplot(p_pd['AQI'], fill=True, color='mediumpurple', alpha=0.5)
    plt.axvline(p_pd['AQI'].mean(), color='red', ls='--', lw=1.5, label='mean')
    plt.title("AQI Distribution")
    plt.xlabel("AQI Value")              
    plt.ylabel("Density")
    plt.legend()
    plt.tight_layout()
    save_plot("pollution_distribution_overlay")

    # CATEGORY ANALYSIS
    plt.figure(figsize=(18,5))

    plt.subplot(1,3,1)
    sns.violinplot(x='weather', y='AQI', data=p_pd,
                palette='Blues', inner='quartile')
    plt.title("AQI Distribution by Weather (Violin)")

    plt.subplot(1,3,2)
    sns.boxplot(x='season', y='AQI', data=p_pd,
                palette='Set2',
                order=['Summer','Monsoon','Winter'])
    plt.title("AQI by Season — Monsoon Washout vs Winter Inversion Visible")

    plt.subplot(1,3,3)
    sns.boxplot(x='zone', y='AQI', data=p_pd, palette='Set3')
    plt.title("AQI Spread by Zone")
    plt.xticks(rotation=45)

    plt.tight_layout()
    save_plot("pollution_category_analysis")

    # TIME SERIES ANALYSIS
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    pivot_hs = p_pd.pivot_table(
        values='AQI', index='hour', columns='season', aggfunc='mean'
    )
    sns.heatmap(pivot_hs, cmap='YlOrRd', annot=True, fmt='.0f',
                linewidths=0.3, annot_kws={'size': 9}, ax=axes[0,0])
    axes[0,0].set_title("Avg AQI — Hour × Season")
    axes[0,0].set_xlabel("Season")
    axes[0,0].set_ylabel("Hour of Day")

    daily_p = p_pd.groupby('dayofweek')['AQI'].mean()
    _day_names = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    daily_p.index = [_day_names[i] for i in daily_p.index]
    daily_p.plot(color='mediumpurple', ax=axes[0,1])
    axes[0,1].set_title("Day-of-Week Average AQI — Weekday Industrial Effect")
    axes[0,1].set_ylabel("Avg AQI")
    axes[0,1].tick_params(axis='x', rotation=0)

    sns.boxplot(x='year', y='AQI', data=p_pd,
                palette='YlOrRd', showfliers=False, ax=axes[1,0])
    axes[1,0].set_title("Year-over-Year AQI Distribution — Growth Trend Visible")
    axes[1,0].tick_params(axis='x', rotation=45)

    axes[1,1].axis('off')
    plt.tight_layout()
    save_plot("pollution_time_series")

    # RELATIONSHIP ANALYSIS
    plt.figure(figsize=(15,5))

    plt.subplot(1,3,1)
    sample_p = p_pd.sample(min(5000, len(p_pd)), random_state=42)
    sns.scatterplot(x='PM2_5', y='AQI', data=sample_p, alpha=0.2, color='mediumpurple')
    z_p = np.polyfit(sample_p['PM2_5'], sample_p['AQI'], 1)
    p_p = np.poly1d(z_p)
    x_p = np.linspace(sample_p['PM2_5'].min(), sample_p['PM2_5'].max(), 100)
    plt.plot(x_p, p_p(x_p), 'r--', lw=2, label=f'Ratio ≈ {z_p[0]:.2f}')
    plt.title("PM2_5 vs AQI (Linear ratio from generator visible)")
    plt.legend()

    plt.subplot(1,3,2)
    sns.scatterplot(x='temperature', y='AQI', data=sample_p, alpha=0.2, color='coral')
    plt.title("Temperature vs AQI — Thermal Inversion Effect")

    plt.subplot(1,3,3)
    sns.scatterplot(x='humidity', y='AQI', hue='weather',
                    data=sample_p, alpha=0.3, palette='Set1')
    plt.title("Humidity vs AQI — Washout Effect by Weather")
    plt.legend(title='Weather')
    plt.tight_layout()
    save_plot("pollution_relationships")

    # ADVANCED INSIGHTS
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    pivot_as = p_pd.pivot_table(
        values='AQI', index='area', columns='season', aggfunc='mean'
    ).sort_values('Winter', ascending=False)

    sns.heatmap(pivot_as, cmap='YlOrRd', annot=True, fmt='.0f',
                linewidths=0.3, annot_kws={'size': 8}, ax=axes[0])
    axes[0].set_title("Avg AQI by Area × Season")
    axes[0].set_xlabel("Season")
    axes[0].set_ylabel("Area")

    sns.barplot(x='is_it_hub', y='AQI', data=p_pd,
                palette=['steelblue','tomato'], ax=axes[1])
    axes[1].set_title("IT Hub Commercial Activity vs AQI")
    axes[1].set_xticks([0, 1])
    axes[1].set_xticklabels(['Non IT Hub', 'IT Hub'])

    sns.boxplot(x='is_weekend', y='AQI', data=p_pd,
                palette=['steelblue','seagreen'], ax=axes[2])
    axes[2].set_title("Weekend vs Weekday AQI — Industrial Emission Effect")
    axes[2].set_xticks([0, 1])
    axes[2].set_xticklabels(['Weekday', 'Weekend'])

    plt.tight_layout()
    save_plot("pollution_advanced_insights")

    # TREND SMOOTHING
    hourly_aqi = (p_pd.groupby('hour')['AQI'].mean()
                .rolling(3, min_periods=1).mean())
    hourly_aqi.plot(figsize=(14, 5), color='mediumpurple')
    plt.title("Smoothed AQI Trend (3hr rolling mean)")
    plt.ylabel("AQI (smoothed)")
    plt.xlabel("Hour of Day")
    plt.tight_layout()
    save_plot("pollution_trend_smoothing")

    # DENSITY PLOT
    plt.figure(figsize=(14, 5))
    cols_density = ['AQI','PM2_5','PM10','NO2']
    for feat_col in cols_density:
        sns.kdeplot(p_pd[feat_col], label=feat_col)
        plt.axvline(p_pd[feat_col].mean(), ls='--', lw=1, alpha=0.6)
    plt.legend()
    plt.title("Pollutant Density Distribution (dashed = mean)")
    plt.tight_layout()
    save_plot("pollution_density")

    # CORRELATION HEATMAP
    plt.figure(figsize=(7, 6))
    sns.heatmap(
        p_pd[['AQI','PM2_5','PM10','NO2','CO','temperature','humidity']].corr(),
        annot=True, fmt='.2f', cmap='coolwarm', annot_kws={'size': 9}
    )
    plt.title("Pollution Feature Correlation Matrix")
    plt.tight_layout()
    save_plot("pollution_correlation")

    # ── ML Prediction ─────────────────────────────────────────────
    log.info("\nRunning pollution predictions...")
    try:
        # Required columns check
        required_cols_p = [
            "AQI",
            "temperature",
            "humidity",
            "zone",
            "weather",
            "season",
            "is_weekend",
            "is_it_hub",
            "area",
            "hour",
            "day",
            "dayofweek",
            "month",
            "year"
        ]
        missing_cols_p = [c for c in required_cols_p if c not in df_p.columns]
        if missing_cols_p:
            log.error(f"Missing columns for prediction: {missing_cols_p}")
            return df_p
        
        df_p_pred = predict_pollution(df_p)
        sample_preds = (
            df_p_pred.select("predicted_AQI")
            .limit(3).toPandas()["predicted_AQI"].values
        )
        log.info(f"  Predictions done — sample: {sample_preds}")
        
        # Prediction vs Actual scatter (actual available in streaming batch)
        if "AQI" in df_p_pred.columns and "predicted_AQI" in df_p_pred.columns:
            scatter_pd = df_p_pred.select("AQI", "predicted_AQI").toPandas()
            plt.figure(figsize=(7, 5))
            plt.scatter(scatter_pd["AQI"],
                        scatter_pd["predicted_AQI"],
                        alpha=0.3, s=10, color="mediumpurple")
            mn_p = scatter_pd["AQI"].min()
            mx_p = scatter_pd["AQI"].max()
            plt.plot([mn_p, mx_p], [mn_p, mx_p], "r--", lw=2)
            plt.xlabel("Actual AQI")
            plt.ylabel("Predicted AQI")
            plt.title("Pollution — Actual vs Predicted")
            plt.tight_layout()
            save_plot("pollution_actual_vs_predicted")

        df_p = df_p_pred
    except Exception as exc:
        log.error(f"  Pollution prediction error: {exc}")
        traceback.print_exc()

    log.info(f"\nFinal Pollution rows: {df_p.count()}")
    df_p.unpersist()
    return df_p

# ══════════════════════════════════════════════════════════════════
#  KAFKA STREAMING - COLLECT MICRO-BATCHES
# ══════════════════════════════════════════════════════════════════
traffic_batches   = []
energy_batches    = []
pollution_batches = []

# Parse batches
def parse_batch(df_spark, schema):
    """Parse raw Kafka bytes → structured PySpark DataFrame."""
    return (
        df_spark.selectExpr("CAST(value AS STRING) as json_str") \
        .select(F.from_json(F.col("json_str"), schema).alias("d")) \
        .select("d.*")
    )

# Parse traffic batch
def process_traffic_batch(df_spark_t, batch_id_t):
    if df_spark_t.rdd.isEmpty(): 
        return
    parsed_t = parse_batch(df_spark_t, traffic_schema)
    traffic_batches.append(parsed_t)
    log.info(f"  Traffic batch {batch_id_t} received — rows: {parsed_t.count()}")

# Parse energy batch
def process_energy_batch(df_spark_e, batch_id_e):
    if df_spark_e.rdd.isEmpty(): 
        return
    parsed_e = parse_batch(df_spark_e, energy_schema)
    energy_batches.append(parsed_e)
    log.info(f"  Energy batch {batch_id_e} received — rows: {parsed_e.count()}")

# Parse pollution batch
def process_pollution_batch(df_spark_p, batch_id_p):
    if df_spark_p.rdd.isEmpty(): 
        return
    parsed_p = parse_batch(df_spark_p, pollution_schema)
    pollution_batches.append(parsed_p)
    log.info(f"  Pollution batch {batch_id_p} received — rows: {parsed_p.count()}")

# Read stream from Kafka
def read_stream(topic: str):
    return (
        spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribe", topic) \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .option("maxOffsetsPerTrigger", 1000) \
        .load()
    )

# ── Start streaming ────────────────────────────────────────────────
q_traffic = (
    read_stream("traffic_topic").writeStream \
    .foreachBatch(process_traffic_batch) \
    .option("checkpointLocation", "/tmp/checkpoint/traffic") \
    .trigger(processingTime=TRIGGER_SECS) \
    .start()
)

q_energy = (
    read_stream("energy_topic").writeStream \
    .foreachBatch(process_energy_batch) \
    .option("checkpointLocation", "/tmp/checkpoint/energy") \
    .trigger(processingTime=TRIGGER_SECS) \
    .start()
)

q_pollution = (
    read_stream("pollution_topic").writeStream \
    .foreachBatch(process_pollution_batch) \
    .option("checkpointLocation", "/tmp/checkpoint/pollution") \
    .trigger(processingTime=TRIGGER_SECS) \
    .start()
)

log.info(f"\nStreaming — collecting data for {COLLECT_SECS} seconds...")
log.info("Start producer.py now in a separate terminal if not already running.\n")
time.sleep(COLLECT_SECS)

q_traffic.stop()
q_energy.stop()
q_pollution.stop()
log.info("Streaming stopped — starting ETL + prediction pipeline...")

# ══════════════════════════════════════════════════════════════════
#  MERGE BATCHES → RUN PIPELINE → SAVE
# ══════════════════════════════════════════════════════════════════
# Merge all micro-batches into a single DataFrame
def merge_batches(batches):
    """Union all collected micro-batches into a single DataFrame."""
    if not batches:
        return None
    result = batches[0]
    for b in batches[1:]:
        result = result.union(b)
    return result
 
 # Save outputs
def save_outputs(df, name: str):
    """Save DataFrame as CSV (output/) and Parquet (per-dataset subdir)."""
    csv_path     = f'{OUTPUT_DIR}/{name}_predictions.csv'
    parquet_path = f'{PARQUET_DIRS.get(name, PARQUET_DIR)}/{name}_predictions'
 
    pdf_out = df.toPandas()
    if "timestamp" in pdf_out.columns:          
        pdf_out["timestamp"] = pd.to_datetime(
            pdf_out["timestamp"], errors="coerce"
        ).dt.tz_localize(None) 
    n_rows  = len(pdf_out)
    log.info(f"  Saving {name}: {n_rows:,} rows, columns: {list(pdf_out.columns)}")
 
    pdf_out.to_csv(csv_path, index=False)
    log.info(f"  CSV     → {csv_path}")
 
    # Drop duplicate columns before writing parquet (parquet is strict about this)
    seen = set()
    dedup_cols = [c for c in df.columns if not (c in seen or seen.add(c))]
    df.select(dedup_cols).write.mode('overwrite').parquet(parquet_path)
    log.info(f"  Parquet → {parquet_path}/")
 
# ── Traffic ────────────────────────────────────────────────────────
traffic_all = merge_batches(traffic_batches)
if traffic_all:
    traffic_final = run_traffic_etl_predict(traffic_all)
    save_outputs(traffic_final, 'traffic')
else:
    log.warning("⚠  No traffic data received — check producer is running")
 
# ── Energy ─────────────────────────────────────────────────────────
energy_all = merge_batches(energy_batches)
if energy_all:
    energy_final = run_energy_etl_predict(energy_all)
    save_outputs(energy_final, 'energy')
else:
    log.warning("⚠  No energy data received — check producer is running")
 
# ── Pollution ──────────────────────────────────────────────────────
pollution_all = merge_batches(pollution_batches)
if pollution_all:
    pollution_final = run_pollution_etl_predict(pollution_all)
    save_outputs(pollution_final, 'pollution')
else:
    log.warning("⚠  No pollution data received — check producer is running")

# ══════════════════════════════════════════════════════════════════
#  WRITE MODEL METRICS JSON  — read by app.py dashboard
#  app.py calls load_model_metrics() which expects output/model_metrics.json
#  Schema: { "traffic": {model, mae, rmse, r2, trained_rows, features, trained_at}, ... }
# ══════════════════════════════════════════════════════════════════
import json as _json
from datetime import datetime as _datetime

def _extract_metrics(metadata: dict, stream_key: str) -> dict:
    k = stream_key[0]  # "t", "e", "p"

    mae          = metadata.get(f"mae_{k}")
    rmse         = metadata.get(f"rmse_{k}")
    r2           = metadata.get(f"r2_{k}")
    trained_rows = metadata.get(f"trained_rows_{k}")
    features     = metadata.get(f"final_feature_cols_{k}")
    model_name   = metadata.get(f"best_name_{k}")

    if isinstance(features, (list, tuple)):
        features_str = ", ".join(str(f) for f in features)
    elif features:
        features_str = str(features)
    else:
        features_str = None

    def fmt(v):
        try:    return round(float(v), 4)
        except: return None

    return {
        "model":        model_name,
        "mae":          fmt(mae),
        "rmse":         fmt(rmse),
        "r2":           fmt(r2),
        "trained_rows": int(trained_rows) if trained_rows else None,
        "features":     features_str,
        "trained_at":   _datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

# Call stays simple — no results/best_name needed
model_metrics_out = {
    "traffic":   _extract_metrics(traffic_metadata,   "traffic"),
    "energy":    _extract_metrics(energy_metadata,    "energy"),
    "pollution": _extract_metrics(pollution_metadata, "pollution"),
}

metrics_path = os.path.join(OUTPUT_DIR, "model_metrics.json")
with open(metrics_path, "w") as _f:
    _json.dump(model_metrics_out, _f, indent=2)
log.info(f"Model metrics written → {metrics_path}")
  
# ══════════════════════════════════════════════════════════════════
#  FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════
log.info("\n" + "="*60)
log.info("  STAGE-3 COMPLETE - SMART CITY ANALYTICS")
log.info("="*60)
log.info(f"  Plots   → {PLOT_DIR}/")
log.info(f"  CSV     → {OUTPUT_DIR}/")
log.info(f"  Parquet → {PARQUET_DIR}/")
log.info("="*60)
 
spark.stop()
log.info("Spark session stopped.")