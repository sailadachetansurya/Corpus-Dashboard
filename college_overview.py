import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import plotly.express as px
import os, glob
import time
import logging

# Set up logging
logger = logging.getLogger(__name__)

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

def load_contributions_data(file_path="contributions_data.csv"):
    """Load pre-computed contributions data from CSV file"""
    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            # Ensure all required columns exist
            required_columns = ["Name", "Phone Number", "Total Contributions", "Image", "Video", "Audio", "Text", "Registered"]
            for col in required_columns:
                if col not in df.columns:
                    st.error(f"Missing required column: {col}")
                    return pd.DataFrame()
            return df
        else:
            st.warning(f"Contributions data file not found: {file_path}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading contributions data: {e}")
        return pd.DataFrame()

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

def generate_summary_csv(records_csv_path, users_csv_path, output_csv_path):
    """
    Generate a summary CSV from records and users data.
    
    Parameters:
    records_csv_path: path to records CSV
    users_csv_path: path to users CSV (with registration info)
    output_csv_path: path to save summary CSV
    
    Returns:
    DataFrame: Summary data with Name, Registered, total contributions, and media type counts
    """
    # Load CSV files
    df_records = pd.read_csv(records_csv_path)
    df_users = pd.read_csv(users_csv_path)
    
    # Find the user ID column in users CSV
    user_id_cols = ['user_id', 'uid', 'User ID', 'UserId', 'id']
    user_id_col = None
    for col in user_id_cols:
        if col in df_users.columns:
            user_id_col = col
            break
    
    if user_id_col is None:
        raise ValueError('User ID column not found in users CSV. Expected one of: ' + ', '.join(user_id_cols))
    
    # Normalize media_type column in records
    df_records['media_type'] = df_records['media_type'].str.lower()
    
    # Group records by user_id and count contributions
    user_contributions = df_records.groupby('user_id').agg({
        'title': 'count',  # total contributions
        'media_type': list
    }).rename(columns={'title': 'total_contributions'})
    
    # Count each media type
    def count_media_types(media_list):
        counts = {'image': 0, 'video': 0, 'audio': 0, 'text': 0}
        for media in media_list:
            if media in counts:
                counts[media] += 1
        return pd.Series(counts)
    
    # Apply media type counting
    media_counts = user_contributions['media_type'].apply(count_media_types)
    
    # Combine total contributions with media type counts
    df_summary = pd.concat([user_contributions['total_contributions'], media_counts], axis=1)
    df_summary = df_summary.reset_index()
    
    # Merge with users data to get Name and Registered status
    df_users_clean = df_users.rename(columns={user_id_col: 'user_id'})
    
    # Ensure required columns exist in users data
    required_cols = ['user_id', 'Name', 'Registered']
    missing_cols = [col for col in required_cols if col not in df_users_clean.columns]
    
    if missing_cols:
        print(f"Warning: Missing columns in users CSV: {missing_cols}")
        # Add missing columns with default values
        if 'Name' not in df_users_clean.columns:
            df_users_clean['Name'] = ''
        if 'Registered' not in df_users_clean.columns:
            df_users_clean['Registered'] = 'N'
    
    # Merge summary with user details
    df_final = df_summary.merge(
        df_users_clean[['user_id', 'Name', 'Registered']], 
        on='user_id', 
        how='left'
    )
    
    # Fill missing values
    df_final['Registered'] = df_final['Registered'].fillna('N')
    df_final['Name'] = df_final['Name'].fillna('')
    df_final = df_final.fillna(0)  # Fill media type counts with 0
    
    # Reorder columns as requested
    df_final = df_final[['Name', 'Registered', 'total_contributions', 'image', 'audio', 'text', 'video']]
    
    # Save summary CSV
    df_final.to_csv(output_csv_path, index=False)
    print(f"Summary CSV saved to {output_csv_path}")
    return df_final


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

def match_users_with_college_details(users_csv_path, clgdetails_csv_path, output_csv_path):
    """
    Match phone numbers from users CSV with college details CSV and append user details.
    
    Parameters:
    users_csv_path: path to users CSV with phone numbers
    clgdetails_csv_path: path to college details CSV
    output_csv_path: path to save the matched CSV
    
    Returns:
    DataFrame: The merged data with user and college details
    """
    # Load CSV files
    df_users = pd.read_csv(users_csv_path)
    df_clg = pd.read_csv(clgdetails_csv_path)
    
    # Function to clean and normalize phone numbers
    def clean_phone(phone):
        if pd.isna(phone):
            return None
        phone_str = str(phone)
        # Remove country code, spaces, dashes, parentheses
        phone_str = phone_str.replace('+91', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        # Remove leading zeros
        phone_str = phone_str.lstrip('0')
        return phone_str if phone_str.isdigit() and len(phone_str) == 10 else None
    
    # Clean phone numbers in both dataframes
    df_users['clean_phone'] = df_users['Phone Number'].apply(clean_phone)
    df_clg['clean_phone'] = df_clg['Contact Number'].apply(clean_phone)
    
    # Merge dataframes on cleaned phone numbers
    df_merged = pd.merge(
        df_users, 
        df_clg, 
        how='left', 
        left_on='clean_phone', 
        right_on='clean_phone', 
        suffixes=('_user', '_clg')
    )
    
    # Drop the temporary clean_phone columns
    df_merged = df_merged.drop(['clean_phone'], axis=1)
    
    # Save the merged data
    df_merged.to_csv(output_csv_path, index=False)
    print(f"Matched data saved to {output_csv_path}")
    return df_merged


def match_contributions_with_students(contributions_df, college_df):
    """Match contributions data with student data based on phone numbers"""
    matched_data = []
    
    # Create phone mapping from contributions data
    contrib_phone_map = {}
    for _, row in contributions_df.iterrows():
        phone = clean_phone_number(row.get("Phone Number", ""))
        if phone:
            contrib_phone_map[phone] = {
                "name": row.get("Name", ""),
                "total_contributions": row.get("Total Contributions", 0),
                "image": row.get("Image", 0),
                "video": row.get("Video", 0),
                "audio": row.get("Audio", 0),
                "text": row.get("Text", 0),
                "registered": row.get("Registered", "N")
            }
    
    # Match with college data
    for _, row in college_df.iterrows():
        cleaned_phone, original_phone = get_phone_from_row(row)
        
        # Get college and other details from college CSV
        college = row.get("Affiliation (College/Company/Organization Name)", 
                         row.get("college", "Unknown College"))
        name = row.get("Full Name", "Unknown")
        email = row.get("Email Address", "")
        created_at = row.get("CreatedAt", "")
        
        # Check if phone exists in contributions data
        if cleaned_phone and cleaned_phone in contrib_phone_map:
            contrib_data = contrib_phone_map[cleaned_phone]
            matched_data.append({
                "Name": contrib_data["name"],
                "Phone Number": original_phone,
                "Total Contributions": contrib_data["total_contributions"],
                "Image": contrib_data["image"],
                "Video": contrib_data["video"],
                "Audio": contrib_data["audio"],
                "Text": contrib_data["text"],
                "Registration Status": contrib_data["registered"],
                "College": college,
                "Email": email,
                "Created At": created_at
            })
        else:
            # Student not found in contributions data - mark as unregistered with 0 contributions
            matched_data.append({
                "Name": name,
                "Phone Number": original_phone or "",
                "Total Contributions": 0,
                "Image": 0,
                "Video": 0,
                "Audio": 0,
                "Text": 0,
                "Registration Status": "N",
                "College": college,
                "Email": email,
                "Created At": created_at
            })
    
    return pd.DataFrame(matched_data)

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
    
    # Load contributions data from CSV
    contributions_df = load_contributions_data("data/Records.csv")
    if contributions_df.empty:
        st.warning("⚠️ No contributions data found. Please ensure 'contributions_data.csv' exists with the required columns.")
        return
    
    # Match contributions with student data
    matched_df = match_contributions_with_students(contributions_df, df_all_college)
    
    if matched_df.empty:
        st.warning("⚠️ No matching data found.")
        return
    
    # Calculate overall metrics
    total_students = len(matched_df)
    registered_count = len(matched_df[matched_df["Registration Status"] == "Y"])
    unregistered_count = len(matched_df[matched_df["Registration Status"] == "N"])
    registration_rate = (registered_count / total_students * 100) if total_students > 0 else 0
    
    # Display OVERALL registration overview
    st.markdown("### 📊 Overall Registration Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Students", total_students)
    with col2:
        st.metric("Registered", registered_count)
    with col3:
        st.metric("Unregistered", unregistered_count)
    with col4:
        st.metric("Registration Rate", f"{registration_rate:.1f}%")
    
    # College selection dropdown
    st.markdown("### 🏫 College Selection")
    colleges = matched_df["College"].unique()
    college_options = ["All Colleges"] + list(colleges)
    selected_college = st.selectbox(
        "Select a college to view detailed statistics:",
        college_options,
        index=0
    )
    
    # Filter data based on selection
    if selected_college != "All Colleges":
        filtered_df = matched_df[matched_df["College"] == selected_college]
        
        # Show detailed college-specific metrics
        st.markdown(f"### 📊 Detailed Analysis for {selected_college}")
        college_total = len(filtered_df)
        college_registered = len(filtered_df[filtered_df["Registration Status"] == "Y"])
        college_unregistered = len(filtered_df[filtered_df["Registration Status"] == "N"])
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
        filtered_df = matched_df
        
        # Show college-wise summary
        st.markdown("### 📊 College-wise Summary")
        college_stats = matched_df.groupby('College').agg({
            'Registration Status': ['count', lambda x: (x == 'Y').sum()]
        }).round(2)
        
        college_stats.columns = ['total_students', 'registered_students']
        college_stats['unregistered_students'] = college_stats['total_students'] - college_stats['registered_students']
        college_stats['registration_rate'] = (college_stats['registered_students'] / college_stats['total_students'] * 100).round(1)
        college_stats = college_stats.reset_index()
        
        st.dataframe(college_stats, use_container_width=True)
        st.info("💡 Select a specific college from the dropdown above to view detailed analysis.")
    
    # Display contribution metrics
    total_users = len(filtered_df)
    registered_users_count = len(filtered_df[filtered_df["Registration Status"] == "Y"])
    unregistered_users_count = len(filtered_df[filtered_df["Registration Status"] == "N"])
    zero_records_count = len(filtered_df[filtered_df["Total Contributions"] == 0])
    activity_rate = ((total_users - zero_records_count) / total_users * 100) if total_users > 0 else 0
    
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
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
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
        filtered_df,
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
        csv_data = filtered_df.to_csv(index=False)
        st.download_button(
            label="📄 Download as CSV",
            data=csv_data,
            file_name=f"{selected_college.replace(' ', '_')}_student_data.csv",
            mime="text/csv"
        )
    
    with col2:
        json_data = filtered_df.to_json(orient="records", indent=2)
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
