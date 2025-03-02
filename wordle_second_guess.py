from itertools import product
# We can use the existing update_wordle_json logic, but adapt it to work with our structure
import wordle_functions as wdl

import tempfile
import json
import os

import pandas as pd


def generate_all_feedback_patterns():
    # Generate all possible combinations of X, A, G in a 5-letter pattern
    feedback_states = ['X', 'A', 'G']
    all_patterns = [''.join(pattern) for pattern in product(feedback_states, repeat=5)]
    return all_patterns

def create_criteria_for_pattern(guess, pattern):
    # Start with empty criteria (similar to reset_wordle_json structure)
    criteria = {
        "exclusions": {
            "1st char": "",
            "2nd char": "",
            "3rd char": "",
            "4th char": "",
            "5th char": ""
        },
        "known_letters": "-----",
        "unlocated_letters_in_word": "",
        "letters_not_in_word": "",
        "previous_guesses": [f"{guess} {pattern}"]
    }
    
    # Create a temporary JSON file to store the criteria
    
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp:
        json.dump(criteria, temp)
        temp_path = temp.name
    
    # Update criteria using existing function
    wdl.update_wordle_json(temp_path, f"{guess} {pattern}")
    
    # Read the updated criteria
    with open(temp_path, 'r') as file:
        updated_criteria = json.load(file)
    
    # Clean up
    os.unlink(temp_path)
    
    return updated_criteria

def generate_aider_outcomes_json(output_file="aider_outcomes.json"):
    guess = "AIDER"
    all_patterns = generate_all_feedback_patterns()
    
    # Create our structured JSON
    outcomes = {}
    
    for pattern in all_patterns:
        criteria = create_criteria_for_pattern(guess, pattern)
        outcomes[pattern] = criteria
    
    # Save to file
    with open(output_file, 'w') as file:
        json.dump(outcomes, file, indent=4)
    
    print(f"Generated {len(outcomes)} possible outcomes for '{guess}' in {output_file}")
    return outcomes

# Run the function
# outcomes_data = generate_aider_outcomes_json()


def add_candidates_to_outcomes(input_file="aider_outcomes.json", output_file="aider_outcomes_with_candidates.json"):
    # Load the existing outcomes file
    with open(input_file, 'r') as file:
        outcomes = json.load(file)
    
    # Load the word list
    word_list = pd.read_csv("word_list.csv")
    
    # Process each pattern
    pattern_count = 0
    for pattern, data in outcomes.items():
        
        # Progress tracker
        pattern_count += 1 #this is just a counter to give user a progress tracker
        print(f"Processing pattern {pattern_count}/243: {pattern}")
        
        # Extract criteria
        if "criteria" in data:
            # If the data is already structured with "criteria" as a key
            criteria = data["criteria"]
        else:
            # If the data is just the criteria itself
            criteria = data
                
        # Format inputs for the filter function
        inputs = {
            "exclusions": criteria["exclusions"],
            "known_letters": criteria["known_letters"],
            "unlocated_letters_in_word": criteria["unlocated_letters_in_word"],
            "letters_not_in_word": criteria["letters_not_in_word"]
        }
        
        # Filter candidates
        candidates = wdl.wordle_filter(inputs, word_list)  
        
        # Update the dictionary structure
        outcomes[pattern] = {
            "criteria": criteria,
            "remaining_candidates": {
                "count": len(candidates),
                "words": candidates["WORD"].tolist()
            }
        }
    
    # Save the updated outcomes
    with open(output_file, 'w') as file:
        json.dump(outcomes, file, indent=4)
    
    print(f"Added candidate information to {len(outcomes)} patterns")
    # print(f"Saved to {output_file}")
    
    return outcomes

# outcomes_with_criteria = add_candidates_to_outcomes()

def remove_invalid_outcomes(outcomes, output_file="aider_outcomes_filtered.json"):
    filtered_data = {
        pattern: details
        for pattern, details in outcomes.items()
        if details.get("remaining_candidates", {}).get("count", 0) > 0
    }

    filtered_data_no_criteria = {
    pattern: {k: v for k, v in details.items() if k != "criteria"}
    for pattern, details in filtered_data.items()
    }

    with open(output_file, 'w') as file:
        json.dump(filtered_data_no_criteria, file, indent=4)

    return filtered_data_no_criteria

# filtered_outcomes = remove_invalid_outcomes()

def create_filtered_outcomes_from_start():
    generate_aider_outcomes_json(output_file="aider_outcomes.json")
    outcomes_with_criteria = add_candidates_to_outcomes(input_file="aider_outcomes.json", output_file="aider_outcomes_with_candidates.json")
    filtered_outcomes = remove_invalid_outcomes(outcomes_with_criteria, output_file="aider_outcomes_filtered.json")
    return filtered_outcomes

filtered_outcomes = create_filtered_outcomes_from_start()
print(filtered_outcomes)




