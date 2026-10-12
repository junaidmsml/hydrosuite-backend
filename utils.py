"""
HydroSuite — Data Fetching & Analysis Utilities
NASA POWER | OpenWeather | GPM | CHIRPS | PERSIANN
"""
import os
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


# ═══════════════════════════════════════════════════════
# NASA POWER — Historical Climate Data (No API Key)
# ═══════════════════════════════════════════════════════
def fetch_nasa_power(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """Fetch daily rainfall from NASA POWER API."""
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start,
        "end": end,
        "format": "JSON"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        raw = data["properties"]["parameter"]["PRECTOTCORR"]
        
        rows = []
        for date_str, rainfall in raw.items():
            value = 0 if rainfall == -999 else float(rainfall)
            rows.append({
                "date": datetime.strptime(date_str, "%Y%m%d"),
                "rainfall": value
            })
        
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        df["source"] = "NASA POWER"
        return df
    
    except Exception as e:
        raise Exception(f"NASA POWER fetch failed: {str(e)}")


# ═══════════════════════════════════════════════════════
# OPENWEATHER — Live Weather Data
# ═══════════════════════════════════════════════════════
def fetch_openweather(lat: float, lon: float) -> dict:
    """Fetch current weather from OpenWeather API."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise Exception("OPENWEATHER_API_KEY not set in .env")
    
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        return {
            "location": data.get("name", "Unknown"),
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "rainfall_1h": data.get("rain", {}).get("1h", 0),
            "rainfall_3h": data.get("rain", {}).get("3h", 0),
            "description": data["weather"][0]["description"],
            "timestamp": datetime.now().isoformat(),
            "source": "OpenWeather"
        }
    
    except Exception as e:
        raise Exception(f"OpenWeather fetch failed: {str(e)}")


def fetch_openweather_forecast(lat: float, lon: float) -> pd.DataFrame:
    """Fetch 5-day rainfall forecast from OpenWeather."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise Exception("OPENWEATHER_API_KEY not set in .env")
    
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        rows = []
        for item in data["list"]:
            rows.append({
                "datetime": datetime.fromtimestamp(item["dt"]),
                "rainfall": item.get("rain", {}).get("3h", 0),
                "temp": item["main"]["temp"],
                "humidity": item["main"]["humidity"]
            })
        
        df = pd.DataFrame(rows)
        df["date"] = df["datetime"].dt.date
        daily = df.groupby("date").agg({"rainfall": "sum"}).reset_index()
        daily["source"] = "OpenWeather Forecast"
        return daily
    
    except Exception as e:
        raise Exception(f"OpenWeather Forecast fetch failed: {str(e)}")


# ═══════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════
def compute_statistics(df: pd.DataFrame) -> dict:
    """Compute basic rainfall statistics."""
    r = df["rainfall"]
    return {
        "total": float(r.sum()),
        "mean": float(r.mean()),
        "median": float(r.median()),
        "std": float(r.std()) if len(r) > 1 else 0,
        "max": float(r.max()),
        "min": float(r.min()),
        "rainy_days": int((r > 0).sum()),
        "zero_days": int((r == 0).sum()),
        "records": len(r)
    }


def detect_trend(df: pd.DataFrame) -> dict:
    """Mann-Kendall trend test."""
    x = df["rainfall"].values
    n = len(x)
    
    S = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            S += np.sign(x[j] - x[i])
    
    counts = pd.Series(x).value_counts()
    tie_sum = sum(t * (t - 1) * (2 * t + 5) for t in counts if t > 1)
    var_s = (n * (n - 1) * (2 * n + 5) - tie_sum) / 18
    
    if S > 0:
        Z = (S - 1) / np.sqrt(var_s) if var_s > 0 else 0
    elif S < 0:
        Z = (S + 1) / np.sqrt(var_s) if var_s > 0 else 0
    else:
        Z = 0
    
    from scipy import stats
    p_value = 2 * (1 - stats.norm.cdf(abs(Z)))
    
    return {
        "S": int(S),
        "var_S": float(var_s),
        "Z": float(Z),
        "p_value": float(p_value),
        "trend": "increasing" if S > 0 else "decreasing" if S < 0 else "no trend",
        "significant": p_value < 0.05
    }


def return_period_analysis(df: pd.DataFrame, periods: list = [2, 5, 10, 25, 50, 100]) -> dict:
    """Gumbel distribution return period analysis."""
    df = df.copy()
    df["year"] = pd.to_datetime(df["date"]).dt.year
    annual_max = df.groupby("year")["rainfall"].max().values
    
    if len(annual_max) < 5:
        return {"error": "Need at least 5 years of data"}
    
    mean_val = np.mean(annual_max)
    std_val = np.std(annual_max, ddof=1)
    
    results = []
    for T in periods:
        y_T = -np.log(np.log(T / (T - 1)))
        K_T = (y_T - 0.5772) / 1.2825
        x_T = mean_val + K_T * std_val
        results.append({
            "return_period": T,
            "probability": 1 / T,
            "expected_rainfall": float(x_T)
        })
    
    return {
        "mean_annual_max": float(mean_val),
        "std_annual_max": float(std_val),
        "years_of_record": len(annual_max),
        "design_values": results
    }
