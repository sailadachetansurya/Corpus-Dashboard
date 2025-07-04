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

    # Load users from API
    all_users = fetch_all_users(token)
    if not all_users:
        st.error("❌ Failed to fetch users from backend.")
        return

    # Normalize phone numbers
    user_phone_map = {}
    for user in all_users:
        raw_phone = user.get("phone", "")
        stripped_phone = raw_phone.replace("+91", "").strip()
        user_phone_map[stripped_phone] = {
            "user_id": user.get("id"),
            "name": user.get("name", "Unknown User"),
        }

    # Build mapping phone → college
    college_contributors = []
    for _, row in df_all_college.iterrows():
        phone = str(row["Phone Number"]).strip()
        college = row.get("college", "Unknown College")
        user_data = user_phone_map.get(phone)
    if user_data:
        college_contributors.append({
            "user_id": user_data["user_id"],
            "name": user_data["name"],
            "phone": phone,
            "college": college,
            "registered": True
        })
    else:
        college_contributors.append({
            "user_id": None,
            "name": row.get("FirstName", "Unknown"),
            "phone": phone,
            "college": college,
            "registered": False
        })

    if not college_contributors:
        st.warning("⚠️ No matching users found between CSVs and backend data.")
        return

    st.success(f"✅ Found {len(college_contributors)} college-mapped contributors.")

    # Fetch contributions
    data = []
    progress = st.progress(0)
    for i, contributor in enumerate(college_contributors):
     if contributor["registered"]:
        user_id = contributor["user_id"]
        user_data = fetch_user_contributions(user_id, token)
        total = user_data["total_contributions"] if user_data else 0
    else:
        total = 0  # Unregistered students get 0

    data.append({**contributor, "contributions": total})
    progress.progress((i + 1) / len(college_contributors))

    progress.empty()

    df = pd.DataFrame(data)

    # College summary
    college_summary = df[df["registered"]].groupby("college")["contributions"].sum().reset_index().sort_values(by="contributions", ascending=False)

    college_summary["percentage"] = (college_summary["contributions"] / college_summary["contributions"].sum()) * 100

    st.markdown("### 📊 Contributions by College")
    st.dataframe(college_summary, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(college_summary, names="college", values="contributions", title="College Contribution Share")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(college_summary, x="college", y="contributions", title="Total Contributions", text="contributions")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🏆 Individual Contributor Leaderboard")
    st.dataframe(
    df.sort_values(by="contributions", ascending=False)[["name", "college", "contributions", "registered"]],
    use_container_width=True
)
    st.markdown("### 🚫 Unregistered Students")
    st.dataframe(df[df["registered"] == False][["name", "college", "phone"]], use_container_width=True)

    st.markdown("### 📥 Download CSV Files")
    # Registered users only
    registered_df = df[df["registered"] == True][["name", "college", "contributions", "phone"]]
    registered_csv = registered_df.to_csv(index=False)
    st.download_button(
    "⬇️ Download Registered Contributions CSV",
    registered_csv,
    "registered_contributions.csv",
    "text/csv"
)
    # Unregistered users only
    unregistered_df = df[df["registered"] == False][["name", "college", "phone"]]
    unregistered_csv = unregistered_df.to_csv(index=False)
    st.download_button(
    "⬇️ Download Unregistered Students CSV",
    unregistered_csv,
    "unregistered_students.csv",
    "text/csv"
)
