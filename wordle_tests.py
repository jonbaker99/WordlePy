from itertools import combinations, product
from collections import Counter

def get_n_letter_combinations(input_string: str, n: int) -> list:
    """
    Finds all possible n-letter combinations from the input string.
    
    :param input_string: String to generate combinations from
    :param n: Number of letters to include in each combination
    :return: List of all possible n-letter combinations
    """
    # Convert to uppercase and remove duplicates while maintaining order
    unique_chars = ''.join(dict.fromkeys(input_string.upper()))
    
    # Get all n-letter combinations
    combos = [''.join(combo) for combo in combinations(unique_chars, n)]
    
    return combos

combos = get_n_letter_combinations("ABCDEF",3)

def check_words_and_candidates_to_df(words, candidates, combos):
    """
    Checks if words in `words` contain all letters in a combination, 
    and counts matches in `candidates` based on boolean criteria.
    
    :param words: List of words to check for inclusion of all letters.
    :param candidates: List of candidate words to check for boolean criteria.
    :param combos: List of letter combinations.
    :return: Pandas DataFrame with results.
    """
    results = []
    for combo in combos:
        # Check Level [0]: If any word in `words` contains all letters in the combo
        viable_words = [word for word in words if all(letter in word for letter in combo)]
        
        if viable_words:  # Only proceed if viable words exist
            # Generate boolean combinations *only* if viable words exist
            bool_combos = list(product([True, False], repeat=len(combo)))
            
            # Evaluate Level [1]: Count matches in `candidates` for each boolean combination
            boolean_results = [
                sum(
                    all((letter in word if condition else letter not in word)
                        for letter, condition in zip(combo, bool_combo))
                    for word in candidates
                )
                for bool_combo in bool_combos
            ]
            
            # Compute max and min matches
            max_matches = max(boolean_results)
            min_matches = min(boolean_results)
            
            # Add results for this combo to the list
            results.append({
                "combo": combo,
                "viable_words": ', '.join(viable_words),
                "max_matches": max_matches,
                "min_matches": min_matches
            })
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    return df

def filter_combos(word_list, combos):
    """
    Filters combos to include only those where at least one word in word_list
    contains every letter in the combo.
    
    :param word_list: List of words to check.
    :param combos: List of letter combinations to filter.
    :return: Filtered list of combos.
    """
    # Preprocess words into sets of letters
    word_sets = [set(word) for word in word_list]
    # print(f"Preprocessed {len(word_sets)} word sets.")

    # Debugging: Check some preprocessed word sets
    # print("Sample word sets:", word_sets[:5])

    # Filter combos
    filtered_combos = []
    for combo in combos:
        combo_set = set(combo)  # Convert combo to a set of letters
        # Debugging: Check the current combo being processed
        # print(f"Processing combo: {combo} as set {combo_set}")
        for word_set in word_sets:
            if combo_set.issubset(word_set):
                filtered_combos.append(combo)
                break  # No need to check other words for this combo

    return filtered_combos

def process_binary_combos_with_sets(filtered_combos, word_list):
    """
    Processes binary combinations for each combo using sets for efficiency.
    
    :param filtered_combos: List of viable letter combos.
    :param word_list: List of words to check.
    :return: Dictionary with results for each combo.
    """
    # Preprocess words into sets of letters
    word_sets = [set(word) for word in word_list]
    
    # Store results
    results = {}
    
    for combo in filtered_combos:
        combo_length = len(combo)
        binary_combos = list(product([True, False], repeat=combo_length))
        
        # Convert the combo into a set for efficient operations
        combo_set = set(combo)
        
        # Store results for this combo
        results[combo] = []
        
        for binary_combo in binary_combos:
            # Split combo into True and False sets based on the binary_combo
            true_letters = {letter for letter, flag in zip(combo, binary_combo) if flag}
            false_letters = combo_set - true_letters  # Remaining letters
            
            # Count matching words
            match_count = sum(
                true_letters.issubset(word_set) and word_set.isdisjoint(false_letters)
                for word_set in word_sets
            )
            
            # Store the result for this binary combo
            results[combo].append({
                "binary_combo": binary_combo,
                "match_count": match_count
            })
    
    return results


def add_binary_combos(filtered_combos):
    """
    Processes binary combinations for each combo using sets for efficiency.
    
    :param filtered_combos: List of viable letter combos.
    :param word_list: List of words to check.
    :return: Dictionary with results for each combo.
    """
    
    # Preprocess words into sets of letters
    #word_sets = [set(word) for word in word_list]
    
    # Store results
    results = {}
    
    for combo in filtered_combos:
        combo_length = len(combo)
        binary_combos = list(product([True, False], repeat=combo_length))
        
        # Convert the combo into a set for efficient operations
        combo_set = set(combo)
        
        # Store results for this combo
        results[combo] = []
        
        for binary_combo in binary_combos:
            # Split combo into True and False sets based on the binary_combo
            true_letters = {letter for letter, flag in zip(combo, binary_combo) if flag}
            false_letters = combo_set - true_letters  # Remaining letters
            
            # # Count matching words
            # match_count = sum(
            #     true_letters.issubset(word_set) and word_set.isdisjoint(false_letters)
            #     for word_set in word_sets
            # )
            
            # Store the result for this binary combo
            results[combo].append({
                "binary_combo": binary_combo,
                # "match_count": match_count
            })
    
    return results



def preprocess_word_list(word_list):
    """
    Preprocess the word list into a dictionary of frozensets for fast lookups.
    
    :param word_list: List of words to preprocess.
    :return: Dictionary with frozensets as keys and their counts as values.
    """
    return Counter(frozenset(word) for word in word_list)

def process_binary_combos_with_optimised_counting(filtered_combos, word_list):
    """
    Processes binary combinations for each combo using a preprocessed word dictionary.
    
    :param filtered_combos: List of viable letter combos.
    :param word_list: List of words (candidates) to count
    :return: Dictionary with results for each combo.
    """
    word_dict = preprocess_word_list(word_list)
    
    results = {}
    for combo in filtered_combos:
        combo_length = len(combo)
        binary_combos = list(product([True, False], repeat=combo_length))
        combo_set = set(combo)  # Convert combo to a set for efficient operations
        
        # Store results for this combo
        results[combo] = []
        
        for binary_combo in binary_combos:
            # Split combo into True and False sets
            true_letters = {letter for letter, flag in zip(combo, binary_combo) if flag}
            false_letters = combo_set - true_letters
            
            # Count matching words using the preprocessed word dictionary
            match_count = sum(
                count for word_set, count in word_dict.items()
                if true_letters.issubset(word_set) and word_set.isdisjoint(false_letters)
            )
            
            # Store the result for this binary combo
            results[combo].append({
                "binary_combo": binary_combo,
                "match_count": match_count
            })
    
    return results

def find_lowest_non_zero_max(results):
    """
    Finds the combo with the lowest non-zero max match count.

    :param results2: Dictionary where each key is a combo, and each value is a list of dictionaries.
    :return: Combo with the lowest non-zero max, and its max match count.
    """
    lowest_max = float('inf')
    best_combo = None

    for combo, binary_results in results.items():
        # Calculate the max match count for this combo
        max_count = max(result['match_count'] for result in binary_results)
        
        # Check if it's a non-zero max and the lowest encountered so far
        if 0 < max_count < lowest_max:
            lowest_max = max_count
            best_combo = combo

    return best_combo, lowest_max