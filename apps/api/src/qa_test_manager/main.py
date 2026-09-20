from typing import Literal, TypedDict

from fastapi import FastAPI


class HealthResponse(TypedDict):
    status: Literal["ok"]
    service: str


app = FastAPI(title="QA Test Manager API", version="0.1.0")


@app.get("/health", tags=["system"])
def health() -> HealthResponse:
    return {"status": "ok", "service": "qa-test-manager-api"}
