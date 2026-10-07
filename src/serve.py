from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
import boto3
import joblib
import pandas as pd
from pydantic import BaseModel, FiniteFloat


FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]
MODEL_KEY = "artifacts/current/model.joblib"


def download_model(bucket_name: str, model_path: Path):
    """Download the deployed model using the AWS credentials chain."""
    model_path.parent.mkdir(parents=True, exist_ok=True)
    client = boto3.client("s3")
    client.download_file(bucket_name, MODEL_KEY, str(model_path))
    print("Model downloaded from Amazon S3.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    bucket_name = os.environ.get("ARTIFACT_BUCKET")
    default_path = "~/models/model.joblib" if bucket_name else "models/model.joblib"
    model_path = Path(os.environ.get("MODEL_PATH", default_path)).expanduser()
    if bucket_name:
        download_model(bucket_name, model_path)
    app.state.model = joblib.load(model_path)
    yield
    del app.state.model


app = FastAPI(title="Income Model API", lifespan=lifespan)


class ScoreRequest(BaseModel):
    features: list[FiniteFloat]


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/score")
def score(req: ScoreRequest):
    """Score ten numeric features in the same order used during training."""
    if len(req.features) != len(FEATURE_NAMES):
        raise HTTPException(status_code=400, detail="Expected 10 features (adult income)")
    features = pd.DataFrame([req.features], columns=FEATURE_NAMES)
    prediction = int(app.state.model.predict(features)[0])
    return {
        "prediction": prediction,
        "label": "thu_nhap_cao" if prediction == 1 else "thu_nhap_thap",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
