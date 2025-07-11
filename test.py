import csv
from collections import Counter

# CSV file path
csv_file_path = 'data/Cohort1.csv'

phone_numbers = []

with open(csv_file_path, mode='r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        phone = row.get('Affiliation (College/Company/Organization Name)')
        if phone:
            phone_numbers.append(phone)

# Count phone number frequencies
phone_counts = Counter(phone_numbers)

# Count how many phone numbers are unique (appear only once)
unique_count = sum(1 for phone in phone_counts if phone_counts[phone] == 1)

print(unique_count)
