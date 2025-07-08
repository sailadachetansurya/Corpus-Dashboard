import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob
import time
import requests
import logging
from typing import Dict, List, Optional

# Set up logging
logger = logging.getLogger(__name__)

def load_college_files(folder_path="data"):
    college_files = glob.glob(os.path.join(folder_path, "*.csv"))
    college_dfs = []
    for file in college_files:
        college_name = os.path.basename(file).replace(".csv", "").replace("_", " ")
        try:
            df = pd.read_csv(file)
            df["college"] = college_name
            college_dfs.append(df)
        except Exception as e:
            st.error(f"Failed to read {file}: {e}")
    if not college_dfs:
        return pd.DataFrame()
    return pd.concat(college_dfs, ignore_index=True)

def fetch_user_contributions_silent(user_id: str, token: str) -> Optional[Dict]:
    """Fetch user contributions without UI elements for batch processing"""
    if not user_id or not token:
        return None
    
    url = f"https://backend2.swecha.org/api/v1/users/{user_id}/contributions"
    headers = {
        "Authorization": f"Bearer {token}", 
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Debug: Log the actual response structure
        logger.info(f"API Response for user {user_id}: {data}")
        
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # User has no contributions
            return {"total_contributions": 0}
        else:
            logger.error(f"HTTP error fetching contributions for user {user_id}: {e.response.status_code}")
            return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching contributions for user {user_id}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching contributions for user {user_id}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching contributions for user {user_id}: {e}")
        return None

def fetch_user_contributions(user_id: str, token: str) -> Optional[Dict]:
    """Fetch enhanced user contributions using the new API endpoint (with UI for single user)"""
    if not user_id or not token:
        st.error("User ID and token are required")
        return None
    
    url = f"https://backend2.swecha.org/api/v1/users/{user_id}/contributions"
    headers = {
        "Authorization": f"Bearer {token}", 
        "Accept": "application/json",
        # "Content-Type": "application/json"
    }
    
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("🔄 Fetching user contributions...")
        progress_bar.progress(30)
        
        response = requests.get(url, headers=headers, timeout=30)
        progress_bar.progress(70)
        status_text.text("📊 Processing contributions data...")
        
        response.raise_for_status()
        data = response.json()
        
        progress_bar.progress(100)
        status_text.text("✅ Contributions loaded!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        return data
        
    except requests.exceptions.HTTPError as e:
        progress_bar.empty()
        status_text.empty()
        if e.response.status_code == 404:
            st.warning(f"No contributions found for user {user_id}")
            return {"total_contributions": 0}
        elif e.response.status_code == 500:
            st.warning("⚠️ Server error - using fallback method")
            return None
        else:
            st.error(f"❌ API Error: {e.response.status_code}")
            return None
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        logger.error(f"Unexpected error fetching contributions: {e}")
        st.error(f"❌ Unexpected error: {e}")
        return None

def safe_fetch_user_contributions(user_id, token, max_retries=3):
    """
    Safely fetch user contributions with retry logic and silent error handling
    """
    for attempt in range(max_retries):
        try:
            # Add a small delay between requests to avoid overwhelming the server
            if attempt > 0:
                time.sleep(0.5)
            
            user_data = fetch_user_contributions_silent(user_id, token)
            
            if user_data:
                if isinstance(user_data, dict):
                    # Check for total_contributions field first
                    if "total_contributions" in user_data:
                        return user_data["total_contributions"]
                    # If not found, try to calculate from contributions_by_media_type
                    elif "contributions_by_media_type" in user_data:
                        contributions_by_type = user_data["contributions_by_media_type"]
                        if isinstance(contributions_by_type, dict):
                            total = sum(contributions_by_type.values())
                            return total
                    # If neither found, try to count individual contribution arrays
                    else:
                        total = 0
                        for key in ["audio_contributions", "video_contributions", "text_contributions", "image_contributions"]:
                            if key in user_data and isinstance(user_data[key], list):
                                total += len(user_data[key])
                        return total
                else:
                    return 0
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error in safe_fetch_user_contributions for user {user_id}: {e}")
            if attempt == max_retries - 1:
                return 0
    
    return 0

def clean_phone_number(phone):
    """
    Clean and normalize phone numbers - handles both columns with and without trailing spaces
    """
    if pd.isna(phone) or phone == 'nan' or str(phone).strip() == '':
        return None
    
    # Convert to string and clean
    phone_str = str(phone).strip()
    
    # Remove common prefixes and formatting
    phone_clean = phone_str.replace("+91", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    
    # Remove leading zeros
    phone_clean = phone_clean.lstrip("0")
    
    # Check if it's a valid Indian mobile number (10 digits)
    if phone_clean.isdigit() and len(phone_clean) == 10:
        return phone_clean
    
    return None

def get_phone_from_row(row):
    """
    Extract phone number from row, handling multiple phone columns
    """
    # Check all possible phone column variations
    phone_columns = ["Phone Number", "Phone Number ", "phone", "Phone", "mobile", "Mobile", "contact", "Contact"]
    
    for col in phone_columns:
        if col in row.index:
            phone = row[col]
            if pd.notna(phone) and str(phone).strip():  # Check if phone is not null and not empty
                cleaned = clean_phone_number(phone)
                if cleaned:
                    return cleaned, str(phone).strip()  # Return both cleaned and original
    
    return None, None

def display_college_overview(fetch_all_users, fetch_user_contributions_param, token: str):
    st.title("🏫 College Overview Dashboard")

    if not token:
        st.warning("🔐 You must be logged in to access this section.")
        return

    # Load CSV data
    df_all_college = load_college_files("data")
    if df_all_college.empty:
        st.warning("⚠️ No CSVs found in the /data folder.")
        return

    # Load users from API (cache to avoid multiple calls)
    if 'cached_users' not in st.session_state:
        with st.spinner("Loading user data..."):
            all_users = fetch_all_users(token)
            st.session_state.cached_users = all_users
    else:
        all_users = st.session_state.cached_users
        
    if not all_users:
        st.error("❌ Failed to fetch users from backend.")
        return

    # Normalize phone numbers
    user_phone_map = {}
    
    for user in all_users:
        raw_phone = user.get("phone", "")
        if raw_phone:
            cleaned_phone = clean_phone_number(raw_phone)
            if cleaned_phone:
                user_phone_map[cleaned_phone] = {
                    "user_id": user.get("id"),
                    "name": user.get("name", "Unknown User"),
                    "original_phone": raw_phone
                }

    # Build mapping with improved phone matching
    college_contributors = []
    matched_count = 0
    unmatched_count = 0
    
    for _, row in df_all_college.iterrows():
        cleaned_phone, original_phone = get_phone_from_row(row)
        college = row.get("college", "Unknown College")
        name = row.get("FirstName", row.get("Name", row.get("Student Name", "Unknown")))
        
        if cleaned_phone and cleaned_phone in user_phone_map:
            user_data = user_phone_map[cleaned_phone]
            college_contributors.append({
                "user_id": user_data["user_id"],
                "name": user_data["name"],
                "phone": original_phone,
                "cleaned_phone": cleaned_phone,
                "college": college,
                "registered": True
            })
            matched_count += 1
        else:
            college_contributors.append({
                "user_id": None,
                "name": name,
                "phone": original_phone,
                "cleaned_phone": cleaned_phone,
                "college": college,
                "registered": False
            })
            unmatched_count += 1

    # College-wise registration status
    df_temp = pd.DataFrame(college_contributors)
    college_stats = df_temp.groupby('college').agg({
        'registered': ['count', 'sum']
    }).round(2)
    college_stats.columns = ['total_students', 'registered_students']
    college_stats['unregistered_students'] = college_stats['total_students'] - college_stats['registered_students']
    college_stats = college_stats.reset_index()
    
    # Display registration overview
    st.markdown("### 📊 Registration Overview")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Students", len(df_all_college))
    with col2:
        st.metric("Registered", matched_count)
    with col3:
        st.metric("Unregistered", unmatched_count)
    with col4:
        registration_rate = (matched_count / len(df_all_college) * 100) if len(df_all_college) > 0 else 0
        st.metric("Registration Rate", f"{registration_rate:.1f}%")
    
    # College-wise breakdown
    st.markdown("#### College-wise Registration Status")
    st.dataframe(college_stats, use_container_width=True)

    if not college_contributors:
        st.warning("⚠️ No contributors found in CSV data.")
        return

    # Add option to limit API calls for testing
    with st.expander("⚙️ API Settings"):
        test_mode = st.checkbox("Enable test mode (limit API calls)", value=False)
        if test_mode:
            max_api_calls = st.slider("Max API calls to test", 1, 100, 10)
        else:
            max_api_calls = len([c for c in college_contributors if c["registered"]])
        
        # Debug mode for API responses
        debug_mode = st.checkbox("Debug API responses (show first response)", value=False)
        
        st.info(f"Will process {min(max_api_calls, len([c for c in college_contributors if c['registered']]))} registered users")

    # Fetch contributions with improved error handling
    st.markdown("### 🔄 Fetching Contribution Data")
    
    data = []
    progress = st.progress(0)
    status_text = st.empty()
    
    api_calls_made = 0
    successful_calls = 0
    users_with_contributions = 0
    failed_calls = 0
    debug_shown = False
    
    registered_users = [c for c in college_contributors if c["registered"]]
    
    for i, contributor in enumerate(college_contributors):
        if contributor["registered"] and api_calls_made < max_api_calls:
            user_id = contributor["user_id"]
            status_text.text(f"Processing {contributor['name']} ({api_calls_made + 1}/{min(max_api_calls, len(registered_users))})...")
            
            # Use the safe fetch function with silent API calls
            try:
                total = safe_fetch_user_contributions(user_id, token)
                
                # Debug: Show first API response if debug mode is enabled
                if debug_mode and not debug_shown:
                    raw_response = fetch_user_contributions_silent(user_id, token)
                    st.write("**Debug - First API call response:**")
                    st.write(f"User ID: {user_id}")
                    st.write(f"Parsed contributions: {total}")
                    st.write("Raw API response:")
                    st.json(raw_response)
                    debug_shown = True
                
                if total > 0:
                    users_with_contributions += 1
                    successful_calls += 1
                else:
                    successful_calls += 1  # Still successful even if 0 contributions
                    
            except Exception as e:
                logger.error(f"Error fetching contributions for {contributor['name']}: {e}")
                total = 0
                failed_calls += 1
            
            api_calls_made += 1
                
        else:
            total = 0  # Skip API call for unregistered users or if limit reached

        data.append({**contributor, "contributions": total})
        progress.progress((i + 1) / len(college_contributors))

    progress.empty()
    status_text.empty()
    
    # Show API summary
    if api_calls_made > 0:
        st.success(f"✅ API Processing Complete: {api_calls_made} calls made, {successful_calls} successful, {users_with_contributions} users have contributions")
        
        if users_with_contributions == 0:
            st.warning("⚠️ No users found with contributions. Check the debug output above to see the API response structure.")
        else:
            st.info(f"📊 Found {users_with_contributions} active contributors out of {api_calls_made} registered users")

    df = pd.DataFrame(data)

    # Show summary statistics
    st.markdown("### 📈 Contribution Summary")
    registered_users_count = len(df[df['registered']])
    users_with_contribs = len(df[df['contributions'] > 0])
    total_contributions = df['contributions'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Registered Users", registered_users_count)
    with col2:
        st.metric("Active Contributors", users_with_contribs)
    with col3:
        st.metric("Total Contributions", total_contributions)

    # DOWNLOAD SECTION - College-wise Downloads
    st.markdown("### 📥 Download CSV Files")
    
    # Create tabs for each college
    colleges = df["college"].unique()
    
    # Overall downloads first
    st.markdown("#### 📊 Overall Downloads")
    col1, col2 = st.columns(2)
    
    with col1:
        # All registered users
        registered_download_df = df[df["registered"]][["name", "college", "contributions", "phone", "cleaned_phone"]]
        if len(registered_download_df) > 0:
            registered_csv = registered_download_df.to_csv(index=False)
            st.download_button(
                f"⬇️ Download Total Registered Users ({len(registered_download_df)} users)",
                registered_csv,
                "all_registered_users.csv",
                "text/csv",
                key="all_registered_download"
            )
        else:
            st.write("No registered users to download")
    
    with col2:
        # All unmatched users
        unmatched_download_df = df[not df["registered"]][["name", "college", "phone", "cleaned_phone"]]
        if len(unmatched_download_df) > 0:
            unmatched_csv = unmatched_download_df.to_csv(index=False)
            st.download_button(
                f"⬇️ Download Total Unregistered Users ({len(unmatched_download_df)} users)",
                unmatched_csv,
                "all_unmatched_users.csv",
                "text/csv",
                key="all_unmatched_download"
            )
        else:
            st.write("No unmatched users to download")
    
    # College-wise downloads
    st.markdown("#### 🏫 College-wise Downloads")
    
    # Create tabs for each college
    if len(colleges) > 1:
        tabs = st.tabs([f"{college} ({len(df[df['college'] == college])})" for college in colleges])
        
        for i, college in enumerate(colleges):
            with tabs[i]:
                college_df = df[df["college"] == college]
                
                # Statistics for this college
                registered_count = len(college_df[college_df["registered"]])
                unregistered_count = len(college_df[not college_df["registered"]])
                total_contributions = college_df["contributions"].sum()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Students", len(college_df))
                with col2:
                    st.metric("Registered", registered_count)
                with col3:
                    st.metric("Unregistered", unregistered_count)
                
                # Download buttons for this college
                col1, col2 = st.columns(2)
                
                with col1:
                    # Registered users for this college
                    college_registered = college_df[college_df["registered"]][["name", "contributions", "phone", "cleaned_phone"]]
                    if len(college_registered) > 0:
                        college_reg_csv = college_registered.to_csv(index=False)
                        st.download_button(
                            f"⬇️ Registered Users ({len(college_registered)})",
                            college_reg_csv,
                            f"{college.replace(' ', '_')}_registered.csv",
                            "text/csv",
                            key=f"{college}_registered_download"
                        )
                    else:
                        st.write("No registered users")
                
                with col2:
                    # Unregistered users for this college
                    college_unregistered = college_df[not college_df["registered"]][["name", "phone", "cleaned_phone"]]
                    if len(college_unregistered) > 0:
                        college_unreg_csv = college_unregistered.to_csv(index=False)
                        st.download_button(
                            f"⬇️ Unregistered Users ({len(college_unregistered)})",
                            college_unreg_csv,
                            f"{college.replace(' ', '_')}_unregistered.csv",
                            "text/csv",
                            key=f"{college}_unregistered_download"
                        )
                    else:
                        st.write("No unregistered users")
                
                # Show preview of data
                if len(college_df) > 0:
                    st.markdown("**Preview:**")
                    st.dataframe(college_df[["name", "phone", "contributions", "registered"]], use_container_width=True)
    else:
        # Single college case
        college = colleges[0]
        college_df = df[df["college"] == college]
        
        col1, col2 = st.columns(2)
        with col1:
            college_registered = college_df[college_df["registered"]][["name", "contributions", "phone", "cleaned_phone"]]
            if len(college_registered) > 0:
                college_reg_csv = college_registered.to_csv(index=False)
                st.download_button(
                    f"⬇️ {college} - Registered Users ({len(college_registered)})",
                    college_reg_csv,
                    f"{college.replace(' ', '_')}_registered.csv",
                    "text/csv",
                    key=f"{college}_registered_download"
                )
        
        with col2:
            college_unregistered = college_df[not college_df["registered"]][["name", "phone", "cleaned_phone"]]
            if len(college_unregistered) > 0:
                college_unreg_csv = college_unregistered.to_csv(index=False)
                st.download_button(
                    f"⬇️ {college} - Unregistered Users ({len(college_unregistered)})",
                    college_unreg_csv,
                    f"{college.replace(' ', '_')}_unregistered.csv",
                    "text/csv",
                    key=f"{college}_unregistered_download"
                )

    # Only show charts if we have data
    if total_contributions > 0:
        # College summary (only registered users)
        registered_df = df[df["registered"]]
        college_summary = registered_df.groupby("college").agg({
            "contributions": ["sum", "count", "mean"]
        }).reset_index()
        
        # Flatten column names
        college_summary.columns = ["college", "total_contributions", "user_count", "avg_contributions"]
        college_summary = college_summary.sort_values(by="total_contributions", ascending=False)
        college_summary["percentage"] = (college_summary["total_contributions"] / college_summary["total_contributions"].sum()) * 100
        college_summary["avg_contributions"] = college_summary["avg_contributions"].round(2)

        st.markdown("### 📊 College Contributions Analysis")
        st.dataframe(college_summary, use_container_width=True)

        # Enhanced visualizations
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(college_summary, 
                        names="college", 
                        values="total_contributions", 
                        title="College Contribution Share",
                        hover_data=["user_count", "avg_contributions"])
            st.plotly_chart(fig, use_container_width=True)
                
        with col2:
            fig = px.bar(college_summary, 
                        x="college", 
                        y="total_contributions", 
                        title="Total Contributions by College",
                        text="total_contributions",
                        hover_data=["user_count", "avg_contributions"])
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        # Additional chart for user counts
        st.markdown("### 👥 User Distribution by College")
        fig = px.bar(college_summary, 
                    x="college", 
                    y="user_count", 
                    title="Number of Active Users by College",
                    text="user_count")
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # Enhanced leaderboards
    st.markdown("### 🏆 Individual Contributor Leaderboard")
    if len(df) > 0:
        # Top contributors overall
        top_contributors = df[df["contributions"] > 0].sort_values(by="contributions", ascending=False)
        if len(top_contributors) > 0:
            st.markdown("#### Top 20 Contributors")
            st.dataframe(top_contributors.head(20)[["name", "college", "contributions", "phone"]], use_container_width=True)
            
            # College-wise leaderboards
            st.markdown("#### College-wise Top Contributors")
            for college in df["college"].unique():
                college_df = df[(df["college"] == college) & (df["contributions"] > 0)]
                if len(college_df) > 0:
                    with st.expander(f"🏫 {college} Top Contributors"):
                        college_top = college_df.sort_values(by="contributions", ascending=False).head(10)
                        st.dataframe(college_top[["name", "contributions", "phone"]], use_container_width=True)
        else:
            st.info("No users with contributions found")
    
    # Enhanced unregistered section
    st.markdown("### 🚫 Unregistered Students")
    unregistered_df = df[not df["registered"]]
    if len(unregistered_df) > 0:
        # Group by college for better organization
        for college in unregistered_df["college"].unique():
            college_unreg = unregistered_df[unregistered_df["college"] == college]
            with st.expander(f"🏫 {college} - {len(college_unreg)} unregistered students"):
                st.dataframe(college_unreg[["name", "phone", "cleaned_phone"]], use_container_width=True)
    else:
        st.success("🎉 All students are registered!")

    # Final summary
    st.markdown("### 📋 Dashboard Summary")
    summary_data = {
        "Metric": [
            "Total Students in CSV",
            "Registered Users",
            "Unregistered Users",
            "Users with Contributions",
            "Total Contributions",
            "Average Contributions per User"
        ],
        "Value": [
            len(df),
            len(df[df["registered"]]),
            len(df[not df["registered"]]),
            len(df[df["contributions"] > 0]),
            df["contributions"].sum(),
            round(df[df["contributions"] > 0]["contributions"].mean(), 2) if len(df[df["contributions"] > 0]) > 0 else 0
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True)

def fetch_user_contributions_by_media_type(
    user_id: str, media_type: str, token: str
) -> List[Dict]:
    """Fetch user contributions by media type from the API"""
    if not user_id or not token or not media_type:
        st.error("User ID, media type, and token are required")
        return []

    # Validate media type
    valid_media_types = ["text", "audio", "image", "video"]
    if media_type not in valid_media_types:
        st.error(f"Invalid media type. Must be one of: {', '.join(valid_media_types)}")
        return []

    url = (
        f"https://backend2.swecha.org/api/v1/users/{user_id}/contributions/"
    )
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    try:
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text(f"🔄 Fetching your {media_type} contributions...")
        progress_bar.progress(30)

        response = requests.get(url, headers=headers, timeout=30)
        progress_bar.progress(70)
        status_text.text(f"📊 Processing {media_type} contributions...")

        response.raise_for_status()
        data = response.json()

        progress_bar.progress(100)
        status_text.text(f"✅ {media_type.title()} contributions loaded!")
        time.sleep(0.5)

        progress_bar.empty()
        status_text.empty()

        if not isinstance(data, list):
            logger.warning(f"Expected list, got {type(data)}")
            st.warning("⚠️ Unexpected data format received from server")
            return []

        logger.info(f"Successfully fetched {len(data)} {media_type} contributions")
        return data

    except requests.exceptions.Timeout:
        progress_bar.empty()
        status_text.empty()
        st.error(f"⏱️ Request timed out. Please try again.")
        return []
    except requests.exceptions.ConnectionError:
        progress_bar.empty()
        status_text.empty()
        st.error(
            "🌐 Unable to connect to the server. Please check your internet connection."
        )
        return []
    except requests.exceptions.HTTPError as e:
        progress_bar.empty()
        status_text.empty()
        if e.response.status_code == 401:
            st.error("🔐 Authentication failed. Please log in again.")
            st.session_state.authenticated = False
        elif e.response.status_code == 404:
            st.warning(f"No {media_type} contributions found for this user.")
            return []
        else:
            st.error(
                f"❌ Failed to fetch {media_type} contributions: HTTP {e.response.status_code}"
            )
        return []
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        logger.error(f"Unexpected error fetching {media_type} contributions: {e}")
        st.error(f"❌ Unexpected error: {e}")
        return []