from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
import json
import math

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse({}, headers=CORS_HEADERS)

    response = await call_next(request)

    for key, value in CORS_HEADERS.items():
        response.headers[key] = value

    return response


@app.options("/{path:path}")
async def options_handler(path: str):
    return Response(status_code=200, headers=CORS_HEADERS)


DATA_FILE = Path(__file__).parent.parent / "q-vercel-latency.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    DATA = json.load(f)


class RequestBody(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile_95(values):
    if not values:
        return 0

    values = sorted(values)

    # Nearest-rank percentile
    rank = math.ceil(0.95 * len(values))
    rank = max(1, min(rank, len(values)))

    return values[rank - 1]


@app.post("/")
async def metrics(payload: RequestBody):
    regions = {}

    for region in payload.regions:
        rows = [r for r in DATA if r["region"] == region]

        latencies = [r["latency_ms"] for r in rows]
        uptimes = [r["uptime_pct"] for r in rows]

        regions[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile_95(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                1 for r in rows
                if r["latency_ms"] > payload.threshold_ms
            ),
        }

    return {"regions": regions}