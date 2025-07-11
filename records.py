
# Enhanced Data Fetching Functions
import streamlit as st
from asyncio.log import logger
import time
from typing import Dict,List, Optional
import requests



def fetch_records_with_cache(
    user_id: str, token: str, use_cache: bool = True
) -> List[Dict]:
    """Fetch records with caching mechanism"""
    cache_key = f"records_{user_id}"

    if use_cache and cache_key in st.session_state:
        cached_data = st.session_state[cache_key]
        if time.time() - cached_data["timestamp"] < 300:  # 5 minutes cache
            return cached_data["data"]

    records = fetch_records(user_id, token)
    if records:
        st.session_state[cache_key] = {"data": records, "timestamp": time.time()}

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
        st.error(
            "🌐 Unable to connect to the server. Please check your internet connection."
        )
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

        status_text.text(f"� Searching for user {query_user_id[:8]}...")
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
    """Enhanced function to fetch ALL records with proper pagination"""
    if not token:
        st.error("Token is required")
        return []
    
    all_records = []
    skip = 0
    limit = 1000  # Keep reasonable batch size
    page = 1
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while True:
            url = f"https://backend2.swecha.org/api/v1/records/?skip={skip}&limit={limit}"
            
            # Update progress
            status_text.text(f"🔄 Loading records... Page {page} ({len(all_records)} records loaded)")
            
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                st.warning("⚠️ Unexpected data format received")
                break
            
            # If no data returned, we've reached the end
            if not data:
                logger.info(f"No more records found at page {page}")
                break
            
            # Add records to our collection
            all_records.extend(data)
            logger.info(f"Fetched {len(data)} records from page {page}, total: {len(all_records)}")
            
            # If we got less than the limit, we've reached the end
            if len(data) < limit:
                logger.info(f"Reached end of records at page {page}")
                break
            
            # Prepare for next iteration
            skip += limit
            page += 1
            
            # Update progress (estimate based on current data)
            if len(all_records) > 0:
                progress_percentage = min(0.95, (len(all_records) / (len(all_records) + 100)) * 100)
                progress_bar.progress(progress_percentage / 100)
            
            # Safety check to prevent infinite loops
            if page > 100:  # Reasonable limit
                logger.warning(f"Stopped at page {page} to prevent infinite loop")
                st.warning(f"⚠️ Stopped loading at page {page}. Contact admin if you need more records.")
                break
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text(f"✅ Completed! Loaded {len(all_records)} records from {page} pages")
        
        # Clear progress indicators after a brief delay
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        if all_records:
            st.success(f"✅ Successfully loaded {len(all_records)} total records!")
            logger.info(f"Total records fetched: {len(all_records)}")
        else:
            st.warning("No records found")
            
        return all_records
        
    except Exception as e:
        st.error(f"❌ Database fetch failed: {e}")
        logger.error(f"Error fetching all records: {e}")
        return []


def fetch_user_contributions(user_id: str, token: str) -> Optional[Dict]:
    """Fetch enhanced user contributions using the new API endpoint"""
    if not user_id or not token:
        st.error("User ID and token are required")
        return None
    
    url = f"https://backend2.swecha.org/api/v1/users/{user_id}/contributions"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
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
            return None
        else:
            st.error(f"❌ Failed to fetch contributions: HTTP {e.response.status_code}")
            return None
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        logger.error(f"Unexpected error fetching contributions: {e}")
        st.error(f"❌ Unexpected error: {e}")
        return None



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
        f"https://backend2.swecha.org/api/v1/users/{user_id}/contributions/{media_type}"
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
