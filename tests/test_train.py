import json

import joblib
import mlflow
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import accuracy_score, f1_score

from src.train import train


FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


def _make_temp_data(tmp_path):
    """Create repeatable binary classification data without cloud access."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.random((200, len(FEATURE_NAMES))), columns=FEATURE_NAMES)
    df["target"] = rng.integers(0, 2, size=200)
    train_path = tmp_path / "train.csv"
    eval_path = tmp_path / "holdout.csv"
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)
    return str(train_path), str(eval_path)


@pytest.fixture
def trained_run(tmp_path, monkeypatch):
    # Keep test artifacts and MLflow runs separate from real experiments.
    monkeypatch.chdir(tmp_path)
    previous_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri((tmp_path / "mlruns").as_uri())
    try:
        train_path, eval_path = _make_temp_data(tmp_path)
        result = train(
            {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
            data_path=train_path,
            eval_path=eval_path,
        )
        yield result, pd.read_csv(eval_path)
    finally:
        mlflow.set_tracking_uri(previous_uri)


def test_train_returns_float(trained_run):
    result, _ = trained_run
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


def test_report_file_created(trained_run):
    result, evaluation = trained_run
    with open("outputs/report.json") as handle:
        report = json.load(handle)
    model = joblib.load("models/model.joblib")
    predictions = model.predict(evaluation[FEATURE_NAMES])
    assert report["f1_score"] == pytest.approx(result)
    assert report["f1_score"] == pytest.approx(f1_score(evaluation.target, predictions))
    assert report["accuracy"] == pytest.approx(accuracy_score(evaluation.target, predictions))


def test_model_file_created(trained_run):
    _, evaluation = trained_run
    model = joblib.load("models/model.joblib")
    predictions = model.predict(evaluation[FEATURE_NAMES])
    assert len(predictions) == len(evaluation)
    assert set(predictions).issubset({0, 1})
    assert list(model.feature_names_in_) == FEATURE_NAMES
