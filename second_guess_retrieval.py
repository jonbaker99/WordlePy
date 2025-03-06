import json
import pandas as pd

def get_top_words_for_pattern(pattern, n=10, json_file_path="pattern_analysis_results.json"):
    """
    Returns the top n suggested words for a given pattern.
    
    Args:
        pattern (str): The Wordle feedback pattern (e.g., "XXXXG")
        n (int): Number of words to return
        json_file_path (str): Path to the JSON file with suggestions
    
    Returns:
        pandas.DataFrame: A DataFrame with the top n words and their metrics
    """
    # Convert pattern to uppercase
    pattern = pattern.upper()
    
    try:
        # Load the JSON data
        with open(json_file_path, 'r') as file:
            suggestions = json.load(file)
        
        # Check if the pattern exists in the data
        if pattern not in suggestions:
            return pd.DataFrame(columns=["Word", "Expected", "Max", "Median"])
        
        # Get the words for this pattern
        pattern_words = suggestions[pattern][0]  # Assuming data is in the first list item
        
        # Take only the first n items
        top_n_words = pattern_words[:n]
        
        # Create a DataFrame with only the required columns
        df = pd.DataFrame(top_n_words)[["Word", "Expected", "Max", "Median"]]
        
        return df
    
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        return pd.DataFrame(columns=["Word", "Expected", "Max", "Median"])
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON file '{json_file_path}'.")
        return pd.DataFrame(columns=["Word", "Expected", "Max", "Median"])
    except Exception as e:
        print(f"Error: {str(e)}")
        return pd.DataFrame(columns=["Word", "Expected", "Max", "Median"])
    

# This block only runs when this file is executed directly
if __name__ == "__main__":
    # Get top 3 words for pattern "XXXXG"
    pattern = "XXXXA"
    top_n = 20
    suggestions = get_top_words_for_pattern(pattern, top_n)
    print(suggestions)