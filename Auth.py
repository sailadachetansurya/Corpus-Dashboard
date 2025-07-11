
import secrets
import streamlit as st
from asyncio.log import logger
import time
from typing import Dict, Optional
from streamlit_js_eval import streamlit_js_eval as js
import base64
import json
import hashlib

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
        
        if user_id and user_id != "null" and user_id is not None:
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
