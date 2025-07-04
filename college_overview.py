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
                    st.warning(f"No 'total_contributions' field found for user {user_id}")
                    return 0
            else:
                st.warning(f"Invalid response format for user {user_id}")
                return 0
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                st.error(f"Server error (500) for user {user_id}, attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    return 0
            else:
                st.error(f"HTTP error {e.response.status_code} for user {user_id}")
                return 0
        except requests.exceptions.RequestException as e:
            st.error(f"Network error for user {user_id}: {str(e)}")
            return 0
        except Exception as e:
            st.error(f"Unexpected error for user {user_id}: {str(e)}")
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
    # Check both phone columns (with and without trailing space)
    phone_columns = ["Phone Number", "Phone Number "]
    
    for col in phone_columns:
        if col in row.index:
            phone = row[col]
            cleaned = clean_phone_number(phone)
            if cleaned:
                return cleaned, phone  # Return both cleaned and original
    
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

    # Debug CSV columns
    st.write("**CSV Columns:**", df_all_college.columns.tolist())
    
    # Check for phone number columns
    phone_columns = [col for col in df_all_college.columns if 'phone' in col.lower() or 'mobile' in col.lower()]
    st.write("**Potential phone columns:**", phone_columns)
    
    # Load users from API (cache to avoid multiple calls)
    if 'cached_users' not in st.session_state:
        st.write("Fetching users from API...")
        all_users = fetch_all_users(token)
        st.session_state.cached_users = all_users
    else:
        st.write("Using cached user data...")
        all_users = st.session_state.cached_users
        
    if not all_users:
        st.error("❌ Failed to fetch users from backend.")
        return

    # Debug: Show sample data
    st.write("**Debug Info:**")
    st.write(f"Total users from API: {len(all_users)}")
    st.write(f"Total rows in CSV: {len(df_all_college)}")
    
    # Show data quality issues for both phone columns
    phone_stats = {}
    for col in phone_columns:
        if col in df_all_college.columns:
            null_count = df_all_college[col].isna().sum()
            valid_count = df_all_college[col].apply(clean_phone_number).notna().sum()
            phone_stats[col] = {"null": null_count, "valid": valid_count}
    
    st.write("**Phone Data Quality:**")
    for col, stats in phone_stats.items():
        st.write(f"- {col}: {stats['null']} null, {stats['valid']} valid")
    
    # Normalize phone numbers with better handling
    user_phone_map = {}
    api_phone_samples = []
    
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
                # Collect samples for debugging
                if len(api_phone_samples) < 10:
                    api_phone_samples.append(f"{raw_phone} -> {cleaned_phone}")

    st.write(f"Phone mapping created for {len(user_phone_map)} users")
    
    # Debug: Show sample phone numbers from API
    st.write("**Sample API Phone Numbers:**")
    for sample in api_phone_samples[:5]:
        st.write(f"- {sample}")
    
    # Debug: Show sample CSV phone numbers
    st.write("**Sample CSV Phone Numbers:**")
    csv_phone_samples = []
    for _, row in df_all_college.head(10).iterrows():
        cleaned_phone, original_phone = get_phone_from_row(row)
        if original_phone:
            csv_phone_samples.append(f"{original_phone} -> {cleaned_phone}")
    
    for sample in csv_phone_samples[:5]:
        st.write(f"- {sample}")

    # Build mapping with improved phone matching
    college_contributors = []
    matched_count = 0
    unmatched_count = 0
    
    # Debug: Track specific BITS students
    bits_debug = []
    
    for _, row in df_all_college.iterrows():
        cleaned_phone, original_phone = get_phone_from_row(row)
        college = row.get("college", "Unknown College")
        name = row.get("FirstName", row.get("Name", row.get("Student Name", "Unknown")))
        
        # Special debugging for BITS students
        if "bits" in college.lower() or "pilani" in college.lower():
            bits_debug.append({
                "name": name,
                "original_phone": original_phone,
                "cleaned_phone": cleaned_phone,
                "in_api": cleaned_phone in user_phone_map if cleaned_phone else False
            })
        
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

    st.write(f"**Matching Results:**")
    st.write(f"✅ Matched phones: {matched_count}")
    st.write(f"❌ Unmatched phones: {unmatched_count}")
    
    # Debug BITS students specifically
    if bits_debug:
        st.write("**BITS Students Debug:**")
        bits_df = pd.DataFrame(bits_debug)
        st.dataframe(bits_df, use_container_width=True)
        
        # Show specific mismatches
        unmatched_bits = bits_df[bits_df["in_api"] == False]
        if len(unmatched_bits) > 0:
            st.write(f"**{len(unmatched_bits)} BITS students not found in API:**")
            for _, student in unmatched_bits.head(5).iterrows():
                st.write(f"- {student['name']}: {student['original_phone']} -> {student['cleaned_phone']}")
                
                # Check if similar numbers exist in API
                if student['cleaned_phone']:
                    similar_in_api = [phone for phone in user_phone_map.keys() 
                                    if phone.startswith(student['cleaned_phone'][:3])]
                    if similar_in_api:
                        st.write(f"  Similar numbers in API: {similar_in_api[:3]}")
    
    # Additional debug: Check for any phone number format issues
    st.write("**Phone Number Format Analysis:**")
    csv_phone_lengths = {}
    for _, row in df_all_college.iterrows():
        cleaned_phone, original_phone = get_phone_from_row(row)
        if cleaned_phone:
            length = len(cleaned_phone)
            csv_phone_lengths[length] = csv_phone_lengths.get(length, 0) + 1
    
    api_phone_lengths = {}
    for phone in user_phone_map.keys():
        length = len(phone)
        api_phone_lengths[length] = api_phone_lengths.get(length, 0) + 1
    
    st.write(f"CSV phone lengths: {csv_phone_lengths}")
    st.write(f"API phone lengths: {api_phone_lengths}")

    if not college_contributors:
        st.warning("⚠️ No contributors found in CSV data.")
        return

    # Add option to limit API calls for testing
    st.write("**API Testing Options:**")
    test_mode = st.checkbox("Enable test mode (limit API calls)", value=True)
    if test_mode:
        max_api_calls = st.slider("Max API calls to test", 1, 100, 20)
    else:
        max_api_calls = len([c for c in college_contributors if c["registered"]])

    st.success(f"✅ Found {len(college_contributors)} college-mapped contributors.")

    # Fetch contributions with improved error handling
    data = []
    progress = st.progress(0)
    api_calls_made = 0
    successful_calls = 0
    failed_calls = 0
    users_with_contributions = 0
    
    for i, contributor in enumerate(college_contributors):
        if contributor["registered"] and api_calls_made < max_api_calls:
            user_id = contributor["user_id"]
            
            # Use the safe fetch function
            total = safe_fetch_user_contributions(user_id, token, fetch_user_contributions)
            
            api_calls_made += 1
            if total > 0:
                successful_calls += 1
                users_with_contributions += 1
            else:
                failed_calls += 1
                
        else:
            total = 0  # Skip API call or unregistered users

        data.append({**contributor, "contributions": total})
        progress.progress((i + 1) / len(college_contributors))

    progress.empty()
    
    # Display comprehensive statistics
    st.write("**API Call Statistics:**")
    st.write(f"📞 API calls made: {api_calls_made}")
    st.write(f"✅ Successful calls: {successful_calls}")
    st.write(f"❌ Failed calls: {failed_calls}")
    st.write(f"🏆 Users with contributions > 0: {users_with_contributions}")
    
    if failed_calls > 0:
        st.error(f"⚠️ {failed_calls} API calls failed. Please check your backend server!")

    df = pd.DataFrame(data)

    # Show summary statistics
    st.write("**Summary Statistics:**")
    registered_users = len(df[df['registered'] == True])
    users_with_contribs = len(df[df['contributions'] > 0])
    total_contributions = df['contributions'].sum()
    
    st.write(f"📊 Total registered users: {registered_users}")
    st.write(f"🏆 Users with contributions > 0: {users_with_contribs}")
    st.write(f"📈 Total contributions: {total_contributions}")

    # DOWNLOAD SECTION - MOVED UP FOR BETTER VISIBILITY
    st.markdown("### 📥 Download CSV Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Registered users with contributions
        registered_download_df = df[df["registered"] == True][["name", "college", "contributions", "phone", "cleaned_phone"]]
        if len(registered_download_df) > 0:
            registered_csv = registered_download_df.to_csv(index=False)
            st.download_button(
                f"⬇️ Download Registered Users ({len(registered_download_df)} users)",
                registered_csv,
                "registered_contributions.csv",
                "text/csv",
                key="registered_download"
            )
        else:
            st.write("No registered users to download")
    
    with col2:
        # Unmatched users (the 99 people you want to download)
        unmatched_download_df = df[df["registered"] == False][["name", "college", "phone", "cleaned_phone"]]
        if len(unmatched_download_df) > 0:
            unmatched_csv = unmatched_download_df.to_csv(index=False)
            st.download_button(
                f"⬇️ Download Unmatched Users ({len(unmatched_download_df)} users)",
                unmatched_csv,
                "unmatched_students.csv",
                "text/csv",
                key="unmatched_download"
            )
        else:
            st.write("No unmatched users to download")

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

        st.markdown("### 📊 College Contributions Summary")
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

    else:
        st.warning("⚠️ No contribution data available to display charts.")

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
                    st.markdown(f"**{college}**")
                    college_top = college_df.sort_values(by="contributions", ascending=False).head(10)
                    st.dataframe(college_top[["name", "contributions", "phone"]], use_container_width=True)
        else:
            st.write("No users with contributions found")
    
    # Enhanced unregistered section
    st.markdown("### 🚫 Unregistered Students Details")
    unregistered_df = df[df["registered"] == False]
    if len(unregistered_df) > 0:
        # Group by college for better organization
        st.markdown("#### Unregistered Students by College")
        for college in unregistered_df["college"].unique():
            college_unreg = unregistered_df[unregistered_df["college"] == college]
            st.markdown(f"**{college}** - {len(college_unreg)} students")
            st.dataframe(college_unreg[["name", "phone", "cleaned_phone"]], use_container_width=True)
    else:
        st.write("No unregistered students found")

    # Final summary
    st.markdown("### 📋 Final Summary")
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