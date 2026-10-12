"""
HydroSuite — Internal Streamlit Testing Dashboard
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(
    page_title="HydroSuite — Testing",
    page_icon="🌧",
    layout="wide"
)

BACKEND_URL = "http://localhost:8000"

st.title("🌧 HydroSuite — Internal Testing")
st.caption("Backend API Testing Dashboard")

with st.sidebar:
    backend_url = st.text_input("Backend URL", value=BACKEND_URL)
    st.divider()
    lat = st.number_input("Latitude", value=31.5204, format="%.4f")
    lon = st.number_input("Longitude", value=74.3587, format="%.4f")
    st.divider()
    start_date = st.date_input("Start", value=datetime.now() - timedelta(days=365))
    end_date = st.date_input("End", value=datetime.now())
    fetch_btn = st.button("🚀 Fetch Data", use_container_width=True, type="primary")

try:
    health = requests.get(f"{backend_url}/health", timeout=5).json()
    st.sidebar.success(f"✅ Backend online")
except:
    st.sidebar.error("❌ Backend offline")

if fetch_btn:
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    with st.spinner("Fetching data..."):
        try:
            r = requests.post(
                f"{backend_url}/api/analyze",
                json={"lat": lat, "lon": lon, "start": start_str, "end": end_str},
                timeout=60
            )
            data = r.json()
            
            if not data.get("success"):
                st.error(f"Error: {data}")
            else:
                stats = data["statistics"]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total", f"{stats['total']:.1f} mm")
                c2.metric("Mean", f"{stats['mean']:.2f} mm")
                c3.metric("Max", f"{stats['max']:.1f} mm")
                c4.metric("Rainy Days", stats["rainy_days"])
                
                if "trend" in data:
                    st.subheader("📈 Trend")
                    st.json(data["trend"])
                
                if "return_period" in data:
                    st.subheader("🔥 Return Period")
                    rp = data["return_period"]
                    if "design_values" in rp:
                        df_rp = pd.DataFrame(rp["design_values"])
                        st.dataframe(df_rp)
                        fig = px.bar(df_rp, x="return_period", y="expected_rainfall")
                        st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.info("👈 Set location and click 'Fetch Data'")
