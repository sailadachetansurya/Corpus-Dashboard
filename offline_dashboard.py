import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("Current working directory:", os.getcwd())
print("Files in directory:", os.listdir('.'))

# Set page configuration
try:
    bits_data = pd.read_csv('user_summary_report_BITS.csv')
    print("BITS data shape:", bits_data.shape)
    print("BITS columns:", bits_data.columns.tolist())
except Exception as e:
    print("Error reading BITS file:", e)
    
st.set_page_config(
    page_title="User Summary Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin: 1rem 0;
    }
    .sidebar-metric {
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        border-left: 3px solid #1f77b4;
    }
    .filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid #e1e5e9;
    }
</style>
""", unsafe_allow_html=True)

# Load data function
@st.cache_data
def load_data():
    # Read CSV files from the 'data' folder
    bits_data = pd.read_csv('user_summary_report_BITS.csv')
    icfai_data = pd.read_csv('user_summary_report_ICFAI.csv')
    
    # Clean the data
    bits_data = bits_data.dropna(subset=['name'])
    icfai_data = icfai_data.dropna(subset=['name'])
    
    # Add institution column
    bits_data['institution'] = 'BITS'
    icfai_data['institution'] = 'ICFAI'
    
    # Add calculated fields for better analysis
    for df in [bits_data, icfai_data]:
        df['has_multimedia'] = (df['image'] > 0) | (df['audio'] > 0) | (df['video'] > 0)
        df['content_diversity'] = (df[['image', 'audio', 'video', 'text']] > 0).sum(axis=1)
        df['multimedia_ratio'] = (df['image'] + df['audio'] + df['video']) / df['total_records']
        df['multimedia_ratio'] = df['multimedia_ratio'].fillna(0)
    
    return bits_data, icfai_data

# Function to calculate percentile ranges
def get_percentile_range(data, column, percentile):
    return data[column].quantile(percentile)

# Function to categorize users
def categorize_user_activity(row):
    if row['total_records'] == 0:
        return 'Inactive'
    elif row['total_records'] <= 5:
        return 'Low Activity'
    elif row['total_records'] <= 20:
        return 'Medium Activity'
    elif row['total_records'] <= 50:
        return 'High Activity'
    else:
        return 'Very High Activity'

# Function to categorize content preference
def get_content_preference(row):
    content_types = ['image', 'audio', 'video', 'text']
    max_content = max(row[content_types])
    if max_content == 0:
        return 'No Content'
    return content_types[np.argmax(row[content_types])]

# Main dashboard function
def main():
    st.markdown('<h1 class="main-header">📊 Enhanced User Summary Dashboard</h1>', unsafe_allow_html=True)
    
    # Load data
    try:
        bits_data, icfai_data = load_data()
        combined_data = pd.concat([bits_data, icfai_data], ignore_index=True)
        
        # Add derived columns
        combined_data['activity_category'] = combined_data.apply(categorize_user_activity, axis=1)
        combined_data['content_preference'] = combined_data.apply(get_content_preference, axis=1)
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.error("Please ensure the CSV files are in the same directory as this script.")
        return
    
    # Enhanced Sidebar with comprehensive filters and statistics
    st.sidebar.markdown("## 🔍 Advanced Filters & Statistics")
    
    # ===== FILTER SECTION =====
    with st.sidebar.expander("🏫 Institution & Basic Filters", expanded=True):
        # Institution filter
        institution_filter = st.multiselect(
            "Select Institution(s)",
            options=["BITS", "ICFAI"],
            default=["BITS", "ICFAI"],
            help="Filter users by their institution"
        )
        
        # Activity level filter
        activity_levels = st.selectbox(
            "Activity Level",
            options=["All Users", "Active Users (>0 records)", "Inactive Users (0 records)", 
                    "High Activity (>20 records)", "Medium Activity (5-20 records)", 
                    "Low Activity (1-5 records)"],
            help="Filter users based on their activity level"
        )
    
    # Advanced Content Filters
    with st.sidebar.expander("📋 Content Type Filters", expanded=False):
        # Content type preference filter
        content_preference_filter = st.multiselect(
            "Content Preference",
            options=["image", "audio", "video", "text", "No Content"],
            default=["image", "audio", "video", "text", "No Content"],
            help="Filter by user's primary content type"
        )
        
        # Multimedia users filter
        multimedia_filter = st.radio(
            "Multimedia Usage",
            options=["All Users", "Multimedia Users Only", "Text-Only Users", "Mixed Content Users"],
            help="Filter based on multimedia content usage"
        )
        
        # Content diversity filter
        diversity_min, diversity_max = st.slider(
            "Content Diversity Range",
            min_value=0, max_value=4, value=(0, 4),
            help="Filter by number of different content types used (0-4)"
        )
    
    # Advanced Numeric Filters
    with st.sidebar.expander("🔢 Numeric Range Filters", expanded=False):
        # Total records range
        if len(combined_data) > 0:
            max_records = int(combined_data['total_records'].max())
            min_records = int(combined_data['total_records'].min())
            
            records_range = st.slider(
                "Total Records Range",
                min_value=min_records, max_value=max_records,
                value=(min_records, max_records),
                help="Filter users by total number of records"
            )
            
            # Multimedia ratio filter
            multimedia_ratio_range = st.slider(
                "Multimedia Ratio",
                min_value=0.0, max_value=1.0, value=(0.0, 1.0),
                step=0.1,
                help="Filter by ratio of multimedia content (0 = text only, 1 = multimedia only)"
            )
        else:
            records_range = (0, 0)
            multimedia_ratio_range = (0.0, 1.0)
    
    # Filter data based on selections
    filtered_data = combined_data.copy()
    
    # Apply filters
    if institution_filter:
        filtered_data = filtered_data[filtered_data['institution'].isin(institution_filter)]
    
    if activity_levels == "Active Users (>0 records)":
        filtered_data = filtered_data[filtered_data['total_records'] > 0]
    elif activity_levels == "Inactive Users (0 records)":
        filtered_data = filtered_data[filtered_data['total_records'] == 0]
    elif activity_levels == "High Activity (>20 records)":
        filtered_data = filtered_data[filtered_data['total_records'] > 20]
    elif activity_levels == "Medium Activity (5-20 records)":
        filtered_data = filtered_data[(filtered_data['total_records'] >= 5) & (filtered_data['total_records'] <= 20)]
    elif activity_levels == "Low Activity (1-5 records)":
        filtered_data = filtered_data[(filtered_data['total_records'] >= 1) & (filtered_data['total_records'] <= 5)]
    
    if content_preference_filter:
        filtered_data = filtered_data[filtered_data['content_preference'].isin(content_preference_filter)]
    
    if multimedia_filter == "Multimedia Users Only":
        filtered_data = filtered_data[filtered_data['has_multimedia'] == True]
    elif multimedia_filter == "Text-Only Users":
        filtered_data = filtered_data[(filtered_data['text'] > 0) & (filtered_data['has_multimedia'] == False)]
    elif multimedia_filter == "Mixed Content Users":
        filtered_data = filtered_data[(filtered_data['text'] > 0) & (filtered_data['has_multimedia'] == True)]
    
    # Apply numeric filters
    filtered_data = filtered_data[
        (filtered_data['total_records'] >= records_range[0]) & 
        (filtered_data['total_records'] <= records_range[1])
    ]
    
    filtered_data = filtered_data[
        (filtered_data['multimedia_ratio'] >= multimedia_ratio_range[0]) & 
        (filtered_data['multimedia_ratio'] <= multimedia_ratio_range[1])
    ]
    
    filtered_data = filtered_data[
        (filtered_data['content_diversity'] >= diversity_min) & 
        (filtered_data['content_diversity'] <= diversity_max)
    ]
    
    # Statistical Analysis Section
    with st.sidebar.expander("📊 Quick Statistics", expanded=True):
        # Display statistics
        if len(filtered_data) > 0:
            st.markdown('<div class="sidebar-metric">', unsafe_allow_html=True)
            st.metric("📊 Filtered Users", len(filtered_data))
            st.metric("📈 Active Users", len(filtered_data[filtered_data['total_records'] > 0]))
            st.metric("📝 Total Records", f"{filtered_data['total_records'].sum():,}")
            st.metric("📊 Avg Records/User", f"{filtered_data['total_records'].mean():.1f}")
            st.metric("🏆 Top User Records", f"{filtered_data['total_records'].max()}")
            st.metric("🎯 Median Records", f"{filtered_data['total_records'].median():.1f}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No users match the selected filters")
    
    # Advanced Statistics Section
    with st.sidebar.expander("📈 Advanced Statistics", expanded=False):
        if len(filtered_data) > 0:
            # Percentile analysis
            st.markdown("**Activity Percentiles:**")
            for percentile in [25, 50, 75, 90, 95]:
                value = filtered_data['total_records'].quantile(percentile/100)
                st.write(f"• {percentile}th percentile: {value:.1f}")
            
            # Content type distribution
            st.markdown("**Content Distribution:**")
            content_cols = ['image', 'audio', 'video', 'text']
            for col in content_cols:
                total = filtered_data[col].sum()
                pct = (total / filtered_data['total_records'].sum() * 100) if filtered_data['total_records'].sum() > 0 else 0
                st.write(f"• {col.capitalize()}: {total:,} ({pct:.1f}%)")
            
            # Diversity analysis
            st.markdown("**Content Diversity:**")
            diversity_stats = filtered_data['content_diversity'].value_counts().sort_index()
            for diversity, count in diversity_stats.items():
                pct = (count / len(filtered_data) * 100)
                st.write(f"• {diversity} types: {count} users ({pct:.1f}%)")
    
    # Data Export Section
    with st.sidebar.expander("📥 Export Options", expanded=False):
        export_format = st.selectbox("Export Format", ["CSV", "Excel", "JSON"])
        
        if st.button("📥 Export Filtered Data"):
            if export_format == "CSV":
                csv = filtered_data.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f'filtered_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                    mime='text/csv'
                )
            elif export_format == "Excel":
                # Create Excel file with multiple sheets
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    filtered_data.to_excel(writer, sheet_name='Filtered Data', index=False)
                    # Add summary sheet
                    summary_data = filtered_data.groupby('institution').agg({
                        'total_records': ['count', 'sum', 'mean'],
                        'image': 'sum',
                        'audio': 'sum',
                        'video': 'sum',
                        'text': 'sum'
                    }).round(2)
                    summary_data.to_excel(writer, sheet_name='Summary')
                
                st.download_button(
                    label="Download Excel",
                    data=output.getvalue(),
                    file_name=f'filtered_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
    
    # Filter Summary
    with st.sidebar.expander("🔍 Applied Filters Summary", expanded=False):
        st.write("**Currently Applied Filters:**")
        st.write(f"• Institutions: {', '.join(institution_filter) if institution_filter else 'None'}")
        st.write(f"• Activity Level: {activity_levels}")
        st.write(f"• Content Types: {', '.join(content_preference_filter) if content_preference_filter else 'None'}")
        st.write(f"• Multimedia Filter: {multimedia_filter}")
        st.write(f"• Records Range: {records_range[0]} - {records_range[1]}")
        st.write(f"• Diversity Range: {diversity_min} - {diversity_max}")
        st.write(f"• Multimedia Ratio: {multimedia_ratio_range[0]:.1f} - {multimedia_ratio_range[1]:.1f}")
        
        if st.button("🔄 Reset All Filters"):
            st.rerun()
    
    # Check if we have filtered data
    if len(filtered_data) == 0:
        st.error("No users match the selected filters. Please adjust your filter criteria.")
        return
    
    # Main dashboard layout with enhanced metrics
    st.markdown("## 📊 Dashboard Overview")
    
    # Enhanced metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="Total Users",
            value=len(filtered_data),
            delta=f"{len(filtered_data)/len(combined_data)*100:.1f}% of total"
        )
    
    with col2:
        active_users = len(filtered_data[filtered_data['total_records'] > 0])
        st.metric(
            label="Active Users",
            value=active_users,
            delta=f"{active_users/len(filtered_data)*100:.1f}% of filtered" if len(filtered_data) > 0 else "0%"
        )
    
    with col3:
        total_records = filtered_data['total_records'].sum()
        st.metric(
            label="Total Records",
            value=f"{total_records:,}",
            delta=f"Avg: {total_records/len(filtered_data):.1f} per user" if len(filtered_data) > 0 else "0"
        )
    
    with col4:
        if len(filtered_data) > 0:
            top_user_records = filtered_data['total_records'].max()
            st.metric(
                label="Most Active User",
                value=f"{top_user_records} records",
                delta=filtered_data.loc[filtered_data['total_records'].idxmax(), 'name']
            )
        else:
            st.metric(label="Most Active User", value="0 records", delta="No data")
    
    with col5:
        if len(filtered_data) > 0:
            avg_diversity = filtered_data['content_diversity'].mean()
            st.metric(
                label="Avg Content Diversity",
                value=f"{avg_diversity:.1f}/4",
                delta=f"Median: {filtered_data['content_diversity'].median():.1f}"
            )
        else:
            st.metric(label="Avg Content Diversity", value="0/4", delta="No data")
    
    # Create enhanced tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Enhanced Overview", 
        "🏫 Institution Analysis", 
        "📊 Content Analysis", 
        "🎯 Advanced Analytics",
        "👥 User Rankings", 
        "📋 Data Table"
    ])
    
    with tab1:
        st.markdown('<h2 class="section-header">📈 Enhanced Overview Statistics</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Enhanced activity distribution with percentiles
            fig_activity = px.histogram(
                filtered_data, 
                x='total_records', 
                title='Distribution of User Activity with Percentiles',
                labels={'total_records': 'Number of Records', 'count': 'Number of Users'},
                color_discrete_sequence=['#1f77b4']
            )
            
            # Add percentile lines
            for percentile, color in [(25, 'red'), (50, 'green'), (75, 'orange'), (90, 'purple')]:
                value = filtered_data['total_records'].quantile(percentile/100)
                fig_activity.add_vline(x=value, line_dash="dash", line_color=color, 
                                     annotation_text=f"{percentile}th percentile: {value:.1f}")
            
            fig_activity.update_layout(height=400)
            st.plotly_chart(fig_activity, use_container_width=True)
        
        with col2:
            # Enhanced institution analysis
            institution_stats = filtered_data.groupby('institution').agg({
                'total_records': ['count', 'sum', 'mean'],
                'content_diversity': 'mean',
                'multimedia_ratio': 'mean'
            }).round(2)
            
            fig_inst_comparison = px.bar(
                x=institution_stats.index,
                y=institution_stats[('total_records', 'mean')],
                title='Average Activity by Institution',
                labels={'x': 'Institution', 'y': 'Average Records per User'},
                color=institution_stats.index,
                color_discrete_sequence=['#1f77b4', '#ff7f0e']
            )
            fig_inst_comparison.update_layout(height=400)
            st.plotly_chart(fig_inst_comparison, use_container_width=True)
        
        # Activity categories pie chart
        col1, col2 = st.columns(2)
        
        with col1:
            activity_dist = filtered_data['activity_category'].value_counts()
            fig_activity_pie = px.pie(
                values=activity_dist.values,
                names=activity_dist.index,
                title='User Activity Distribution',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_activity_pie, use_container_width=True)
        
        with col2:
            content_preference_dist = filtered_data['content_preference'].value_counts()
            fig_content_pie = px.pie(
                values=content_preference_dist.values,
                names=content_preference_dist.index,
                title='Content Preference Distribution',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig_content_pie, use_container_width=True)
    
    with tab2:
        st.markdown('<h2 class="section-header">🏫 Institution Analysis</h2>', unsafe_allow_html=True)
        
        # Institution comparison table
        institution_comparison = filtered_data.groupby('institution').agg({
            'name': 'count',
            'total_records': ['sum', 'mean', 'median'],
            'image': 'sum',
            'audio': 'sum',
            'video': 'sum',
            'text': 'sum',
            'content_diversity': 'mean',
            'multimedia_ratio': 'mean'
        }).round(2)
        
        st.subheader("Institution Comparison Table")
        st.dataframe(institution_comparison)
        
        # Side by side comparison charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Content type distribution by institution
            content_by_institution = filtered_data.groupby('institution')[['image', 'audio', 'video', 'text']].sum()
            fig_content_by_inst = px.bar(
                content_by_institution.T,
                title='Content Distribution by Institution',
                labels={'index': 'Content Type', 'value': 'Total Records'},
                barmode='group'
            )
            st.plotly_chart(fig_content_by_inst, use_container_width=True)
        
        with col2:
            # User activity distribution by institution
            fig_activity_by_inst = px.box(
                filtered_data,
                x='institution',
                y='total_records',
                title='Activity Distribution by Institution',
                labels={'total_records': 'Number of Records', 'institution': 'Institution'}
            )
            st.plotly_chart(fig_activity_by_inst, use_container_width=True)
    
    with tab3:
        st.markdown('<h2 class="section-header">📊 Content Analysis</h2>', unsafe_allow_html=True)
        
        # Content type analysis
        content_cols = ['image', 'audio', 'video', 'text']
        content_totals = filtered_data[content_cols].sum()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Content type distribution
            fig_content_dist = px.bar(
                x=content_totals.index,
                y=content_totals.values,
                title='Total Content Distribution',
                labels={'x': 'Content Type', 'y': 'Total Records'},
                color=content_totals.index,
                color_discrete_sequence=px.colors.qualitative.Set1
            )
            st.plotly_chart(fig_content_dist, use_container_width=True)
        
        with col2:
            # Content diversity analysis
            diversity_dist = filtered_data['content_diversity'].value_counts().sort_index()
            fig_diversity = px.bar(
                x=diversity_dist.index,
                y=diversity_dist.values,
                title='Content Diversity Distribution',
                labels={'x': 'Number of Content Types Used', 'y': 'Number of Users'},
                color_discrete_sequence=['#ff7f0e']
            )
            st.plotly_chart(fig_diversity, use_container_width=True)
        
        # Content type correlation analysis
        st.subheader("Content Type Correlation Analysis")
        correlation_matrix = filtered_data[content_cols].corr()
        fig_corr = px.imshow(
            correlation_matrix,
            title='Content Type Correlation Matrix',
            color_continuous_scale='RdBu',
            aspect="auto"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    
    with tab4:
        st.markdown('<h2 class="section-header">🎯 Advanced Analytics</h2>', unsafe_allow_html=True)
        
        # Advanced analytics and insights
        col1, col2 = st.columns(2)
        
        with col1:
            # Multimedia vs text-only users
            multimedia_comparison = pd.DataFrame({
                'User Type': ['Multimedia Users', 'Text-Only Users'],
                'Count': [
                    len(filtered_data[filtered_data['has_multimedia'] == True]),
                    len(filtered_data[filtered_data['has_multimedia'] == False])
                ]
            })
            
            fig_multimedia = px.bar(
                multimedia_comparison,
                x='User Type',
                y='Count',
                title='Multimedia vs Text-Only Users',
                color='User Type',
                color_discrete_sequence=['#1f77b4', '#ff7f0e']
            )
            st.plotly_chart(fig_multimedia, use_container_width=True)
        
        with col2:
            # User activity over time (if timestamp available)
            # For now, we'll show activity distribution by content type preference
            activity_by_preference = filtered_data.groupby('content_preference')['total_records'].mean().sort_values(ascending=False)
            
            fig_activity_by_pref = px.bar(
                x=activity_by_preference.index,
                y=activity_by_preference.values,
                title='Average Activity by Content Preference',
                labels={'x': 'Content Preference', 'y': 'Average Records'},
                color=activity_by_preference.index,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_activity_by_pref, use_container_width=True)
        
        # Scatter plot analysis
        st.subheader("Relationship Analysis")
        fig_scatter = px.scatter(
            filtered_data,
            x='total_records',
            y='content_diversity',
            color='institution',
            size='multimedia_ratio',
            hover_data=['name'],
            title='User Activity vs Content Diversity',
            labels={'total_records': 'Total Records', 'content_diversity': 'Content Diversity'}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with tab5:
        st.markdown('<h2 class="section-header">👥 User Rankings</h2>', unsafe_allow_html=True)
        
        # Top user rankings
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 10 Most Active Users")
            top_users = filtered_data.nlargest(10, 'total_records')[['name', 'institution', 'total_records', 'content_diversity']]
            for i, (idx, row) in enumerate(top_users.iterrows(), 1):
                st.write(f"{i}. **{row['name']}** ({row['institution']}) - {row['total_records']} records")
        
        with col2:
            st.subheader("Most Diverse Content Users")
            diverse_users = filtered_data.nlargest(10, 'content_diversity')[['name', 'institution', 'content_diversity', 'total_records']]
            for i, (idx, row) in enumerate(diverse_users.iterrows(), 1):
                st.write(f"{i}. **{row['name']}** ({row['institution']}) - {row['content_diversity']} types")
        
        # Leaderboard table
        st.subheader("Complete User Leaderboard")
        leaderboard = filtered_data.sort_values('total_records', ascending=False)[
            ['name', 'institution', 'total_records', 'image', 'audio', 'video', 'text', 'content_diversity', 'multimedia_ratio']
        ].reset_index(drop=True)
        leaderboard.index = leaderboard.index + 1
        st.dataframe(leaderboard, use_container_width=True)
    
    with tab6:
        st.markdown('<h2 class="section-header">📋 Data Table</h2>', unsafe_allow_html=True)
        
        # Search and filter functionality
        search_term = st.text_input("Search users by name:", "")
        if search_term:
            filtered_data = filtered_data[filtered_data['name'].str.contains(search_term, case=False, na=False)]
        
        # Sort options
        sort_by = st.selectbox(
            "Sort by:",
            options=['name', 'total_records', 'content_diversity', 'multimedia_ratio'],
            index=1
        )
        
        sort_order = st.radio("Sort order:", ["Descending", "Ascending"])
        ascending = sort_order == "Ascending"
        
        # Display filtered and sorted data
        sorted_data = filtered_data.sort_values(sort_by, ascending=ascending)
        
        st.subheader(f"Filtered Data ({len(sorted_data)} users)")
        st.dataframe(sorted_data, use_container_width=True)
        
        # Export option
        if st.button("Export Current View as CSV"):
            csv = sorted_data.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f'filtered_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv'
            )
    
    # Footer with additional information
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9em;">
    Enhanced Dashboard v2.0 | Data Analysis Tool for User Summary Reports<br>
    📊 Analyzing user activity patterns across BITS and ICFAI institutions<br>
    🔍 Advanced filtering and analytics capabilities<br>
    📈 Real-time statistics and interactive visualizations<br>
    </div>
    """, unsafe_allow_html=True)
    
    # Additional insights in expander
    with st.expander("📊 Data Insights & Recommendations"):
        st.markdown("""
        ### Key Insights:
        - **User Engagement**: Monitor active vs inactive users to improve engagement strategies
        - **Content Preferences**: Understand which content types drive user activity
        - **Institution Comparison**: Compare performance metrics between institutions
        - **Multimedia Impact**: Analyze how multimedia content affects user engagement
        
        ### Recommendations:
        - Focus on increasing content diversity for better user engagement
        - Encourage multimedia content creation for higher activity levels
        - Implement targeted strategies for inactive users
        - Monitor content preferences to optimize platform features
        """)
    
    # Performance metrics
    with st.expander("⚡ Performance Metrics"):
        end_time = datetime.now()
        st.write(f"Dashboard loaded successfully at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"Total records processed: {len(combined_data):,}")
        st.write(f"Active filters: {len([f for f in [institution_filter, activity_levels, content_preference_filter] if f != 'All Users' and f])}")
        st.write(f"Data freshness: Real-time analysis")

if __name__ == "__main__":
    main()