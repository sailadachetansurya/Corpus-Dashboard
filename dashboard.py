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

# Set page config
st.set_page_config(
    page_title="GitLab Records Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

user_id = "2bcc18a7-03a4-40ea-ae9b-223607f239df"  # Example
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTA1OTcyNjEsInN1YiI6IjJiY2MxOGE3LTAzYTQtNDBlYS1hZTliLTIyMzYwN2YyMzlkZiJ9.rB-kyrL1UQ1Yz8ZsPzIVhW9ao4ORM4AhDJtZZH-6Dn0"


def fetch_records(user_id, token):
    url = f"https://backend2.swecha.org/api/v1/records/?user_id={user_id}&skip=0&limit=1000"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch records: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return []



def summarize(records):
    if not records or not isinstance(records, list):
        st.warning("No valid records data to process")
        return None
    
    try:
        df = pd.DataFrame(records)
        
        # Check if required columns exist
        required_columns = ['category_id', 'created_at', 'media_type', 'status']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns: {missing_columns}")
            return None
            
        # Map category_id to category name using CATEGORIES
        category_id_to_name = {v: k for k, v in CATEGORIES.items()}
        df["category"] = df["category_id"].map(category_id_to_name).fillna("Unknown")
        df["created_at"] = pd.to_datetime(df["created_at"], errors='coerce').dt.date
        
        # Remove rows with invalid dates
        df = df.dropna(subset=['created_at'])
        
        if df.empty:
            st.warning("No valid data after processing")
            return None
    
    
    
        media_type_counts = df["media_type"].value_counts()
        status_counts = df["status"].value_counts()
        category_counts = df["category"].value_counts()
        uploads_per_day = df.groupby("created_at").size()

        return {
            "media_type": media_type_counts,
            "status": status_counts,
            "category": category_counts,
            "uploads_per_day": uploads_per_day,
            "df": df,  # Return full DataFrame for later use
        }
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return None


def plot_summary(summary):
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))

    # Media type distribution
    summary["media_type"].plot(kind="bar", color="skyblue", ax=axs[0, 0])
    axs[0, 0].set_title("Uploads by Media Type")
    axs[0, 0].set_ylabel("Count")

    # Upload status
    summary["status"].plot(kind="pie", autopct="%1.1f%%", startangle=140, ax=axs[0, 1])
    axs[0, 1].set_title("Upload Status Distribution")
    axs[0, 1].set_ylabel("")

    # Category distribution
    summary["category"].head(5).plot(kind="bar", color="coral", ax=axs[1, 0])
    axs[1, 0].set_title("Top 5 Categories")
    axs[1, 0].set_ylabel("Count")

    # Uploads over time
    summary["uploads_per_day"].plot(kind="line", marker="o", ax=axs[1, 1])
    axs[1, 1].set_title("Uploads Over Time")
    axs[1, 1].set_ylabel("Count")
    axs[1, 1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    st.pyplot(fig)


st.markdown(
    """<link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400&display=swap" rel="stylesheet">
<style>
    /* Remove left padding/margin from the sidebar */
    .css-1d391kg {
        padding-left: 0 !important;
        margin-left: 0 !important;
        width: 280px !important;  /* Adjust width if needed */
    }
    /* Adjust main content margin if needed */
    .css-1v3fvcr {
        padding-left: 280px !important;  /* Match sidebar width */
    }
</style>
""",
    unsafe_allow_html=True,
)

# Custom CSS
st.markdown(
    """
<style>
    .main {
        padding-top: 2rem;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .st-emotion-cache-16txtl3 h1 {
        font-weight: 700;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid rgba(49, 51, 63, 0.2);
    }
    .dashboard-header {
        margin-bottom: 2rem;
    }
    .dashboard-metric {
        padding: 1rem;
        border-radius: 5px;
        background-color: #f0f2f6;
        text-align: center;
    }
    
    .dashboard-metric h3 {
        margin-bottom: 0.2rem;
        font-size: 1rem;
    }
    .dashboard-metric p {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }
    .sidebar-header {
        text-align: center;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(49, 51, 63, 0.2);
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state if not exists
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "username" not in st.session_state:
    st.session_state["username"] = None

if "token" not in st.session_state:
    st.session_state["token"] = None

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

# Update session state init
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

# Login page updated


# New: Authentication via phone and password
def login_user(phone: str, password: str) -> Optional[Dict]:
    try:
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
        else:
            st.error(f"Login failed with status {e.response.status_code}")
        return None
    except Exception as e:
        st.error(f"Unexpected error during login: {e}")
        return None



def show_login_page():
    st.title("Corpus Records Dashboard - Login")
    with st.form("login_form"):
        phone = st.text_input("Phone")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            login_result = login_user(phone, password)
            if login_result:
                token = login_result.get("access_token")
                if token:
                    # decode user_id from token
                    try:
                    # decode user_id from token
                        payload = token.split(".")[1] + "=="
                        import base64
                        import json
                        payload_decoded = json.loads(base64.b64decode(payload).decode("utf-8"))
                        user_id = payload_decoded.get("sub")
                        if not user_id:
                            st.error("Invalid token: user ID not found")
                            return
                        st.session_state["user_id"] = user_id
                    except (IndexError, json.JSONDecodeError, base64.binascii.Error) as e:
                        st.error(f"Failed to decode token: {e}")
                        return

                    st.session_state["user_id"] = payload_decoded.get("sub")
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = phone
                    st.session_state["token"] = token
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Token not found in response")
            else:
                st.error("Invalid credentials")


# Main Dashboard Page
def show_dashboard():
    """Display the main dashboard after authentication."""
    # Sidebar with user info
    with st.sidebar:
        st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
        st.image(
            "https://about.gitlab.com/images/press/logo/png/gitlab-icon-rgb.png",
            width=80,
        )
        st.markdown(f"### Welcome, {st.session_state['username']}")
        # User ID input at the top
    st.markdown('<div class="user-id-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("**User ID:**")
    with col2:
        user_id_input = st.text_input("", value=user_id, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    # Fetch and display data
    if user_id_input:
        with st.spinner("Fetching records..."):
            records = fetch_records(user_id_input, token)
        if (records == None) :
            st.warning("No records found for the specified user ID.")
    else:
        st.info("Please enter a User ID to fetch records.")
        
    st.markdown("</div>", unsafe_allow_html=True)

    # Add spacer
    st.divider()

    # User ID input
    # user_id = st.text_input("User ID", placeholder="Enter User ID")

    # Category selection
    selected_category = st.selectbox(
        "Select Category",
        options=list(CATEGORIES.keys()),
        format_func=lambda x: f"{x}: {CATEGORIES[x]}",
    )

    # Add spacer
    st.divider()

    # Logout button
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.session_state["token"] = None
        st.rerun()

    # Main area - Dashboard header
    st.title("Corpus Records Dashboard")
    st.markdown('<div class="dashboard-header">', unsafe_allow_html=True)

    records = fetch_records(user_id, token)
    if not records:
        st.warning("No records found for this user ID.")
        return
    with st.expander("🔍 Raw Record Dump"):
        st.json(records)
    summary = summarize(records)
    plot_summary(summary)

    # Generate dummy data
    with st.spinner("Loading data..."):
        df = summary["df"]

    # Raw data view
    with st.expander("🔍 Raw Record Dump"):
        st.json(records)

    # Metrics
    total_count = len(df)
    audio_count = len(df[df["media_type"] == "audio"])
    video_count = len(df[df["media_type"] == "video"])
    text_count = len(df[df["media_type"] == "text"])
    image_count = len(df[df["media_type"] == "image"])

    st.metric("🎯 Total Records", total_count)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📸 Image Records", image_count)
    col2.metric("👂 Audio Records", audio_count)
    col3.metric("📽️ Video Records", video_count)
    col4.metric("🗨️ Text Records", text_count)

    # Pie chart of category distribution
    category_totals = df["category"].value_counts().reset_index()
    category_totals.columns = ["category", "count"]
    top_category = category_totals.iloc[0]

    col1, col2 = st.columns([3, 1])
    with col1:
        fig_pie = px.pie(
            category_totals,
            values="count",
            names="category",
            title="Distribution of Records by Category",
            template="plotly_dark",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown("### Category Insights")
        st.markdown(f"**Total records:** {total_count}")
        st.markdown(f"**Top category:** {top_category['category']}")
        st.markdown(f"**Record count:** {top_category['count']}")
        st.markdown(f"**Percentage:** {top_category['count'] / total_count:.1%}")

    # Bar chart by media type
    media_counts = df["media_type"].value_counts().reset_index()
    media_counts.columns = ["media_type", "count"]  # Rename columns explicitly

    fig_bar = px.bar(
        media_counts,
        x="media_type",
        y="count",
        labels={"media_type": "Media Type", "count": "Count"},
        title="Count of Records by Media Type",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Stacked bar chart: type distribution by category
    df_grouped = df.groupby(["category", "media_type"]).size().reset_index(name="count")
    fig_stacked = px.bar(
        df_grouped,
        x="category",
        y="count",
        color="media_type",
        title="Distribution of Record Types by Category",
        barmode="stack",
    )
    st.plotly_chart(fig_stacked, use_container_width=True)

    # Raw Data Table
    with st.expander("🗃️ View Raw DataFrame"):
        st.dataframe(df, use_container_width=True)

    st.header("Category Filter")
    records = fetch_records(user_id_input, token)
    df = pd.DataFrame(records)
    df["category"] = (
        df["category_id"].map({v: k for k, v in CATEGORIES.items()}).fillna("Unknown")
    )
    selected_category = st.selectbox(
        "Select a Category", options=df["category"].unique()
    )

    filtered_df = df[df["category"] == selected_category]
    pie_data = filtered_df["media_type"].value_counts().reset_index()
    pie_data.columns = ["media_type", "count"]

    st.subheader(f"Media Type Distribution for '{selected_category}'")
    fig_category_pie = px.pie(pie_data, values="count", names="media_type")
    st.plotly_chart(fig_category_pie, use_container_width=True)

    # Add footer
    st.divider()
    st.markdown(
        "<p style='text-align: center; color: gray;'>© 2025 GitLab Records Dashboard</p>",
        unsafe_allow_html=True,
    )


# Main app flow
def main():
    if not st.session_state["authenticated"]:
        show_login_page()
    else:
        show_dashboard()


if __name__ == "__main__":
    main()
