"""Same REST interface for MATLAB Runtime, MATLAB Engine and the explicit Python reference."""
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import threading
import hmac
from typing import Literal
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from vault_core import scoring

MODE = os.getenv("SCORING_BACKEND", "python-reference")
runtime = None
engine_details = {}
lock = threading.Lock()


@asynccontextmanager
async def lifespan(app):
    global runtime, engine_details
    runtime, engine_details = None, {}
    if MODE == "matlab-runtime":
        import vault_matlab
        runtime = vault_matlab.initialize()
    elif MODE == "matlab-engine":
        from matlab_host import open_engine
        runtime, engine_details = open_engine()
    elif MODE != "python-reference":
        raise RuntimeError("Unknown SCORING_BACKEND; refusing to silently fall back")
    try:
        yield
    finally:
        if runtime is not None:
            runtime.terminate() if MODE == "matlab-runtime" else runtime.quit()
        runtime, engine_details = None, {}


def authorize(x_scoring_key: str = Header(default="")):
    expected = os.getenv("SCORING_TOKEN", "")
    if expected and not hmac.compare_digest(x_scoring_key, expected):
        raise HTTPException(401, "Scoring service credential required")


app = FastAPI(title="THE VAULT scoring engine", lifespan=lifespan, dependencies=[Depends(authorize)])


class Enrollment(BaseModel):
    captures: list[dict] = Field(min_length=2, max_length=5)


class Comparison(BaseModel):
    capture: dict
    template: dict
    minimum_score: float = Field(default=0.8, ge=0.8, le=0.99)


def execute(operation, layer, payload):
    try:
        with lock:
            if MODE == "python-reference":
                if operation == "enroll":
                    result = {"template": scoring.enroll(layer, payload["captures"])}
                else:
                    result = scoring.score(layer, **payload)
            else:
                if runtime is None:
                    raise RuntimeError("MATLAB is not initialized")
                request = json.dumps({"operation": operation, "layer": layer, **payload})
                result = json.loads(str(runtime.vaulte_engine(request, nargout=1)))
        return {**result, "engine": MODE}
    except (ValueError, KeyError, IndexError) as exc:
        raise HTTPException(422, str(exc)) from None
    except Exception as exc:
        if "vault:Quality" in str(exc) or "vault:Timing" in str(exc):
            raise HTTPException(422, "Capture quality is insufficient; please retry") from None
        raise HTTPException(503, "Scoring engine failed") from None


@app.get("/health")
def health():
    return {"ready": MODE == "python-reference" or runtime is not None, "engine": MODE,
            "matlab": MODE.startswith("matlab-"), **engine_details}


@app.post("/enroll/{layer}")
def enroll(layer: Literal["face", "body", "hand"], body: Enrollment):
    return execute("enroll", layer, body.model_dump())


@app.post("/score/{layer}")
def score(layer: Literal["face", "body", "hand"], body: Comparison):
    return execute("score", layer, body.model_dump())
