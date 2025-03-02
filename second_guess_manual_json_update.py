import csv
import json

def add_csv_to_json(csv_filename, json_filename, pattern_key):
    # Read CSV file and convert each row to a dict with proper types
    rows = []
    with open(csv_filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            processed_row = {
                "Word": row["Word"],
                "Max": int(row["Max"]),
                "Expected": float(row["Expected"]),
                "Median": float(row["Median"]),
                "25th Perc": float(row["25th Perc"]),
                "75th Perc": float(row["75th Perc"])
            }
            rows.append(processed_row)
    
    # Load the existing JSON dictionary
    with open(json_filename, 'r') as jsonfile:
        data = json.load(jsonfile)
    
    # Add the new results under the given pattern key.
    # The new value is a list containing the list of row dictionaries,
    # matching the nested structure in the existing JSON.
    data[pattern_key] = [rows]
    
    # Write the updated dictionary back to the JSON file
    with open(json_filename, 'w') as jsonfile:
        json.dump(data, jsonfile, indent=2)

# Example usage:
# add_csv_to_json("full_analysis_xxxxx.csv", "pattern_analysis_results.json", "XXXXX")


def get_pattern_summary(json_filename, pattern_key, num_rows=3):
    # Load the existing JSON dictionary
    with open(json_filename, 'r') as jsonfile:
        data = json.load(jsonfile)
    
    # Check if the pattern_key exists in the dictionary
    if pattern_key not in data:
        print(f"Pattern '{pattern_key}' not found in the JSON data.")
        return None
    
    # The JSON structure is a list containing a single list of rows
    # We'll retrieve that inner list. If the structure is different, adjust accordingly.
    pattern_data = data[pattern_key]
    if not pattern_data or not isinstance(pattern_data, list):
        print(f"Data for pattern '{pattern_key}' is not in the expected format.")
        return None

    # Assuming the first element in the list holds our rows
    rows = pattern_data[0]
    row_count = len(rows)
    first_rows = rows[:num_rows]
    
    return first_rows, row_count

# Example usage:
summary, count = get_pattern_summary("pattern_analysis_results.json", "XXXXX", num_rows=5)
if summary is not None:
    print("First few rows:", summary)
    print("Total row count:", count)