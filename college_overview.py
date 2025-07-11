import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import plotly.express as px
import os
import logging
from user import fetch_all_users, fetch_all_records

logger = logging.getLogger(__name__)

def clean_phone_number(phone):
    """Clean and normalize phone numbers for matching"""
    if pd.isna(phone) or phone == 'nan' or str(phone).strip() == '':
        return None
    
    phone_str = str(phone).strip()
    # Remove country code, spaces, dashes, parentheses
    phone_clean = phone_str.replace("+91", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    phone_clean = phone_clean.lstrip("0")
    
    if phone_clean.isdigit() and len(phone_clean) == 10:
        return phone_clean
    return None

def generate_contribution_data(token):
    """Generate contribution_data.csv following the exact specified flow"""
    
    # Step 1: Fetch all users
    st.info("Step 1: Fetching all users...")
    try:
        users_data = fetch_all_users(token)
        if not users_data:
            st.error("Failed to fetch users data")
            return None
        
        df_users = pd.DataFrame(users_data)
        st.success(f"✅ Fetched {len(df_users)} users")
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return None
    
    # Step 2: Read clgdetails.csv
    st.info("Step 2: Reading college details...")
    clgdetails_path = "data/clgdetails/Cohort1.csv"
    
    if not os.path.exists(clgdetails_path):
        st.error(f"College details file not found: {clgdetails_path}")
        return None
    
    try:
        df_clg = pd.read_csv(clgdetails_path)
        st.success(f"✅ Loaded {len(df_clg)} college records")
    except Exception as e:
        st.error(f"Error reading college details: {e}")
        return None
    
    # Step 3: Map students with users based on phone number
    st.info("Step 3: Mapping students with users based on phone numbers...")
    
    # Clean phone numbers in both dataframes
    df_users['clean_phone'] = df_users['phone'].apply(clean_phone_number)
    df_clg['clean_phone'] = df_clg['Contact Number'].apply(clean_phone_number)
    
    # Create user lookup dictionary
    user_lookup = {}
    for _, user in df_users.iterrows():
        clean_phone = user['clean_phone']
        if clean_phone:
            user_lookup[clean_phone] = {
                'user_id': user.get('id', user.get('user_id', 'N/A')),
                'registered': 'Y'
            }
    
    # Map students with users
    mapped_students = []
    for _, student in df_clg.iterrows():
        clean_phone = student['clean_phone']
        original_phone = student['Contact Number']
        
        if clean_phone and clean_phone in user_lookup:
            # Student is registered
            user_info = user_lookup[clean_phone]
            mapped_students.append({
                'Name': student['Full Name'],
                'Phone no': original_phone,
                'Registration status': 'Y',
                'user id': user_info['user_id'],
                'College': student['Affiliation (College/Company/Organization Name)'],
                'Email': student.get('Email Address', ''),
                'CreatedAt': student.get('CreatedAt', '')
            })
        else:
            # Student is not registered
            mapped_students.append({
                'Name': student['Full Name'],
                'Phone no': original_phone,
                'Registration status': 'N',
                'user id': 'N/A',
                'College': student['Affiliation (College/Company/Organization Name)'],
                'Email': student.get('Email Address', ''),
                'CreatedAt': student.get('CreatedAt', '')
            })
    
    df_mapped = pd.DataFrame(mapped_students)
    st.success(f"✅ Mapped {len(df_mapped)} students")
    
    # Step 4: Read Records.csv and map contributions
    st.info("Step 4: Reading records and mapping contributions...")
    records_path = "data/Records.csv"
    
    if not os.path.exists(records_path):
        st.error(f"Records file not found: {records_path}")
        return None
    
    try:
        df_records = pd.read_csv(records_path)
        st.success(f"✅ Loaded {len(df_records)} records")
    except Exception as e:
        st.error(f"Error reading records: {e}")
        return None
    
    # Calculate contributions by user_id
    df_records['media_type'] = df_records['media_type'].str.lower()
    
    # Group by user_id and count contributions by media type
    contributions = df_records.groupby('user_id').agg({
        'title': 'count',  # total contributions
        'media_type': list
    }).rename(columns={'title': 'total_contributions'})
    
    # Count each media type
    def count_media_types(media_list):
        counts = {'image': 0, 'video': 0, 'audio': 0, 'text': 0}
        for media in media_list:
            if media in counts:
                counts[media] += 1
        return counts
    
    # Apply media type counting
    contribution_details = []
    for user_id, row in contributions.iterrows():
        media_counts = count_media_types(row['media_type'])
        contribution_details.append({
            'user_id': user_id,
            'total contributions': row['total_contributions'],
            'image': media_counts['image'],
            'video': media_counts['video'],
            'audio': media_counts['audio'],
            'text': media_counts['text']
        })
    
    df_contributions = pd.DataFrame(contribution_details)
    
    # Step 5: Final mapping - merge students with their contributions
    st.info("Step 5: Creating final contribution data...")
    
    # Merge mapped students with contributions
    df_final = df_mapped.merge(
        df_contributions,
        left_on='user id',
        right_on='user_id',
        how='left'
    )
    
    # Fill missing contribution data with zeros
    contribution_columns = ['total contributions', 'image', 'video', 'audio', 'text']
    for col in contribution_columns:
        df_final[col] = df_final[col].fillna(0).astype(int)
    
    # Select and reorder final columns as specified
    final_columns = ['Name', 'Phone no', 'Registration status', 'user id', 
                    'total contributions', 'image', 'audio', 'video', 'text', 
                    'College', 'Email', 'CreatedAt']
    
    df_final = df_final[final_columns]
    
    # Save to contribution_data.csv
    output_path = "data/contributions_data.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_final.to_csv(output_path, index=False)
    
    st.success(f"✅ Generated contribution_data.csv with {len(df_final)} records")
    return df_final

def display_college_overview(fetch_all_users, fetch_user_contributions_param, token: str):
    st.title("🏫 College Overview Dashboard")
    
    if not token:
        st.warning("🔐 You must be logged in to access this section.")
        return
    
    contributions_data_path = "data/contributions_data.csv"
    
    # Check if contributions_data.csv exists
    if not os.path.exists(contributions_data_path):
        st.info("🔄 Contributions data not found. Generating from scratch...")
        
        with st.spinner("Generating contribution data..."):
            df_final = generate_contribution_data(token)
            if df_final is None:
                return
    else:
        st.info("📊 Loading existing contributions data...")
        try:
            df_final = pd.read_csv(contributions_data_path)
        except Exception as e:
            st.error(f"Error loading contributions data: {e}")
            return
    
    # AG Grid 1: College-wise Summary
    st.markdown("### 📊 AG Grid 1: College-wise Summary")
    
    # Calculate college-wise statistics
    college_stats = df_final.groupby('College').agg({
        'Name': 'count',  # Total students
        'Registration status': lambda x: (x == 'Y').sum()  # Registered users
    }).rename(columns={
        'Name': 'No of Students',
        'Registration status': 'No of Registered Users'
    })
    
    college_stats['No of Unregistered Users'] = college_stats['No of Students'] - college_stats['No of Registered Users']
    college_stats = college_stats.reset_index()
    college_stats.rename(columns={'College': 'Total Colleges'}, inplace=True)
    
    # Configure AG Grid for college summary
    gb1 = GridOptionsBuilder.from_dataframe(college_stats)
    gb1.configure_pagination(paginationAutoPageSize=True)
    gb1.configure_side_bar()
    gb1.configure_default_column(sortable=True, filter=True, resizable=True)
    gb1.configure_selection(selection_mode="single", use_checkbox=False)
    
    grid_options1 = gb1.build()
    
    # Display AG Grid 1
    grid_response1 = AgGrid(
        college_stats,
        gridOptions=grid_options1,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=400,
        width='100%'
    )
    
    # AG Grid 2: Student Details for Selected College
    st.markdown("### 📋 AG Grid 2: Student Details")
    
    # Get selected college
    selected_college = None
    if (grid_response1['selected_rows'] is not None and 
        not grid_response1['selected_rows'].empty):
        # Convert DataFrame to dict and get the first row
        selected_row = grid_response1['selected_rows'].iloc[0].to_dict()
        selected_college = selected_row['Total Colleges']
        st.info(f"📍 Showing details for: **{selected_college}**")
    else:
        st.info("👆 Please select a college from the table above to view student details")
        return
    
    # Filter data for selected college
    filtered_df = df_final[df_final['College'] == selected_college].copy()
    
    # Prepare data for AG Grid 2
    student_details = filtered_df[[
        'Name', 'Registration status', 'total contributions', 
        'image', 'video', 'audio', 'text'
    ]].copy()
    
    student_details.rename(columns={
        'Registration status': 'Status of App Registration (Y/N)',
        'total contributions': 'Total No of Contributions',
        'image': 'Image',
        'video': 'Video',
        'audio': 'Audio',
        'text': 'Text'
    }, inplace=True)
    
    # Configure AG Grid for student details
    gb2 = GridOptionsBuilder.from_dataframe(student_details)
    gb2.configure_pagination(paginationAutoPageSize=True)
    gb2.configure_side_bar()
    gb2.configure_default_column(sortable=True, filter=True, resizable=True)
    
    # Configure specific columns
    gb2.configure_column("Name", pinned="left", width=200)
    gb2.configure_column("Total No of Contributions", type=["numericColumn"], width=180)
    gb2.configure_column("Image", type=["numericColumn"], width=100)
    gb2.configure_column("Video", type=["numericColumn"], width=100)
    gb2.configure_column("Audio", type=["numericColumn"], width=100)
    gb2.configure_column("Text", type=["numericColumn"], width=100)
    
    grid_options2 = gb2.build()
    
    # Display AG Grid 2
    grid_response2 = AgGrid(
        student_details,
        gridOptions=grid_options2,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=600,
        width='100%'
    )
    
    # Export options
    st.markdown("### 📥 Export Data")
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = student_details.to_csv(index=False)
        st.download_button(
            label="📄 Download Student Details as CSV",
            data=csv_data,
            file_name=f"{selected_college.replace(' ', '_')}_student_details.csv",
            mime="text/csv"
        )
    
    with col2:
        if st.button("🔄 Regenerate Contributions Data"):
            if os.path.exists(contributions_data_path):
                os.remove(contributions_data_path)
                st.success("Contributions data cleared. Please refresh the page to regenerate.")
                st.experimental_rerun()
