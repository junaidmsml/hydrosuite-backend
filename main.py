"""
HydroSuite Backend — FastAPI
Live Satellite Data API for Hydrology Analysis
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import os
from dotenv import load_dotenv

from utils import (
    fetch_nasa_power, fetch_openweather, fetch_openweather_forecast,
    compute_statistics, detect_trend, return_period_analysis
)

load_dotenv()

app = FastAPI(
    title="HydroSuite API",
    description="Live Hydrology Data & Analysis API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8501"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "HydroSuite API",
        "version": "2.0.0",
        "endpoints": [
            "/api/nasa-power",
            "/api/openweather",
            "/api/openweather/forecast",
            "/api/statistics",
            "/api/trend",
            "/api/return-period",
            "/api/analyze"
        ]
    }


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/nasa-power")
def nasa_power(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    start: str = Query(..., description="Start date YYYYMMDD"),
    end: str = Query(..., description="End date YYYYMMDD")
):
    try:
        df = fetch_nasa_power(lat, lon, start, end)
        return {
            "success": True,
            "source": "NASA POWER",
            "location": {"lat": lat, "lon": lon},
            "period": {"start": start, "end": end},
            "records": len(df),
            "statistics": compute_statistics(df),
            "data": df.to_dict(orient="records")[:365]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/openweather")
def openweather(
    lat: float = Query(...),
    lon: float = Query(...)
):
    try:
        data = fetch_openweather(lat, lon)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/openweather/forecast")
def openweather_forecast(
    lat: float = Query(...),
    lon: float = Query(...)
):
    try:
        df = fetch_openweather_forecast(lat, lon)
        return {
            "success": True,
            "source": "OpenWeather Forecast",
            "records": len(df),
            "data": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AnalyzeRequest(BaseModel):
    lat: float
    lon: float
    start: str
    end: str
    analysis_types: List[str] = Field(
        default=["statistics", "trend", "return_period"]
    )


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    try:
        df = fetch_nasa_power(req.lat, req.lon, req.start, req.end)
        
        result = {
            "success": True,
            "source": "NASA POWER",
            "location": {"lat": req.lat, "lon": req.lon},
            "period": {"start": req.start, "end": req.end},
            "records": len(df)
        }
        
        if "statistics" in req.analysis_types:
            result["statistics"] = compute_statistics(df)
        
        if "trend" in req.analysis_types:
            result["trend"] = detect_trend(df)
        
        if "return_period" in req.analysis_types:
            result["return_period"] = return_period_analysis(df)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
