import json
import itertools
from collections import defaultdict

# Step 1: Generate all combinations of states (X, A, G)
def generate_combinations(word_length):
    states = ['X', 'A', 'G']
    return list(itertools.product(states, repeat=word_length))

# Step 2: Map each combination to constraints
def map_to_constraints(guess, combination):
    guess = guess.lower()  # Ensure guess is lowercase
    constraints = {
        "In": set(),
        "Out": set(),
        "Known": defaultdict(str),  # Key: position, Value: letter
        "Not": defaultdict(set),   # Key: position, Value: set of letters
    }
    for i, (char, status) in enumerate(zip(guess, combination)):
        char = char.lower()  # Ensure character is lowercase
        if status == "X":
            constraints["Out"].add(char)
            constraints["Not"][i].add(char)
        elif status == "A":
            constraints["In"].add(char)
            constraints["Not"][i].add(char)
        elif status == "G":
            constraints["In"].add(char)
            constraints["Known"][i] = char
    return constraints

# Step 3: Group by frozen sets
def group_by_frozensets(all_constraints):
    frozensets_dict = {
        "In": {},
        "Out": {},
        "Known": {},
        "Not": {}
    }
    for entry in all_constraints:
        for key in ["In", "Out", "Known", "Not"]:
            if key == "Known":
                frozen_set = frozenset(entry["constraints"][key].items())
            elif key == "Not":
                frozen_set = frozenset((k, frozenset(v)) for k, v in entry["constraints"][key].items())
            else:
                frozen_set = frozenset(entry["constraints"][key])
            frozensets_dict[key].setdefault(frozen_set, []).append(entry)
    return frozensets_dict

# Step 4: Filter combinations based on criteria
def filter_combinations(frozensets_dict, criteria, key):
    valid_frozensets = set()
    for frozen_set in frozensets_dict[key]:
        if key in ["In", "Out"]:
            if (criteria[key].issubset(frozen_set) if key == "In" else criteria[key].isdisjoint(frozen_set)):
                valid_frozensets.add(frozen_set)
        elif key == "Known":
            if all(criteria[key].get(k, v) == v for k, v in frozen_set):
                valid_frozensets.add(frozen_set)
        elif key == "Not":
            if all(criteria[key].get(pos, set()).isdisjoint(values) for pos, values in frozen_set):
                valid_frozensets.add(frozen_set)
    filtered_combinations = []
    for frozen_set in valid_frozensets:
        filtered_combinations.extend(frozensets_dict[key][frozen_set])
    return filtered_combinations

# Step 5: Test all sets in specified order
def test_combinations(guess, criteria, test_order):
    combinations = generate_combinations(len(guess))
    all_constraints = [
        {"combination": combination, "constraints": map_to_constraints(guess, combination)}
        for combination in combinations
    ]
    frozensets_dict = group_by_frozensets(all_constraints)
    for key in test_order:
        all_constraints = filter_combinations(frozensets_dict, criteria, key)
        frozensets_dict = group_by_frozensets(all_constraints)
    return all_constraints

# Step 6: Parse `wordle.json` and map to criteria
def parse_wordle_json(json_path):
    with open(json_path, 'r') as file:
        wordle_data = json.load(file)
    
    # Normalise inputs to lowercase
    wordle_data["known_letters"] = wordle_data["known_letters"].lower()
    wordle_data["unlocated_letters_in_word"] = wordle_data["unlocated_letters_in_word"].lower()
    wordle_data["letters_not_in_word"] = wordle_data["letters_not_in_word"].lower()
    wordle_data["exclusions"] = {k.lower(): v.lower() for k, v in wordle_data["exclusions"].items()}
    
    # Extract criteria
    criteria = {
        "In": set(wordle_data["unlocated_letters_in_word"]),
        "Out": set(wordle_data["letters_not_in_word"]),
        "Known": {},
        "Not": defaultdict(set)
    }
    
    # Map "known_letters" to "Known"
    for i, char in enumerate(wordle_data["known_letters"]):
        if char != "-":  # "-" indicates no known letter at this position
            criteria["Known"][i] = char
    
    # Map "exclusions" to "Not"
    for pos, excluded_letters in enumerate(wordle_data["exclusions"].values()):
        if excluded_letters:
            criteria["Not"][pos].update(excluded_letters)
    
    return criteria

# # Example Usage
# guess = "apple"
# test_order = ["In", "Out", "Known", "Not"]  # Order of testing

# # # Parse the JSON file
# wordle_json_path = "wordle.json"
# criteria = parse_wordle_json(wordle_json_path)

# # # Get filtered combinations
# filtered_combinations = test_combinations(guess, criteria, test_order)

# # # Display results
# print(f"Filtered combinations count: {len(filtered_combinations)}")
# for entry in filtered_combinations[:5]:  # Display the first 5 results
#     print(f"Combination: {entry['combination']}")
#     print(f"Constraints: {entry['constraints']}")
#     print()

import pandas as pd
from collections import defaultdict

def preprocess_candidates(candidates):
    """Ensure candidates is a DataFrame with a 'WORD' column and preprocess for case-normalised filtering."""
    # Normalise candidates to a DataFrame
    if isinstance(candidates, list) or isinstance(candidates, pd.Series):
        candidates_df = pd.DataFrame({"WORD": candidates})
    elif isinstance(candidates, pd.DataFrame):
        if 'WORD' not in candidates.columns:
            raise KeyError("'WORD' column is missing in the DataFrame")
        candidates_df = candidates
    else:
        raise TypeError("Unsupported candidates format. Must be DataFrame, Series, or list.")

    # Normalise all words to lowercase
    candidates_df["WORD"] = candidates_df["WORD"].str.lower()

    # Create indexes for faster filtering
    letter_index = defaultdict(set)
    position_index = defaultdict(lambda: defaultdict(set))
    
    for word in candidates_df["WORD"]:
        for i, letter in enumerate(word):
            letter = letter.lower()  # Ensure letter is lowercase
            letter_index[letter].add(word)
            position_index[i][letter].add(word)
    
    return letter_index, position_index

def fast_count_matching_words(remaining_combos, candidates):
    """Efficiently count matching words for each combination."""
    # Preprocess candidates
    letter_index, position_index = preprocess_candidates(candidates)
    results = []
    
    for combo in remaining_combos:
        # Extract constraints
        in_set = {letter.lower() for letter in combo["constraints"]["In"]}  # Normalise case
        out_set = {letter.lower() for letter in combo["constraints"]["Out"]}  # Normalise case
        known = {pos: letter.lower() for pos, letter in combo["constraints"]["Known"].items()}  # Normalise case
        not_set = {pos: {letter.lower() for letter in letters} for pos, letters in combo["constraints"]["Not"].items()}  # Normalise case
        
        # Start with all candidates
        filtered_words = set(candidates["WORD"].str.lower())
        
        # Apply "In" filter: words must contain all letters in the "In" set
        for letter in in_set:
            filtered_words &= letter_index[letter]
        
        # Apply "Out" filter: words must not contain any letters in the "Out" set
        for letter in out_set:
            filtered_words -= letter_index[letter]
        
        # Apply "Known" filter: words must have the correct letters at specific positions
        for pos, letter in known.items():
            filtered_words &= position_index[pos][letter]
        
        # Apply "Not" filter: words must not have specific letters at specific positions
        for pos, letters in not_set.items():
            for letter in letters:
                filtered_words -= position_index[pos][letter]
        
        # Count matching words
        results.append({
            "combination": combo["combination"],
            "matching_words_count": len(filtered_words),
            "matching_words": list(filtered_words),  # Optional: Keep the matching words
        })
    
    return results

# # Example usage:
# # Assume `candidates` is your DataFrame containing all candidate words in the "WORD" column
# # Example:
# # candidates = pd.DataFrame({"WORD": ["Apple", "ample", "APPLY", "spare", "PLATE"]})

# candidates_by_combo = fast_count_matching_words(remaining_combos, candidates)

# # Extracting the results
# non_zero_combinations = [result for result in candidates_by_combo if result["matching_words_count"] > 0]
# num_non_zero_combinations = len(non_zero_combinations)

# # Maximum non-zero matching_words_count and the associated combination
# max_result = max(non_zero_combinations, key=lambda x: x["matching_words_count"], default=None)

# if max_result:
#     max_non_zero_count = max_result["matching_words_count"]
#     max_combination = max_result["combination"]
# else:
#     max_non_zero_count = 0
#     max_combination = None

# # Output the results
# print(f"Number of combinations with non-zero matching_words_count: {num_non_zero_combinations}")
# print(f"Maximum non-zero matching_words_count: {max_non_zero_count}")
# print(f"Combination with the max matching_words_count: {max_combination}")


def get_max_non_zero_matches(guesses, candidates_df):
    """
    Takes a list of guess words and outputs a DataFrame with each word 
    and the maximum non-zero matching_words_count for that word.
    """
    results = []

    for guess in guesses:
        # Generate combinations based on the guess
        word_length = len(guess)
        combinations = generate_combinations(word_length)

        # Map combinations to constraints
        remaining_combos = [
            {"combination": combination, "constraints": map_to_constraints(guess, combination)}
            for combination in combinations
        ]

        # Generate filtered combinations for the guess
        filtered_combos = fast_count_matching_words(remaining_combos, candidates_df)

        # Get the maximum non-zero matching_words_count for the current guess
        non_zero_combinations = [
            result for result in filtered_combos if result["matching_words_count"] > 0
        ]
        
        max_result = max(
            non_zero_combinations,
            key=lambda x: x["matching_words_count"],
            default=None
        )

        max_count = max_result["matching_words_count"] if max_result else 0

        # Store the guess and its max matching count
        results.append({"Guess": guess, "Max Matching Words Count": max_count})
    
    # Convert results to a DataFrame and sort by max count in descending order
    results_df = pd.DataFrame(results)
    results_df.sort_values(by="Max Matching Words Count", ascending=True, inplace=True)
    results_df.reset_index(drop=True, inplace=True)

    return results_df

# # Example Usage
# # Assume guesses is a list of guess words, and candidates_df is your DataFrame containing candidates
# # Example:
# # guesses = ["apple", "spare", "plate", "apply", "ample"]

# # Generate the DataFrame
# results_df = get_max_non_zero_matches(guesses, candidates_df)

# # Display the sorted DataFrame
# print(results_df)