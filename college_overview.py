import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import plotly.express as px
import os, glob
import time
import requests
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional
import json

# Set up logging
logger = logging.getLogger(__name__)

# Keep all existing helper functions unchanged
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
        
        # Fixed debug logging - now shows actual API response
        logger.info(f"API Response for user {user_id}: {data}")
        
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"No contributions found for user {user_id}")
            return {"total_contributions": 0}
        else:
            logger.error(f"HTTP error fetching contributions for user {user_id}: {e.response.status_code} - {e.response.text}")
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

def clean_phone_number(phone):
    """Clean and normalize phone numbers"""
    if pd.isna(phone) or phone == 'nan' or str(phone).strip() == '':
        return None
    
    phone_str = str(phone).strip()
    phone_clean = phone_str.replace("+91", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    phone_clean = phone_clean.lstrip("0")
    
    if phone_clean.isdigit() and len(phone_clean) == 10:
        return phone_clean
    
    return None

def get_phone_from_row(row):
    """Extract phone number from row, handling multiple phone columns"""
    phone_columns = ["Phone Number", "Phone Number ", "phone", "Phone", "mobile", "Mobile", "contact", "Contact"]
    
    for col in phone_columns:
        if col in row.index:
            phone = row[col]
            if pd.notna(phone) and str(phone).strip():
                cleaned = clean_phone_number(phone)
                if cleaned:
                    return cleaned, str(phone).strip()
    
    return None, None

def fetch_detailed_contributions(user_id: str, token: str) -> Dict:
    """Fetch detailed contributions by media type"""
    try:
        raw_response = fetch_user_contributions_silent(user_id, token)
        
        if raw_response is None:
            return {
                "total_contributions": 0,
                "image": 0,
                "video": 0,
                "audio": 0,
                "text": 0
            }
        
        # Handle different API response structures
        if isinstance(raw_response, dict):
            # Method 1: Check for total_contributions field
            if "total_contributions" in raw_response:
                total = raw_response["total_contributions"]
            # Method 2: Calculate from contributions_by_media_type
            elif "contributions_by_media_type" in raw_response:
                contributions_by_type = raw_response["contributions_by_media_type"]
                if isinstance(contributions_by_type, dict):
                    total = sum(contributions_by_type.values())
                    return {
                        "total_contributions": total,
                        "image": contributions_by_type.get("image", 0),
                        "video": contributions_by_type.get("video", 0),
                        "audio": contributions_by_type.get("audio", 0),
                        "text": contributions_by_type.get("text", 0)
                    }
            
            # Method 3: Count individual contribution arrays
            image_count = len(raw_response.get("image_contributions", []))
            video_count = len(raw_response.get("video_contributions", []))
            audio_count = len(raw_response.get("audio_contributions", []))
            text_count = len(raw_response.get("text_contributions", []))
            
            total = image_count + video_count + audio_count + text_count
            
            return {
                "total_contributions": total,
                "image": image_count,
                "video": video_count,
                "audio": audio_count,
                "text": text_count
            }
        
        return {
            "total_contributions": 0,
            "image": 0,
            "video": 0,
            "audio": 0,
            "text": 0
        }
        
    except Exception as e:
        logger.error(f"Error fetching detailed contributions for user {user_id}: {e}")
        return {
            "total_contributions": 0,
            "image": 0,
            "video": 0,
            "audio": 0,
            "text": 0
        }
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
        
        # Updated column mappings for new CSV format
        college = row.get("Affiliation (College/Company/Organization Name)", 
                         row.get("college", "Unknown College"))
        name = row.get("Full Name", "Unknown")
        email = row.get("Email Address", "")
        created_at = row.get("CreatedAt", "")
        
        if cleaned_phone and cleaned_phone in user_phone_map:
            user_data = user_phone_map[cleaned_phone]
            college_contributors.append({
                "user_id": user_data["user_id"],
                "name": user_data["name"],
                "phone": original_phone,
                "cleaned_phone": cleaned_phone,
                "college": college,
                "email": email,
                "created_at": created_at,
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
                "email": email,
                "created_at": created_at,
                "registered": False
            })
            unmatched_count += 1

    # Create initial dataframe
    df = pd.DataFrame(college_contributors)

    # Display OVERALL registration overview (always shown)
    st.markdown("### 📊 Overall Registration Overview")
    
    # Summary metrics for ALL colleges
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

    # College selection dropdown
    st.markdown("### 🏫 College Selection")
    colleges = df["college"].unique()
    college_options = ["All Colleges"] + list(colleges)
    selected_college = st.selectbox(
        "Select a college to view detailed statistics:",
        college_options,
        index=0
    )

    # Filter data based on selection
    if selected_college != "All Colleges":
        filtered_df = df[df["college"] == selected_college]
        
        # Show detailed college-wise breakdown ONLY for selected college
        st.markdown(f"### 📊 Detailed Analysis for {selected_college}")
        
        # College-specific metrics
        college_total = len(filtered_df)
        college_registered = len(filtered_df[filtered_df["registered"] == True])
        college_unregistered = len(filtered_df[filtered_df["registered"] == False])
        college_reg_rate = (college_registered / college_total * 100) if college_total > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Students", college_total)
        with col2:
            st.metric("Registered", college_registered)
        with col3:
            st.metric("Unregistered", college_unregistered)
        with col4:
            st.metric("Registration Rate", f"{college_reg_rate:.1f}%")
        
    else:
        filtered_df = df
        # Show high-level summary for all colleges
        st.markdown("### 📊 College-wise Summary")
        
        # College-wise registration status (summary table only)
        df_temp = pd.DataFrame(college_contributors)
        college_stats = df_temp.groupby('college').agg({
            'registered': ['count', 'sum']
        }).round(2)
        college_stats.columns = ['total_students', 'registered_students']
        college_stats['unregistered_students'] = college_stats['total_students'] - college_stats['registered_students']
        college_stats['registration_rate'] = (college_stats['registered_students'] / college_stats['total_students'] * 100).round(1)
        college_stats = college_stats.reset_index()
        
        st.dataframe(college_stats, use_container_width=True)
        st.info("💡 Select a specific college from the dropdown above to view detailed analysis and fetch contribution data.")

    # API Settings and Button Control - ONLY show for specific college selection
    if selected_college != "All Colleges":
        st.markdown("### ⚙️ API Settings")
        col1, col2 = st.columns(2)
        
        with col1:
            test_mode = st.checkbox("Enable test mode (limit API calls)", value=False)
            if test_mode:
                max_api_calls = st.slider("Max API calls to test", 1, 100, 10)
            else:
                max_api_calls = len(filtered_df[filtered_df["registered"] == True])
        
        with col2:
            debug_mode = st.checkbox("Debug API responses", value=False)

        # Button to fetch contributions
        fetch_button = st.button("🔄 Fetch User Contributions", type="primary")
        
        if fetch_button:
            st.session_state["contributions_fetched"] = False
            st.session_state["contributions_data"] = None

        # Only fetch contributions when button is pressed AND specific college is selected
        if fetch_button or st.session_state.get("contributions_fetched", False):
            st.markdown("### 🔄 Fetching Contribution Data")
            
            contributions_data = []
            progress = st.progress(0)
            status_text = st.empty()
            
            registered_users = filtered_df[filtered_df["registered"] == True]
            api_calls_made = 0
            successful_calls = 0
            debug_shown = False
            
            # Process registered users
            for i, (idx, user) in enumerate(registered_users.iterrows()):
                if api_calls_made < max_api_calls:
                    user_id = user["user_id"]
                    status_text.text(f"Processing {user['name']} ({api_calls_made + 1}/{min(max_api_calls, len(registered_users))})...")
                    
                    try:
                        contrib_details = fetch_detailed_contributions(user_id, token)
                        
                        # Debug: Show first API response if debug mode is enabled
                        if debug_mode and not debug_shown:
                            raw_response = fetch_user_contributions_silent(user_id, token)
                            st.write("**Debug - First API call response:**")
                            st.write(f"User ID: {user_id}")
                            st.write(f"Parsed contributions: {contrib_details}")
                            st.write("Raw API response:")
                            st.json(raw_response)
                            debug_shown = True
                        
                        contributions_data.append({
                            "Name": user["name"],
                            "Total Contributions": contrib_details["total_contributions"],
                            "Image": contrib_details["image"],
                            "Video": contrib_details["video"],
                            "Audio": contrib_details["audio"],
                            "Text": contrib_details["text"],
                            "Registration Status": "Y",
                            "College": user["college"],
                            "Phone": user["phone"],
                            "Email": user["email"],
                            "Created At": user["created_at"]
                        })
                        
                        successful_calls += 1
                        
                    except Exception as e:
                        logger.error(f"Error fetching contributions for {user['name']}: {e}")
                        contributions_data.append({
                            "Name": user["name"],
                            "Total Contributions": 0,
                            "Image": 0,
                            "Video": 0,
                            "Audio": 0,
                            "Text": 0,
                            "Registration Status": "Y",
                            "College": user["college"],
                            "Phone": user["phone"],
                            "Email": user["email"],
                            "Created At": user["created_at"]
                        })
                    
                    api_calls_made += 1
                    progress.progress((api_calls_made) / min(max_api_calls, len(registered_users)))
            
            # Add unregistered users
            unregistered_users = filtered_df[filtered_df["registered"] == False]
            for idx, user in unregistered_users.iterrows():
                contributions_data.append({
                    "Name": user["name"],
                    "Total Contributions": 0,
                    "Image": 0,
                    "Video": 0,
                    "Audio": 0,
                    "Text": 0,
                    "Registration Status": "N",
                    "College": user["college"],
                    "Phone": user["phone"],
                    "Email": user["email"],
                    "Created At": user["created_at"]
                })
            
            progress.empty()
            status_text.empty()
            
            # Store in session state
            contributions_df = pd.DataFrame(contributions_data)
            st.session_state["contributions_data"] = contributions_df
            st.session_state["contributions_fetched"] = True
            
            st.success(f"✅ API Processing Complete: {api_calls_made} calls made, {successful_calls} successful")

        # Display data if available - ONLY for specific college
        if st.session_state.get("contributions_data") is not None:
            contributions_df = st.session_state["contributions_data"]
            
            # Calculate metrics for selected college
            total_users = len(contributions_df)
            registered_users_count = len(contributions_df[contributions_df["Registration Status"] == "Y"])
            unregistered_users_count = len(contributions_df[contributions_df["Registration Status"] == "N"])
            zero_records_count = len(contributions_df[contributions_df["Total Contributions"] == 0])
            activity_rate = ((total_users - zero_records_count) / total_users * 100) if total_users > 0 else 0

            # Display metrics above AG Grid
            st.markdown("### 📊 Contribution Metrics")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Total Users", total_users)
            with col2:
                st.metric("Registered Users", registered_users_count)
            with col3:
                st.metric("Unregistered Users", unregistered_users_count)
            with col4:
                st.metric("Users with Zero Records", zero_records_count)
            with col5:
                st.metric("Activity Rate", f"{activity_rate:.1f}%")

            # AG Grid Implementation
            st.markdown("### 📋 Student Data Grid")
            
            # Configure AG Grid
            gb = GridOptionsBuilder.from_dataframe(contributions_df)
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_side_bar()
            gb.configure_default_column(
                sortable=True, 
                filter=True, 
                resizable=True,
                minWidth=100
            )
            
            # Configure specific columns
            gb.configure_column("Name", pinned="left", width=200)
            gb.configure_column("Total Contributions", type=["numericColumn"], width=150)
            gb.configure_column("Image", type=["numericColumn"], width=100)
            gb.configure_column("Video", type=["numericColumn"], width=100)
            gb.configure_column("Audio", type=["numericColumn"], width=100)
            gb.configure_column("Text", type=["numericColumn"], width=100)
            gb.configure_column("Registration Status", width=150)
            gb.configure_column("Email", width=200)
            gb.configure_column("Created At", width=150)
            
            # Enable selection
            gb.configure_selection(selection_mode="multiple", use_checkbox=True)
            
            # Build grid options
            grid_options = gb.build()

            # Display AG Grid
            grid_response = AgGrid(
                contributions_df,
                gridOptions=grid_options,
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                update_mode=GridUpdateMode.MODEL_CHANGED,
                fit_columns_on_grid_load=False,
                theme="streamlit",
                height=600,
                width='100%',
                reload_data=False
            )

            # Export options
            st.markdown("### 📥 Export Data")
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = contributions_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download as CSV",
                    data=csv_data,
                    file_name=f"{selected_college.replace(' ', '_')}_student_data.csv",
                    mime="text/csv"
                )
            
            with col2:
                json_data = contributions_df.to_json(orient="records", indent=2)
                st.download_button(
                    label="📋 Download as JSON",
                    data=json_data,
                    file_name=f"{selected_college.replace(' ', '_')}_student_data.json",
                    mime="application/json"
                )

            # Display selected rows info
            if grid_response['selected_rows'] is not None and len(grid_response['selected_rows']) > 0:
                st.markdown("### 🎯 Selected Users")
                selected_df = pd.DataFrame(grid_response['selected_rows'])
                st.dataframe(selected_df, use_container_width=True)

        else:
            st.info("👆 Press the 'Fetch User Contributions' button to load contribution data and display the AG Grid.")

    if not college_contributors:
        st.warning("⚠️ No contributors found in CSV data.")
        return



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
    phone_columns = ["Phone Number", "Phone Number ", "phone", "Phone", "mobile", "Mobile", "contact", "Contact","Contact Number", "contact_number"]
    
    for col in phone_columns:
        if col in row.index:
            phone = row[col]
            if pd.notna(phone) and str(phone).strip():  # Check if phone is not null and not empty
                cleaned = clean_phone_number(phone)
                if cleaned:
                    return cleaned, str(phone).strip()  # Return both cleaned and original
    
    return None, None


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
