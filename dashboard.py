

import streamlit as st

import pandas as pd
import plotly.express as px
from typing import Dict, List, Optional
from datetime import datetime
import json
import time


from records import fetch_records,fetch_all_records,fetch_records_with_cache,fetch_any_user_records,fetch_user_contributions,fetch_user_contributions_by_media_type
from college_overview import display_college_overview
from user import logger,login_user,verify_otp,request_otp,fetch_all_users,find_users_with_zero_records
from Auth import decode_jwt_token,initialize_session_state,validate_session_with_refresh,CATEGORIES,CATEGORY_ID_TO_NAME



def display_zero_records_analysis():
    """Display analysis of users with zero records"""
    st.subheader("📊 Zero Records Analysis")
    
    if st.button("🔍 Find Users with Zero Records"):
        with st.spinner("Analyzing user activity..."):
            zero_record_users = find_users_with_zero_records(st.session_state.token)
            
            if zero_record_users:
                st.error(f"❌ Found {len(zero_record_users)} users with zero records uploaded")
                
                # Create DataFrame for better display
                df_zero_users = pd.DataFrame(zero_record_users)
                
                # Display in expandable section
                with st.expander(f"View {len(zero_record_users)} Users with Zero Records"):
                    st.dataframe(
                        df_zero_users[['name', 'id', 'phone']],
                        use_container_width=True
                    )
                
                # Show summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Users with Zero Records", len(zero_record_users))
                with col2:
                    total_users = len(fetch_all_users(st.session_state.token))
                    percentage = (len(zero_record_users) / total_users) * 100
                    st.metric("Percentage", f"{percentage:.1f}%")
                with col3:
                    st.metric("Active Users", total_users - len(zero_record_users))
                    
            else:
                st.success("✅ All users have uploaded at least one record!")



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
                    "🏫 College Overview",
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
                    display_zero_records_analysis()
                else:
                    st.warning(f"No records found for user: {selected_user_id}")

    elif dashboard_mode == "🌐 Database Overview": 
     st.markdown("## 🌐 Database Overview & Analytics") 
    
    # Time filter selection
    st.markdown("### ⏰ Time Filter")
    time_filter = st.selectbox(
        "Select time range:",
        ["📊 Overall", "📅 Last 24 Hours", "📆 Last 7 Days"],
        key="db_time_filter"
    )
    
    # Helper function to filter records by time
    def filter_records_by_time(records, time_filter):
        if time_filter == "📊 Overall":
            return records
        
        from datetime import datetime, timedelta
        import pytz
        
        now = datetime.now(pytz.UTC)
        
        if time_filter == "📅 Last 24 Hours":
            cutoff_time = now - timedelta(hours=24)
        elif time_filter == "📆 Last 7 Days":
            cutoff_time = now - timedelta(days=7)
        else:
            return records
        
        filtered_records = []
        for record in records:
            try:
                # Try different timestamp field names
                timestamp_str = record.get('timestamp') or record.get('created_at') or record.get('date')
                if timestamp_str:
                    # Parse timestamp (adjust format as needed)
                    if 'T' in timestamp_str:
                        record_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        record_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    # Make timezone aware if needed
                    if record_time.tzinfo is None:
                        record_time = pytz.UTC.localize(record_time)
                    
                    if record_time >= cutoff_time:
                        filtered_records.append(record)
            except (ValueError, TypeError, AttributeError):
                # If timestamp parsing fails, include the record in overall view
                if time_filter == "📊 Overall":
                    filtered_records.append(record)
                continue
        
        return filtered_records
    
    # Display selected time range info
    if time_filter == "📅 Last 24 Hours":
        st.info("📅 Showing data from the last 24 hours")
    elif time_filter == "📆 Last 7 Days":
        st.info("📆 Showing data from the last 7 days")
    else:
        st.info("📊 Showing all-time data")
 
    if st.button("📊 Load Database Overview", type="primary"): 
        # Load all records 
        all_records = fetch_all_records(st.session_state.token) 
 
        if all_records: 
            # Filter records based on selected time range
            filtered_records = filter_records_by_time(all_records, time_filter)
            
            st.session_state.database_overview = filtered_records
            st.session_state.database_overview_filter = time_filter
            st.session_state.database_overview_all = all_records  # Keep original for reference
 
            # Load users if not already loaded 
            if st.session_state.users_list is None: 
                with st.spinner("Loading users for leaderboard..."): 
                    users = fetch_all_users(st.session_state.token) 
                    if users: 
                        st.session_state.users_list = users 
                        st.session_state.user_mapping = create_user_mapping(users) 
 
            # Create summary from filtered records
            summary = advanced_summarize(filtered_records) 
 
            if summary: 
                # Get total users count 
                total_users = ( 
                    len(st.session_state.users_list) 
                    if st.session_state.users_list 
                    else 0 
                ) 
                
                # Display filter summary
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("📊 Total Records", len(all_records))
                    
                with col2:
                    st.metric("🔍 Filtered Records", len(filtered_records))
                    
                with col3:
                    filter_percentage = (len(filtered_records) / len(all_records) * 100) if len(all_records) > 0 else 0
                    st.metric("📈 Filter Coverage", f"{filter_percentage:.1f}%")
 
                # Create enhanced dashboard with filtered data
                create_advanced_overview_dashboard( 
                    summary, st.session_state.user_mapping, total_users 
                ) 
 
                # Export functionality for database overview
                st.markdown("---") 
                st.markdown("### 📥 Export Database Summary") 
                df = pd.DataFrame(filtered_records)  # Use filtered records
                create_export_section(df, summary) 
                 
                # Add zero records analysis 
                st.markdown("---") 
                st.subheader("👥 User Activity Analysis") 
                 
                col1, col2, col3, col4 = st.columns(4) 
                 
                with col1: 
                    total_users = len(fetch_all_users(st.session_state.token)) 
                    st.metric("Total Registered Users", total_users) 
                 
                with col2: 
                    active_users = summary.get("total_users", 0) 
                    st.metric(f"Active Users ({time_filter.split(' ')[-1] if time_filter != '📊 Overall' else 'Overall'})", active_users) 
                 
                with col3: 
                    inactive_users = total_users - active_users 
                    st.metric("Users with Zero Records", inactive_users) 
                 
                with col4: 
                    activity_rate = (active_users / total_users) * 100 if total_users > 0 else 0 
                    st.metric("Activity Rate", f"{activity_rate:.1f}%") 
            else:
                st.warning(f"No records found for {time_filter.lower()}")
 
    # Show existing overview if available 
    elif st.session_state.database_overview: 
        # Check if filter has changed
        current_filter = getattr(st.session_state, 'database_overview_filter', "📊 Overall")
        
        if current_filter != time_filter:
            st.warning(f"⚠️ Currently showing data for '{current_filter}'. Click 'Load Database Overview' to apply '{time_filter}' filter.")
        else:
            st.info( 
                f"📊 Database overview already loaded for '{time_filter}'. Click 'Load Database Overview' to refresh." 
            ) 
 
        summary = advanced_summarize(st.session_state.database_overview) 
        if summary: 
            total_users = ( 
                len(st.session_state.users_list) 
                if st.session_state.users_list 
                else 0 
            ) 
            
            # Display current filter info
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            all_records_count = len(getattr(st.session_state, 'database_overview_all', st.session_state.database_overview))
            filtered_records_count = len(st.session_state.database_overview)
            
            with col1:
                st.metric("📊 Total Records", all_records_count)
                
            with col2:
                st.metric("🔍 Filtered Records", filtered_records_count)
                
            with col3:
                filter_percentage = (filtered_records_count / all_records_count * 100) if all_records_count > 0 else 0
                st.metric("📈 Filter Coverage", f"{filter_percentage:.1f}%")
            
            create_advanced_overview_dashboard( 
                summary, st.session_state.user_mapping, total_users 
            ) 
             
            # Add export section for existing overview too 
            st.markdown("---") 
            st.markdown("### 📥 Export Database Summary") 
            df = pd.DataFrame(st.session_state.database_overview) 
            create_export_section(df, summary)
    
        else:
          st.info("👆 Click 'Load Database Overview' to start analyzing your database with the selected time filter.")

    elif dashboard_mode == "🏫 College Overview":
       display_college_overview(fetch_all_users, fetch_user_contributions, st.session_state.token)


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
