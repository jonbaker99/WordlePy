import json

def format_expected_field(json_file_path="pattern_analysis_results.json", output_path=None):
    """
    Loads the JSON file, formats the 'Expected' field to 1 decimal place,
    and saves it back to the same or a new file.
    
    Args:
        json_file_path (str): Path to the JSON file to format
        output_path (str, optional): Path to save the formatted JSON. 
                                      If None, overwrites the original file.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load the JSON data
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        # Process each pattern
        for pattern, pattern_data in data.items():
            # Check if pattern_data is a list (based on your example structure)
            if isinstance(pattern_data, list) and len(pattern_data) > 0:
                # Process each word in the first list item
                for word_data in pattern_data[0]:
                    if 'Expected' in word_data:
                        # Format the Expected field to 1 decimal place
                        word_data['Expected'] = round(word_data['Expected'], 1)
        
        # Determine output path
        if output_path is None:
            output_path = json_file_path
        
        # Save the formatted data back to file
        with open(output_path, 'w') as file:
            json.dump(data, file, indent=2)
        
        print(f"Successfully formatted 'Expected' field and saved to {output_path}")
        return True
    
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        return False
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON file '{json_file_path}'.")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

# Only run when this file is executed directly
if __name__ == "__main__":
    format_expected_field()