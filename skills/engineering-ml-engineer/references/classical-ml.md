# Classical Machine Learning Patterns

Production-grade patterns for scikit-learn, XGBoost, LightGBM, feature engineering, and model evaluation.

## scikit-learn Pipeline with ColumnTransformer

```python
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Load data
df = pd.read_csv("data.csv")
X = df.drop(columns=["target"])
y = df["target"]

# Identify column types
numeric_features = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
categorical_features = X.select_dtypes(include=["object", "category"]).columns.tolist()

# Numeric preprocessing: impute missing + scale
numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

# Categorical preprocessing: impute missing + encode
categorical_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])

# Combine preprocessing
preprocessor = ColumnTransformer(
    transformers=[
        ("num", numeric_transformer, numeric_features),
        ("cat", categorical_transformer, categorical_features),
    ],
    remainder="drop",  # Drop columns not explicitly listed
)

# Full pipeline: preprocessing + model
pipeline = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )),
])

# Split and train
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

pipeline.fit(X_train, y_train)
score = pipeline.score(X_test, y_test)
print(f"Accuracy: {score:.4f}")

# Predict with the full pipeline (handles all preprocessing automatically)
predictions = pipeline.predict(X_test)
probabilities = pipeline.predict_proba(X_test)
```

## XGBoost with Early Stopping and SHAP

```python
import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

# Load data
df = pd.read_csv("data.csv")
X = df.drop(columns=["target"])
y = df["target"]

X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

# XGBoost with early stopping
model = xgb.XGBClassifier(
    n_estimators=1000,           # High number -- early stopping will find optimal
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,               # Row sampling
    colsample_bytree=0.8,        # Column sampling
    min_child_weight=5,
    reg_alpha=0.1,               # L1 regularization
    reg_lambda=1.0,              # L2 regularization
    scale_pos_weight=1.0,        # Set to sum(negative) / sum(positive) for imbalanced
    objective="binary:logistic",
    eval_metric="logloss",
    tree_method="hist",          # Fast histogram-based method
    random_state=42,
    n_jobs=-1,
    early_stopping_rounds=50,
)

model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    verbose=100,
)

print(f"Best iteration: {model.best_iteration}")
print(f"Best score: {model.best_score:.4f}")

# Evaluate
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]
print(classification_report(y_test, y_pred))
print(f"AUC-ROC: {roc_auc_score(y_test, y_proba):.4f}")

# Feature importance (built-in)
importance = model.feature_importances_
feature_importance = pd.DataFrame({
    "feature": X.columns,
    "importance": importance
}).sort_values("importance", ascending=False)
print(feature_importance.head(20))

# SHAP explanations (more reliable than built-in importance)
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Summary plot showing feature impact
shap.summary_plot(shap_values, X_test)

# Single prediction explanation
shap.force_plot(explainer.expected_value, shap_values[0], X_test.iloc[0])

# Dependence plot for a specific feature
shap.dependence_plot("feature_name", shap_values, X_test)
```

## LightGBM for Large Datasets

```python
import lightgbm as lgb
from sklearn.model_selection import train_test_split

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# LightGBM native API (faster than sklearn API for large data)
train_data = lgb.Dataset(X_train, label=y_train)
val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

params = {
    "objective": "binary",
    "metric": "binary_logloss",
    "boosting_type": "gbdt",
    "num_leaves": 31,            # Main parameter for complexity
    "learning_rate": 0.05,
    "feature_fraction": 0.8,     # colsample_bytree equivalent
    "bagging_fraction": 0.8,     # subsample equivalent
    "bagging_freq": 5,
    "min_child_samples": 20,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "verbose": -1,
    "n_jobs": -1,
    "seed": 42,
}

callbacks = [
    lgb.early_stopping(stopping_rounds=50),
    lgb.log_evaluation(period=100),
]

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[val_data],
    callbacks=callbacks,
)

# Predict
y_pred_proba = model.predict(X_test)  # Returns probabilities for binary
y_pred = (y_pred_proba > 0.5).astype(int)

# Feature importance
importance = pd.DataFrame({
    "feature": X.columns,
    "importance": model.feature_importance(importance_type="gain"),
}).sort_values("importance", ascending=False)

# LightGBM sklearn API (for use in Pipeline)
from lightgbm import LGBMClassifier

lgb_model = LGBMClassifier(
    n_estimators=1000,
    num_leaves=31,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_samples=20,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=-1,
)

lgb_model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
)
```

## Hyperparameter Tuning

### GridSearchCV and RandomizedSearchCV

```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from scipy.stats import randint, uniform

# Stratified cross-validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# GridSearchCV -- exhaustive, use for small search spaces
param_grid = {
    "n_estimators": [100, 200, 500],
    "max_depth": [5, 10, 15, None],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42, n_jobs=-1),
    param_grid,
    cv=cv,
    scoring="f1_weighted",
    n_jobs=-1,
    verbose=1,
    refit=True,       # Retrain on full train set with best params
)
grid_search.fit(X_train, y_train)
print(f"Best params: {grid_search.best_params_}")
print(f"Best F1: {grid_search.best_score_:.4f}")

# RandomizedSearchCV -- sample from distributions, use for large search spaces
param_distributions = {
    "n_estimators": randint(100, 1000),
    "max_depth": randint(3, 20),
    "min_samples_split": randint(2, 20),
    "min_samples_leaf": randint(1, 10),
    "max_features": uniform(0.1, 0.9),
}

random_search = RandomizedSearchCV(
    RandomForestClassifier(random_state=42, n_jobs=-1),
    param_distributions,
    n_iter=50,        # Number of random combinations to try
    cv=cv,
    scoring="f1_weighted",
    n_jobs=-1,
    verbose=1,
    random_state=42,
    refit=True,
)
random_search.fit(X_train, y_train)
```

### Optuna for Advanced Tuning

```python
import optuna
from sklearn.model_selection import cross_val_score, StratifiedKFold
import xgboost as xgb

def objective(trial):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
    }

    model = xgb.XGBClassifier(
        **params,
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
        eval_metric="logloss",
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1_weighted", n_jobs=-1)

    return scores.mean()

study = optuna.create_study(direction="maximize", study_name="xgb_tuning")
study.optimize(objective, n_trials=100, show_progress_bar=True)

print(f"Best F1: {study.best_value:.4f}")
print(f"Best params: {study.best_params}")

# Train final model with best params
best_model = xgb.XGBClassifier(
    **study.best_params,
    tree_method="hist",
    random_state=42,
    n_jobs=-1,
)
best_model.fit(X_train, y_train)
```

## Cross-Validation Strategies

```python
from sklearn.model_selection import (
    StratifiedKFold,
    TimeSeriesSplit,
    KFold,
    RepeatedStratifiedKFold,
    cross_validate,
)

# Stratified K-Fold -- preserves class distribution in each fold
stratified_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Time Series Split -- respects temporal ordering, no data leakage
ts_cv = TimeSeriesSplit(n_splits=5, gap=0)  # gap=N skips N samples between train/test

# Repeated Stratified K-Fold -- more reliable estimates for small datasets
repeated_cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=42)

# Cross-validate with multiple metrics
results = cross_validate(
    model,
    X_train,
    y_train,
    cv=stratified_cv,
    scoring=["accuracy", "f1_weighted", "roc_auc"],
    return_train_score=True,
    n_jobs=-1,
)

for metric in ["accuracy", "f1_weighted", "roc_auc"]:
    test_key = f"test_{metric}"
    train_key = f"train_{metric}"
    print(f"{metric}: test={results[test_key].mean():.4f} (+/- {results[test_key].std():.4f}), "
          f"train={results[train_key].mean():.4f}")
```

## Feature Engineering

```python
import numpy as np
import pandas as pd
from sklearn.preprocessing import (
    PolynomialFeatures,
    PowerTransformer,
    KBinsDiscretizer,
)
from category_encoders import TargetEncoder

# Polynomial and interaction features
poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
X_poly = poly.fit_transform(X_train[numeric_features])

# Power transform for skewed distributions (Yeo-Johnson handles negative values)
power = PowerTransformer(method="yeo-johnson")
X_normalized = power.fit_transform(X_train[numeric_features])

# Binning continuous features
binner = KBinsDiscretizer(n_bins=10, encode="ordinal", strategy="quantile")
X_binned = binner.fit_transform(X_train[["age", "income"]])

# Target encoding for high-cardinality categorical features
# (OneHotEncoder creates too many columns when cardinality > 20)
target_enc = TargetEncoder(cols=["city", "product_id"], smoothing=1.0)
X_target_encoded = target_enc.fit_transform(X_train[["city", "product_id"]], y_train)

# Date feature extraction
df["date"] = pd.to_datetime(df["date"])
df["day_of_week"] = df["date"].dt.dayofweek
df["month"] = df["date"].dt.month
df["quarter"] = df["date"].dt.quarter
df["is_weekend"] = df["date"].dt.dayofweek.isin([5, 6]).astype(int)
df["days_since_epoch"] = (df["date"] - pd.Timestamp("1970-01-01")).dt.days

# Text feature engineering (basic -- for deep features use transformers)
df["text_length"] = df["text"].str.len()
df["word_count"] = df["text"].str.split().str.len()
df["avg_word_length"] = df["text"].str.split().apply(lambda x: np.mean([len(w) for w in x]) if x else 0)
df["uppercase_ratio"] = df["text"].apply(lambda x: sum(1 for c in x if c.isupper()) / max(len(x), 1))

# Aggregation features (for relational data)
user_stats = df.groupby("user_id").agg(
    total_purchases=("amount", "sum"),
    avg_purchase=("amount", "mean"),
    purchase_count=("amount", "count"),
    days_active=("date", lambda x: (x.max() - x.min()).days),
).reset_index()
df = df.merge(user_stats, on="user_id", how="left")
```

## Handling Imbalanced Data

```python
from sklearn.utils.class_weight import compute_class_weight
from imblearn.over_sampling import SMOTE, ADASYN
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline as ImbPipeline
import numpy as np

# Method 1: Class weights (no resampling, adjust loss function)
class_weights = compute_class_weight("balanced", classes=np.unique(y_train), y=y_train)
weight_dict = dict(zip(np.unique(y_train), class_weights))

model_weighted = RandomForestClassifier(class_weight="balanced", random_state=42)
# Or pass explicit weights:
model_weighted = RandomForestClassifier(class_weight=weight_dict, random_state=42)

# For XGBoost:
ratio = (y_train == 0).sum() / (y_train == 1).sum()
xgb_model = xgb.XGBClassifier(scale_pos_weight=ratio)

# Method 2: SMOTE (Synthetic Minority Over-sampling)
smote = SMOTE(random_state=42, k_neighbors=5)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

# Method 3: Combined over+under sampling in a pipeline
from imblearn.pipeline import Pipeline as ImbPipeline

imb_pipeline = ImbPipeline(steps=[
    ("preprocessor", preprocessor),
    ("smote", SMOTE(random_state=42)),
    ("undersample", RandomUnderSampler(sampling_strategy=0.8, random_state=42)),
    ("classifier", RandomForestClassifier(random_state=42)),
])

# Method 4: Threshold tuning for binary classification
from sklearn.metrics import precision_recall_curve

y_proba = model.predict_proba(X_val)[:, 1]
precisions, recalls, thresholds = precision_recall_curve(y_val, y_proba)

# Find threshold that maximizes F1
f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
best_threshold = thresholds[np.argmax(f1_scores)]
print(f"Best threshold: {best_threshold:.3f}, F1: {f1_scores.max():.4f}")

y_pred_tuned = (y_proba >= best_threshold).astype(int)
```

## Model Evaluation

```python
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_curve,
    auc,
    precision_recall_curve,
    average_precision_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score,
)
import numpy as np

# Classification evaluation
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)

# Full classification report
print(classification_report(y_test, y_pred, digits=4))

# Confusion matrix
cm = confusion_matrix(y_test, y_pred)
print("Confusion Matrix:")
print(cm)

# ROC curve and AUC
fpr, tpr, _ = roc_curve(y_test, y_proba[:, 1])
roc_auc = auc(fpr, tpr)
print(f"AUC-ROC: {roc_auc:.4f}")

# Precision-Recall curve (more informative than ROC for imbalanced data)
precision, recall, _ = precision_recall_curve(y_test, y_proba[:, 1])
ap = average_precision_score(y_test, y_proba[:, 1])
print(f"Average Precision: {ap:.4f}")

# Regression evaluation
y_pred_reg = reg_model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, y_pred_reg))
mae = mean_absolute_error(y_test, y_pred_reg)
r2 = r2_score(y_test, y_pred_reg)
print(f"RMSE: {rmse:.4f}, MAE: {mae:.4f}, R2: {r2:.4f}")
```

## Model Persistence

```python
import joblib
from datetime import datetime
from pathlib import Path

# Save model with versioning
def save_model(model, model_name, metrics, base_dir="./models"):
    """Save model with metadata and versioning."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_dir = Path(base_dir) / model_name / timestamp
    version_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = version_dir / "model.joblib"
    joblib.dump(model, model_path)

    # Save metadata
    import json
    metadata = {
        "model_name": model_name,
        "timestamp": timestamp,
        "metrics": metrics,
        "model_type": type(model).__name__,
    }
    with open(version_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model saved to {version_dir}")
    return str(version_dir)

# Load model
def load_model(model_dir):
    """Load model and metadata."""
    model = joblib.load(Path(model_dir) / "model.joblib")
    import json
    with open(Path(model_dir) / "metadata.json") as f:
        metadata = json.load(f)
    return model, metadata

# Usage:
# save_model(pipeline, "sentiment_classifier", {"f1": 0.95, "accuracy": 0.94})
# model, meta = load_model("./models/sentiment_classifier/20240115_143022")
```

## Full Pipeline Example: End-to-End

```python
"""Complete ML pipeline: data loading through evaluation and export."""

import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb
import joblib

# 1. Data loading
df = pd.read_csv("customers.csv")
target_col = "churn"
X = df.drop(columns=[target_col])
y = df[target_col]

# 2. EDA (quick stats)
print(f"Shape: {X.shape}")
print(f"Class distribution:\n{y.value_counts(normalize=True)}")
print(f"Missing values:\n{X.isnull().sum()[X.isnull().sum() > 0]}")

# 3. Feature engineering
numeric_features = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
categorical_features = X.select_dtypes(include=["object", "category"]).columns.tolist()

preprocessor = ColumnTransformer(transformers=[
    ("num", Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ]), numeric_features),
    ("cat", Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ]), categorical_features),
])

# 4. Model training
pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", xgb.XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )),
])

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Cross-validate
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_results = cross_validate(
    pipeline, X_train, y_train, cv=cv,
    scoring=["f1_weighted", "roc_auc"], n_jobs=-1,
)
print(f"CV F1: {cv_results['test_f1_weighted'].mean():.4f} (+/- {cv_results['test_f1_weighted'].std():.4f})")
print(f"CV AUC: {cv_results['test_roc_auc'].mean():.4f}")

# Final train and evaluate
pipeline.fit(X_train, y_train)
y_pred = pipeline.predict(X_test)
y_proba = pipeline.predict_proba(X_test)[:, 1]

print("\n--- Test Set Results ---")
print(classification_report(y_test, y_pred, digits=4))
print(f"AUC-ROC: {roc_auc_score(y_test, y_proba):.4f}")

# 5. Export
joblib.dump(pipeline, "churn_model_v1.joblib")
print("Model saved to churn_model_v1.joblib")
```
