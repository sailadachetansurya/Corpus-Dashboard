import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from typing import Dict, List, Optional
import os
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Corpus Records Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Categories data (this would be updated from a real data source)
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

# Reverse mapping for category ID to name
CATEGORY_ID_TO_NAME = {v: k for k, v in CATEGORIES.items()}

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables"""
    session_vars = {
        "authenticated": False,
        "username": None,
        "token": None,
        "user_id": None,
        "login_attempts": 0,
        "selected_category": "Fables",
        "query_user_id": "",
        "query_results": None,
        "last_queried_user": None
    }
    
    for var, default_value in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default_value

# Authentication Functions
def decode_jwt_token(token: str) -> Optional[Dict]:
    """Decode JWT token to extract user information"""
    try:
        # Split token and get payload
        parts = token.split(".")
        if len(parts) != 3:
            logger.error("Invalid JWT token format")
            return None
            
        payload = parts[1] + "=="  # Add padding
        payload_decoded = json.loads(base64.b64decode(payload).decode("utf-8"))
        
        user_id = payload_decoded.get("sub")
        if not user_id:
            logger.error("User ID not found in token")
            return None
            
        return {
            "user_id": user_id,
            "payload": payload_decoded
        }
        
    except (IndexError, json.JSONDecodeError, base64.binascii.Error) as e:
        logger.error(f"Failed to decode token: {e}")
        st.error(f"Failed to decode token: {e}")
        return None

def login_user(phone: str, password: str) -> Optional[Dict]:
    """Authenticate user with phone and password"""
    if not phone or not password:
        st.error("Please enter both phone number and password")
        return None
        
    try:
        with st.spinner("Authenticating..."):
            response = requests.post(
                "https://backend2.swecha.org/api/v1/auth/login",
                json={"phone": phone, "password": password},
                headers={"accept": "application/json", "Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
    except requests.exceptions.Timeout:
        st.error("Login request timed out. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Unable to connect to the server. Please check your internet connection.")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Invalid phone number or password.")
            st.session_state.login_attempts += 1
            if st.session_state.login_attempts >= 3:
                st.error("Too many failed attempts. Please wait before trying again.")
        elif e.response.status_code == 429:
            st.error("Too many requests. Please wait before trying again.")
        else:
            st.error(f"Login failed with status {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        st.error(f"Unexpected error during login: {e}")
        return None

# Data Fetching Functions
def fetch_records(user_id: str, token: str) -> List[Dict]:
    """Fetch records from the API with improved error handling"""
    if not user_id or not token:
        st.error("User ID and token are required")
        return []
        
    url = f"https://backend2.swecha.org/api/v1/records/?user_id={user_id}&skip=0&limit=1000"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        with st.spinner("Fetching records..."):
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Expected list, got {type(data)}")
                st.warning("Unexpected data format received from server")
                return []
                
            logger.info(f"Successfully fetched {len(data)} records")
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
            st.error("Access denied. You don't have permission to view this data.")
        elif e.response.status_code == 404:
            st.error("Records not found for this user.")
        else:
            st.error(f"Failed to fetch records: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching records: {e}")
        st.error(f"Unexpected error: {e}")
        return []

def fetch_any_user_records(query_user_id: str, token: str) -> List[Dict]:
    """Fetch records for any user ID with specific error handling"""
    if not query_user_id or not token:
        st.error("User ID and token are required")
        return []
        
    # Validate UUID format (basic validation)
    if len(query_user_id.strip()) < 10:
        st.error("Please enter a valid User ID")
        return []
        
    url = f"https://backend2.swecha.org/api/v1/records/?user_id={query_user_id.strip()}&skip=0&limit=1000"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        with st.spinner(f"Fetching records for user {query_user_id[:8]}..."):
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Expected list, got {type(data)}")
                st.warning("Unexpected data format received from server")
                return []
                
            logger.info(f"Successfully fetched {len(data)} records for user {query_user_id}")
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
            st.error("Access denied. You don't have permission to view this user's data.")
        elif e.response.status_code == 404:
            st.warning(f"No records found for user ID: {query_user_id}")
        else:
            st.error(f"Failed to fetch records: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching records for user {query_user_id}: {e}")
        st.error(f"Unexpected error: {e}")
        return []
    
def fetch_all_records(token: str) -> List[Dict]:
    """Fetch all records from the database for overview"""
    if not token:
        st.error("Token is required")
        return []
        
    # Remove user_id parameter to get all records
    url = f"https://backend2.swecha.org/api/v1/records/?skip=0&limit=10000"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        with st.spinner("🌐 Fetching database overview..."):
            response = requests.get(url, headers=headers, timeout=60)  # Longer timeout for large data
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Expected list, got {type(data)}")
                st.warning("Unexpected data format received from server")
                return []
                
            logger.info(f"Successfully fetched {len(data)} total records from database")
            return data
            
    except requests.exceptions.Timeout:
        st.error("Request timed out. The database might be large. Please try again.")
        return []
    except requests.exceptions.ConnectionError:
        st.error("Unable to connect to the server. Please check your internet connection.")
        return []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Authentication failed. Please log in again.")
            st.session_state.authenticated = False
        elif e.response.status_code == 403:
            st.error("Access denied. You don't have permission to view database overview.")
        else:
            st.error(f"Failed to fetch database overview: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching database overview: {e}")
        st.error(f"Unexpected error: {e}")
        return []


def validate_records_data(records: List[Dict]) -> bool:
    """Validate the structure of records data"""
    if not records:
        return True  # Empty list is valid
        
    required_fields = ['category_id', 'created_at', 'media_type', 'status']
    sample = records[0]
    
    missing_fields = [field for field in required_fields if field not in sample]
    if missing_fields:
        st.error(f"Missing required fields in data: {missing_fields}")
        return False
        
    return True

# Data Processing Functions
def summarize(records: List[Dict]) -> Optional[Dict]:
    """Summarize the records data with improved error handling"""
    if not records or not isinstance(records, list):
        st.warning("No valid records data to process")
        return None
        
    if not validate_records_data(records):
        return None
    
    try:
        df = pd.DataFrame(records)
        
        # Map category_id to category name
        df["category"] = df["category_id"].map(CATEGORY_ID_TO_NAME).fillna("Unknown")
        
        # Handle date conversion with error handling
        df["created_at"] = pd.to_datetime(df["created_at"], errors='coerce').dt.date
        
        # Remove rows with invalid dates
        initial_count = len(df)
        df = df.dropna(subset=['created_at'])
        
        if len(df) < initial_count:
            logger.warning(f"Removed {initial_count - len(df)} records with invalid dates")
        
        if df.empty:
            st.warning("No valid data after processing")
            return None
        
        # Generate summary statistics
        media_type_counts = df["media_type"].value_counts()
        status_counts = df["status"].value_counts()
        category_counts = df["category"].value_counts()
        uploads_per_day = df.groupby("created_at").size()
        
        return {
            "media_type": media_type_counts,
            "status": status_counts,
            "category": category_counts,
            "uploads_per_day": uploads_per_day,
            "df": df,
            "total_records": len(df)
        }
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        st.error(f"Error processing data: {e}")
        return None

def summarize_category(records: List[Dict], selected_category: str) -> Optional[Dict]:
    """Summarize records for a specific category"""
    if not records:
        return None
    
    try:
        df = pd.DataFrame(records)
        df["category"] = df["category_id"].map(CATEGORY_ID_TO_NAME).fillna("Unknown")
        df["created_at"] = pd.to_datetime(df["created_at"], errors='coerce').dt.date
        
        # Filter by selected category
        category_df = df[df["category"] == selected_category]
        
        if category_df.empty:
            return None
        
        media_type_counts = category_df["media_type"].value_counts()
        status_counts = category_df["status"].value_counts()
        uploads_per_day = category_df.groupby("created_at").size()
        
        return {
            "media_type": media_type_counts,
            "status": status_counts,
            "uploads_per_day": uploads_per_day,
            "df": category_df,
            "total_records": len(category_df)
        }
        
    except Exception as e:
        logger.error(f"Error processing category data: {e}")
        st.error(f"Error processing category data: {e}")
        return None

# Visualization Functions
def plot_summary(summary: Dict):
    """Plot summary using matplotlib with dark theme"""
    if not summary:
        st.warning("No data available to plot")
        return
    
    try:
        # Set dark theme for matplotlib
        plt.style.use('dark_background')
        fig, axs = plt.subplots(2, 2, figsize=(12, 8))
        fig.patch.set_facecolor('#0E1117')
        
        # Media type distribution
        if not summary["media_type"].empty:
            summary["media_type"].plot(kind="bar", color="#FF6B6B", ax=axs[0, 0])
            axs[0, 0].set_title("Uploads by Media Type", color='white')
            axs[0, 0].set_ylabel("Count", color='white')
            axs[0, 0].tick_params(axis='x', rotation=45, colors='white')
            axs[0, 0].tick_params(axis='y', colors='white')
            axs[0, 0].set_facecolor('#0E1117')
        
        # Upload status
        if not summary["status"].empty:
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
            summary["status"].plot(kind="pie", autopct="%1.1f%%", startangle=140, ax=axs[0, 1], colors=colors)
            axs[0, 1].set_title("Upload Status Distribution", color='white')
            axs[0, 1].set_ylabel("")
            axs[0, 1].set_facecolor('#0E1117')
        
        # Category distribution
        if not summary["category"].empty:
            top_categories = summary["category"].head(5)
            top_categories.plot(kind="bar", color="#4ECDC4", ax=axs[1, 0])
            axs[1, 0].set_title("Top 5 Categories", color='white')
            axs[1, 0].set_ylabel("Count", color='white')
            axs[1, 0].tick_params(axis='x', rotation=45, colors='white')
            axs[1, 0].tick_params(axis='y', colors='white')
            axs[1, 0].set_facecolor('#0E1117')
        
        # Uploads over time
        if not summary["uploads_per_day"].empty:
            summary["uploads_per_day"].plot(kind="line", marker="o", ax=axs[1, 1], color='#45B7D1')
            axs[1, 1].set_title("Uploads Over Time", color='white')
            axs[1, 1].set_ylabel("Count", color='white')
            axs[1, 1].tick_params(axis="x", rotation=45, colors='white')
            axs[1, 1].tick_params(axis='y', colors='white')
            axs[1, 1].set_facecolor('#0E1117')
        
        plt.tight_layout()
        st.pyplot(fig)
        
    except Exception as e:
        logger.error(f"Error creating summary plots: {e}")
        st.error(f"Error creating summary plots: {e}")

def create_plotly_charts(summary: Dict):
    """Create interactive Plotly charts with dark theme"""
    if not summary:
        st.warning("No data available for charts")
        return
    
    try:
        df = summary['df']
        
        # Create columns for layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Total Records Card
            total_records = summary.get('total_records', len(df))
            st.metric(
                label="📊 Total Records Uploaded",
                value=f"{total_records:,}",
                delta=None
            )
            
            # Media Type Distribution Pie Chart
            if not summary["media_type"].empty:
                media_counts = summary["media_type"]
                fig_pie = px.pie(
                    values=media_counts.values,
                    names=media_counts.index,
                    title="Records by Media Type",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Category Distribution Bar Chart
            if not summary["category"].empty:
                category_counts = summary["category"].head(10)
                fig_bar = px.bar(
                    x=category_counts.values,
                    y=category_counts.index,
                    orientation='h',
                    title="Top 10 Categories",
                    labels={'x': 'Count', 'y': 'Category'},
                    color=category_counts.values,
                    color_continuous_scale='viridis'
                )
                fig_bar.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # Timeline Chart
        if not summary["uploads_per_day"].empty:
            st.subheader("📅 Upload Timeline")
            daily_uploads = summary["uploads_per_day"].reset_index()
            daily_uploads.columns = ['Date', 'Count']
            
            fig_timeline = px.line(
                daily_uploads,
                x='Date',
                y='Count',
                title="Daily Upload Activity",
                markers=True
            )
            fig_timeline.update_traces(line_color='#FF6B6B', line_width=3)
            fig_timeline.update_layout(
                xaxis_title="Date",
                yaxis_title="Number of Uploads",
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
            
    except Exception as e:
        logger.error(f"Error creating Plotly charts: {e}")
        st.error(f"Error creating Plotly charts: {e}")

def create_category_plotly_charts(summary: Dict, category_name: str):
    """Create interactive Plotly charts for specific category"""
    if not summary:
        st.warning(f"No data available for {category_name}")
        return
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            # Total Records Card for Category
            total_records = summary.get('total_records', 0)
            st.metric(
                label=f"📊 {category_name} Records",
                value=f"{total_records:,}",
                delta=None
            )
            
            # Media Type Distribution Pie Chart
            if not summary['media_type'].empty:
                fig_pie = px.pie(
                    values=summary['media_type'].values,
                    names=summary['media_type'].index,
                    title=f"{category_name} - Media Types",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Status Distribution
            if not summary['status'].empty:
                fig_status = px.bar(
                    x=summary['status'].values,
                    y=summary['status'].index,
                    orientation='h',
                    title=f"{category_name} - Status Distribution",
                    labels={'x': 'Count', 'y': 'Status'},
                    color=summary['status'].values,
                    color_continuous_scale='plasma'
                )
                fig_status.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig_status, use_container_width=True)
        
        # Timeline Chart for Category
        if not summary['uploads_per_day'].empty:
            st.subheader(f"📅 {category_name} Upload Timeline")
            daily_uploads = summary['uploads_per_day'].reset_index()
            daily_uploads.columns = ['Date', 'Count']
            
            fig_timeline = px.line(
                daily_uploads,
                x='Date',
                y='Count',
                title=f"{category_name} - Daily Upload Activity",
                markers=True
            )
            fig_timeline.update_traces(line_color='#4ECDC4', line_width=3)
            fig_timeline.update_layout(
                xaxis_title="Date",
                yaxis_title="Number of Uploads",
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
            
    except Exception as e:
        logger.error(f"Error creating category charts: {e}")
        st.error(f"Error creating category charts: {e}")

def create_user_query_charts(summary: Dict, queried_user_id: str):
    """Create charts for queried user data"""
    if not summary:
        st.warning(f"No data available for user {queried_user_id}")
        return
    
    try:
        df = summary['df']
        
        # Create columns for layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Total Records Card
            total_records = summary.get('total_records', len(df))
            st.metric(
                label=f"📊 Total Records for User {queried_user_id[:8]}...",
                value=f"{total_records:,}",
                delta=None
            )
            
            # Media Type Distribution Pie Chart
            if not summary["media_type"].empty:
                media_counts = summary["media_type"]
                fig_pie = px.pie(
                    values=media_counts.values,
                    names=media_counts.index,
                    title=f"Media Types - User {queried_user_id[:8]}...",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Category Distribution Bar Chart
            if not summary["category"].empty:
                category_counts = summary["category"].head(10)
                fig_bar = px.bar(
                    x=category_counts.values,
                    y=category_counts.index,
                    orientation='h',
                    title=f"Categories - User {queried_user_id[:8]}...",
                    labels={'x': 'Count', 'y': 'Category'},
                    color=category_counts.values,
                    color_continuous_scale='plasma'
                )
                fig_bar.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # Status Distribution
        if not summary["status"].empty:
            st.subheader(f"📈 Status Distribution - User {queried_user_id[:8]}...")
            fig_status = px.bar(
                x=summary["status"].index,
                y=summary["status"].values,
                title=f"Upload Status - User {queried_user_id[:8]}...",
                labels={'x': 'Status', 'y': 'Count'},
                color=summary["status"].values,
                color_continuous_scale='viridis'
            )
            fig_status.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        # Timeline Chart
        if not summary["uploads_per_day"].empty:
            st.subheader(f"📅 Upload Timeline - User {queried_user_id[:8]}...")
            daily_uploads = summary["uploads_per_day"].reset_index()
            daily_uploads.columns = ['Date', 'Count']
            
            fig_timeline = px.line(
                daily_uploads,
                x='Date',
                y='Count',
                title=f"Daily Upload Activity - User {queried_user_id[:8]}...",
                markers=True
            )
            fig_timeline.update_traces(line_color='#96CEB4', line_width=3)
            fig_timeline.update_layout(
                xaxis_title="Date",
                yaxis_title="Number of Uploads",
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
            
    except Exception as e:
        logger.error(f"Error creating user query charts: {e}")
        st.error(f"Error creating user query charts: {e}")

def create_database_overview_charts(summary: Dict):
    """Create charts for database overview"""
    if not summary:
        st.warning("No database data available")
        return
    
    try:
        df = summary['df']
        
        # Database Statistics Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🗄️ Total Records", f"{summary['total_records']:,}")
        
        with col2:
            if not summary["category"].empty:
                total_categories = len(summary["category"])
                st.metric("📂 Categories", f"{total_categories}")
        
        with col3:
            if not summary["media_type"].empty:
                total_media_types = len(summary["media_type"])
                st.metric("🎬 Media Types", f"{total_media_types}")
        
        with col4:
            # Calculate unique users
            if 'user_id' in df.columns:
                unique_users = df['user_id'].nunique()
                st.metric("👥 Active Users", f"{unique_users:,}")
            else:
                st.metric("📊 Data Points", f"{len(df):,}")
        
        st.divider()
        
        # Create visualization columns
        col1, col2 = st.columns(2)
        
        with col1:
            # Media Type Distribution
            if not summary["media_type"].empty:
                fig_media = px.pie(
                    values=summary["media_type"].values,
                    names=summary["media_type"].index,
                    title="🎬 Database Media Type Distribution",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#F7DC6F', '#BB8FCE']
                )
                fig_media.update_traces(textposition='inside', textinfo='percent+label')
                fig_media.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=400
                )
                st.plotly_chart(fig_media, use_container_width=True)
            
            # Status Distribution
            if not summary["status"].empty:
                fig_status = px.bar(
                    x=summary["status"].index,
                    y=summary["status"].values,
                    title="📈 Database Status Distribution",
                    labels={'x': 'Status', 'y': 'Count'},
                    color=summary["status"].values,
                    color_continuous_scale='viridis'
                )
                fig_status.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=400
                )
                st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Top Categories
            if not summary["category"].empty:
                top_categories = summary["category"].head(15)
                fig_categories = px.bar(
                    x=top_categories.values,
                    y=top_categories.index,
                    orientation='h',
                    title="📂 Top 15 Categories in Database",
                    labels={'x': 'Count', 'y': 'Category'},
                    color=top_categories.values,
                    color_continuous_scale='plasma'
                )
                fig_categories.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    height=800
                )
                st.plotly_chart(fig_categories, use_container_width=True)
        
        # Timeline Chart
        if not summary["uploads_per_day"].empty:
            st.subheader("📅 Database Upload Timeline")
            daily_uploads = summary["uploads_per_day"].reset_index()
            daily_uploads.columns = ['Date', 'Count']
            
            fig_timeline = px.line(
                daily_uploads,
                x='Date',
                y='Count',
                title="📈 Daily Upload Activity - Entire Database",
                markers=True
            )
            fig_timeline.update_traces(line_color='#F39C12', line_width=3)
            fig_timeline.update_layout(
                xaxis_title="Date",
                yaxis_title="Number of Uploads",
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        # User Activity Heatmap (if user_id is available)
        if 'user_id' in df.columns:
            st.subheader("👥 User Activity Overview")
            user_activity = df.groupby('user_id').size().sort_values(ascending=False).head(20)
            
            fig_users = px.bar(
                x=user_activity.values,
                y=[f"User {uid[:8]}..." for uid in user_activity.index],
                orientation='h',
                title="🏆 Top 20 Most Active Users",
                labels={'x': 'Records Count', 'y': 'User ID'},
                color=user_activity.values,
                color_continuous_scale='sunset'
            )
            fig_users.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=600
            )
            st.plotly_chart(fig_users, use_container_width=True)
            
    except Exception as e:
        logger.error(f"Error creating database overview charts: {e}")
        st.error(f"Error creating database overview charts: {e}")



# UI Functions
def show_login_page():
    """Display the login page"""
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0E1117;
            color: white;
        }
        .login-container {
            background-color: #1E1E1E;
            padding: 2rem;
            border-radius: 1rem;
            margin: 2rem auto;
            max-width: 400px;
            border-left: 4px solid #FF6B6B;
        }
        .login-title {
            font-size: 2rem;
            font-weight: bold;
            color: #FF6B6B;
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown('<div class="login-title">🎯 Corpus Records Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.subheader("Login")
    
    with st.form("login_form"):
        phone = st.text_input("Phone Number", placeholder="Enter your phone number")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            if st.session_state.login_attempts >= 3:
                st.error("Too many failed attempts. Please refresh the page and try again.")
                return
                
            login_result = login_user(phone, password)
            if login_result:
                token = login_result.get("access_token")
                if token:
                    # Decode user_id from token
                    token_data = decode_jwt_token(token)
                    if token_data:
                        st.session_state["user_id"] = token_data["user_id"]
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = phone
                        st.session_state["token"] = token
                        st.session_state["login_attempts"] = 0  # Reset attempts on success
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Failed to process authentication token")
                else:
                    st.error("Authentication token not received")
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_user_query_section():
    """Display the user query section"""
    st.markdown('<div class="category-section">', unsafe_allow_html=True)
    st.subheader("🔍 Query Any User's Records")
    st.markdown("Enter any user ID to view their records and analytics.")
    
    # User ID input with form
    with st.form("user_query_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query_user_id = st.text_input(
                "User ID to Query:",
                value=st.session_state.get("query_user_id", ""),
                placeholder="Enter user ID (e.g., 2bcc18a7-03a4-40ea-ae9b-223607f239df)",
                help="Enter the complete User ID to fetch their records"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
            query_submit = st.form_submit_button("🔍 Search", use_container_width=True)
    
    # Process query
    if query_submit and query_user_id.strip():
        st.session_state["query_user_id"] = query_user_id.strip()
        st.session_state["last_queried_user"] = query_user_id.strip()
        
        # Fetch records for the queried user
        token = st.session_state.get("token")
        
        with st.spinner(f"🔍 Searching records for user {query_user_id[:8]}..."):
            queried_records = fetch_any_user_records(query_user_id.strip(), token)
        
        if queried_records:
            st.session_state["query_results"] = queried_records
            st.success(f"Found {len(queried_records)} records for user {query_user_id[:8]}...")
        else:
            st.session_state["query_results"] = None
            st.info(f"No records found for user {query_user_id[:8]}...")
    
    # Display results if available
    if st.session_state.get("query_results") and st.session_state.get("last_queried_user"):
        queried_records = st.session_state["query_results"]
        queried_user_id = st.session_state["last_queried_user"]
        
        # Process and display the queried user's data
        query_summary = summarize(queried_records)
        
        if query_summary:
            st.subheader(f"📊 Analytics for User {queried_user_id[:8]}...")
            
            # Display summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Records", f"{query_summary['total_records']:,}")
            
            with col2:
                if not query_summary["media_type"].empty:
                    most_common_media = query_summary["media_type"].index[0]
                    st.metric("Most Common Media", most_common_media)
            
            with col3:
                if not query_summary["category"].empty:
                    most_common_category = query_summary["category"].index[0]
                    st.metric("Top Category", most_common_category)
            
            with col4:
                if not query_summary["status"].empty:
                    most_common_status = query_summary["status"].index[0]
                    st.metric("Primary Status", most_common_status)
            
            st.divider()
            
            # Display charts for queried user
            create_user_query_charts(query_summary, queried_user_id)
            
            # Display data table
            st.subheader(f"📋 Records Table - User {queried_user_id[:8]}...")
            df_display = query_summary['df'].copy()
            
            # Select relevant columns for display
            display_columns = ['created_at', 'category', 'media_type', 'status']
            if 'file_name' in df_display.columns:
                display_columns.append('file_name')
            
            df_display = df_display[display_columns]
            df_display.columns = [col.replace('_', ' ').title() for col in df_display.columns]
            
            # Add download button for the data
            csv = df_display.to_csv(index=False)
            st.download_button(
                label=f"📥 Download CSV - User {queried_user_id[:8]}...",
                data=csv,
                file_name=f"user_records_{queried_user_id[:8]}.csv",
                mime="text/csv"
            )
            
            st.dataframe(df_display, use_container_width=True, height=400)
            
        else:
            st.warning(f"Unable to process data for user {queried_user_id[:8]}...")
    
    # Clear results button
    if st.session_state.get("query_results"):
        if st.button("🗑️ Clear Query Results"):
            st.session_state["query_results"] = None
            st.session_state["last_queried_user"] = None
            st.session_state["query_user_id"] = ""
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_database_overview_section():
    """Display the database overview section"""
    st.markdown('<div class="category-section">', unsafe_allow_html=True)
    st.subheader("🌐 Database Overview")
    st.markdown("View comprehensive analytics for the entire database across all users.")
    
    # Add warning about data size
    st.info("⚠️ **Note**: This section loads data from the entire database and may take longer to load.")
    
    # Fetch database overview button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🔍 Load Database Overview", use_container_width=True, type="primary"):
            token = st.session_state.get("token")
            
            if not token:
                st.error("Authentication required. Please log in again.")
                return
            
            # Fetch all records
            all_records = fetch_all_records(token)
            
            if all_records:
                st.session_state["database_overview"] = all_records
                st.success(f"✅ Loaded {len(all_records):,} records from database!")
            else:
                st.session_state["database_overview"] = None
                st.error("Failed to load database overview.")
    
    # Display results if available
    if st.session_state.get("database_overview"):
        all_records = st.session_state["database_overview"]
        
        # Process database summary
        with st.spinner("📊 Processing database analytics..."):
            database_summary = summarize(all_records)
        
        if database_summary:
            st.subheader("📈 Database Analytics Dashboard")
            
            # Show last updated info
            st.caption(f"📅 Data loaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Records: {len(all_records):,}")
            
            # Display database overview charts
            create_database_overview_charts(database_summary)
            
            # Additional insights
            st.subheader("🔍 Database Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Quick Stats")
                df = database_summary['df']
                
                # Calculate some interesting stats
                avg_records_per_day = len(df) / max(len(database_summary["uploads_per_day"]), 1)
                most_active_day = database_summary["uploads_per_day"].idxmax() if not database_summary["uploads_per_day"].empty else "N/A"
                peak_uploads = database_summary["uploads_per_day"].max() if not database_summary["uploads_per_day"].empty else 0
                
                st.metric("📈 Avg Records/Day", f"{avg_records_per_day:.1f}")
                st.metric("🏆 Peak Upload Day", str(most_active_day))
                st.metric("🔥 Peak Daily Uploads", f"{peak_uploads}")
            
            with col2:
                st.markdown("#### 🎯 Category Insights")
                if not database_summary["category"].empty:
                    top_category = database_summary["category"].index[0]
                    top_category_count = database_summary["category"].iloc[0]
                    category_percentage = (top_category_count / len(df)) * 100
                    
                    st.metric("🥇 Top Category", top_category)
                    st.metric("📊 Top Category Count", f"{top_category_count:,}")
                    st.metric("📈 Top Category %", f"{category_percentage:.1f}%")
            
            # Download option for database overview
            st.subheader("💾 Export Database Overview")
            
            # Prepare export data
            export_df = database_summary['df'].copy()
            export_columns = ['created_at', 'category', 'media_type', 'status']
            if 'user_id' in export_df.columns:
                export_columns.append('user_id')
            
            export_df = export_df[export_columns]
            export_df.columns = [col.replace('_', ' ').title() for col in export_df.columns]
            
            csv_data = export_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Database Overview (CSV)",
                data=csv_data,
                file_name=f"database_overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        else:
            st.error("Failed to process database overview data.")
    
    # Clear database overview
    if st.session_state.get("database_overview"):
        if st.button("🗑️ Clear Database Overview"):
            st.session_state["database_overview"] = None
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def show_dashboard():
    """Display the main dashboard after authentication"""
    # Apply dark theme CSS
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0E1117;
            color: white;
        }
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #FF6B6B;
            text-align: center;
            margin-bottom: 2rem;
        }
        .user-info-container {
            background-color: #1E1E1E;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
            border-left: 4px solid #FF6B6B;
        }
        .category-section {
            background-color: #1E1E1E;
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-top: 2rem;
            border-left: 4px solid #4ECDC4;
        }
        .stSelectbox > div > div {
            background-color: #1E1E1E;
            color: white;
        }
        .stTextInput > div > div > input {
            background-color: #1E1E1E;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Header
    st.markdown('<div class="main-header">🎯 Corpus Records Dashboard</div>', unsafe_allow_html=True)
    
    # User info and logout section
    st.markdown('<div class="user-info-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.markdown(f"**Welcome:** {st.session_state.get('username', 'Unknown User')}")
    
    with col2:
        st.markdown(f"**User ID:** {st.session_state.get('user_id', 'Unknown')}")
    
    with col3:
        if st.button("Logout", use_container_width=True):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Validate session state
    if not st.session_state.get("user_id") or not st.session_state.get("token"):
        st.error("Session expired. Please log in again.")
        st.session_state["authenticated"] = False
        st.rerun()
        return
    
    # Fetch and display data
    user_id = st.session_state["user_id"]
    token = st.session_state["token"]
    
    # Fetch records
    # Enhanced loading for main records
    progress_bar = st.progress(0)
    status_text = st.empty()

    status_text.text("🔄 Connecting to server...")
    progress_bar.progress(25)

    status_text.text("📡 Fetching your records...")
    progress_bar.progress(50)

    records = fetch_records(user_id, token)

    progress_bar.progress(100)
    status_text.text("✅ Records loaded successfully!")

    # Clear the progress indicators
    progress_bar.empty()
    status_text.empty()

    
    if records:
        # Overall summary
        summary = summarize(records)
        
        if summary:
            # Display matplotlib summary plots
            st.subheader("📊 Overall Data Summary")
            plot_summary(summary)
            
            st.divider()
            
            # Display interactive Plotly charts
            st.subheader("🎨 Interactive Dashboard")
            create_plotly_charts(summary)
            
            st.divider()
            
            # Category Selection Section
            st.markdown('<div class="category-section">', unsafe_allow_html=True)
            st.subheader("🎯 Category-Specific Analysis")
            
            # Category selectbox with session state
            category_options = list(CATEGORIES.keys())
            current_selection = st.session_state.get("selected_category", "Fables")
            
            if current_selection not in category_options:
                current_selection = category_options[0]
            
            selected_category = st.selectbox(
                "Select a category to analyze:",
                options=category_options,
                index=category_options.index(current_selection),
                key="category_selector"
            )
            
            # Update session state
            st.session_state["selected_category"] = selected_category
            
            # Show category-specific analysis
            if selected_category:
                with st.spinner(f"Processing data for {selected_category}..."):
                    category_summary = summarize_category(records, selected_category)
                    
                if category_summary:
                    st.subheader(f"📈 {selected_category} Category Report")
                    
                    # Display category-specific charts
                    create_category_plotly_charts(category_summary, selected_category)
                    
                    # Display category-specific data table
                    st.subheader(f"📋 {selected_category} Records Data")
                    df_display = category_summary['df'].copy()
                    df_display = df_display[['created_at', 'media_type', 'status']]
                    df_display.columns = ['Created Date', 'Media Type', 'Status']
                    st.dataframe(df_display, use_container_width=True)
                    
                else:
                    st.warning(f"No records found for {selected_category} category.")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            
            # User Query Section - NEW ADDITION
            show_user_query_section()
            
            st.divider()
            
            # User Query Section
            show_user_query_section()
            
            st.divider()
            
            # Database Overview Section - ADD THIS
            show_database_overview_section()

            
        else:
            st.warning("Unable to process the fetched data.")
    else:
        st.info("No records found. This could be because:")
        st.markdown("""
        - You haven't uploaded any records yet
        - There's a connectivity issue
        - Your session has expired
        """)

# Main application flow
def main():
    """Main application entry point"""
    try:
        # Initialize session state
        initialize_session_state()
        
        # Route to appropriate page based on authentication status
        if not st.session_state.get("authenticated", False):
            show_login_page()
        else:
            show_dashboard()
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error("An unexpected error occurred. Please refresh the page and try again.")
        
        # Clear session state on critical error
        if st.button("Reset Application"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
