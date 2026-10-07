from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import joblib
import pandas as pd
import pytest
from sklearn.ensemble import GradientBoostingClassifier

from src.serve import app, FEATURE_NAMES, MODEL_KEY


@pytest.fixture
def saved_model(tmp_path):
    rows = [
        [60, 2, 5, 2, 4, 0, 1, 0, 0, 45],
        [28, 2, 14, 2, 11, 0, 1, 0, 0, 45],
    ]
    model = GradientBoostingClassifier(n_estimators=10, random_state=42)
    model.fit(pd.DataFrame(rows, columns=FEATURE_NAMES), [0, 1])
    path = tmp_path / "model.joblib"
    joblib.dump(model, path)
    return path, rows


@pytest.fixture
def client(saved_model, monkeypatch):
    path, _ = saved_model
    monkeypatch.delenv("ARTIFACT_BUCKET", raising=False)
    monkeypatch.setenv("MODEL_PATH", str(path))
    with TestClient(app) as test_client:
        yield test_client


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("prediction,label", [(0, "thu_nhap_thap"), (1, "thu_nhap_cao")])
def test_score(client, saved_model, prediction, label):
    _, rows = saved_model
    response = client.post("/score", json={"features": rows[prediction]})
    assert response.status_code == 200
    assert response.json() == {"prediction": prediction, "label": label}


@pytest.mark.parametrize("count", [0, 9, 11])
def test_score_rejects_wrong_feature_count(client, count):
    response = client.post("/score", json={"features": [0] * count})
    assert response.status_code == 400


def test_score_rejects_non_numeric_features(client):
    response = client.post("/score", json={"features": ["invalid"] * 10})
    assert response.status_code == 422


def test_cloud_startup_downloads_model(saved_model, tmp_path, monkeypatch):
    source_path, _ = saved_model
    destination = tmp_path / "downloaded" / "model.joblib"
    storage_client = MagicMock()
    storage_client.download_file.side_effect = lambda bucket, key, filename: joblib.dump(
        joblib.load(source_path), filename
    )
    client_factory = MagicMock(return_value=storage_client)
    monkeypatch.setattr("src.serve.boto3.client", client_factory)
    monkeypatch.setenv("ARTIFACT_BUCKET", "test-income-bucket")
    monkeypatch.setenv("MODEL_PATH", str(destination))
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
    client_factory.assert_called_once_with("s3")
    storage_client.download_file.assert_called_once_with(
        "test-income-bucket", MODEL_KEY, str(destination)
    )
    assert destination.is_file()
