#!/usr/bin/env python3
"""
Enhanced Script to find User IDs from names in CSV file with phone number fallback
Uses the existing dashboard API functions to match names with UIDs, with phone fallback
"""

import csv
import requests
import pandas as pd
import logging
import time
from typing import Dict, List, Optional
import sys
import os
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class EnhancedUserIDFinder:
    def __init__(self, token: str):
        """Initialize with authentication token"""
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        self.all_users = []
        self.user_mapping = {}

    def normalize_phone_number(self, phone: str) -> str:
        """Normalize phone number for consistent matching"""
        if not phone or pd.isna(phone):
            return ""

        # Convert to string and remove all non-digit characters
        phone_str = str(phone).strip()
        normalized = re.sub(r"[^\d]", "", phone_str)

        # Handle different phone number formats
        if len(normalized) == 10:
            # Assume it's an Indian number without country code
            return f"91{normalized}"
        elif len(normalized) == 12 and normalized.startswith("91"):
            # Already has country code
            return normalized
        elif len(normalized) == 13 and normalized.startswith("091"):
            # Remove leading 0
            return normalized[1:]

        return normalized

    def fetch_all_users(self) -> List[Dict]:
        """Fetch all users from the API with pagination"""
        if self.all_users:  # Return cached data if available
            return self.all_users

        print("🔄 Fetching all users from API...")
        all_users = []
        skip = 0
        limit = 1000
        page = 1

        try:
            while True:
                url = f"https://backend2.swecha.org/api/v1/users/?skip={skip}&limit={limit}"

                print(f"📄 Loading page {page}... ({len(all_users)} users loaded)")

                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                if not isinstance(data, list):
                    logger.warning(f"Expected list, got {type(data)} on page {page}")
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
                if page > 50:
                    logger.warning(f"Stopped at page {page} to prevent infinite loop")
                    break

                # Small delay to be respectful to the API
                time.sleep(0.1)

            print(f"✅ Successfully loaded {len(all_users)} total users!")
            self.all_users = all_users
            return all_users

        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            return []
        except requests.exceptions.ConnectionError:
            logger.error("Unable to connect to the server")
            return []
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

    def create_user_mapping(self) -> Dict[str, str]:
        """Create comprehensive mapping from user name and phone to user ID"""
        if self.user_mapping:  # Return cached mapping if available
            return self.user_mapping

        print("🗂️ Creating comprehensive user mapping (name + phone)...")
        users = self.fetch_all_users()

        if not users:
            logger.error("No users fetched, cannot create mapping")
            return {}

        # Create multiple mappings for flexible matching
        name_to_id = {}
        phone_to_id = {}

        for user in users:
            user_id = user.get("id", "")
            user_name = user.get("name", "").strip()
            user_phone = user.get("phone", "").strip()

            if user_id and user_name:
                # Store exact name match
                name_to_id[user_name.lower()] = user_id
                # Store name without spaces for fuzzy matching
                name_to_id[user_name.lower().replace(" ", "")] = user_id

            if user_id and user_phone:
                # Normalize phone number and store
                normalized_phone = self.normalize_phone_number(user_phone)
                if normalized_phone:
                    phone_to_id[normalized_phone] = user_id
                    # Also store original phone format
                    phone_to_id[user_phone] = user_id

        self.user_mapping = {
            "name_to_id": name_to_id,
            "phone_to_id": phone_to_id,
            "users": users,
        }

        print(
            f"✅ Created mapping for {len(name_to_id)} names and {len(phone_to_id)} phone numbers"
        )
        return self.user_mapping

    def find_user_by_name(self, search_name: str) -> Optional[Dict]:
        """Find user ID by name with fuzzy matching"""
        if not self.user_mapping:
            self.create_user_mapping()

        search_name = search_name.strip()
        if not search_name:
            return None

        name_to_id = self.user_mapping.get("name_to_id", {})
        users = self.user_mapping.get("users", [])

        # Try exact match first (case insensitive)
        exact_match = name_to_id.get(search_name.lower())
        if exact_match:
            # Find the full user details
            for user in users:
                if user.get("id") == exact_match:
                    return {
                        "user_id": exact_match,
                        "matched_name": user.get("name", ""),
                        "phone": user.get("phone", ""),
                        "match_type": "exact_name",
                    }

        # Try fuzzy match without spaces
        fuzzy_match = name_to_id.get(search_name.lower().replace(" ", ""))
        if fuzzy_match:
            for user in users:
                if user.get("id") == fuzzy_match:
                    return {
                        "user_id": fuzzy_match,
                        "matched_name": user.get("name", ""),
                        "phone": user.get("phone", ""),
                        "match_type": "fuzzy_name",
                    }

        # # Try partial matching
        # search_lower = search_name.lower()
        # for user in users:
        #     user_name = user.get("name", "").lower()
        #     if search_lower in user_name or user_name in search_lower:
        #         return {
        #             "user_id": user.get("id", ""),
        #             "matched_name": user.get("name", ""),
        #             "phone": user.get("phone", ""),
        #             "match_type": "partial_name",
        #         }

        return None

    def find_user_by_phone(self, search_phone: str) -> Optional[Dict]:
        """Find user ID by phone number with normalization"""
        if not self.user_mapping:
            self.create_user_mapping()

        search_phone = str(search_phone).strip()
        if not search_phone or search_phone.lower() in ["nan", "none", ""]:
            return None

        phone_to_id = self.user_mapping.get("phone_to_id", {})
        users = self.user_mapping.get("users", [])

        # Normalize the search phone
        normalized_search = self.normalize_phone_number(search_phone)

        # Try exact match with normalized phone
        if normalized_search and normalized_search in phone_to_id:
            user_id = phone_to_id[normalized_search]
            for user in users:
                if user.get("id") == user_id:
                    return {
                        "user_id": user_id,
                        "matched_name": user.get("name", ""),
                        "phone": user.get("phone", ""),
                        "match_type": "exact_phone",
                    }

        # Try original phone format
        if search_phone in phone_to_id:
            user_id = phone_to_id[search_phone]
            for user in users:
                if user.get("id") == user_id:
                    return {
                        "user_id": user_id,
                        "matched_name": user.get("name", ""),
                        "phone": user.get("phone", ""),
                        "match_type": "original_phone",
                    }

        return None

    def find_user_id(
        self, search_name: str, search_phone: str = None
    ) -> Optional[Dict]:
        """Find user ID by name first, then fallback to phone number"""
        # First try to find by name
        result = self.find_user_by_name(search_name)
        if result:
            return result

        # If name search failed and phone is provided, try phone search
        if search_phone:
            phone_result = self.find_user_by_phone(search_phone)
            if phone_result:
                return phone_result

        return None

    def process_csv_file(
        self,
        input_file: str,
        output_file: str,
        name_column: str = "name",
        phone_column: str = None,
    ):
        """Process CSV file and add user IDs with phone fallback"""
        try:
            # Read input CSV
            print(f"📖 Reading input file: {input_file}")
            df = pd.read_csv(input_file)

            # Validate columns
            missing_columns = []
            if name_column not in df.columns:
                missing_columns.append(name_column)
            if phone_column and phone_column not in df.columns:
                missing_columns.append(phone_column)

            if missing_columns:
                available_columns = ", ".join(df.columns.tolist())
                logger.error(
                    f"Columns {missing_columns} not found. Available columns: {available_columns}"
                )
                return False

            print(f"📊 Found {len(df)} rows to process")

            # Initialize new columns
            df["user_id"] = ""
            df["matched_name"] = ""
            df["matched_phone"] = ""
            df["match_type"] = ""
            df["match_status"] = ""

            # Process each row
            matched_count = 0
            name_matches = 0
            phone_matches = 0

            for index, row in df.iterrows():
                name = (
                    str(row[name_column]).strip() if pd.notna(row[name_column]) else ""
                )
                phone = (
                    str(row[phone_column]).strip()
                    if phone_column and pd.notna(row[phone_column])
                    else ""
                )

                if not name and not phone:
                    df.at[index, "match_status"] = "empty_data"
                    continue

                print(
                    f"🔍 Processing ({index + 1}/{len(df)}): Name='{name}', Phone='{phone}'"
                )

                # Find user ID with fallback
                result = self.find_user_id(name, phone if phone_column else None)

                if result:
                    df.at[index, "user_id"] = result["user_id"]
                    df.at[index, "matched_name"] = result["matched_name"]
                    df.at[index, "matched_phone"] = result["phone"]
                    df.at[index, "match_type"] = result["match_type"]
                    df.at[index, "match_status"] = "found"
                    matched_count += 1

                    # Track match type statistics
                    if "name" in result["match_type"]:
                        name_matches += 1
                        print(
                            f"  ✅ Found by name: {result['matched_name']} ({result['match_type']})"
                        )
                    elif "phone" in result["match_type"]:
                        phone_matches += 1
                        print(
                            f"  ✅ Found by phone: {result['matched_name']} ({result['match_type']})"
                        )
                else:
                    df.at[index, "match_status"] = "not_found"
                    print(f"  ❌ Not found: Name='{name}', Phone='{phone}'")

                # Small delay to be respectful
                time.sleep(0.05)

            # Save results
            print(f"💾 Saving results to: {output_file}")
            df.to_csv(output_file, index=False)

            # Print comprehensive summary
            print(f"\n📈 Processing Summary:")
            print(f"   Total rows processed: {len(df)}")
            print(f"   Successfully matched: {matched_count}")
            print(f"   Not found: {len(df) - matched_count}")
            print(f"   Success rate: {(matched_count / len(df) * 100):.1f}%")

            if phone_column:
                print(f"\n🎯 Match Method Breakdown:")
                print(f"   Matched by name: {name_matches}")
                print(f"   Matched by phone: {phone_matches}")
                if len(df) - name_matches > 0:
                    print(
                        f"   Phone fallback success rate: {(phone_matches / (len(df) - name_matches) * 100):.1f}%"
                    )

            # Show detailed match type breakdown
            match_types = df["match_type"].value_counts()
            if not match_types.empty:
                print(f"\n📊 Detailed Match Type Breakdown:")
                for match_type, count in match_types.items():
                    if match_type:  # Skip empty values
                        print(f"   {match_type}: {count}")

            return True

        except FileNotFoundError:
            logger.error(f"Input file not found: {input_file}")
            return False
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            return False


def main():
    """Main function for User ID finding only"""
    print("🚀 Enhanced User ID Finder Script with Phone Fallback")
    print("=" * 60)

    # Configuration - UPDATE THESE VALUES
    TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTIwNDAxODksInN1YiI6IjJiY2MxOGE3LTAzYTQtNDBlYS1hZTliLTIyMzYwN2YyMzlkZiJ9.SZd-7BXKhSr1T6_-4zpilkQzmhflQML1XbvS_AAML8E"
    INPUT_CSV = "data/ICFAI.csv"
    OUTPUT_CSV = "data/output_with_uids_ICFAI.csv"
    NAME_COLUMN = "FirstName"
    PHONE_COLUMN = "Phone Number"

    if not os.path.exists(INPUT_CSV):
        print(f"❌ Input file not found: {INPUT_CSV}")
        print("Please make sure the file exists and update the INPUT_CSV variable")
        return

    try:
        # Initialize enhanced finder
        finder = EnhancedUserIDFinder(TOKEN)
        
        # Process the CSV file
        success = finder.process_csv_file(INPUT_CSV, OUTPUT_CSV, NAME_COLUMN, PHONE_COLUMN)
        
        if success:
            print(f"\n🎉 Successfully completed! Results saved to: {OUTPUT_CSV}")
            print(f"📋 The output includes both name and phone number matching results")
            print(f"\n💡 To match with records, run: python records_matcher.py")
        else:
            print(f"\n❌ Processing failed. Check the logs above for details.")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")

if __name__ == "__main__":
    main()