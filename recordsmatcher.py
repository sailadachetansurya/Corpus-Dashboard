#!/usr/bin/env python3
"""
Enhanced Standalone Records Matcher Script with Detailed Debugging
Matches users CSV (with UIDs) with records CSV to create comprehensive dataset
No API calls required - pure CSV manipulation
"""

import pandas as pd
import logging
import os
import sys
from typing import Optional, Dict, List

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class EnhancedRecordsMatcher:
    def __init__(self):
        """Initialize the records matcher"""
        self.debug_info = {
            'users_processed': 0,
            'users_matched': 0,
            'users_not_matched': [],
            'duplicate_user_ids': [],
            'invalid_user_ids': [],
            'record_user_ids': set(),
            'user_user_ids': set()
        }
    
    def analyze_data_quality(self, users_df: pd.DataFrame, records_df: pd.DataFrame, 
                           user_id_column: str, record_user_id_column: str):
        """Analyze data quality and identify potential issues"""
        print("\n🔍 Data Quality Analysis:")
        print("=" * 50)
        
        # Analyze users data
        print(f"📊 Users Data Analysis:")
        print(f"   Total users: {len(users_df)}")
        
        # Check for missing user IDs
        missing_user_ids = users_df[user_id_column].isna().sum()
        empty_user_ids = (users_df[user_id_column] == "").sum()
        print(f"   Missing user IDs: {missing_user_ids}")
        print(f"   Empty user IDs: {empty_user_ids}")
        
        # Check for duplicate user IDs
        duplicate_user_ids = users_df[users_df[user_id_column].duplicated()][user_id_column].tolist()
        if duplicate_user_ids:
            print(f"   Duplicate user IDs found: {len(duplicate_user_ids)}")
            self.debug_info['duplicate_user_ids'] = duplicate_user_ids
        
        # Get unique user IDs
        valid_user_ids = users_df[users_df[user_id_column].notna() & (users_df[user_id_column] != "")][user_id_column].unique()
        self.debug_info['user_user_ids'] = set(valid_user_ids)
        print(f"   Valid unique user IDs: {len(valid_user_ids)}")
        
        # Analyze records data
        print(f"\n📊 Records Data Analysis:")
        print(f"   Total records: {len(records_df)}")
        
        # Check for missing record user IDs
        missing_record_user_ids = records_df[record_user_id_column].isna().sum()
        empty_record_user_ids = (records_df[record_user_id_column] == "").sum()
        print(f"   Missing record user IDs: {missing_record_user_ids}")
        print(f"   Empty record user IDs: {empty_record_user_ids}")
        
        # Get unique record user IDs
        valid_record_user_ids = records_df[records_df[record_user_id_column].notna() & (records_df[record_user_id_column] != "")][record_user_id_column].unique()
        self.debug_info['record_user_ids'] = set(valid_record_user_ids)
        print(f"   Valid unique record user IDs: {len(valid_record_user_ids)}")
        
        # Find overlap
        overlap = self.debug_info['user_user_ids'].intersection(self.debug_info['record_user_ids'])
        print(f"\n🔗 Overlap Analysis:")
        print(f"   User IDs that will match: {len(overlap)}")
        print(f"   User IDs with no records: {len(self.debug_info['user_user_ids'] - self.debug_info['record_user_ids'])}")
        print(f"   Record user IDs not in users: {len(self.debug_info['record_user_ids'] - self.debug_info['user_user_ids'])}")
        
        # Show sample user IDs for debugging
        print(f"\n🔍 Sample User IDs (first 10):")
        for i, uid in enumerate(list(valid_user_ids)[:10]):
            print(f"   {i+1}. {uid}")
        
        print(f"\n🔍 Sample Record User IDs (first 10):")
        for i, uid in enumerate(list(valid_record_user_ids)[:10]):
            print(f"   {i+1}. {uid}")

    def debug_individual_users_efficient(self, users_df: pd.DataFrame, records_df: pd.DataFrame, 
                                   user_id_column: str, record_user_id_column: str):
        """Debug all users efficiently with reduced output"""
        print("\n🔍 Processing All Users (Efficient Mode):")
        print("=" * 50)
        
        # Get valid users
        valid_users = users_df[users_df[user_id_column].notna() & (users_df[user_id_column] != "")]
        total_users = len(valid_users)
        
        print(f"Processing all {total_users} users...")
        
        # Process all users but only show detailed output for first 20 and last 10
        for index, user_row in valid_users.iterrows():
            user_id = user_row[user_id_column]
            user_name = user_row.get('matched_name', user_row.get('FirstName', user_row.get('name', 'Unknown')))
            
            self.debug_info['users_processed'] += 1
            
            # Check if this user has records
            user_records = records_df[records_df[record_user_id_column] == user_id]
            
            if len(user_records) > 0:
                self.debug_info['users_matched'] += 1
                # Show details only for first 20 and last 10 users
                if self.debug_info['users_processed'] <= 20 or self.debug_info['users_processed'] > total_users - 10:
                    print(f"✅ User {self.debug_info['users_processed']}/{total_users}: {user_name} ({user_id}) - {len(user_records)} records found")
            else:
                self.debug_info['users_not_matched'].append({
                    'name': user_name,
                    'user_id': user_id,
                    'index': index
                })
                # Show details only for first 20 and last 10 users
                if self.debug_info['users_processed'] <= 20 or self.debug_info['users_processed'] > total_users - 10:
                    print(f"❌ User {self.debug_info['users_processed']}/{total_users}: {user_name} ({user_id}) - No records found")
            
            # Show progress every 100 users
            if self.debug_info['users_processed'] % 100 == 0:
                matched_so_far = self.debug_info['users_matched']
                success_rate = (matched_so_far / self.debug_info['users_processed']) * 100
                print(f"📊 Progress: {self.debug_info['users_processed']}/{total_users} users processed | {matched_so_far} matched ({success_rate:.1f}%)")

    def debug_individual_users(self, users_df: pd.DataFrame, records_df: pd.DataFrame, 
                            user_id_column: str, record_user_id_column: str):
        """Debug each individual user to see why they match or don't match - ALL USERS"""
        print("\n🔍 Individual User Debugging (Processing ALL users):")
        print("=" * 50)
        
        # Get valid users
        valid_users = users_df[users_df[user_id_column].notna() & (users_df[user_id_column] != "")]
        total_users = len(valid_users)
        
        print(f"Processing all {total_users} users...")
        
        for index, user_row in valid_users.iterrows():
            user_id = user_row[user_id_column]
            user_name = user_row.get('matched_name', user_row.get('FirstName', user_row.get('name', 'Unknown')))
            
            self.debug_info['users_processed'] += 1
            
            # Check if this user has records
            user_records = records_df[records_df[record_user_id_column] == user_id]
            
            if len(user_records) > 0:
                self.debug_info['users_matched'] += 1
                # Only show details for verbose debugging (first 50 users)
                if self.debug_info['users_processed'] <= 50:
                    print(f"✅ User {self.debug_info['users_processed']}/{total_users}: {user_name} ({user_id}) - {len(user_records)} records found")
            else:
                self.debug_info['users_not_matched'].append({
                    'name': user_name,
                    'user_id': user_id,
                    'index': index
                })
                # Only show details for verbose debugging (first 50 users)
                if self.debug_info['users_processed'] <= 50:
                    print(f"❌ User {self.debug_info['users_processed']}/{total_users}: {user_name} ({user_id}) - No records found")
            
            # Show progress every 100 users
            if self.debug_info['users_processed'] % 100 == 0:
                matched_so_far = self.debug_info['users_matched']
                success_rate = (matched_so_far / self.debug_info['users_processed']) * 100
                print(f"📊 Progress: {self.debug_info['users_processed']}/{total_users} users processed | {matched_so_far} matched ({success_rate:.1f}%)")
        
        print(f"\n✅ Completed processing all {total_users} users!")

    def analyze_unmatched_users(self):
        """Provide detailed analysis of why users didn't match"""
        if not self.debug_info['users_not_matched']:
            print("\n✅ All users with valid IDs were matched!")
            return
        
        print(f"\n❌ Unmatched Users Analysis:")
        print("=" * 50)
        print(f"Total unmatched users: {len(self.debug_info['users_not_matched'])}")
        
        # Show first 20 unmatched users
        print(f"\n🔍 Unmatched Users (first 20):")
        for i, user in enumerate(self.debug_info['users_not_matched'][:20]):
            print(f"   {i+1}. {user['name']} | ID: {user['user_id']}")
        
        if len(self.debug_info['users_not_matched']) > 20:
            print(f"   ... and {len(self.debug_info['users_not_matched']) - 20} more")
        
        # Analyze user ID patterns
        unmatched_ids = [user['user_id'] for user in self.debug_info['users_not_matched']]
        
        print(f"\n🔍 User ID Pattern Analysis:")
        print(f"   Sample unmatched user IDs:")
        for i, uid in enumerate(unmatched_ids[:10]):
            print(f"     {i+1}. {uid} (length: {len(str(uid))}, type: {type(uid)})")
        
        # Check if these IDs exist in records with different formatting
        print(f"\n🔍 Checking for formatting issues...")
        sample_record_ids = list(self.debug_info['record_user_ids'])[:10]
        print(f"   Sample record user IDs:")
        for i, uid in enumerate(sample_record_ids):
            print(f"     {i+1}. {uid} (length: {len(str(uid))}, type: {type(uid)})")

    def create_user_summary_report(
        self,
        users_csv: str,
        records_csv: str,
        output_csv: str,
        user_id_column: str = "user_id",
        record_user_id_column: str = "user_id",
    ) -> bool:
        """
        Create a summary report with columns: name, user_id, total_records, image, audio, video, text
        Includes ALL users, even those with zero records
        """
        try:
            print("📊 Creating User Summary Report...")
            print("=" * 50)
            
            # Read both CSV files
            print(f"📖 Reading users file: {users_csv}")
            users_df = pd.read_csv(users_csv)
            
            print(f"📖 Reading records file: {records_csv}")
            records_df = pd.read_csv(records_csv)
            
            # Validate required columns
            if user_id_column not in users_df.columns:
                logger.error(f"Column '{user_id_column}' not found in users CSV")
                print(f"Available columns in users CSV: {list(users_df.columns)}")
                return False
            
            if record_user_id_column not in records_df.columns:
                logger.error(f"Column '{record_user_id_column}' not found in records CSV")
                print(f"Available columns in records CSV: {list(records_df.columns)}")
                return False
            
            # Get all users (including those without user IDs for completeness)
            all_users = users_df.copy()
            
            # Initialize the summary dataframe
            summary_data = []
            
            print(f"Processing {len(all_users)} users for summary report...")
            
            for index, user_row in all_users.iterrows():
                user_id = user_row.get(user_id_column, "")
                
               # Get user name from FirstName column in your list
                user_name = user_row.get('FirstName', 'Unknown')

                
                # Initialize counters
                total_records = 0
                image_count = 0
                audio_count = 0
                video_count = 0
                text_count = 0
                
                # If user has a valid ID, count their records
                if pd.notna(user_id) and user_id != "":
                    # Get all records for this user
                    user_records = records_df[records_df[record_user_id_column] == user_id]
                    total_records = len(user_records)
                    
                    if total_records > 0:
                        # Count by media type
                        media_counts = user_records['media_type'].value_counts()
                        
                        image_count = media_counts.get('image', 0)
                        audio_count = media_counts.get('audio', 0)
                        video_count = media_counts.get('video', 0)
                        text_count = media_counts.get('text', 0)
                
                # Add to summary data
                summary_data.append({
                    'name': user_name,
                    'user_id': user_id if pd.notna(user_id) else "",
                    'total_records': total_records,
                    'image': image_count,
                    'audio': audio_count,
                    'video': video_count,
                    'text': text_count
                })
                
                # Show progress every 100 users
                if (index + 1) % 100 == 0:
                    print(f"📊 Progress: {index + 1}/{len(all_users)} users processed...")
            
            # Create DataFrame
            summary_df = pd.DataFrame(summary_data)
            
            # Sort by total records (descending) then by name
            summary_df = summary_df.sort_values(['total_records', 'name'], ascending=[False, True])
            
            # Save the summary report
            print(f"💾 Saving summary report to: {output_csv}")
            summary_df.to_csv(output_csv, index=False)
            
            # Print summary statistics
            self._print_summary_statistics(summary_df)
            
            return True
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating summary report: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _print_summary_statistics(self, summary_df: pd.DataFrame):
        """Print statistics about the summary report"""
        print(f"\n📈 Summary Report Statistics:")
        print("=" * 50)
        
        total_users = len(summary_df)
        users_with_records = len(summary_df[summary_df['total_records'] > 0])
        users_without_records = total_users - users_with_records
        
        print(f"   Total users in report: {total_users}")
        print(f"   Users with records: {users_with_records}")
        print(f"   Users without records: {users_without_records}")
        print(f"   Success rate: {(users_with_records / total_users * 100):.1f}%")
        
        # Overall record statistics
        total_all_records = summary_df['total_records'].sum()
        total_images = summary_df['image'].sum()
        total_audio = summary_df['audio'].sum()
        total_video = summary_df['video'].sum()
        total_text = summary_df['text'].sum()
        
        print(f"\n📊 Overall Record Statistics:")
        print(f"   Total records: {total_all_records}")
        print(f"   Image records: {total_images}")
        print(f"   Audio records: {total_audio}")
        print(f"   Video records: {total_video}")
        print(f"   Text records: {total_text}")
        
        # Top contributors
        top_contributors = summary_df[summary_df['total_records'] > 0].head(10)
        if len(top_contributors) > 0:
            print(f"\n🏆 Top Contributors:")
            for index, row in top_contributors.iterrows():
                print(f"   {row['name']}: {row['total_records']} records (I:{row['image']}, A:{row['audio']}, V:{row['video']}, T:{row['text']})")
        
        # Media type distribution
        if total_all_records > 0:
            print(f"\n📊 Media Type Distribution:")
            print(f"   Images: {(total_images/total_all_records*100):.1f}%")
            print(f"   Audio: {(total_audio/total_all_records*100):.1f}%")
            print(f"   Video: {(total_video/total_all_records*100):.1f}%")
            print(f"   Text: {(total_text/total_all_records*100):.1f}%")

    def match_users_with_records(
        self,
        users_csv: str,
        records_csv: str,
        output_csv: str,
        user_id_column: str = "user_id",
        record_user_id_column: str = "user_id",
    ) -> bool:
        """
        Match users CSV (with UIDs) with records CSV with detailed debugging
        """
        try:
            print("🔗 Starting enhanced user-records matching process...")
            
            # Read both CSV files
            print(f"📖 Reading users file: {users_csv}")
            users_df = pd.read_csv(users_csv)
            
            print(f"📖 Reading records file: {records_csv}")
            records_df = pd.read_csv(records_csv)
            
            # Validate required columns
            if user_id_column not in users_df.columns:
                logger.error(f"Column '{user_id_column}' not found in users CSV")
                print(f"Available columns in users CSV: {list(users_df.columns)}")
                return False
            
            if record_user_id_column not in records_df.columns:
                logger.error(f"Column '{record_user_id_column}' not found in records CSV")
                print(f"Available columns in records CSV: {list(records_df.columns)}")
                return False
            
            # Analyze data quality
            self.analyze_data_quality(users_df, records_df, user_id_column, record_user_id_column)
            
            # Debug individual users
            self.debug_individual_users(users_df, records_df, user_id_column, record_user_id_column)
            
            print(f"\n📊 Basic Statistics:")
            print(f"   Users data: {len(users_df)} rows")
            print(f"   Records data: {len(records_df)} rows")
            
            # Filter users that have valid UIDs (not empty)
            valid_users = users_df[
                users_df[user_id_column].notna() & (users_df[user_id_column] != "")
            ]
            print(f"   Users with valid UIDs: {len(valid_users)}")
            
            # Filter records that have valid user IDs
            valid_records = records_df[
                records_df[record_user_id_column].notna()
                & (records_df[record_user_id_column] != "")
            ]
            print(f"   Records with valid user IDs: {len(valid_records)}")
            
            # Perform the merge
            print("\n🔄 Performing merge operation...")
            merged_df = pd.merge(
                valid_users,
                valid_records,
                left_on=user_id_column,
                right_on=record_user_id_column,
                how="inner",
                suffixes=("_user", "_record"),
            )
            
            print(f"✅ Successfully matched {len(merged_df)} user-record combinations")
            
            # Analyze unmatched users
            self.analyze_unmatched_users()
            
            if len(merged_df) == 0:
                print("\n❌ No matches found! This suggests a data formatting issue.")
                print("🔍 Troubleshooting suggestions:")
                print("   1. Check if user IDs in both files have the same format")
                print("   2. Look for extra spaces, different data types, or encoding issues")
                print("   3. Verify the column names are correct")
                return False
            
            # Add metadata columns
            merged_df["match_timestamp"] = pd.Timestamp.now()
            merged_df["total_records_per_user"] = merged_df.groupby(user_id_column)[
                user_id_column
            ].transform("count")
            
            # Sort by user information and then by record information
            sort_columns = [user_id_column]
            if "matched_name" in merged_df.columns:
                sort_columns.append("matched_name")
            if "id" in merged_df.columns:
                sort_columns.append("id")
            
            merged_df = merged_df.sort_values(sort_columns)
            
            # Save results
            print(f"\n💾 Saving matched results to: {output_csv}")
            merged_df.to_csv(output_csv, index=False)
            
            # Generate detailed statistics
            self._print_enhanced_statistics(merged_df, valid_users, user_id_column)
            
            return True
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Error matching users with records: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _print_enhanced_statistics(self, merged_df: pd.DataFrame, valid_users: pd.DataFrame, user_id_column: str):
        """Print enhanced statistics about the matching results"""
        print(f"\n📈 Enhanced Matching Summary:")
        print("=" * 50)
        print(f"   Total user-record matches: {len(merged_df)}")
        print(f"   Unique users with records: {merged_df[user_id_column].nunique()}")
        print(f"   Users without records: {len(valid_users) - merged_df[user_id_column].nunique()}")
        print(f"   Success rate: {(merged_df[user_id_column].nunique() / len(valid_users) * 100):.1f}%")
        
        # Show users with multiple records
        user_record_counts = merged_df[user_id_column].value_counts()
        multiple_records = user_record_counts[user_record_counts > 1]
        
        if len(multiple_records) > 0:
            print(f"\n📊 Users with Multiple Records:")
            print(f"   Users with multiple records: {len(multiple_records)}")
            print(f"   Max records per user: {multiple_records.max()}")
            print(f"   Average records per user: {user_record_counts.mean():.1f}")
            
            # Show top users with most records
            print(f"\n🏆 Top Users by Record Count:")
            top_users = multiple_records.head(10)
            for user_id, count in top_users.items():
                user_name = (
                    merged_df[merged_df[user_id_column] == user_id]["matched_name"].iloc[0]
                    if "matched_name" in merged_df.columns
                    else "Unknown"
                )
                print(f"   {user_name} ({user_id}): {count} records")
        
        # Show record type breakdown if available
        if "media_type" in merged_df.columns:
            print(f"\n📊 Record Type Breakdown:")
            media_counts = merged_df["media_type"].value_counts()
            for media_type, count in media_counts.items():
                print(f"   {media_type}: {count}")
        
        # Show category breakdown if available
        if "category" in merged_df.columns:
            print(f"\n📊 Category Breakdown:")
            category_counts = merged_df["category"].value_counts()
            for category, count in category_counts.head(10).items():
                print(f"   {category}: {count}")
        
        # Debug summary
        print(f"\n🔍 Debug Summary:")
        print(f"   Users processed: {self.debug_info['users_processed']}")
        print(f"   Users matched: {self.debug_info['users_matched']}")
        print(f"   Users not matched: {len(self.debug_info['users_not_matched'])}")

def main():
    """Main function for enhanced standalone records matching"""
    print("🔗 Enhanced Standalone Records Matcher with Debugging")
    print("=" * 60)
    
    # Configuration - UPDATE THESE VALUES
    USERS_CSV = "data/output_with_uids_BITS.csv"  # CSV with user IDs
    RECORDS_CSV = "data/records_20250708_061217.csv"          # CSV with records data
    OUTPUT_CSV = "data/users_with_records_BITS.csv"  # Final output
    SUMMARY_CSV = "data/user_summary_report_BITS.csv"  # Summary report output
    
    # Column configuration
    USER_ID_COLUMN = "user_id"        # Column name for user ID in users CSV
    RECORD_USER_ID_COLUMN = "user_id" # Column name for user ID in records CSV
    
    # Choose operation mode
    print("Choose operation mode:")
    print("1. Full detailed matching (original functionality)")
    print("2. Create summary report only (name, user_id, total_records, image, audio, video, text)")
    print("3. Both (detailed matching + summary report)")
    
    try:
        mode = input("Enter mode (1/2/3): ").strip()
        if not mode:
            mode = "2"  # Default to summary report
            print(f"No input provided, defaulting to mode {mode}")
    except (EOFError, KeyboardInterrupt):
        print("\nDefaulting to summary report mode...")
        mode = "2"
    
    # Validate input files
    if not os.path.exists(USERS_CSV):
        print(f"❌ Users file not found: {USERS_CSV}")
        print("Please ensure the file exists and update the USERS_CSV variable")
        return
    
    if not os.path.exists(RECORDS_CSV):
        print(f"❌ Records file not found: {RECORDS_CSV}")
        print("Please ensure the file exists and update the RECORDS_CSV variable")
        return
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(OUTPUT_CSV)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize enhanced matcher
        matcher = EnhancedRecordsMatcher()
        
        if mode in ["1", "3"]:
            # Perform detailed matching with debugging
            print(f"\n🔗 Step 1: Detailed Matching...")
            success = matcher.match_users_with_records(
                users_csv=USERS_CSV,
                records_csv=RECORDS_CSV,
                output_csv=OUTPUT_CSV,
                user_id_column=USER_ID_COLUMN,
                record_user_id_column=RECORD_USER_ID_COLUMN,
            )
            
            if success:
                print(f"✅ Detailed matching completed! Results saved to: {OUTPUT_CSV}")
            else:
                print(f"❌ Detailed matching failed.")
                if mode == "1":
                    return
        
        if mode in ["2", "3"]:
            # Create summary report
            print(f"\n📊 Step 2: Creating Summary Report...")
            success = matcher.create_user_summary_report(
                users_csv=USERS_CSV,
                records_csv=RECORDS_CSV,
                output_csv=SUMMARY_CSV,
                user_id_column=USER_ID_COLUMN,
                record_user_id_column=RECORD_USER_ID_COLUMN,
            )
            
            if success:
                print(f"✅ Summary report completed! Results saved to: {SUMMARY_CSV}")
            else:
                print(f"❌ Summary report failed.")
                return
        
        print(f"\n🎉 All operations completed successfully!")
        
        if mode == "1":
            print(f"📋 Detailed matching results: {OUTPUT_CSV}")
        elif mode == "2":
            print(f"📋 Summary report: {SUMMARY_CSV}")
        else:
            print(f"📋 Detailed matching results: {OUTPUT_CSV}")
            print(f"📋 Summary report: {SUMMARY_CSV}")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
