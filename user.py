

import streamlit as st
from asyncio.log import logger
import time
from typing import Dict, List, Optional

import requests

from Auth import decode_jwt_token,clear_auth_from_browser,save_auth_to_browser
from records import fetch_all_records


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



def find_users_with_zero_records(token: str) -> List[Dict]:
    """Find users who have zero records uploaded"""
    try:
        # Fetch all users and all records
        all_users = fetch_all_users(token)
        all_records = fetch_all_records(token)
        
        if not all_users or not all_records:
            st.error("Failed to fetch required data")
            return []
        
        # Get set of user IDs who have uploaded records
        users_with_records = set()
        for record in all_records:
            if record.get("user_id"):
                users_with_records.add(record["user_id"])
        
        # Find users with zero records
        users_with_zero_records = []
        for user in all_users:
            user_id = user.get("id")
            if user_id and user_id not in users_with_records:
                users_with_zero_records.append(user)
        
        return users_with_zero_records
        
    except Exception as e:
        logger.error(f"Error finding users with zero records: {e}")
        st.error(f"Error: {e}")
        return []

