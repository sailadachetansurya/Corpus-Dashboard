

import streamlit as st
from streamlit_js_eval import streamlit_js_eval as js
import hashlib
import secrets
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import base64
import json
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_session_token():
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hash token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def save_auth_to_browser(user_id: str, token: str, username: str):
    """Save authentication data to browser localStorage with error handling"""
    try:
        session_token = generate_session_token()
        
        st.write("🔍 DEBUG: Attempting to save auth to browser...")
        
        # Test if we can write to localStorage first
        test_result = js(
            js_expressions="try { localStorage.setItem('test', 'test'); localStorage.removeItem('test'); return 'success'; } catch(e) { return 'failed: ' + e.message; }", 
            want_output=True,
            key="test_localStorage_write"
        )
        st.write(f"🔍 DEBUG: localStorage write test: {test_result}")
        
        if test_result != "success":
            st.error(f"❌ localStorage not available: {test_result}")
            return None
        
        # Save the actual data
        save_result = js(
            js_expressions=f"""
                try {{
                    localStorage.setItem('auth_user_id', '{user_id}');
                    localStorage.setItem('auth_token', '{token}');
                    localStorage.setItem('auth_username', '{username}');
                    localStorage.setItem('auth_session_token', '{session_token}');
                    localStorage.setItem('auth_timestamp', '{int(time.time())}');
                    return 'saved_successfully';
                }} catch(e) {{
                    return 'save_failed: ' + e.message;
                }}
            """, 
            want_output=True,
            key="save_auth_data"
        )
        
        st.write(f"🔍 DEBUG: Save result: {save_result}")
        
        if save_result == "saved_successfully":
            st.success("✅ Auth data saved to browser storage!")
            
            # Verify the save worked
            verification = js(
                js_expressions="localStorage.getItem('auth_user_id')", 
                want_output=True,
                key="verify_save"
            )
            st.write(f"🔍 DEBUG: Verification - saved user_id: {verification}")
            
            return session_token
        else:
            st.error(f"❌ Failed to save auth data: {save_result}")
            return None
            
    except Exception as e:
        st.error(f"❌ Error in save_auth_to_browser: {e}")
        return None



def load_auth_from_browser():
    """Load authentication data from browser localStorage with debugging"""
    st.write("🔍 DEBUG: Attempting to load auth from browser...")
    
    try:
        # Add a small delay to ensure DOM is ready
        time.sleep(0.5)
        
        # Test if localStorage is accessible
        test_result = js(
            js_expressions="typeof(Storage) !== 'undefined' ? 'available' : 'not_available'", 
            want_output=True, 
            key="test_storage"
        )
        st.write(f"🔍 DEBUG: localStorage availability: {test_result}")
        
        user_id = js(
            js_expressions="localStorage.getItem('auth_user_id')", 
            want_output=True, 
            key="get_user_id"
        )
        st.write(f"🔍 DEBUG: Retrieved user_id: {user_id}")
        
        if user_id and user_id != "null" and user_id != None:
            token = js(
                js_expressions="localStorage.getItem('auth_token')", 
                want_output=True, 
                key="get_token"
            )
            username = js(
                js_expressions="localStorage.getItem('auth_username')", 
                want_output=True, 
                key="get_username"
            )
            timestamp = js(
                js_expressions="localStorage.getItem('auth_timestamp')", 
                want_output=True, 
                key="get_timestamp"
            )
            
            st.write(f"🔍 DEBUG: Retrieved values - token: {token is not None}, username: {username}, timestamp: {timestamp}")
            
            if all([token, username, timestamp]):
                # Check if session is still valid (24 hours)
                current_time = int(time.time())
                stored_time = int(timestamp)
                time_diff = current_time - stored_time
                
                st.write(f"🔍 DEBUG: Time difference: {time_diff} seconds")
                
                if time_diff < 86400:  # 24 hours
                    st.write("✅ DEBUG: Valid session found in browser storage!")
                    return {
                        'user_id': user_id,
                        'token': token,
                        'username': username,
                        'timestamp': timestamp
                    }
                else:
                    st.write("❌ DEBUG: Session expired")
            else:
                st.write("❌ DEBUG: Missing required auth data")
        else:
            st.write("❌ DEBUG: No user_id found in localStorage")
            
    except Exception as e:
        st.write(f"❌ DEBUG: Error loading auth from browser: {e}")
    
    st.write("❌ DEBUG: No valid session found in browser storage")
    time.sleep(2500)
    return None


def clear_auth_from_browser():
    """Clear authentication data from browser"""
    js("""
        localStorage.removeItem('auth_user_id');
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_username');
        localStorage.removeItem('auth_session_token');
        localStorage.removeItem('auth_timestamp');
    """,
    key="clear_auth"
    )
    

# Enhanced page config
st.set_page_config(
    page_title="Advanced Corpus Records Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://docs.streamlit.io",
        "Report a bug": None,
        "About": "Advanced Corpus Records Dashboard v2.0",
    },
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
            "animation_speed": "normal",
        },
        "browser_auth_checked": False,
    }

    for var, default_value in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default_value

    # Check browser storage for existing authentication on first load
    if not st.session_state.browser_auth_checked:
        st.session_state.browser_auth_checked = True
        
        # Try to load authentication from browser
        browser_auth = load_auth_from_browser()
        if browser_auth:
            # Validate the token is still valid
            token_data = decode_jwt_token(browser_auth['token'])
            if token_data and token_data.get('expires_at', 0) > time.time():
                # Restore authentication state
                st.session_state.authenticated = True
                st.session_state.user_id = browser_auth['user_id']
                st.session_state.token = browser_auth['token']
                st.session_state.username = browser_auth['username']
                st.success("✅ Session restored from browser storage!")
            else:
                # Token expired, clear browser storage
                clear_auth_from_browser()


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
            "issued_at": payload_decoded.get("iat"),
        }

    except Exception as e:
        logger.error(f"Failed to decode token: {e}")
        return None

def check_token_renewal():
    """Check if token needs renewal and handle it"""
    token = st.session_state.get("token")
    if not token:
        return
    
    token_data = decode_jwt_token(token)
    if token_data:
        expires_at = token_data.get("expires_at", 0)
        current_time = time.time()
        
        # Renew if token expires in less than 5 minutes
        if expires_at - current_time < 300:
            st.warning("Session expiring soon. Please save your work.")

def validate_session():
    """Validate current session and token"""
    if not st.session_state.get("authenticated", False):
        return False
    
    token = st.session_state.get("token")
    if not token:
        logout_user()
        return False
    
    # Validate token expiration
    token_data = decode_jwt_token(token)
    if not token_data:
        logout_user()
        return False
    
    expires_at = token_data.get("expires_at")
    if expires_at and time.time() > expires_at:
        st.error("Session expired. Please log in again.")
        logout_user()
        return False
    
    return True

def validate_session_with_refresh():
    """Validate session and refresh token if needed"""
    if not st.session_state.get("authenticated", False):
        return False
    
    token = st.session_state.get("token")
    if not token:
        logout_user()
        return False
    
    # Validate token expiration
    token_data = decode_jwt_token(token)
    if not token_data:
        logout_user()
        return False
    
    expires_at = token_data.get("expires_at", 0)
    current_time = time.time()
    
    # If token expires in less than 1 hour, try to refresh it
    if expires_at - current_time < 3600:  # 1 hour
        st.warning("🔄 Refreshing your session...")
        # Here you could implement token refresh logic if your API supports it
        
    if expires_at <= current_time:
        st.error("Session expired. Please log in again.")
        logout_user()
        return False
    
    return True


def logout_user():
    """Properly cleanup session state and browser storage"""
    # Clear browser storage
    clear_auth_from_browser()
    
    # Clear session state
    session_keys_to_clear = [
        "authenticated", "username", "token", "user_id",
        "query_results", "database_overview", "users_list",
        "user_mapping", "export_triggered", "export_type", 
        "export_format_selected", "browser_auth_checked"
    ]
    
    for key in session_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.session_state.authenticated = False
    st.session_state.browser_auth_checked = False  # Reset this flag
    st.success("✅ Logged out successfully!")
    st.rerun()



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
            timeout=30,
        )        

        progress_bar.progress(75)
        status_text.text("✅ Authentication successful!")
        progress_bar.progress(100)
        time.sleep(0.5)  # Brief pause for UX

        progress_bar.empty()
        status_text.empty()

        response.raise_for_status()
        login_result = response.json()

        if login_result and "access_token" in login_result:
            token_info = decode_jwt_token(login_result["access_token"])

            if token_info:
                # Set session state
                st.session_state.authenticated = True
                st.session_state.token = login_result["access_token"]
                st.session_state.user_id = token_info["user_id"]
                st.session_state.username = phone
                st.session_state.login_attempts = 0

                # Save to browser storage for persistence
                save_auth_to_browser(
                    token_info["user_id"], 
                    login_result["access_token"], 
                    phone
                )

                return login_result


    except requests.exceptions.HTTPError as e:
        progress_bar.empty()
        status_text.empty()

        if e.response.status_code == 401:
            st.error("❌ Invalid phone number or password.")
            st.session_state.login_attempts += 1
            if st.session_state.login_attempts >= 3:
                st.error(
                    "🚫 Too many failed attempts. Please wait before trying again."
                )
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
            json={"phone_number": phone},
            headers={"accept": "application/json", "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"❌ Failed to request OTP: {e}")
        return False


def verify_otp(phone: str, otp: str) -> Optional[Dict]:
    """Verify OTP and get token"""
    try:
        response = requests.post(
            "https://backend2.swecha.org/api/v1/auth/verify-otp",
            json={"phone_number": phone, "otp_code": otp,"has_given_consent": True},
            headers={"accept": "application/json", "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"❌ OTP verification failed: {e}")
        return None


# Enhanced Data Fetching Functions
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


def fetch_user_contributions(user_id: str, token: str) -> List[Dict]:
    """Fetch user contributions from the API"""
    if not user_id or not token:
        st.error("User ID and token are required")
        return []

    url = f"https://backend2.swecha.org/api/v1/users/{user_id}/contributions"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    try:
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("🔄 Fetching your contributions...")
        progress_bar.progress(30)

        response = requests.get(url, headers=headers, timeout=30)
        progress_bar.progress(70)
        status_text.text("📊 Processing contributions...")

        response.raise_for_status()
        data = response.json()

        progress_bar.progress(100)
        status_text.text("✅ Contributions loaded!")
        time.sleep(0.5)

        progress_bar.empty()
        status_text.empty()

        if not isinstance(data, list):
            logger.warning(f"Expected list, got {type(data)}")
            st.warning("⚠️ Unexpected data format received from server")
            return []

        logger.info(f"Successfully fetched {len(data)} contributions")
        return data

    except requests.exceptions.Timeout:
        progress_bar.empty()
        status_text.empty()
        st.error("⏱️ Request timed out. Please try again.")
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
        else:
            st.error(f"❌ Failed to fetch contributions: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        logger.error(f"Unexpected error fetching contributions: {e}")
        st.error(f"❌ Unexpected error: {e}")
        return []


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


def fetch_all_users(token: str) -> List[Dict]:
    """Fetch all users from the API with pagination and progress bar"""
    if not token:
        st.error("Token is required")
        return []

    all_users = []
    skip = 0
    limit = 1000
    page = 1

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    try:
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Estimate total pages (you can adjust this based on your knowledge)
        estimated_total_users = 5000  # Adjust based on your database size
        estimated_pages = (estimated_total_users // limit) + 1

        while True:
            url = f"https://backend2.swecha.org/api/v1/users/?skip={skip}&limit={limit}"

            # Update progress
            progress_percentage = min(
                (page - 1) / max(estimated_pages, 1), 0.95
            )  # Cap at 95% until complete
            progress_bar.progress(progress_percentage)
            status_text.text(
                f"🔄 Loading users... Page {page} ({len(all_users)} users loaded)"
            )

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list):
                logger.warning(f"Expected list, got {type(data)} on page {page}")
                st.warning("Unexpected data format received from server")
                break

            # If no data returned, we've reached the end
            if not data:
                logger.info(f"No more users found at page {page}")
                break

            # Add users to our collection
            all_users.extend(data)
            logger.info(
                f"Fetched {len(data)} users from page {page}, total: {len(all_users)}"
            )

            # If we got less than the limit, we've reached the end
            if len(data) < limit:
                logger.info(f"Reached end of users list at page {page}")
                break

            # Prepare for next iteration
            skip += limit
            page += 1

            # Safety check to prevent infinite loops
            if page > 50:  # Reasonable limit for most databases
                logger.warning(f"Stopped at page {page} to prevent infinite loop")
                st.warning(
                    f"⚠️ Stopped loading at page {page}. Contact admin if you need more users."
                )
                break

        # Complete progress
        progress_bar.progress(1.0)
        status_text.text(
            f"✅ Completed! Loaded {len(all_users)} users from {page} pages"
        )

        # Clear progress indicators after a brief delay
        import time

        time.sleep(1)
        progress_bar.empty()
        status_text.empty()

        if all_users:
            st.success(f"✅ Successfully loaded {len(all_users)} users!")
            logger.info(f"Total users fetched: {len(all_users)}")
        else:
            st.warning("No users found")

        return all_users

    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return []
    except requests.exceptions.ConnectionError:
        st.error(
            "Unable to connect to the server. Please check your internet connection."
        )
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

# Export Changed to here 
def create_export_section(df, summary):
    """Create export section with proper state management"""
    st.subheader("📥 Export Data")
    
    if df is None or df.empty:
        st.warning("No data available for export")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        export_format = st.selectbox(
            "Export Format",
            ["CSV", "JSON", "Excel"],
            key="export_format_select"
        )
    
    # Use session state to track export actions
    if "export_triggered" not in st.session_state:
        st.session_state.export_triggered = False
    
    with col2:
        if st.button("📊 Export Records", key="export_records_btn"):
            st.session_state.export_triggered = True
            st.session_state.export_type = "records"
            st.session_state.export_format_selected = export_format
    
    with col3:
        if st.button("📈 Export Summary", key="export_summary_btn"):
            st.session_state.export_triggered = True
            st.session_state.export_type = "summary"
            st.session_state.export_format_selected = export_format
    
    # Handle export after button press
    if st.session_state.get("export_triggered", False):
        export_type = st.session_state.get("export_type")
        selected_format = st.session_state.get("export_format_selected", "CSV")
        
        if export_type == "records":
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if selected_format == "CSV":
                csv_data = df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name=f"records_{timestamp}.csv",
                    mime="text/csv",
                    key="download_csv_final"
                )
            elif selected_format == "JSON":
                json_data = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_data,
                    file_name=f"records_{timestamp}.json",
                    mime="application/json",
                    key="download_json_final"
                )
            elif selected_format == "Excel":
                from io import BytesIO
                buffer = BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                st.download_button(
                    label="⬇️ Download Excel",
                    data=buffer.getvalue(),
                    file_name=f"records_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_final"
                )
        
        elif export_type == "summary" and summary:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_data = {
                "total_records": summary["total_records"],
                "total_users": summary["total_users"],
                "media_breakdown": dict(summary["media_type"]),
                "category_breakdown": dict(summary["category"]),
                "export_timestamp": datetime.now().isoformat()
            }
            json_data = json.dumps(summary_data, indent=2)
            st.download_button(
                label="⬇️ Download Summary",
                data=json_data,
                file_name=f"summary_{timestamp}.json",
                mime="application/json",
                key="download_summary_final"
            )
        
        # Reset export trigger after handling
        if st.button("✅ Export Complete - Reset", key="reset_export"):
            st.session_state.export_triggered = False
            st.rerun()


def create_user_mapping(users: List[Dict]) -> Dict[str, str]:
    """Create mapping from user ID to user name"""
    try:
        user_mapping = {}
        for user in users:
            user_id = user.get("id", "")
            user_name = user.get("name", "Unknown User")
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
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["date"] = df["created_at"].dt.date
        df["hour"] = df["created_at"].dt.hour
        df["day_of_week"] = df["created_at"].dt.day_name()
        df["month"] = df["created_at"].dt.month_name()
        df["week"] = df["created_at"].dt.isocalendar().week

        # Apply filters if provided
        if filters:
            if filters.get("date_range"):
                start_date, end_date = filters["date_range"]
                df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
            if filters.get("categories"):
                df = df[df["category"].isin(filters["categories"])]
            if filters.get("media_types"):
                df = df[df["media_type"].isin(filters["media_types"])]
            if filters.get("status"):
                df = df[df["status"].isin(filters["status"])]

        if df.empty:
            return None

        # Calculate total users
        total_users = df["user_id"].nunique() if "user_id" in df.columns else 0

        # Enhanced metrics with media type breakdown
        media_counts = df["media_type"].value_counts()

        # Calculate file size statistics
        total_file_size = 0
        file_size_by_media_type = {}
        avg_file_size_by_media_type = {}
        file_size_by_category = {}
        file_size_by_date = {}

        # Check if 'size' column exists in the dataframe
        if "size" in df.columns:
            # Convert size to numeric, handling any non-numeric values
            df["size"] = pd.to_numeric(df["size"], errors="coerce").fillna(0)

            # Calculate total file size
            total_file_size = df["size"].sum()

            # Calculate average file size
            avg_file_size = total_file_size / len(df) if len(df) > 0 else 0

            # Calculate file size by media type
            for media_type in df["media_type"].unique():
                media_df = df[df["media_type"] == media_type]
                media_size = media_df["size"].sum()
                file_size_by_media_type[media_type] = media_size

                # Calculate average file size by media type
                avg_size = media_size / len(media_df) if len(media_df) > 0 else 0
                avg_file_size_by_media_type[media_type] = avg_size

            # Calculate file size by category
            for category in df["category"].unique():
                category_df = df[df["category"] == category]
                category_size = category_df["size"].sum()
                file_size_by_category[category] = category_size

            # Calculate file size by date (for storage growth tracking)
            date_groups = df.groupby("date")
            for date, group in date_groups:
                file_size_by_date[date] = group["size"].sum()

        summary = {
            "total_records": len(df),
            "total_users": total_users,
            "unique_dates": df["date"].nunique(),
            "date_range": (df["date"].min(), df["date"].max()),
            "avg_daily_uploads": len(df) / max(df["date"].nunique(), 1),
            "media_type": media_counts,
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
            # New: Individual media type counts
            "images_count": media_counts.get("image", 0),
            "videos_count": media_counts.get("video", 0),
            "texts_count": media_counts.get("text", 0),
            "audios_count": media_counts.get("audio", 0),
            # File size statistics
            "total_file_size": total_file_size,
            "avg_file_size": avg_file_size if "avg_file_size" in locals() else 0,
            "file_size_by_media_type": file_size_by_media_type,
            "avg_file_size_by_media_type": avg_file_size_by_media_type,
            "file_size_by_category": file_size_by_category,
            "file_size_by_date": file_size_by_date,
            # Storage growth metrics
            "storage_growth_weekly": calculate_storage_growth_rate(
                file_size_by_date, "weekly"
            ),
            "storage_growth_monthly": calculate_storage_growth_rate(
                file_size_by_date, "monthly"
            ),
            "df": df,
        }

        return summary

    except Exception as e:
        logger.error(f"Error in advanced summarization: {e}")
        st.error(f"❌ Data processing error: {e}")
        return None
    
def format_file_size(size_in_bytes: int) -> str:
    """Format file size in a human-readable format"""
    if size_in_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_in_bytes >= 1024 and i < len(size_names) - 1:
        size_in_bytes /= 1024
        i += 1

    # Round to 2 decimal places
    return f"{size_in_bytes:.2f} {size_names[i]}"


def bytes_to_mb(size_in_bytes: int) -> float:
    """Convert bytes to megabytes"""
    if size_in_bytes == 0:
        return 0.0

    # Convert to MB (1 MB = 1024 * 1024 bytes)
    return size_in_bytes / (1024 * 1024)


def calculate_growth_rate(series: pd.Series) -> float:
    """Calculate growth rate for time series data"""
    if len(series) < 2:
        return 0.0

    current = series.iloc[-1]
    previous = series.iloc[-2]

    if previous == 0:
        return 100.0 if current > 0 else 0.0

    return ((current - previous) / previous) * 100


def calculate_storage_growth_rate(
    file_size_by_date: Dict, period: str = "weekly"
) -> float:
    """Calculate storage growth rate over a specified period"""
    if not file_size_by_date or len(file_size_by_date) < 2:
        return 0.0

    # Convert dictionary to Series for easier manipulation
    date_series = pd.Series(file_size_by_date)
    date_series.index = pd.to_datetime(date_series.index)
    date_series = date_series.sort_index()

    if period == "weekly":
        # Group by week and calculate weekly totals
        weekly_data = date_series.resample("W").sum()
        if len(weekly_data) < 2:
            return 0.0

        current = weekly_data.iloc[-1]
        previous = weekly_data.iloc[-2]
    elif period == "monthly":
        # Group by month and calculate monthly totals
        monthly_data = date_series.resample("M").sum()
        if len(monthly_data) < 2:
            return 0.0

        current = monthly_data.iloc[-1]
        previous = monthly_data.iloc[-2]
    else:
        # Default to comparing the latest two dates
        current = date_series.iloc[-1]
        previous = date_series.iloc[-2]

    if previous == 0:
        return 100.0 if current > 0 else 0.0

    return ((current - previous) / previous) * 100


def get_data_insights(summary: Dict) -> List[str]:
    """Generate intelligent insights from data"""
    insights = []
    if not summary:
        return insights

    # Upload pattern insights
    peak_day = summary.get("peak_upload_day")
    if peak_day:
        insights.append(
            f"📈 Peak activity was on {peak_day} with {summary['peak_upload_count']} uploads"
        )

    # Time pattern insights
    most_active_hour = summary.get("most_active_hour")
    if most_active_hour:
        insights.append(f"🕐 Most active hour is {most_active_hour}:00")

    # Category insights
    if not summary["category"].empty:
        top_category = summary["category"].index[0]
        category_percent = (
            summary["category"].iloc[0] / summary["total_records"]
        ) * 100
        insights.append(
            f"📂 {top_category} dominates with {category_percent:.1f}% of all uploads"
        )

    # Growth insights
    weekly_growth = summary.get("weekly_growth", 0)
    if abs(weekly_growth) > 5:
        trend = "increasing" if weekly_growth > 0 else "decreasing"
        insights.append(f"📊 Weekly uploads are {trend} by {abs(weekly_growth):.1f}%")

    # User diversity insights
    total_users = summary.get("total_users", 0)
    if total_users > 0:
        insights.append(f"👥 {total_users} unique users contributed to these records")

    # Diversity insights
    category_diversity = summary.get("category_diversity", 0)
    if category_diversity >= len(CATEGORIES) * 0.8:
        insights.append(
            f"🌈 High category diversity: {category_diversity} different categories used"
        )

    # File size insights
    total_file_size = summary.get("total_file_size", 0)
    if total_file_size > 0:
        insights.append(f"💾 Total storage used: {bytes_to_mb(total_file_size):.2f} MB")

        # Add insight about largest media type by size
        if summary.get("file_size_by_media_type"):
            largest_media_type = max(
                summary["file_size_by_media_type"].items(), key=lambda x: x[1]
            )
            media_type_name = largest_media_type[0]
            media_type_size = largest_media_type[1]
            size_percent = (
                (media_type_size / total_file_size) * 100 if total_file_size > 0 else 0
            )
            insights.append(
                f"📊 {media_type_name.title()} files use {size_percent:.1f}% of total storage"
            )

        # Add insight about storage growth
        storage_growth_weekly = summary.get("storage_growth_weekly", 0)
        if abs(storage_growth_weekly) > 5:
            trend = "increasing" if storage_growth_weekly > 0 else "decreasing"
            insights.append(
                f"💾 Weekly storage usage is {trend} by {abs(storage_growth_weekly):.1f}%"
            )

        # Add insight about category with highest storage usage
        if summary.get("file_size_by_category"):
            largest_category = max(
                summary["file_size_by_category"].items(), key=lambda x: x[1]
            )
            category_name = largest_category[0]
            category_size = largest_category[1]
            size_percent = (
                (category_size / total_file_size) * 100 if total_file_size > 0 else 0
            )
            insights.append(
                f"📁 {category_name} category uses {size_percent:.1f}% of total storage"
            )

        # Add insight about average file size
        avg_file_size = summary.get("avg_file_size", 0)
        if avg_file_size > 0:
            insights.append(
                f"📏 Average file size is {bytes_to_mb(avg_file_size):.2f} MB"
            )

    return insights


def create_leaderboard_with_names(
    df: pd.DataFrame, user_mapping: Dict[str, str]
) -> pd.DataFrame:
    """Create leaderboard showing user names instead of IDs"""
    try:
        # Count contributions per user
        user_contributions = df.groupby("user_id").size().reset_index()
        user_contributions.columns = ["user_id", "contributions"]

        # Map user IDs to names
        user_contributions["user_name"] = user_contributions["user_id"].map(
            user_mapping
        )
        user_contributions["user_name"] = user_contributions["user_name"].fillna(
            "Unknown User"
        )

        # Sort by contributions (descending)
        user_contributions = user_contributions.sort_values(
            "contributions", ascending=False
        )

        # Add rank
        user_contributions["rank"] = range(1, len(user_contributions) + 1)

        # Reorder columns
        user_contributions = user_contributions[
            ["rank", "user_name", "contributions", "user_id"]
        ]

        return user_contributions

    except Exception as e:
        logger.error(f"Error creating leaderboard: {e}")
        st.error(f"Error creating leaderboard: {e}")
        return pd.DataFrame()


def display_media_gallery(df: pd.DataFrame, media_type: str, limit: int = 20):
    """Display gallery of images or videos with titles"""
    try:
        # Filter by media type
        media_df = df[df["media_type"] == media_type].copy()

        if media_df.empty:
            st.info(f"No {media_type}s found in the database.")
            return

        # Sort by creation date (newest first)
        media_df = media_df.sort_values("created_at", ascending=False).head(limit)

        st.subheader(f"📸 Latest {media_type.title()}s ({len(media_df)} shown)")

        # Create columns for gallery display
        cols_per_row = 3
        for i in range(0, len(media_df), cols_per_row):
            cols = st.columns(cols_per_row)

            for j in range(cols_per_row):
                if i + j < len(media_df):
                    row = media_df.iloc[i + j]

                    with cols[j]:
                        # Display media based on type
                        if media_type == "image":
                            # Check for different possible URL fields
                            image_url = None
                            for field in [
                                "file_url",
                                "url",
                                "image_url",
                                "media_url",
                                "thumbnail",
                            ]:
                                if field in row and pd.notna(row[field]):
                                    image_url = row[field]
                                    break

                            if image_url:
                                try:
                                    # Add error handling for image loading
                                    st.markdown(
                                        f"""
                                    <div style="border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 10px;">
                                        <img src="{image_url}" style="width: 100%; border-radius: 10px 10px 0 0;">
                                        <div style="padding: 10px; background: white;">
                                            <p style="margin: 0; font-weight: bold;">{row.get("title", "Untitled")}</p>
                                        </div>
                                    </div>
                                    """,
                                        unsafe_allow_html=True,
                                    )
                                except Exception as e:
                                    st.error(f"Failed to load image: {e}")
                                    st.text(f"Title: {row.get('title', 'Untitled')}")
                            else:
                                # Placeholder for missing image
                                st.markdown(
                                    f"""
                                <div style="border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 10px; background: #f8f9fa; height: 200px; display: flex; align-items: center; justify-content: center;">
                                    <div style="text-align: center;">
                                        <p style="font-size: 2em; margin: 0;">📷</p>
                                        <p style="margin: 0;">{row.get("title", "Untitled")}</p>
                                    </div>
                                </div>
                                """,
                                    unsafe_allow_html=True,
                                )

                        elif media_type == "video":
                            # Check for different possible URL fields
                            video_url = None
                            for field in ["file_url", "url", "video_url", "media_url"]:
                                if field in row and pd.notna(row[field]):
                                    video_url = row[field]
                                    break

                            if video_url:
                                try:
                                    st.video(video_url)
                                    st.caption(row.get("title", "Untitled"))
                                except Exception as e:
                                    st.error(f"Failed to load video: {e}")
                                    st.text(f"Title: {row.get('title', 'Untitled')}")
                            else:
                                # Placeholder for missing video
                                st.markdown(
                                    f"""
                                <div style="border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 10px; background: #f8f9fa; height: 200px; display: flex; align-items: center; justify-content: center;">
                                    <div style="text-align: center;">
                                        <p style="font-size: 2em; margin: 0;">🎥</p>
                                        <p style="margin: 0;">{row.get("title", "Untitled")}</p>
                                    </div>
                                </div>
                                """,
                                    unsafe_allow_html=True,
                                )

                        # Show additional info with better styling
                        st.markdown(
                            f"""
                        <div style="display: flex; justify-content: space-between; padding: 5px 0;">
                            <span style="color: #666;">📅 {row["created_at"].strftime("%Y-%m-%d")}</span>
                            <span style="color: #666;">🏷️ {row.get("category", "Uncategorized")}</span>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

    except Exception as e:
        logger.error(f"Error displaying media gallery: {e}")
        st.error(f"Error displaying {media_type} gallery: {e}")


# Advanced Visualization Functions
def create_advanced_overview_dashboard(
    summary: Dict, user_mapping: Dict[str, str] = None, users_count: int = 0
):
    """Create comprehensive overview dashboard with new metrics"""
    if not summary:
        st.warning("No data available for dashboard")
        return

    # Key metrics row with new additions
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.markdown(
            f"""
        <div style="background: linear-gradient(45deg, #FF6B6B, #4ECDC4); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;">
            <h2 style="margin: 0; font-size: 2em;">📊</h2>
            <h3 style="margin: 0;">{summary["total_records"]:,}</h3>
            <p style="margin: 0;">Total Records</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div style="background: linear-gradient(45deg, #A8E6CF, #88D8A3); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;">
            <h2 style="margin: 0; font-size: 2em;">👥</h2>
            <h3 style="margin: 0;">{users_count:,}</h3>
            <p style="margin: 0;">Total Users</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
        <div style="background: linear-gradient(45deg, #FFD93D, #6BCF7F); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;">
            <h2 style="margin: 0; font-size: 2em;">📷</h2>
            <h3 style="margin: 0;">{summary.get("images_count", 0):,}</h3>
            <p style="margin: 0;">Images</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
        <div style="background: linear-gradient(45deg, #A8A8F0, #8E8EF5); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;">
            <h2 style="margin: 0; font-size: 2em;">🎥</h2>
            <h3 style="margin: 0;">{summary.get("videos_count", 0):,}</h3>
            <p style="margin: 0;">Videos</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
        <div style="background: linear-gradient(45deg, #FF9A9A, #FAD0C4); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;">
            <h2 style="margin: 0; font-size: 2em;">📝</h2>
            <h3 style="margin: 0;">{summary.get("texts_count", 0):,}</h3>
            <p style="margin: 0;">Texts</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col6:
        st.markdown(
            f"""
        <div style="background: linear-gradient(45deg, #C7A2FF, #D4A5FF); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;">
            <h2 style="margin: 0; font-size: 2em;">🎵</h2>
            <h3 style="margin: 0;">{summary.get("audios_count", 0):,}</h3>
            <p style="margin: 0;">Audios</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # File size by media type chart
    if summary.get("file_size_by_media_type"):
        st.markdown("### 📊 Storage Usage by Media Type")

        # Prepare data for the chart
        media_types = list(summary["file_size_by_media_type"].keys())
        sizes = list(summary["file_size_by_media_type"].values())

        # Create a DataFrame for the chart
        size_df = pd.DataFrame(
            {
                "Media Type": media_types,
                "Size (MB)": [
                    size / (1024 * 1024) for size in sizes
                ],  # Convert to MB for better visualization
            }
        )

        # Create the chart
        fig = px.bar(
            size_df,
            x="Media Type",
            y="Size (MB)",
            color="Media Type",
            title="Storage Usage by Media Type (MB)",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )

        fig.update_layout(
            title_font_size=16,
            title_x=0.5,
            height=400,
            xaxis_title="Media Type",
            yaxis_title="Size (MB)",
        )

        st.plotly_chart(fig, use_container_width=True)

        # Display average file size by media type
        if summary.get("avg_file_size_by_media_type"):
            st.markdown("### 📏 Average File Size by Media Type")

            # Create columns for each media type
            cols = st.columns(len(summary["avg_file_size_by_media_type"]))

            # Display average file size for each media type
            for i, (media_type, avg_size) in enumerate(
                summary["avg_file_size_by_media_type"].items()
            ):
                with cols[i]:
                    icon = (
                        "📷"
                        if media_type == "image"
                        else "🎥"
                        if media_type == "video"
                        else "🎵"
                        if media_type == "audio"
                        else "📝"
                    )
                    st.markdown(
                        f"""
                    <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px;">
                        <h2 style="margin: 0; font-size: 1.5em;">{icon}</h2>
                        <h3 style="margin: 0;">{bytes_to_mb(avg_size):.2f} MB</h3>
                        <p style="margin: 0;">Avg {media_type.title()} Size</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

    # Leaderboard Section
    st.markdown("---")
    st.markdown("## 🏆 Top Contributors Leaderboard")

    if user_mapping and summary.get("df") is not None:
        leaderboard = create_leaderboard_with_names(summary["df"], user_mapping)

        if not leaderboard.empty:
            # Display top 10 contributors
            top_contributors = leaderboard.head(10)

            # Create a more visual leaderboard
            col1, col2 = st.columns([2, 1])

            with col1:
                st.dataframe(
                    top_contributors[["rank", "user_name", "contributions"]],
                    column_config={
                        "rank": st.column_config.NumberColumn("Rank", width="small"),
                        "user_name": st.column_config.TextColumn(
                            "User Name", width="medium"
                        ),
                        "contributions": st.column_config.NumberColumn(
                            "Contributions", width="small"
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

            with col2:
                # Top 3 podium style display
                if len(top_contributors) >= 3:
                    st.markdown("### 🥇 Top 3")
                    for i, row in top_contributors.head(3).iterrows():
                        medal = ["🥇", "🥈", "🥉"][row["rank"] - 1]
                        st.markdown(f"**{medal} {row['user_name']}**")
                        st.markdown(f"*{row['contributions']} contributions*")
                        st.markdown("---")
    else:
        st.info(
            "User names not available. Please load users data to see names in leaderboard."
        )

    # Charts Row
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Media Type Distribution")
        if not summary["media_type"].empty:
            fig = px.pie(
                values=summary["media_type"].values,
                names=summary["media_type"].index,
                title="Media Types",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(
                title_font_size=16, title_x=0.5, showlegend=True, height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No media type data available")

    with col2:
        st.markdown("### 📈 Category Distribution")
        if not summary["category"].empty:
            fig = px.bar(
                x=summary["category"].head(10).values,
                y=summary["category"].head(10).index,
                orientation="h",
                title="Top 10 Categories",
                color=summary["category"].head(10).values,
                color_continuous_scale="viridis",
            )
            fig.update_layout(
                title_font_size=16,
                title_x=0.5,
                height=400,
                xaxis_title="Number of Records",
                yaxis_title="Category",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category data available")

    # Timeline Analysis
    st.markdown("---")
    st.markdown("### 📅 Upload Timeline")

    if not summary["uploads_per_day"].empty:
        timeline_df = summary["uploads_per_day"].reset_index()
        timeline_df.columns = ["date", "uploads"]

        fig = px.line(
            timeline_df,
            x="date",
            y="uploads",
            title="Daily Upload Activity",
            markers=True,
        )
        fig.update_layout(
            title_font_size=16,
            title_x=0.5,
            height=400,
            xaxis_title="Date",
            yaxis_title="Number of Uploads",
        )
        fig.update_traces(line_color="#FF6B6B", line_width=3, marker_size=6)
        st.plotly_chart(fig, use_container_width=True)

    # Activity Heatmap
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🕐 Hourly Activity Pattern")
        if not summary["uploads_per_hour"].empty:
            fig = px.bar(
                x=summary["uploads_per_hour"].index,
                y=summary["uploads_per_hour"].values,
                title="Uploads by Hour of Day",
                color=summary["uploads_per_hour"].values,
                color_continuous_scale="blues",
            )
            fig.update_layout(
                title_font_size=16,
                title_x=0.5,
                height=400,
                xaxis_title="Hour of Day",
                yaxis_title="Number of Uploads",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📅 Weekly Activity Pattern")
        if not summary["uploads_per_weekday"].empty:
            # Reorder days for better visualization
            day_order = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            weekday_data = summary["uploads_per_weekday"].reindex(
                day_order, fill_value=0
            )

            fig = px.bar(
                x=weekday_data.index,
                y=weekday_data.values,
                title="Uploads by Day of Week",
                color=weekday_data.values,
                color_continuous_scale="greens",
            )
            fig.update_layout(
                title_font_size=16,
                title_x=0.5,
                height=400,
                xaxis_title="Day of Week",
                yaxis_title="Number of Uploads",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Data Insights
    st.markdown("---")
    st.markdown("### 🔍 Key Insights")
    insights = get_data_insights(summary)

    if insights:
        cols = st.columns(2)
        for i, insight in enumerate(insights):
            with cols[i % 2]:
                st.markdown(
                    f"""
                <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; margin: 5px 0; border-left: 4px solid #FF6B6B;">
                    <p style="margin: 0; color: #333;">{insight}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No specific insights available for this dataset")

    # Media Gallery Section for Database Overview
    if summary.get("df") is not None:
        st.markdown("---")
        st.markdown("## 🖼️ Media Gallery")

        # Create tabs for different media types
        tabs = st.tabs(["📷 Images", "🎥 Videos"])

        with tabs[0]:
            if summary.get("images_count", 0) > 0:
                display_media_gallery(summary["df"], "image", limit=12)
            else:
                st.info("No images found in the database.")

        with tabs[1]:
            if summary.get("videos_count", 0) > 0:
                display_media_gallery(summary["df"], "video", limit=12)
            else:
                st.info("No videos found in the database.")


def create_user_analytics_dashboard(user_records: List[Dict], username: str):
    """Create personalized user analytics dashboard"""
    if not user_records:
        st.warning(f"No records found for user: {username}")
        return

    summary = advanced_summarize(user_records)
    if not summary:
        st.error("Failed to process user data")
        return

    st.markdown(f"## 👤 Personal Analytics for {username}")

    # Personal metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📊 Total Records", summary["total_records"])
    with col2:
        st.metric("📅 Active Days", summary["unique_dates"])
    with col3:
        st.metric("📈 Daily Average", f"{summary['avg_daily_uploads']:.1f}")
    with col4:
        growth = summary.get("weekly_growth", 0)
        st.metric("📊 Weekly Growth", f"{growth:+.1f}%")

    # File size statistics
    if summary.get("total_file_size", 0) > 0:
        st.markdown("### 💾 Your Storage Usage")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f"""
            <div style="background: linear-gradient(45deg, #6A82FB, #FC5C7D); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;">
                <h2 style="margin: 0; font-size: 2em;">💾</h2>
                <h3 style="margin: 0;">{bytes_to_mb(summary.get("total_file_size", 0)):.2f} MB</h3>
                <p style="margin: 0;">Total Storage Used</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
            <div style="background: linear-gradient(45deg, #36D1DC, #5B86E5); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;">
                <h2 style="margin: 0; font-size: 2em;">📊</h2>
                <h3 style="margin: 0;">{bytes_to_mb(summary.get("avg_file_size", 0)):.2f} MB</h3>
                <p style="margin: 0;">Average File Size</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # File size by media type chart
        if summary.get("file_size_by_media_type"):
            # Prepare data for the chart
            media_types = list(summary["file_size_by_media_type"].keys())
            sizes = list(summary["file_size_by_media_type"].values())

            # Create a DataFrame for the chart
            size_df = pd.DataFrame(
                {
                    "Media Type": media_types,
                    "Size (MB)": [
                        size / (1024 * 1024) for size in sizes
                    ],  # Convert to MB for better visualization
                }
            )

            # Create the chart
            fig = px.bar(
                size_df,
                x="Media Type",
                y="Size (MB)",
                color="Media Type",
                title="Your Storage Usage by Media Type (MB)",
                color_discrete_sequence=px.colors.qualitative.Bold,
            )

            fig.update_layout(
                title_font_size=16,
                title_x=0.5,
                height=400,
                xaxis_title="Media Type",
                yaxis_title="Size (MB)",
            )

            st.plotly_chart(fig, use_container_width=True)

    # Personal charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎯 Your Categories")
        if not summary["category"].empty:
            fig = px.pie(
                values=summary["category"].values,
                names=summary["category"].index,
                title="Your Upload Categories",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📱 Your Media Types")
        if not summary["media_type"].empty:
            fig = px.bar(
                x=summary["media_type"].values,
                y=summary["media_type"].index,
                orientation="h",
                title="Your Media Distribution",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Personal timeline
    st.markdown("### 📅 Your Upload Timeline")
    if not summary["uploads_per_day"].empty:
        timeline_df = summary["uploads_per_day"].reset_index()
        timeline_df.columns = ["date", "uploads"]

        fig = px.line(
            timeline_df,
            x="date",
            y="uploads",
            title="Your Daily Activity",
            markers=True,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Display insights
    if summary.get("total_file_size", 0) > 0:
        st.markdown("### 🔍 Storage Insights")

        # Create insights specific to file size
        insights = []

        # Add insight about total storage
        insights.append(
            f"💾 You've used {bytes_to_mb(summary.get('total_file_size', 0)):.2f} MB of storage space"
        )

        # Add insight about largest media type
        if summary.get("file_size_by_media_type"):
            largest_media_type = max(
                summary["file_size_by_media_type"].items(), key=lambda x: x[1]
            )
            media_type_name = largest_media_type[0]
            media_type_size = largest_media_type[1]
            size_percent = (media_type_size / summary.get("total_file_size", 1)) * 100
            insights.append(
                f"📊 Your {media_type_name.title()} files use {size_percent:.1f}% of your total storage"
            )

        # Add insight about average file size
        if summary.get("avg_file_size", 0) > 0:
            insights.append(
                f"📏 Your average file size is {bytes_to_mb(summary.get('avg_file_size', 0)):.2f} MB"
            )

        # Display insights
        for insight in insights:
            st.markdown(
                f"""
            <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; margin: 5px 0; border-left: 4px solid #FF6B6B;">
                <p style="margin: 0; color: #333;">{insight}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )


# Main Application Logic
def main():
    """Enhanced main application with all new features"""
    initialize_session_state()
        # Add this debug info to see what's happening
    if st.sidebar.button("🔍 Debug Session"):
        st.sidebar.write("Session State Keys:", list(st.session_state.keys()))
        st.sidebar.write("Authenticated:", st.session_state.get("authenticated", False))
        st.sidebar.write("Browser Auth Checked:", st.session_state.get("browser_auth_checked", False))
    
    if st.session_state.get("authenticated", False):
        if not validate_session_with_refresh():
            return 

    # Enhanced CSS for better UI
    st.markdown(
        """
    <style>
        /* Main header styling */
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        /* Card styling */
        .metric-card {
            background: white;
            padding: 1.2rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            text-align: center;
            margin: 0.7rem 0;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid #f0f2f6;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 7px 20px rgba(0,0,0,0.1);
        }
        
        /* Sidebar styling */
        .sidebar-info {
            background: #f8f9fa;
            padding: 1.2rem;
            border-radius: 12px;
            margin: 1rem 0;
            border-left: 4px solid #667eea;
        }
        
        /* Button styling */
        .stButton>button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        /* Dataframe styling */
        .dataframe {
            border-radius: 10px;
            overflow: hidden;
            border: none;
        }
        
        /* Chart container styling */
        .chart-container {
            background: white;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            margin: 1rem 0;
        }
        
        /* Section headers */
        h2, h3 {
            color: #333;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
        }
        
        /* Insights styling */
        .insight-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin: 8px 0;
            border-left: 4px solid #667eea;
            transition: transform 0.2s ease;
        }
        .insight-card:hover {
            transform: translateX(5px);
        }
        
        /* Form styling */
        .stForm {
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            color: gray !important;
        }
        
        /* Input fields */
        .stTextInput>div>div>input, .stSelectbox>div>div>div {
            border-radius: 8px;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Header with improved logout button placement
    if st.session_state.authenticated:
        st.markdown(
            """
        <div class="main-header">
            <h1>🚀 Advanced Corpus Records Dashboard</h1>
            <p style="margin: 0; font-size: 1.2em;">Deep insights into your corpus data with AI-powered analytics</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            """
        <div class="main-header">
            <h1>🚀 Advanced Corpus Records Dashboard</h1>
            <p style="margin: 0; font-size: 1.2em;">Deep insights into your corpus data with AI-powered analytics</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Navigation")

        if not st.session_state.authenticated:
            st.markdown("### 🔐 Login Required")
            st.info("Please log in to access the dashboard")
        else:
            st.success(f"👋 Welcome, {st.session_state.get('username', 'User')}!")

            # Navigation options
            dashboard_option = st.selectbox(
                "Choose Dashboard View",
                [
                    "🏠 My Records",
                    "🔍 Search User",
                    "🌐 Database Overview",
                    "⚙️ Settings",
                ],
                key="dashboard_option",
            )

            st.session_state.dashboard_mode = dashboard_option

            # Additional settings
            st.markdown("---")
            st.markdown("### ⚙️ Dashboard Settings")

            auto_refresh = st.checkbox(
                "🔄 Auto Refresh", value=st.session_state.auto_refresh
            )
            st.session_state.auto_refresh = auto_refresh

            export_format = st.selectbox(
                "📊 Export Format",
                ["csv", "excel", "json"],
                index=0 if st.session_state.export_format == "csv" else 1,
            )
            st.session_state.export_format = export_format

            # Move logout button to top-right corner with better styling
            st.markdown(
                """
            <style>
            .logout-button {
                position: fixed;
                top: 0.5rem;
                right: 1rem;
                z-index: 1000;
            }
            </style>
            """,
                unsafe_allow_html=True,
            )

            with st.container():
                if st.button(
                    "🚪 Logout",
                    key="header_logout",
                    type="primary",
                    help="Log out of your account",
                ):
                    # Clear authentication
                    st.session_state.authenticated = False
                    st.session_state.token = None
                    st.session_state.user_id = None
                    st.session_state.username = None
                    st.success("✅ Logged out successfully!")
                    time.sleep(1)
                    st.rerun()

    # Authentication Logic
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("### 🔐 Authentication")

            auth_method = st.radio(
                "Choose authentication method:",
                ["📱 Login with Password", "📲 Login with OTP"],
                horizontal=True,
            )

            if auth_method == "📱 Login with Password":
                with st.form("login_form"):
                    phone = st.text_input(
                        "📞 Phone Number", placeholder="Enter your phone number"
                    )
                    phone = f"+91{phone}"
                    password = st.text_input(
                        "🔒 Password",
                        type="password",
                        placeholder="Enter your password",
                    )

                    if st.form_submit_button("🚀 Login", type="primary"):
                        if phone and password:
                            login_result = login_user(phone, password)

                            if login_result and "access_token" in login_result:
                                token_info = decode_jwt_token(
                                    login_result["access_token"]
                                )

                                if token_info:
                                    st.session_state.authenticated = True
                                    st.session_state.token = login_result[
                                        "access_token"
                                    ]
                                    st.session_state.user_id = token_info["user_id"]
                                    st.session_state.username = phone
                                    st.success("✅ Login successful! Redirecting...")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(
                                        "❌ Failed to process authentication token"
                                    )
                            else:
                                st.error(
                                    "❌ Login failed. Please check your credentials."
                                )
                        else:
                            st.warning("⚠️ Please fill in all fields")

            else:  # OTP Login
                with st.form("otp_login_form"):
                    phone = st.text_input(
                        "📞 Phone Number", placeholder="Enter your phone number"
                    )
                    phone = f"+91{phone}"
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("📲 Send OTP"):
                            if phone:
                                if request_otp(phone):
                                    st.success("✅ OTP sent successfully!")
                                    st.session_state.otp_phone = phone
                            else:
                                st.warning("⚠️ Please enter your phone number")

                    if "otp_phone" in st.session_state:
                        otp = st.text_input(
                            "🔢 Enter OTP", placeholder="Enter the 6-digit OTP"
                        )

                        with col2:
                            if st.form_submit_button("✅ Verify OTP"):
                                if otp:
                                    verify_result = verify_otp(
                                        st.session_state.otp_phone, otp
                                    )

                                    if (
                                        verify_result
                                        and "access_token" in verify_result
                                    ):
                                        token_info = decode_jwt_token(
                                            verify_result["access_token"]
                                        )

                                        if token_info:
                                            st.session_state.authenticated = True
                                            st.session_state.token = verify_result[
                                                "access_token"
                                            ]
                                            st.session_state.user_id = token_info[
                                                "user_id"
                                            ]
                                            st.session_state.username = (
                                                st.session_state.otp_phone
                                            )
                                            st.success(
                                                "✅ OTP verification successful!"
                                            )
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error(
                                                "❌ Failed to process authentication token"
                                            )
                                    else:
                                        st.error("❌ Invalid OTP. Please try again.")
                                else:
                                    st.warning("⚠️ Please enter the OTP")
        return

    # Main Dashboard Logic (when authenticated)
    dashboard_mode = st.session_state.dashboard_mode

    if dashboard_mode == "🏠 My Records":
        st.markdown("## 👤 Your Personal Analytics")

        if st.button("🔄 Refresh My Data", type="primary"):
            user_records = fetch_records_with_cache(
                st.session_state.user_id, st.session_state.token, use_cache=False
            )

            if user_records:
                create_user_analytics_dashboard(user_records, st.session_state.username)

                # Export functionality
                st.markdown("---")
                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button("📥 Export Data"):
                        df = pd.DataFrame(user_records)

                        if st.session_state.export_format == "csv":
                            csv = df.to_csv(index=False)
                            st.download_button(
                                "💾 Download CSV",
                                csv,
                                f"my_records_{datetime.now().strftime('%Y%m%d')}.csv",
                                "text/csv",
                            )
                        elif st.session_state.export_format == "excel":
                            from io import BytesIO

                            buffer = BytesIO()
                            df.to_excel(buffer, index=False)
                            st.download_button(
                                "💾 Download Excel",
                                buffer.getvalue(),
                                f"my_records_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
            else:
                st.info("Click 'Refresh My Data' to load your analytics")

    elif dashboard_mode == "🔍 Search User":
        st.markdown("## 🔍 User Search & Analytics")

        # Load users list if not already loaded
        if st.session_state.users_list is None:
            if st.button("👥 Load Users List", type="primary"):
                with st.spinner("Loading users..."):
                    users = fetch_all_users(st.session_state.token)
                    if users:
                        st.session_state.users_list = users
                        st.session_state.user_mapping = create_user_mapping(users)
                        st.success(f"✅ Loaded {len(users)} users!")
                        st.rerun()
        else:
            st.success(f"👥 {len(st.session_state.users_list)} users loaded")

            # User selection methods
            search_method = st.radio(
                "Choose search method:",
                ["🔤 Select from Dropdown", "🔢 Enter User ID"],
                horizontal=True,
            )

            selected_user_id = None

            if search_method == "🔤 Select from Dropdown":
                if st.session_state.user_mapping:
                    # Create options with both name and ID
                    user_options = [
                        f"{name} ({user_id})"
                        for user_id, name in st.session_state.user_mapping.items()
                    ]

                    selected_option = st.selectbox(
                        "👤 Select User:", [""] + user_options, key="user_dropdown"
                    )

                    if selected_option:
                        # Extract user ID from the selected option
                        selected_user_id = selected_option.split("(")[-1].rstrip(")")

            else:  # Manual ID entry
                selected_user_id = st.text_input(
                    "🔢 Enter User ID:",
                    placeholder="Enter the user ID to search",
                    key="manual_user_id",
                )

            if selected_user_id and st.button("🔍 Search User Records", type="primary"):
                user_records = fetch_any_user_records(
                    selected_user_id, st.session_state.token
                )

                if user_records:
                    st.session_state.query_results = user_records
                    st.session_state.last_queried_user = selected_user_id

                    # Get user name from mapping
                    user_name = st.session_state.user_mapping.get(
                        selected_user_id, selected_user_id
                    )

                    create_user_analytics_dashboard(user_records, user_name)
                    
                    st.markdown("---")
                    st.markdown("### 📥 Export User Data")
                    df = pd.DataFrame(user_records)
                    user_name = st.session_state.user_mapping.get(selected_user_id, selected_user_id)
                    
                    # Create a modified summary for this user
                    user_summary = advanced_summarize(user_records)
                    create_export_section(df, user_summary)
                else:
                    st.warning(f"No records found for user: {selected_user_id}")

    elif dashboard_mode == "🌐 Database Overview":
        st.markdown("## 🌐 Database Overview & Analytics")

        if st.button("📊 Load Database Overview", type="primary"):
            # Load all records
            all_records = fetch_all_records(st.session_state.token)

            if all_records:
                st.session_state.database_overview = all_records

                # Load users if not already loaded
                if st.session_state.users_list is None:
                    with st.spinner("Loading users for leaderboard..."):
                        users = fetch_all_users(st.session_state.token)
                        if users:
                            st.session_state.users_list = users
                            st.session_state.user_mapping = create_user_mapping(users)

                # Create summary
                summary = advanced_summarize(all_records)

                if summary:
                    # Get total users count
                    total_users = (
                        len(st.session_state.users_list)
                        if st.session_state.users_list
                        else 0
                    )

                    # Create enhanced dashboard with all new features
                    create_advanced_overview_dashboard(
                        summary, st.session_state.user_mapping, total_users
                    )

                    # Export functionality for database overview - FIXED
                    st.markdown("---")
                    st.markdown("### 📥 Export Database Summary")
                    df = pd.DataFrame(all_records)  # Use all_records instead of user_records
                    create_export_section(df, summary)

        # Show existing overview if available
        elif st.session_state.database_overview:
            st.info(
                "📊 Database overview already loaded. Click 'Load Database Overview' to refresh."
            )

            summary = advanced_summarize(st.session_state.database_overview)
            if summary:
                total_users = (
                    len(st.session_state.users_list)
                    if st.session_state.users_list
                    else 0
                )
                create_advanced_overview_dashboard(
                    summary, st.session_state.user_mapping, total_users
                )
                
                # Add export section for existing overview too
                st.markdown("---")
                st.markdown("### 📥 Export Database Summary")
                df = pd.DataFrame(st.session_state.database_overview)
                create_export_section(df, summary)


    elif dashboard_mode == "⚙️ Settings":
        st.markdown("## ⚙️ Dashboard Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🎨 Appearance")

            # Theme settings
            new_theme = st.selectbox(
                "Chart Theme",
                ["dark", "light", "auto"],
                index=["dark", "light", "auto"].index(st.session_state.chart_theme),
            )
            st.session_state.chart_theme = new_theme

            # Animation settings
            animation_speed = st.selectbox(
                "Animation Speed", ["slow", "normal", "fast"], index=1
            )
            st.session_state.user_preferences["animation_speed"] = animation_speed

        with col2:
            st.markdown("### 📊 Data")

            # Export settings
            new_export_format = st.selectbox(
                "Default Export Format",
                ["csv", "excel", "json"],
                index=["csv", "excel", "json"].index(st.session_state.export_format),
            )
            st.session_state.export_format = new_export_format

            # Auto-refresh settings
            new_auto_refresh = st.checkbox(
                "Enable Auto Refresh", value=st.session_state.auto_refresh
            )
            st.session_state.auto_refresh = new_auto_refresh

        # Account actions
        st.markdown("---")
        st.markdown("### 🔐 Account")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Clear Cache"):
                # Clear all cached data
                keys_to_clear = [
                    k for k in st.session_state.keys() if k.startswith("records_")
                ]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.session_state.database_overview = None
                st.session_state.users_list = None
                st.session_state.user_mapping = {}
                st.success("✅ Cache cleared successfully!")

        with col2:
            if st.button("📥 Export Settings"):
                settings = {
                    "chart_theme": st.session_state.chart_theme,
                    "export_format": st.session_state.export_format,
                    "auto_refresh": st.session_state.auto_refresh,
                    "user_preferences": st.session_state.user_preferences,
                }
                st.download_button(
                    "💾 Download Settings",
                    json.dumps(settings, indent=2),
                    "dashboard_settings.json",
                    "application/json",
                )

        with col3:
            if st.button("🚪 Logout"):
                # Clear authentication
                st.session_state.authenticated = False
                st.session_state.token = None
                st.session_state.user_id = None
                st.session_state.username = None
                st.success("✅ Logged out successfully!")
                time.sleep(1)
                st.rerun()

    # Footer
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>🚀 Advanced Corpus Records Dashboard v2.0 | Built with ❤️ using Streamlit</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
