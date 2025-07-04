import streamlit as st
import pandas as pd
import plotly.express as px
import os, glob
import time
import requests

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

def safe_fetch_user_contributions(user_id, token, fetch_function, max_retries=3):
    """
    Safely fetch user contributions with retry logic and better error handling
    """
    for attempt in range(max_retries):
        try:
            # Add a small delay between requests to avoid overwhelming the server
            if attempt > 0:
                time.sleep(1)
            
            user_data = fetch_function(user_id, token)
            
            if user_data and isinstance(user_data, dict):
                if "total_contributions" in user_data:
                    return user_data["total_contributions"]
                else:
                    return 0
            else:
                return 0
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                if attempt == max_retries - 1:
                    return 0
            else:
                return 0
        except requests.exceptions.RequestException as e:
            return 0
        except Exception as e:
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

def display_college_overview(fetch_all_users, fetch_user_contributions, token: str):
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
        test_mode = st.checkbox("Enable test mode (limit API calls)", value=True)
        if test_mode:
            max_api_calls = st.slider("Max API calls to test", 1, 100, 20)
        else:
            max_api_calls = len([c for c in college_contributors if c["registered"]])

    # Fetch contributions with improved error handling
    st.markdown("### 🔄 Fetching Contribution Data")
    
    data = []
    progress = st.progress(0)
    status_text = st.empty()
    
    api_calls_made = 0
    successful_calls = 0
    users_with_contributions = 0
    
    for i, contributor in enumerate(college_contributors):
        if contributor["registered"] and api_calls_made < max_api_calls:
            user_id = contributor["user_id"]
            status_text.text(f"Fetching data for {contributor['name']}...")
            
            # Use the safe fetch function
            total = safe_fetch_user_contributions(user_id, token, fetch_user_contributions)
            
            api_calls_made += 1
            if total > 0:
                successful_calls += 1
                users_with_contributions += 1
                
        else:
            total = 0  # Skip API call or unregistered users

        data.append({**contributor, "contributions": total})
        progress.progress((i + 1) / len(college_contributors))

    progress.empty()
    status_text.empty()
    
    # Display API call summary
    if api_calls_made > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("API Calls Made", api_calls_made)
        with col2:
            st.metric("Successful Calls", successful_calls)
        with col3:
            st.metric("Users with Contributions", users_with_contributions)

    df = pd.DataFrame(data)

    # Show summary statistics
    st.markdown("### 📈 Contribution Summary")
    registered_users = len(df[df['registered'] == True])
    users_with_contribs = len(df[df['contributions'] > 0])
    total_contributions = df['contributions'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Registered Users", registered_users)
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
        registered_download_df = df[df["registered"] == True][["name", "college", "contributions", "phone", "cleaned_phone"]]
        if len(registered_download_df) > 0:
            registered_csv = registered_download_df.to_csv(index=False)
            st.download_button(
                f"⬇️ Download All Registered Users ({len(registered_download_df)} users)",
                registered_csv,
                "all_registered_users.csv",
                "text/csv",
                key="all_registered_download"
            )
        else:
            st.write("No registered users to download")
    
    with col2:
        # All unmatched users
        unmatched_download_df = df[df["registered"] == False][["name", "college", "phone", "cleaned_phone"]]
        if len(unmatched_download_df) > 0:
            unmatched_csv = unmatched_download_df.to_csv(index=False)
            st.download_button(
                f"⬇️ Download All Unmatched Users ({len(unmatched_download_df)} users)",
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
                registered_count = len(college_df[college_df["registered"] == True])
                unregistered_count = len(college_df[college_df["registered"] == False])
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
                    college_registered = college_df[college_df["registered"] == True][["name", "contributions", "phone", "cleaned_phone"]]
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
                    college_unregistered = college_df[college_df["registered"] == False][["name", "phone", "cleaned_phone"]]
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
            college_registered = college_df[college_df["registered"] == True][["name", "contributions", "phone", "cleaned_phone"]]
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
            college_unregistered = college_df[college_df["registered"] == False][["name", "phone", "cleaned_phone"]]
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
        registered_df = df[df["registered"] == True]
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
    unregistered_df = df[df["registered"] == False]
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
            len(df[df["registered"] == True]),
            len(df[df["registered"] == False]),
            len(df[df["contributions"] > 0]),
            df["contributions"].sum(),
            round(df[df["contributions"] > 0]["contributions"].mean(), 2) if len(df[df["contributions"] > 0]) > 0 else 0
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True)