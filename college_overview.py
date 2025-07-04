import streamlit as st
import pandas as pd
import plotly.express as px
import os, glob

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
    st.write("Sample CSV data:")
    st.write(df_all_college.head())
    st.write("Sample user data:")
    st.write(all_users[:2] if len(all_users) >= 2 else all_users)

    # Normalize phone numbers with better handling
    user_phone_map = {}
    for user in all_users:
        raw_phone = user.get("phone", "")
        if raw_phone:
            # Handle different phone formats
            stripped_phone = str(raw_phone).replace("+91", "").replace("-", "").replace(" ", "").strip()
            user_phone_map[stripped_phone] = {
                "user_id": user.get("id"),
                "name": user.get("name", "Unknown User"),
                "original_phone": raw_phone
            }

    st.write(f"Phone mapping created for {len(user_phone_map)} users")
    
    # Debug: Show sample phone mappings
    st.write("**Sample phone mappings:**")
    sample_phones = list(user_phone_map.items())[:5]
    for phone, user_info in sample_phones:
        st.write(f"  {phone} -> {user_info['name']} (ID: {user_info['user_id']})")
    
    # Debug: Show sample CSV phone numbers
    st.write("**Sample CSV phone numbers:**")
    sample_csv_phones = df_all_college['Phone Number'].astype(str).head(10).tolist()
    for phone in sample_csv_phones:
        st.write(f"  CSV: '{phone}'")
        # Show how it gets normalized
        normalized = phone.replace("+91", "").replace("-", "").replace(" ", "").strip()
        st.write(f"  Normalized: '{normalized}'")
        match_found = normalized in user_phone_map
        st.write(f"  Match found: {match_found}")
        if match_found:
            st.write(f"  Matches to: {user_phone_map[normalized]['name']}")
        st.write("---")

    # Build mapping phone → college with better phone matching
    college_contributors = []
    matched_phones = []
    unmatched_phones = []
    
    for _, row in df_all_college.iterrows():
        phone = str(row.get("Phone Number", "")).strip()
        college = row.get("college", "Unknown College")
        
        # Try multiple phone formats
        phone_variants = [
            phone,
            phone.replace("+91", "").replace("-", "").replace(" ", "").strip(),
            phone.replace("-", "").replace(" ", "").strip(),
            phone.lstrip("0")  # Remove leading zeros
        ]
        
        user_data = None
        matched_phone = None
        
        for variant in phone_variants:
            if variant in user_phone_map:
                user_data = user_phone_map[variant]
                matched_phone = variant
                break
        
        if user_data:
            college_contributors.append({
                "user_id": user_data["user_id"],
                "name": user_data["name"],
                "phone": phone,
                "college": college,
                "registered": True
            })
            matched_phones.append(f"{phone} -> {user_data['original_phone']}")
        else:
            college_contributors.append({
                "user_id": None,
                "name": row.get("FirstName", row.get("Name", "Unknown")),
                "phone": phone,
                "college": college,
                "registered": False
            })
            unmatched_phones.append(phone)

    st.write(f"**Matching Results:**")
    st.write(f"Matched phones: {len(matched_phones)}")
    st.write(f"Unmatched phones: {len(unmatched_phones)}")
    
    if matched_phones:
        st.write("Sample matches:")
        st.write(matched_phones[:5])
    
    if unmatched_phones:
        st.write("Sample unmatched phones:")
        st.write(unmatched_phones[:5])

    if not college_contributors:
        st.warning("⚠️ No matching users found between CSVs and backend data.")
        return

    st.success(f"✅ Found {len(college_contributors)} college-mapped contributors.")

    # Fetch contributions with detailed debugging
    data = []
    progress = st.progress(0)
    contribution_errors = []
    successful_fetches = 0
    users_with_contributions = 0
    
    # Test with first few users to debug the issue
    st.write("**Detailed Debug - Testing first 5 registered users:**")
    
    for i, contributor in enumerate(college_contributors):
        if contributor["registered"]:
            user_id = contributor["user_id"]
            try:
                st.write(f"Fetching data for user: {contributor['name']} (ID: {user_id})")
                user_data = fetch_user_contributions(user_id, token)
                
                if user_data:
                    st.write(f"✅ API Response received")
                    
                    # Check if total_contributions exists and its value
                    if "total_contributions" in user_data:
                        total = user_data["total_contributions"]
                        st.write(f"✅ total_contributions field found: {total}")
                        
                        # Also show breakdown by media type
                        if "contributions_by_media_type" in user_data:
                            media_breakdown = user_data["contributions_by_media_type"]
                            st.write(f"Media type breakdown: {media_breakdown}")
                            
                            # Calculate total from breakdown as verification
                            calculated_total = sum(media_breakdown.values())
                            st.write(f"Calculated total from breakdown: {calculated_total}")
                            
                            if calculated_total != total:
                                st.warning(f"⚠️ Mismatch: API says {total}, breakdown sums to {calculated_total}")
                        
                        successful_fetches += 1
                        if total > 0:
                            users_with_contributions += 1
                    else:
                        st.write(f"❌ total_contributions field not found in response")
                        st.write(f"Available fields: {list(user_data.keys())}")
                        total = 0
                        
                else:
                    total = 0
                    contribution_errors.append(f"No data returned for user {contributor['name']} (ID: {user_id})")
                    st.write(f"❌ No data returned for user {contributor['name']}")
                    
            except Exception as e:
                total = 0
                contribution_errors.append(f"Error fetching data for user {contributor['name']}: {str(e)}")
                st.write(f"❌ Error for user {contributor['name']}: {str(e)}")
        else:
            total = 0  # Unregistered students get 0

        data.append({**contributor, "contributions": total})
        progress.progress((i + 1) / len(college_contributors))
        
        # Only show detailed debug for first 5 registered users
        if contributor["registered"] and len([c for c in college_contributors[:i+1] if c["registered"]]) >= 5:
            break

    progress.empty()
    
    st.write(f"**Debug Summary:**")
    st.write(f"Successful API calls: {successful_fetches}")
    st.write(f"Users with contributions > 0: {users_with_contributions}")
    st.write(f"Total registered users: {len([c for c in college_contributors if c['registered']])}")
    
    # Complete the data collection for remaining users (without detailed debug)
    remaining_contributors = college_contributors[len(data):]
    for i, contributor in enumerate(remaining_contributors):
        if contributor["registered"]:
            user_id = contributor["user_id"]
            try:
                user_data = fetch_user_contributions(user_id, token)
                if user_data and "total_contributions" in user_data:
                    total = user_data["total_contributions"]
                    if total > 0:
                        users_with_contributions += 1
                else:
                    total = 0
            except Exception as e:
                total = 0
        else:
            total = 0

        data.append({**contributor, "contributions": total})
        progress.progress((len(data)) / len(college_contributors))

    if contribution_errors:
        st.write("**Contribution Fetch Errors:**")
        for error in contribution_errors[:10]:  # Show first 10 errors
            st.write(f"- {error}")

    df = pd.DataFrame(data)

    # Show summary statistics
    st.write("**Summary Statistics:**")
    st.write(f"Total registered users: {len(df[df['registered'] == True])}")
    st.write(f"Users with contributions > 0: {len(df[df['contributions'] > 0])}")
    st.write(f"Total contributions: {df['contributions'].sum()}")

    # College summary (only registered users)
    registered_df = df[df["registered"] == True]
    if len(registered_df) > 0:
        college_summary = registered_df.groupby("college")["contributions"].sum().reset_index().sort_values(by="contributions", ascending=False)
        college_summary["percentage"] = (college_summary["contributions"] / college_summary["contributions"].sum()) * 100 if college_summary["contributions"].sum() > 0 else 0

        st.markdown("### 📊 Contributions by College")
        st.dataframe(college_summary, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if college_summary["contributions"].sum() > 0:
                fig = px.pie(college_summary, names="college", values="contributions", title="College Contribution Share")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("No contributions to display in pie chart")
                
        with col2:
            fig = px.bar(college_summary, x="college", y="contributions", title="Total Contributions", text="contributions")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No registered users found to display college summary")

    st.markdown("### 🏆 Individual Contributor Leaderboard")
    st.dataframe(
        df.sort_values(by="contributions", ascending=False)[["name", "college", "contributions", "registered"]],
        use_container_width=True
    )
    
    st.markdown("### 🚫 Unregistered Students")
    unregistered_df = df[df["registered"] == False]
    if len(unregistered_df) > 0:
        st.dataframe(unregistered_df[["name", "college", "phone"]], use_container_width=True)
    else:
        st.write("No unregistered students found")

    st.markdown("### 📥 Download CSV Files")
    # Registered users only
    registered_download_df = df[df["registered"] == True][["name", "college", "contributions", "phone"]]
    if len(registered_download_df) > 0:
        registered_csv = registered_download_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download Registered Contributions CSV",
            registered_csv,
            "registered_contributions.csv",
            "text/csv"
        )
    
    # Unregistered users only
    unregistered_download_df = df[df["registered"] == False][["name", "college", "phone"]]
    if len(unregistered_download_df) > 0:
        unregistered_csv = unregistered_download_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download Unregistered Students CSV",
            unregistered_csv,
            "unregistered_students.csv",
            "text/csv"
        )