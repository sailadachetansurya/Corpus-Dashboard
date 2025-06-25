import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from typing import Dict, List, Optional, Tuple
import os
from collections import Counter
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import json
import logging
import time
from wordcloud import WordCloud
import altair as alt

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enhanced page config
st.set_page_config(
    page_title="Advanced Corpus Records Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://docs.streamlit.io',
        'Report a bug': None,
        'About': "Advanced Corpus Records Dashboard v2.0"
    }
)

# Categories data
CATEGORIES = {
    "Fables": "379d6867-57c1-4f57-b6ee-fb734313e538",
    "Events": "7a184c41-1a49-4beb-a01a-d8dc01693b15",
    "Music": "94979e9f-4895-4cd7-8601-ad53d8099bf4",
    "Places": "96e5104f-c786-4928-b932-f59f5b4ddbf0",
    "Food": "833299f6-ff1c-4fde-804f-6d3b3877c76e",
    "People": "af8b7a27-00b4-4192-9fa6-90152a0640b2",
    "Literature": "74b133e7-e496-4e9d-85b0-3bd5eb4c3871",
    "Architecture": "94a13c20-8a03-45da-8829-10e2fe1e61a1",
    "Skills": "6f6f5023-a99e-4a29-a44a-6d5acbf88085",
    "Images": "4366cab1-031e-4b37-816b-311ee34461a9",
    "Culture": "ab9fa2ce-1f83-4e91-b89d-cca18e8b301e",
    "Flora & Fauna": "5f40610f-ae47-4472-944c-cb899128ebbf",
    "Education": "784ddb92-9540-4ce1-b4e4-6c1b7b18849d",
    "Vegetation": "2f831ae2-f0cd-4142-8646-68dd195dfba2",
    "Dance": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
}

CATEGORY_ID_TO_NAME = {v: k for k, v in CATEGORIES.items()}

# Initialize enhanced session state
def initialize_session_state():
    """Initialize comprehensive session state variables"""
    session_vars = {
        "authenticated": False,
        "username": None,
        "token": None,
        "user_id": None,
        "login_attempts": 0,
        "selected_category": "Fables",
        "query_user_id": "",
        "query_results": None,
        "last_queried_user": None,
        "database_overview": None,
        "dashboard_mode": "overview",
        "date_filter": None,
        "advanced_filters": {},
        "comparison_data": {},
        "real_time_updates": False,
        "export_format": "csv",
        "chart_theme": "dark",
        "auto_refresh": False,
        "notifications": [],
        "users_list": None,
        "user_mapping": {},
        "selected_user_from_dropdown": None,
        "user_preferences": {
            "theme": "dark",
            "chart_style": "modern",
            "animation_speed": "normal"
        }
    }
    
    for var, default_value in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default_value

# Authentication Functions
def decode_jwt_token(token: str) -> Optional[Dict]:
    """Enhanced JWT token decoder with better error handling"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            logger.error("Invalid JWT token format")
            return None
            
        payload = parts[1] + "=="
        payload_decoded = json.loads(base64.b64decode(payload).decode("utf-8"))
        
        user_id = payload_decoded.get("sub")
        if not user_id:
            logger.error("User ID not found in token")
            return None
            
        return {
            "user_id": user_id,
            "payload": payload_decoded,
            "expires_at": payload_decoded.get("exp"),
            "issued_at": payload_decoded.get("iat")
        }
        
    except Exception as e:
        logger.error(f"Failed to decode token: {e}")
        return None

def login_user(phone: str, password: str) -> Optional[Dict]:
    """Enhanced login with better UX"""
    if not phone or not password:
        st.error("Please enter both phone number and password")
        return None
        
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🔐 Authenticating credentials...")
        progress_bar.progress(25)
        
        response = requests.post(
            "https://backend2.swecha.org/api/v1/auth/login",
            json={"phone": phone, "password": password},
            headers={"accept": "application/json", "Content-Type": "application/json"},
            timeout=30
        )
        
        progress_bar.progress(75)
        status_text.text("✅ Authentication successful!")
        progress_bar.progress(100)
        
        time.sleep(0.5)  # Brief pause for UX
        progress_bar.empty()
        status_text.empty()
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        progress_bar.empty()
        status_text.empty()
        
        if e.response.status_code == 401:
            st.error("❌ Invalid phone number or password.")
            st.session_state.login_attempts += 1
            if st.session_state.login_attempts >= 3:
                st.error("🚫 Too many failed attempts. Please wait before trying again.")
        else:
            st.error(f"❌ Login failed with status {e.response.status_code}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None

def request_otp(phone: str) -> bool:
    """Request OTP for login"""
    try:
        response = requests.post(
            "https://backend2.swecha.org/api/v1/auth/send-otp",
            json={"phone": phone},
            headers={"accept": "application/json", "Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        print("✅ OTP request response:", response.json())  # Add this
        return True
    except Exception as e:
        st.error(f"❌ Failed to request OTP: {e}")
        return False

def verify_otp(phone: str, otp: str) -> Optional[Dict]:
    """Verify OTP and get token"""
    try:
        response = requests.post(
            "https://backend2.swecha.org/api/v1/auth/verify-otp",
            json={"phone": phone, "otp": otp},
            headers={"accept": "application/json", "Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"❌ OTP verification failed: {e}")
        return None

# Enhanced Data Fetching Functions
def fetch_records_with_cache(user_id: str, token: str, use_cache: bool = True) -> List[Dict]:
    """Fetch records with caching mechanism"""
    cache_key = f"records_{user_id}"
    
    if use_cache and cache_key in st.session_state:
        cached_data = st.session_state[cache_key]
        if time.time() - cached_data['timestamp'] < 300:  # 5 minutes cache
            return cached_data['data']
    
    records = fetch_records(user_id, token)
    
    if records:
        st.session_state[cache_key] = {
            'data': records,
            'timestamp': time.time()
        }
    
    return records

def fetch_records(user_id: str, token: str) -> List[Dict]:
    """Enhanced records fetching with better progress indication"""
    if not user_id or not token:
        st.error("User ID and token are required")
        return []
        
    url = f"https://backend2.swecha.org/api/v1/records/?user_id={user_id}&skip=0&limit=1000"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        with st.spinner("🔄 Fetching your records..."):
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Expected list, got {type(data)}")
                st.warning("⚠️ Unexpected data format received from server")
                return []
                
            logger.info(f"Successfully fetched {len(data)} records")
            return data
            
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Please try again.")
        return []
    except requests.exceptions.ConnectionError:
        st.error("🌐 Unable to connect to the server. Please check your internet connection.")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("🔐 Authentication failed. Please log in again.")
            st.session_state.authenticated = False
        else:
            st.error(f"❌ Failed to fetch records: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching records: {e}")
        st.error(f"❌ Unexpected error: {e}")
        return []

def fetch_any_user_records(query_user_id: str, token: str) -> List[Dict]:
    """Enhanced user query with validation"""
    if not query_user_id or not token:
        st.error("User ID and token are required")
        return []
        
    if len(query_user_id.strip()) < 10:
        st.error("Please enter a valid User ID")
        return []
        
    url = f"https://backend2.swecha.org/api/v1/records/?user_id={query_user_id.strip()}&skip=0&limit=1000"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text(f"🔍 Searching for user {query_user_id[:8]}...")
        progress_bar.progress(30)
        
        response = requests.get(url, headers=headers, timeout=30)
        
        progress_bar.progress(70)
        status_text.text("📊 Processing results...")
        
        response.raise_for_status()
        data = response.json()
        
        progress_bar.progress(100)
        status_text.text("✅ Search complete!")
        
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        if not isinstance(data, list):
            st.warning("⚠️ Unexpected data format received")
            return []
            
        return data
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Search failed: {e}")
        return []

def fetch_all_records(token: str) -> List[Dict]:
    """Enhanced database overview fetching"""
    if not token:
        st.error("Token is required")
        return []
        
    url = f"https://backend2.swecha.org/api/v1/records/?skip=0&limit=1000"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🌐 Connecting to database...")
        progress_bar.progress(20)
        
        response = requests.get(url, headers=headers, timeout=60)
        
        progress_bar.progress(60)
        status_text.text("📥 Downloading database records...")
        
        response.raise_for_status()
        data = response.json()
        
        progress_bar.progress(90)
        status_text.text("🔄 Processing data...")
        
        if not isinstance(data, list):
            st.warning("⚠️ Unexpected data format received")
            return []
        
        progress_bar.progress(100)
        status_text.text("✅ Database overview loaded!")
        
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        return data
        
    except Exception as e:
        st.error(f"❌ Database fetch failed: {e}")
        return []

def fetch_all_users(token: str) -> List[Dict]:
    """Fetch all users from the API for dropdown selection"""
    if not token:
        st.error("Token is required")
        return []
        
    url = f"https://backend2.swecha.org/api/v1/users/?skip=0&limit=1000"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        with st.spinner("🔄 Loading users..."):
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Expected list, got {type(data)}")
                st.warning("Unexpected data format received from server")
                return []
                
            logger.info(f"Successfully fetched {len(data)} users")
            return data
            
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return []
    except requests.exceptions.ConnectionError:
        st.error("Unable to connect to the server. Please check your internet connection.")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Authentication failed. Please log in again.")
            st.session_state.authenticated = False
        elif e.response.status_code == 403:
            st.error("Access denied. You don't have permission to view users list.")
        else:
            st.error(f"Failed to fetch users: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching users: {e}")
        st.error(f"Unexpected error: {e}")
        return []

def create_user_mapping(users: List[Dict]) -> Dict[str, str]:
    """Create mapping from user ID to user name"""
    try:
        user_mapping = {}
        for user in users:
            user_id = user.get('id', '')
            user_name = user.get('name', 'Unknown User')
            if user_id:
                user_mapping[user_id] = user_name
        
        logger.info(f"Created mapping for {len(user_mapping)} users")
        return user_mapping
        
    except Exception as e:
        logger.error(f"Error creating user mapping: {e}")
        st.error(f"Error processing user data: {e}")
        return {}

# Enhanced Data Processing Functions
def advanced_summarize(records: List[Dict], filters: Dict = None) -> Optional[Dict]:
    """Advanced data summarization with filtering and more metrics"""
    if not records:
        return None
        
    try:
        df = pd.DataFrame(records)
        df["category"] = df["category_id"].map(CATEGORY_ID_TO_NAME).fillna("Unknown")
        df["created_at"] = pd.to_datetime(df["created_at"], errors='coerce')
        df["date"] = df["created_at"].dt.date
        df["hour"] = df["created_at"].dt.hour
        df["day_of_week"] = df["created_at"].dt.day_name()
        df["month"] = df["created_at"].dt.month_name()
        df["week"] = df["created_at"].dt.isocalendar().week
        
        # Apply filters if provided
        if filters:
            if filters.get('date_range'):
                start_date, end_date = filters['date_range']
                df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if filters.get('categories'):
                df = df[df['category'].isin(filters['categories'])]
            
            if filters.get('media_types'):
                df = df[df['media_type'].isin(filters['media_types'])]
            
            if filters.get('status'):
                df = df[df['status'].isin(filters['status'])]
        
        if df.empty:
            return None
        
        # Calculate total users
        total_users = df['user_id'].nunique() if 'user_id' in df.columns else 0
        
        # Enhanced metrics
        summary = {
            "total_records": len(df),
            "total_users": total_users,
            "unique_dates": df['date'].nunique(),
            "date_range": (df['date'].min(), df['date'].max()),
            "avg_daily_uploads": len(df) / max(df['date'].nunique(), 1),
            "media_type": df["media_type"].value_counts(),
            "status": df["status"].value_counts(),
            "category": df["category"].value_counts(),
            "uploads_per_day": df.groupby("date").size(),
            "uploads_per_hour": df.groupby("hour").size(),
            "uploads_per_weekday": df.groupby("day_of_week").size(),
            "uploads_per_month": df.groupby("month").size(),
            "uploads_per_week": df.groupby("week").size(),
            "peak_upload_day": df.groupby("date").size().idxmax(),
            "peak_upload_count": df.groupby("date").size().max(),
            "most_active_hour": df.groupby("hour").size().idxmax(),
            "most_active_weekday": df.groupby("day_of_week").size().idxmax(),
            "category_diversity": len(df["category"].unique()),
            "media_diversity": len(df["media_type"].unique()),
            "weekly_growth": calculate_growth_rate(df.groupby("week").size()),
            "monthly_growth": calculate_growth_rate(df.groupby("month").size()),
            "df": df
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in advanced summarization: {e}")
        st.error(f"❌ Data processing error: {e}")
        return None

def calculate_growth_rate(series: pd.Series) -> float:
    """Calculate growth rate for time series data"""
    if len(series) < 2:
        return 0.0
    
    current = series.iloc[-1]
    previous = series.iloc[-2]
    
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    
    return ((current - previous) / previous) * 100

def get_data_insights(summary: Dict) -> List[str]:
    """Generate intelligent insights from data"""
    insights = []
    
    if not summary:
        return insights
    
    df = summary['df']
    
    # Upload pattern insights
    peak_day = summary.get('peak_upload_day')
    if peak_day:
        insights.append(f"📈 Peak activity was on {peak_day} with {summary['peak_upload_count']} uploads")
    
    # Time pattern insights
    most_active_hour = summary.get('most_active_hour')
    if most_active_hour:
        insights.append(f"🕐 Most active hour is {most_active_hour}:00")
    
    # Category insights
    if not summary['category'].empty:
        top_category = summary['category'].index[0]
        category_percent = (summary['category'].iloc[0] / summary['total_records']) * 100
        insights.append(f"📂 {top_category} dominates with {category_percent:.1f}% of all uploads")
    
    # Growth insights
    weekly_growth = summary.get('weekly_growth', 0)
    if abs(weekly_growth) > 5:
        trend = "increasing" if weekly_growth > 0 else "decreasing"
        insights.append(f"📊 Weekly uploads are {trend} by {abs(weekly_growth):.1f}%")
    
    # User diversity insights
    total_users = summary.get('total_users', 0)
    if total_users > 0:
        insights.append(f"👥 {total_users} unique users contributed to these records")
    
    # Diversity insights
    category_diversity = summary.get('category_diversity', 0)
    if category_diversity >= len(CATEGORIES) * 0.8:
        insights.append(f"🌈 High category diversity: {category_diversity} different categories used")
    
    return insights

# Advanced Visualization Functions
def create_advanced_overview_dashboard(summary: Dict):
    """Create comprehensive overview dashboard"""
    if not summary:
        st.warning("No data available for dashboard")
        return
    
    # Key metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            label="📊 Total Records",
            value=f"{summary['total_records']:,}",
            delta=f"+{summary.get('weekly_growth', 0):.1f}% this week"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            label="📈 Daily Average",
            value=f"{summary['avg_daily_uploads']:.1f}",
            delta=f"{summary['unique_dates']} active days"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            label="🏆 Peak Day",
            value=f"{summary['peak_upload_count']}",
            delta=str(summary['peak_upload_day'])
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            label="👥 Total Contributers",
            value=f"{summary.get('total_users', 0)}",
            delta="Unique Contributors"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col5:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            label="Categories",
            value=f"{summary['category_diversity']}",
            delta=f"of {len(CATEGORIES)} total"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", "📈 Trends", "🎯 Categories", "⏰ Time Analysis", "🔍 Insights"
    ])
    
    with tab1:
        create_overview_charts(summary)
    
    with tab2:
        create_trend_analysis(summary)
    
    with tab3:
        create_category_analysis(summary)
    
    with tab4:
        create_time_analysis(summary)
    
    with tab5:
        create_insights_panel(summary)

def create_overview_charts(summary: Dict):
    """Create overview charts"""
    col1, col2 = st.columns(2)
    
    with col1:
        # Media type distribution with enhanced styling
        if not summary["media_type"].empty:
            fig = px.pie(
                values=summary["media_type"].values,
                names=summary["media_type"].index,
                title="🎬 Media Type Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.4
            )
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title_font_size=18,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Status distribution
        if not summary["status"].empty:
            fig = px.bar(
                x=summary["status"].values,
                y=summary["status"].index,
                orientation='h',
                title="📈 Status Distribution",
                color=summary["status"].values,
                color_continuous_scale='viridis'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title_font_size=18,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

def create_trend_analysis(summary: Dict):
    """Create trend analysis charts"""
    # Daily uploads trend
    if not summary["uploads_per_day"].empty:
        daily_data = summary["uploads_per_day"].reset_index()
        daily_data.columns = ['Date', 'Count']
        
        fig = px.line(
            daily_data,
            x='Date',
            y='Count',
            title="📈 Daily Upload Trends",
            markers=True
        )
        
        # Add moving average
        daily_data['MA7'] = daily_data['Count'].rolling(window=7, center=True).mean()
        fig.add_scatter(
            x=daily_data['Date'],
            y=daily_data['MA7'],
            mode='lines',
            name='7-Day Moving Average',
            line=dict(color='orange', width=3, dash='dash')
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_font_size=18,
            height=500,
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Weekly trend heatmap
    col1, col2 = st.columns(2)
    
    with col1:
        if not summary["uploads_per_weekday"].empty:
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_data = summary["uploads_per_weekday"].reindex(weekday_order, fill_value=0)
            
            fig = px.bar(
                x=weekday_data.index,
                y=weekday_data.values,
                title="📅 Weekly Pattern",
                color=weekday_data.values,
                color_continuous_scale='plasma'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title_font_size=16,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if not summary["uploads_per_hour"].empty:
            fig = px.line_polar(
                r=summary["uploads_per_hour"].values,
                theta=summary["uploads_per_hour"].index,
                line_close=True,
                title="🕐 Hourly Activity Pattern"
            )
            fig.update_traces(fill='toself')
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, summary["uploads_per_hour"].max()])
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title_font_size=16,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

def create_category_analysis(summary: Dict):
    """Create category analysis charts"""
    if summary["category"].empty:
        st.warning("No category data available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top categories bar chart
        top_categories = summary["category"].head(10)
        fig = px.bar(
            x=top_categories.values,
            y=top_categories.index,
            orientation='h',
            title="🏆 Top 10 Categories",
            color=top_categories.values,
            color_continuous_scale='viridis'
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_font_size=18,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Category distribution treemap
        fig = px.treemap(
            names=summary["category"].index,
            values=summary["category"].values,
            title="🗂️ Category Distribution",
            color=summary["category"].values,
            color_continuous_scale='viridis'
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_font_size=18,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Category performance over time
    df = summary['df']
    if 'date' in df.columns and 'category' in df.columns:
        category_timeline = df.groupby(['date', 'category']).size().unstack(fill_value=0).reset_index()
        
        # Select top 5 categories for timeline
        top_5_categories = summary["category"].head(5).index.tolist()
        
        fig = go.Figure()
        colors = px.colors.qualitative.Set1
        
        for i, category in enumerate(top_5_categories):
            if category in category_timeline.columns:
                fig.add_trace(go.Scatter(
                    x=category_timeline['date'],
                    y=category_timeline[category],
                    mode='lines+markers',
                    name=category,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=6)
                ))
        
        fig.update_layout(
            title="📊 Category Trends Over Time",
            xaxis_title="Date",
            yaxis_title="Upload Count",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_font_size=18,
            height=400,
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)

def create_time_analysis(summary: Dict):
    """Create detailed time analysis"""
    col1, col2 = st.columns(2)
    
    with col1:
        # Monthly distribution
        if not summary["uploads_per_month"].empty:
            month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            monthly_data = summary["uploads_per_month"].reindex(month_order, fill_value=0)
            
            fig = px.bar(
                x=monthly_data.index,
                y=monthly_data.values,
                title="📅 Monthly Distribution",
                color=monthly_data.values,
                color_continuous_scale='blues'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title_font_size=16,
                height=400,
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Activity heatmap by hour and day
        df = summary['df']
        if 'hour' in df.columns and 'day_of_week' in df.columns:
            heatmap_data = df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
            
            # Reorder days
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = heatmap_data.reindex(day_order, fill_value=0)
            
            fig = px.imshow(
                heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                title="🔥 Activity Heatmap (Hour vs Day)",
                color_continuous_scale='viridis',
                aspect='auto'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title_font_size=16,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Peak activity analysis
    st.subheader("⏰ Peak Activity Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f"**🏆 Most Active Day:**")
        st.markdown(f"**{summary.get('most_active_weekday', 'N/A')}**")
        if not summary["uploads_per_weekday"].empty:
            max_day_count = summary["uploads_per_weekday"].max()
            st.markdown(f"*{max_day_count} uploads*")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f"**🕐 Peak Hour:**")
        st.markdown(f"**{summary.get('most_active_hour', 'N/A')}:00**")
        if not summary["uploads_per_hour"].empty:
            max_hour_count = summary["uploads_per_hour"].max()
            st.markdown(f"*{max_hour_count} uploads*")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f"**📊 Peak Single Day:**")
        st.markdown(f"**{summary.get('peak_upload_day', 'N/A')}**")
        st.markdown(f"*{summary.get('peak_upload_count', 0)} uploads*")
        st.markdown('</div>', unsafe_allow_html=True)

def create_insights_panel(summary: Dict):
    """Create AI-powered insights panel"""
    st.subheader("🧠 Smart Insights")
    
    insights = get_data_insights(summary)
    
    if insights:
        for i, insight in enumerate(insights):
            st.markdown(f"""
            <div class="glass-card">
                <h4>💡 Insight #{i+1}</h4>
                <p>{insight}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No insights available for the current data.")
    
    # Performance metrics
    st.subheader("📊 Performance Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Upload consistency score
        df = summary['df']
        if 'date' in df.columns:
            daily_uploads = df.groupby('date').size()
            consistency_score = (1 - (daily_uploads.std() / daily_uploads.mean())) * 100 if daily_uploads.mean() > 0 else 0
            consistency_score = max(0, min(100, consistency_score))
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=consistency_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Upload Consistency Score"},
                delta={'reference': 80},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "darkblue"},
                       'steps': [{'range': [0, 50], 'color': "lightgray"},
                                {'range': [50, 80], 'color': "gray"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                   'thickness': 0.75, 'value': 90}}))
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Category diversity score
        total_categories = len(CATEGORIES)
        used_categories = summary.get('category_diversity', 0)
        diversity_score = (used_categories / total_categories) * 100
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=diversity_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Category Diversity Score"},
            delta={'reference': 70},
            gauge={'axis': {'range': [None, 100]},
                   'bar': {'color': "darkgreen"},
                   'steps': [{'range': [0, 40], 'color': "lightgray"},
                            {'range': [40, 70], 'color': "gray"}],
                   'threshold': {'line': {'color': "red", 'width': 4},
                               'thickness': 0.75, 'value': 90}}))
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Recommendations
    st.subheader("🎯 Recommendations")
    recommendations = generate_recommendations(summary)
    
    for i, rec in enumerate(recommendations):
        st.markdown(f"""
        <div class="glass-card">
            <h4>🚀 Recommendation #{i+1}</h4>
            <p>{rec}</p>
        </div>
        """, unsafe_allow_html=True)

def generate_recommendations(summary: Dict) -> List[str]:
    """Generate personalized recommendations"""
    recommendations = []
    
    if not summary:
        return recommendations
    
    # Upload frequency recommendations
    avg_daily = summary.get('avg_daily_uploads', 0)
    if avg_daily < 1:
        recommendations.append("Consider increasing your daily upload frequency to build a more robust dataset.")
    elif avg_daily > 10:
        recommendations.append("Great upload frequency! Consider focusing on quality and category diversity.")
    
    # Category diversity recommendations
    diversity = summary.get('category_diversity', 0)
    total_categories = len(CATEGORIES)
    if diversity < total_categories * 0.3:
        recommendations.append("Try exploring more categories to diversify your content and improve data richness.")
    
    # Time-based recommendations
    if not summary["uploads_per_weekday"].empty:
        weekend_uploads = summary["uploads_per_weekday"].get('Saturday', 0) + summary["uploads_per_weekday"].get('Sunday', 0)
        weekday_uploads = summary["uploads_per_weekday"].sum() - weekend_uploads
        
        if weekend_uploads < weekday_uploads * 0.2:
            recommendations.append("Consider uploading content during weekends to maintain consistent activity.")
    
    # User contribution recommendations
    total_users = summary.get('total_users', 0)
    if total_users < 5:
        recommendations.append("Encourage more users to contribute to increase dataset diversity.")
    
    # Peak time recommendations
    if not summary["uploads_per_hour"].empty:
        peak_hour = summary["uploads_per_hour"].idxmax()
        if peak_hour < 9 or peak_hour > 17:
            recommendations.append(f"Your peak activity is at {peak_hour}:00. Consider maintaining this schedule for consistency.")
    
    return recommendations

def create_comparison_dashboard(records1: List[Dict], records2: List[Dict], label1: str, label2: str):
    """Create comparison dashboard between two datasets"""
    summary1 = advanced_summarize(records1)
    summary2 = advanced_summarize(records2)
    
    if not summary1 or not summary2:
        st.warning("Insufficient data for comparison")
        return
    
    st.subheader(f"⚖️ Comparison: {label1} vs {label2}")
    
    # Comparison metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        diff_total = summary2['total_records'] - summary1['total_records']
        st.metric(
            "Total Records",
            f"{summary2['total_records']:,}",
            delta=f"{diff_total:+,} vs {label1}"
        )
    
    with col2:
        diff_avg = summary2['avg_daily_uploads'] - summary1['avg_daily_uploads']
        st.metric(
            "Daily Average",
            f"{summary2['avg_daily_uploads']:.1f}",
            delta=f"{diff_avg:+.1f} vs {label1}"
        )
    
    with col3:
        diff_categories = summary2['category_diversity'] - summary1['category_diversity']
        st.metric(
            "Categories Used",
            f"{summary2['category_diversity']}",
            delta=f"{diff_categories:+} vs {label1}"
        )
    
    with col4:
        diff_users = summary2.get('total_users', 0) - summary1.get('total_users', 0)
        st.metric(
            "Total Users",
            f"{summary2.get('total_users', 0)}",
            delta=f"{diff_users:+} vs {label1}"
        )
    
    # Side-by-side comparison charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### 📊 {label1}")
        if not summary1["category"].empty:
            fig1 = px.pie(
                values=summary1["category"].values,
                names=summary1["category"].index,
                title=f"Categories - {label1}"
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.markdown(f"### 📊 {label2}")
        if not summary2["category"].empty:
            fig2 = px.pie(
                values=summary2["category"].values,
                names=summary2["category"].index,
                title=f"Categories - {label2}"
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)

def create_export_options(data: List[Dict], filename_prefix: str = "corpus_data"):
    """Create data export options"""
    if not data:
        st.warning("No data to export")
        return
    
    st.subheader("📥 Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        export_format = st.selectbox(
            "Export Format",
            ["CSV", "JSON", "Excel"],
            key=f"export_format_{filename_prefix}"
        )
    
    with col2:
        include_summary = st.checkbox(
            "Include Summary",
            value=True,
            key=f"include_summary_{filename_prefix}"
        )
    
    with col3:
        if st.button(f"📥 Download {export_format}", key=f"download_{filename_prefix}"):
            try:
                df = pd.DataFrame(data)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{filename_prefix}_{timestamp}"
                
                if export_format == "CSV":
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=f"{filename}.csv",
                        mime="text/csv"
                    )
                
                elif export_format == "JSON":
                    json_data = df.to_json(orient='records', indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_data,
                        file_name=f"{filename}.json",
                        mime="application/json"
                    )
                
                elif export_format == "Excel":
                    from io import BytesIO
                    output = BytesIO()
                    
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name='Records', index=False)
                        
                        if include_summary:
                            summary = advanced_summarize(data)
                            if summary:
                                summary_data = {
                                    'Metric': ['Total Records', 'Total Users', 'Unique Dates', 'Average Daily Uploads', 
                                             'Peak Upload Count', 'Category Diversity'],
                                    'Value': [
                                        summary['total_records'],
                                        summary['total_users'],
                                        summary['unique_dates'],
                                        f"{summary['avg_daily_uploads']:.2f}",
                                        summary['peak_upload_count'],
                                        summary['category_diversity']
                                    ]
                                }
                                summary_df = pd.DataFrame(summary_data)
                                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    st.download_button(
                        label="Download Excel",
                        data=output.getvalue(),
                        file_name=f"{filename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                st.success(f"✅ {export_format} export prepared successfully!")
                
            except Exception as e:
                st.error(f"❌ Export failed: {e}")

# Enhanced Login Interface
def show_enhanced_login():
    """Show enhanced login interface"""
    st.markdown('<h1 class="main-header">🚀 Advanced Corpus Records Dashboard</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-card">
        <h2 style="text-align: center; color: #4ECDC4;">🔐 Secure Login</h2>
        <p style="text-align: center; opacity: 0.8;">
            Access your personalized corpus analytics dashboard
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        login_tab, otp_tab = st.tabs(["🔑 Password Login", "📱 OTP Login"])
        
        with login_tab:
            with st.form("password_login_form", clear_on_submit=False):
                st.markdown("### 📱 Login with Password")
                
                col_phone, col_prefix = st.columns([4, 1])
                with col_prefix:
                    st.text_input("", value="+91", disabled=True)
                with col_phone:
                    phone = st.text_input(
                        "Phone Number",
                        placeholder="Enter your 10-digit number",
                        help="Enter your 10-digit phone number without country code",
                        max_chars=10
                    )
                
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    help="Enter your account password"
                )
                
                col_login, col_demo = st.columns(2)
                
                with col_login:
                    login_clicked = st.form_submit_button("🔑 Login", use_container_width=True)
                
                with col_demo:
                    demo_clicked = st.form_submit_button("🎯 Demo Mode", use_container_width=True)
                
                if login_clicked:
                    if phone and password:
                        full_phone = f"+91{phone}"
                        login_response = login_user(full_phone, password)
                        
                        if login_response and "access_token" in login_response:
                            token_data = decode_jwt_token(login_response["access_token"])
                            
                            if token_data:
                                st.session_state.authenticated = True
                                st.session_state.token = login_response["access_token"]
                                st.session_state.user_id = token_data["user_id"]
                                st.session_state.username = full_phone
                                st.session_state.login_attempts = 0
                                
                                st.success("🎉 Login successful! Redirecting to dashboard...")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Invalid token received")
                        else:
                            st.error("❌ Login failed. Please check your credentials.")
                    else:
                        st.warning("⚠️ Please enter both phone number and password")
                
                elif demo_clicked:
                    st.info("🎯 Demo mode activated! Using sample data for demonstration.")
                    st.session_state.authenticated = True
                    st.session_state.demo_mode = True
                    st.session_state.username = "Demo User"
                    st.rerun()
        
        with otp_tab:
            with st.form("otp_login_form", clear_on_submit=True):
                st.markdown("### 📱 Login with OTP")
                
                col_phone, col_prefix = st.columns([4, 1])
                with col_prefix:
                    st.text_input("", value="+91", disabled=True)
                with col_phone:
                    phone = st.text_input(
                        "Phone Number",
                        placeholder="Enter your 10-digit number",
                        help="Enter your 10-digit phone number without country code",
                        max_chars=10,
                        key="otp_phone"
                    )
                
                request_otp_clicked = st.form_submit_button("📤 Request OTP", use_container_width=True)
                
                if request_otp_clicked and phone:
                    full_phone = f"+91{phone}"
                    if request_otp(full_phone):
                        st.session_state["otp_phone"] = full_phone
                        st.success("✅ OTP sent successfully! Please check your phone.")
                        st.rerun()
            
            if st.session_state.get("otp_phone"):
                with st.form("otp_verify_form", clear_on_submit=True):
                    st.markdown(f"### 🔐 Verify OTP for {st.session_state['otp_phone']}")
                    otp = st.text_input(
                        "Enter OTP",
                        placeholder="Enter the 6-digit OTP",
                        help="Enter the OTP sent to your phone",
                        max_chars=6
                    )
                    
                    if st.form_submit_button("✅ Verify OTP", use_container_width=True):
                        if otp:
                            login_response = verify_otp(st.session_state["otp_phone"], otp)
                            
                            if login_response and "access_token" in login_response:
                                token_data = decode_jwt_token(login_response["access_token"])
                                
                                if token_data:
                                    st.session_state.authenticated = True
                                    st.session_state.token = login_response["access_token"]
                                    st.session_state.user_id = token_data["user_id"]
                                    st.session_state.username = st.session_state["otp_phone"]
                                    st.session_state.login_attempts = 0
                                    st.session_state.pop("otp_phone", None)
                                    
                                    st.success("🎉 OTP verified! Redirecting to dashboard...")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Invalid token received")
                            else:
                                st.error("❌ Invalid OTP. Please try again.")
                        else:
                            st.warning("⚠️ Please enter the OTP")
    
    # Login attempts warning
    if st.session_state.login_attempts >= 2:
        st.warning(f"⚠️ Login attempts: {st.session_state.login_attempts}/3")
    
    # Features preview
    st.markdown("---")
    st.markdown("### ✨ Dashboard Features")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>📊</h3>
            <h4>Advanced Analytics</h4>
            <p>Deep insights into your corpus data with AI-powered analytics</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>🎨</h3>
            <h4>Beautiful Visualizations</h4>
            <p>Interactive charts and graphs with modern design</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>⚡</h3>
            <h4>Real-time Updates</h4>
            <p>Live data synchronization and instant insights</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>📥</h3>
            <h4>Export Options</h4>
            <p>Download your data in multiple formats</p>
        </div>
        """, unsafe_allow_html=True)

# Main Application
def main():
    """Enhanced main application"""
    # Apply styling
    apply_advanced_styling()
    
    # Initialize session state
    initialize_session_state()
    
    # Show login if not authenticated
    if not st.session_state.authenticated:
        show_enhanced_login()
        return
    
    # Main dashboard for authenticated users
    st.markdown(f'<h1 class="main-header">🚀 Welcome back, {st.session_state.username}!</h1>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🎛️ Dashboard Control")
        
        dashboard_mode = st.selectbox(
            "Select Mode",
            ["🏠 My Records", "🔍 User Query", "🌐 Database Overview", "⚖️ Compare Users"],
            key="dashboard_mode_select"
        )
        
        st.markdown("---")
        
        # Filters section
        st.markdown("### 🎯 Filters")
        
        date_filter = st.date_input(
            "Date Range",
            value=None,
            help="Filter records by date range"
        )
        
        category_filter = st.multiselect(
            "Categories",
            options=list(CATEGORIES.keys()),
            help="Filter by specific categories"
        )
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            # Clear cache and reload data
            for key in list(st.session_state.keys()):
                if key.startswith("records_"):
                    del st.session_state[key]
            st.session_state.query_results = None
            st.session_state.database_overview = None
            st.rerun()
        
        st.markdown("---")
        
        # Settings
        st.markdown("### ⚙️ Settings")
        
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=False)
        
        if auto_refresh:
            refresh_interval = st.slider("Refresh Interval (seconds)", 30, 300, 60)
        
        theme_style = st.selectbox("🎨 Chart Style", ["Modern", "Classic", "Minimal"])
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Update filters
    filters = {}
    if date_filter:
        filters['date_range'] = (date_filter, date_filter) if isinstance(date_filter, datetime.date) else date_filter
    if category_filter:
        filters['categories'] = category_filter
    
    st.session_state.advanced_filters = filters
    
    # Main content based on selected mode
    if dashboard_mode == "🏠 My Records":
        show_my_records_dashboard()
    elif dashboard_mode == "🔍 User Query":
        show_user_query_dashboard()
    elif dashboard_mode == "🌐 Database Overview":
        show_database_overview_dashboard()
    elif dashboard_mode == "⚖️ Compare Users":
        show_comparison_dashboard()

def show_my_records_dashboard():
    """Show user's own records dashboard"""
    if st.session_state.get('demo_mode'):
        st.info("🎯 Demo Mode: Showing sample data")
        return
    
    records = fetch_records_with_cache(st.session_state.user_id, st.session_state.token, use_cache=False)
    
    if not records:
        st.warning("No records found for your account.")
        return
    
    summary = advanced_summarize(records, st.session_state.advanced_filters)
    
    if summary:
        create_advanced_overview_dashboard(summary)
        create_export_options(records, "my_records")
    else:
        st.error("Failed to process your records data.")

def show_user_query_dashboard():
    """Enhanced user query dashboard with dropdown selection"""
    st.subheader("🔍 User Records Query")
    
    # Initialize session state for user query
    if "users_list" not in st.session_state:
        st.session_state["users_list"] = None
    if "user_mapping" not in st.session_state:
        st.session_state["user_mapping"] = {}
    
    # Load users button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("👥 Load Users List", use_container_width=True, type="secondary"):
            token = st.session_state.get("token")
            if token:
                users_data = fetch_all_users(token)
                if users_data:
                    st.session_state["users_list"] = users_data
                    st.session_state["user_mapping"] = create_user_mapping(users_data)
                    st.success(f"✅ Loaded {len(users_data)} users!")
                else:
                    st.error("Failed to load users list.")
            else:
                st.error("Authentication token not found. Please log in again.")
    
    # User selection methods
    if st.session_state.get("users_list"):
        st.subheader("📋 Select User")
        
        # Create tabs for different selection methods
        tab1, tab2 = st.tabs(["👥 Select from List", "✏️ Enter User ID"])
        
        with tab1:
            # Dropdown selection
            user_mapping = st.session_state.get("user_mapping", {})
            if user_mapping:
                # Create options for selectbox (Name - ID format)
                user_options = ["Select a user..."] + [f"{name} - {user_id[:8]}..." for user_id, name in user_mapping.items()]
                
                selected_option = st.selectbox(
                    "Choose a user:",
                    options=user_options,
                    key="user_dropdown_enhanced"
                )
                
                if selected_option != "Select a user...":
                    # Extract user ID from the selected option
                    selected_user_id = None
                    for user_id, name in user_mapping.items():
                        if selected_option.startswith(f"{name} - {user_id[:8]}"):
                            selected_user_id = user_id
                            break
                    
                    if selected_user_id:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.info(f"Selected: {user_mapping[selected_user_id]} (ID: {selected_user_id[:8]}...)")
                        with col2:
                            if st.button("🔍 Query User", use_container_width=True):
                                st.session_state["query_user_id"] = selected_user_id
                                st.session_state["last_queried_user"] = selected_user_id
                                
                                # Fetch records for the selected user
                                token = st.session_state.get("token")
                                if token:
                                    records = fetch_any_user_records(selected_user_id, token)
                                    
                                    if records:
                                        st.session_state["query_results"] = records
                                        st.success(f"Found {len(records)} records for {user_mapping[selected_user_id]}!")
                                        st.rerun()
                                    else:
                                        st.session_state["query_results"] = None
                                        st.info(f"No records found for {user_mapping[selected_user_id]}.")
                                else:
                                    st.error("Authentication token not found. Please log in again.")
            else:
                st.warning("No users loaded. Please click 'Load Users List' first.")
        
        with tab2:
            # Manual ID input
            with st.form("user_query_form_manual"):
                query_user_id = st.text_input(
                    "User ID to Query",
                    value=st.session_state.get("query_user_id", ""),
                    help="Enter the User ID whose records you want to view"
                )
                
                query_submitted = st.form_submit_button("🔍 Search User Records")
                
                if query_submitted and query_user_id:
                    st.session_state.query_user_id = query_user_id
                    
                    records = fetch_any_user_records(query_user_id, st.session_state.token)
                    
                    if records:
                        st.session_state.query_results = records
                        st.session_state.last_queried_user = query_user_id
                        st.success(f"✅ Found {len(records)} records for user {query_user_id[:8]}...")
                        st.rerun()
                    else:
                        st.warning(f"No records found for user ID: {query_user_id}")
    
    else:
        # Show manual input only if users list is not loaded
        st.subheader("✏️ Enter User ID")
        st.info("💡 **Tip**: Click 'Load Users List' above to select users from a dropdown instead of entering IDs manually.")
        
        with st.form("user_query_form_fallback"):
            query_user_id = st.text_input(
                "User ID to Query",
                value=st.session_state.get("query_user_id", ""),
                help="Enter the User ID whose records you want to view"
            )
            
            query_submitted = st.form_submit_button("🔍 Search User Records")
            
            if query_submitted and query_user_id:
                st.session_state.query_user_id = query_user_id
                
                records = fetch_any_user_records(query_user_id, st.session_state.token)
                
                if records:
                    st.session_state.query_results = records
                    st.session_state.last_queried_user = query_user_id
                    st.success(f"✅ Found {len(records)} records for user {query_user_id[:8]}...")
                    st.rerun()
                else:
                    st.warning(f"No records found for user ID: {query_user_id}")
    
    # Display results
    if st.session_state.get("query_results") and st.session_state.get("last_queried_user"):
        st.divider()
        
        # Get user details
        records = st.session_state["query_results"]
        user_id = st.session_state["last_queried_user"]
        user_mapping = st.session_state.get("user_mapping", {})
        user_name = user_mapping.get(user_id, f"User {user_id[:8]}...")
        
        st.subheader(f"📊 Analytics for {user_name}")
        
        # Process summary
        summary = advanced_summarize(records, st.session_state.advanced_filters)
        
        if summary:
            create_advanced_overview_dashboard(summary)
            create_export_options(records, f"user_{user_name.replace(' ', '_')}")
        else:
            st.error("Failed to process the queried user's records.")
    
    # Clear results button
    if st.session_state.get("query_results"):
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Query Results"):
                st.session_state["query_results"] = None
                st.session_state["last_queried_user"] = None
                st.session_state["query_user_id"] = ""
                st.rerun()
        with col2:
            if st.button("🔄 Refresh Users List"):
                st.session_state["users_list"] = None
                st.session_state["user_mapping"] = {}
                st.rerun()

def show_database_overview_dashboard():
    """Show database overview dashboard"""
    st.subheader("🌐 Database Overview")
    
    if st.button("🔄 Load Database Overview"):
        with st.spinner("Loading database overview..."):
            all_records = fetch_all_records(st.session_state.token)
            
            if all_records:
                st.session_state.database_overview = all_records
                st.success(f"✅ Database overview loaded: {len(all_records)} total records")
            else:
                st.error("Failed to load database overview")
    
    if st.session_state.get("database_overview"):
        records = st.session_state.database_overview
        summary = advanced_summarize(records, st.session_state.advanced_filters)
        
        if summary:
            st.markdown("### 📈 Global Statistics")
            create_advanced_overview_dashboard(summary)
            
            # Additional database-specific insights
            st.markdown("### 🌍 Database-Wide Insights")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Top contributors
                df = summary['df']
                if 'user_id' in df.columns:
                    top_contributors = df['user_id'].value_counts().head(10)
                    
                    fig = px.bar(
                        x=top_contributors.values,
                        y=[f"User {uid[:8]}..." for uid in top_contributors.index],
                        orientation='h',
                        title="🏆 Top Contributors",
                        color=top_contributors.values,
                        color_continuous_scale='viridis'
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Global category distribution
                if not summary["category"].empty:
                    fig = px.treemap(
                        names=summary["category"].index,
                        values=summary["category"].values,
                        title="🗂️ Global Category Distribution"
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col3:
                # Upload timeline
                if not summary["uploads_per_day"].empty:
                    daily_data = summary["uploads_per_day"].reset_index()
                    daily_data.columns = ['Date', 'Count']
                    
                    fig = px.area(
                        daily_data,
                        x='Date',
                        y='Count',
                        title="📅 Global Upload Timeline"
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            create_export_options(records, "database_overview")
        else:
            st.error("Failed to process database overview data.")

def show_comparison_dashboard():
    """Enhanced comparison dashboard with user dropdowns"""
    st.subheader("⚖️ User Comparison")
    
    # Load users button
    if st.button("👥 Load Users for Comparison", use_container_width=True):
        token = st.session_state.get("token")
        if token:
            users_data = fetch_all_users(token)
            if users_data:
                st.session_state["users_list"] = users_data
                st.session_state["user_mapping"] = create_user_mapping(users_data)
                st.success(f"✅ Loaded {len(users_data)} users!")
    
    user_mapping = st.session_state.get("user_mapping", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 User 1")
        if user_mapping:
            user_options = ["Select a user..."] + [f"{name} - {user_id[:8]}..." for user_id, name in user_mapping.items()]
            selected_user1 = st.selectbox("Choose User 1:", options=user_options, key="compare_user1_dropdown")
            
            # Extract user ID
            user1_id = None
            if selected_user1 != "Select a user...":
                for user_id, name in user_mapping.items():
                    if selected_user1.startswith(f"{name} - {user_id[:8]}"):
                        user1_id = user_id
                        break
        else:
            user1_id = st.text_input("User 1 ID", key="compare_user1_manual")
        
    with col2:
        st.markdown("### 👤 User 2")
        if user_mapping:
            selected_user2 = st.selectbox("Choose User 2:", options=user_options, key="compare_user2_dropdown")
            
            # Extract user ID
            user2_id = None
            if selected_user2 != "Select a user...":
                for user_id, name in user_mapping.items():
                    if selected_user2.startswith(f"{name} - {user_id[:8]}"):
                        user2_id = user_id
                        break
        else:
            user2_id = st.text_input("User 2 ID", key="compare_user2_manual")
    
    if st.button("🔄 Compare Users"):
        if user1_id and user2_id:
            with st.spinner("Fetching comparison data..."):
                records1 = fetch_any_user_records(user1_id, st.session_state.token)
                records2 = fetch_any_user_records(user2_id, st.session_state.token)
                
                if records1 and records2:
                    # Get user names for labels
                    user1_name = user_mapping.get(user1_id, f"User {user1_id[:8]}...")
                    user2_name = user_mapping.get(user2_id, f"User {user2_id[:8]}...")
                    
                    create_comparison_dashboard(
                        records1, records2,
                        user1_name, user2_name
                    )
                else:
                    if not records1:
                        st.error(f"No records found for User 1")
                    if not records2:
                        st.error(f"No records found for User 2")
        else:
            st.warning("Please select both users for comparison")

def apply_advanced_styling():
    """Apply advanced CSS styling"""
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, #0A0A0A 0%, #1A061A 50%, #0A0A0A 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Custom Headers */
    .main-header {
        background: linear-gradient(90deg, #4ECDC4, #44A08D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Glass Card Effect */
    .glass-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    }
    
    /* Metric Containers */
    .metric-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        padding: 15px;
        margin: 5px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: transform 0.3s ease;
    }
    
    .metric-container:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(45deg, #4ECDC4, #44A08D);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    
    /* Form Styling */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        color: white;
    }
    
    .stSelectbox > div > div > div {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #4ECDC4, #44A08D);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 10px 20px;
        color: white;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #4ECDC4, #44A08D);
    }
    
    /* Plotly Charts */
    .js-plotly-plot {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    }
    
    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .metric-container {
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(45deg, #4ECDC4, #44A08D);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(45deg, #44A08D, #4ECDC4);
    }
    </style>
    """, unsafe_allow_html=True)

# Run the application
if __name__ == "__main__":
    main()
