# wordle_functions.py

import pandas as pd
import json
from collections import Counter, defaultdict
from itertools import combinations, product
import operator


def reset_wordle_json(file_path: str):
    """
    Resets the wordle.json file to its default state.

    :param file_path: Path to the wordle.json file
    """
    default_data = {
        "exclusions": {
            "1st char": "",
            "2nd char": "",
            "3rd char": "",
            "4th char": "",
            "5th char": ""
        },
        "known_letters": "-----",
        "unlocated_letters_in_word": "",
        "letters_not_in_word": ""
    }
    with open(file_path, "w") as f:
        json.dump(default_data, f, indent=4)
    print(f"{file_path} has been reset.")


def update_wordle_json(wordle_json_name, input_string):
    """
    Updates the JSON file (wordle_json_name) with a guess and pattern.

    The pattern uses:
     - 'G' (Green) to indicate correct letter and position
     - 'A' (Amber) to indicate correct letter, wrong position
     - 'X' (Gray) to indicate the letter is not in the final word

    :param wordle_json_name: Path to your Wordle JSON file
    :param input_string: String of the form "WORD PATTERN",
                        e.g. "APPLE XGXAX"
    """
    with open(wordle_json_name, "r") as file:
        wordle_data = json.load(file)

    word, pattern = input_string.split()
    processed_letters = set()

    for idx, (char, status) in enumerate(zip(word, pattern)):
        if status == "G":
            # Place letter in known_letters
            wordle_data["known_letters"] = (
                wordle_data["known_letters"][:idx]
                + char
                + wordle_data["known_letters"][idx + 1:]
            )
            # Remove from 'unlocated_letters_in_word' if it was there
            if char in wordle_data["unlocated_letters_in_word"]:
                wordle_data["unlocated_letters_in_word"] = \
                    wordle_data["unlocated_letters_in_word"].replace(char, "")
            processed_letters.add(char)

        elif status in ["A", "X"]:
            # Add to exclusions for this position
            exclusion_key = f"{idx + 1}{['st', 'nd', 'rd'][idx] if idx < 3 else 'th'} char"
            if exclusion_key not in wordle_data["exclusions"]:
                wordle_data["exclusions"][exclusion_key] = ""
            if char not in wordle_data["exclusions"][exclusion_key]:
                wordle_data["exclusions"][exclusion_key] += char
                
            if status == "A" and char not in wordle_data["unlocated_letters_in_word"]:
                # Add to unlocated letters if status is "A"
                wordle_data["unlocated_letters_in_word"] += char
            elif status == "X" and char not in wordle_data["letters_not_in_word"]:
                # Add to letters_not_in_word if status is "X"
                wordle_data["letters_not_in_word"] += char
                
            processed_letters.add(char)

    # Clean up letters_not_in_word by removing any letters that appear in known_letters or unlocated_letters
    letters_to_remove = set(wordle_data["known_letters"].replace("-", "")) | set(wordle_data["unlocated_letters_in_word"])
    wordle_data["letters_not_in_word"] = "".join(
        char for char in wordle_data["letters_not_in_word"]
        if char not in letters_to_remove
    )

    with open(wordle_json_name, "w") as file:
        json.dump(wordle_data, file, indent=4)


def load_wordle_inputs(json_file):
    """
    Loads inputs for the Wordle helper tool from a JSON file.

    :param json_file: Path to the JSON file
    :return: Dictionary with exclusions, known_letters, 
             unlocated_letters_in_word, and letters_not_in_word
    """
    with open(json_file, "r") as f:
        config = json.load(f)

    return {
        "exclusions": config["exclusions"],  # dictionary of chars excluded at each position
        "known_letters": config["known_letters"],
        "unlocated_letters_in_word": config["unlocated_letters_in_word"],
        "letters_not_in_word": config["letters_not_in_word"]
    }


def candidates_match_known(word_list: pd.DataFrame, known_letters: str):
    """
    Filters the word list based on the known_letters pattern 
    (where '-' is a wildcard).
    
    :param word_list: DataFrame containing the words
    :param known_letters: String with known letters/wildcards (e.g., "---NY")
    :return: Filtered DataFrame with matching words
    """
    # Convert known_letters pattern into a regex pattern (non-letter => '.')
    known_pattern = pd.Series([known_letters]).str.replace(r"[^A-Za-z]", ".", regex=True).iloc[0]
    candidates = word_list[word_list['WORD'].str.match(known_pattern, na=False)]
    return candidates


def filter_words_by_exclusions(word_list, exclusions):
    """
    Filters a DataFrame of 5-letter words based on position-specific exclusions.
    
    :param word_list: DataFrame with column 'WORD' containing 5-letter words
    :param exclusions: A dict with keys like '1st char', '2nd char', etc., 
                       and values as strings of excluded characters
    :return: Filtered DataFrame
    """
    def meets_criteria(word):
        for idx, (char_set, char) in enumerate(zip(exclusions.values(), word), start=1):
            if char.upper() in char_set.upper():
                return False
        return True

    return word_list[word_list['WORD'].apply(meets_criteria)]


def candidates_all_letters(word_list: pd.DataFrame,
                           known_letters: str,
                           unlocated_letters: str):
    """
    Filters the word list to include words that contain all the known and unlocated letters.
    
    :param word_list: DataFrame containing the words
    :param known_letters: Uppercase string for letters in correct positions (if known)
    :param unlocated_letters: Uppercase string for letters that must be in the word, 
                              but not necessarily at a known position
    :return: Filtered DataFrame
    """
    all_letters_in_word = unlocated_letters + \
        pd.Series([known_letters]).str.replace(r"[^A-Za-z]", "", regex=True).iloc[0]
    
    required_counts = Counter(all_letters_in_word.upper())

    def matches_condition(word):
        word_counts = Counter(word.upper())
        return all(word_counts[ch] >= cnt for ch, cnt in required_counts.items())

    return word_list[word_list['WORD'].apply(matches_condition)]


def candidates_ex_excluded(word_list: pd.DataFrame, letters_not_in_word: str):
    """
    Removes words that contain any of the excluded letters (letters_not_in_word).
    
    :param word_list: DataFrame of 5-letter words
    :param letters_not_in_word: String of letters known NOT to appear in the final word
    :return: Filtered DataFrame
    """
    excluded_letters = set(letters_not_in_word.upper())

    def does_not_contain_excluded_letters(word):
        return excluded_letters.isdisjoint(set(word.upper()))

    return word_list[word_list['WORD'].apply(does_not_contain_excluded_letters)]


def wordle_filter(inputs, word_list: pd.DataFrame):
    """
    Applies multiple filters (known letters, position exclusions, 
    letters not in word, etc.) to narrow down possible Wordle candidates.
    
    :param inputs: Dictionary with keys:
                    'exclusions', 'known_letters', 'unlocated_letters_in_word', 
                    'letters_not_in_word'
    :param word_list: Pandas DataFrame with a column 'WORD'
    :return: Filtered DataFrame of candidates
    """
    known_letters = inputs['known_letters'].upper()
    unlocated_letters = inputs['unlocated_letters_in_word'].upper()
    exclusions = inputs['exclusions']
    letters_not_in_word = inputs['letters_not_in_word'].upper()

    candidates = word_list

    # Only include known letters (if any pattern is set)
    if len(known_letters) > 0:
        candidates = candidates_match_known(candidates, known_letters)

    # If any position-based exclusions exist
    if any(bool(chars) for chars in exclusions.values()):
        # Convert to uppercase in the dictionary
        exclusions = {k: v.upper() for k, v in exclusions.items()}
        candidates = filter_words_by_exclusions(candidates, exclusions)
        # Exclusion letters are no longer added to unlocated letters

    # Must contain these 'unlocated' letters
    if len(unlocated_letters) > 0:
        candidates = candidates_all_letters(candidates, known_letters, unlocated_letters)

    # Exclude words containing letters known not to be in the solution
    if len(letters_not_in_word) > 0:
        candidates = candidates_ex_excluded(candidates, letters_not_in_word)

    return candidates


def get_unique_letters(word_list):
    """
    Returns all unique letters from a list/series of words.

    :param word_list: An iterable of words (strings)
    :return: Set of unique letters
    """
    all_letters = ''.join(word_list).upper()
    return set(all_letters)


def letters_in_candidates(word_list, inputs):
    """
    Given a list of candidate words and the current Wordle inputs, 
    returns a set of letters that might still be relevant (i.e., 
    letters not already accounted for in known/unlocated).
    
    :param word_list: DataFrame with a column 'WORD'
    :param inputs: Dictionary with 'known_letters' and 'unlocated_letters_in_word'
    :return: A set of letters
    """
    unique_letters = get_unique_letters(word_list['WORD'])
    known_letters = inputs['known_letters'] + inputs['unlocated_letters_in_word']
    letters_to_remove_set = set(known_letters.upper())
    return unique_letters.difference(letters_to_remove_set)


def filter_list_for_chosen_letters(words: pd.DataFrame, required_letters: str) -> pd.DataFrame:
    """
    Filters a list of words to include only those containing all letters 
    from the input string (regardless of position).
    
    :param words: DataFrame containing the words (column: 'WORD')
    :param required_letters: String of letters that must be in each word
    :return: Filtered DataFrame
    """
    required_set = set(required_letters.upper())
    def contains_all_letters(word):
        return required_set.issubset(set(word.upper()))
    return words[words['WORD'].apply(contains_all_letters)]


def preprocess_word_list(word_list):
    """
    Converts a list of words into a Counter keyed by frozenset(letters),
    for efficient subset/disjoint queries.

    :param word_list: List/iterable of words
    :return: A Counter with frozenset(word) as keys, counts as values
    """
    return Counter(frozenset(word) for word in word_list)


def get_n_letter_combinations(input_string: str, n: int) -> list:
    """
    Finds all possible n-letter combinations from the input string (unique letters).
    
    :param input_string: String to generate combinations from
    :param n: Number of letters to include in each combination
    :return: List of n-letter combinations (as strings)
    """
    unique_chars = ''.join(dict.fromkeys(input_string.upper()))
    return [''.join(combo) for combo in combinations(unique_chars, n)]


def filter_combos(word_list, combos):
    """
    Filters combos to include only those where at least one word in word_list
    contains every letter in the combo.
    
    :param word_list: List or Series of words to check
    :param combos: List of letter combinations to filter
    :return: Filtered list of combos
    """
    word_sets = [set(word) for word in word_list]
    filtered = []
    for combo in combos:
        combo_set = set(combo)
        for wset in word_sets:
            if combo_set.issubset(wset):
                filtered.append(combo)
                break
    return filtered


def process_binary_combos_with_optimised_counting(filtered_combos, word_list):
    """
    For each viable combo of letters, compute match counts for all 
    True/False (in or out) subsets, using a preprocessed word dictionary.
    
    :param filtered_combos: List of combos that appear in at least one word
    :param word_list: List (or Series) of candidate words (strings)
    :return: Dictionary { combo: [ {binary_combo, match_count}, ... ] }
    """
    word_dict = preprocess_word_list(word_list)
    results = {}
    for combo in filtered_combos:
        combo_length = len(combo)
        combo_set = set(combo)
        binary_combos = list(product([True, False], repeat=combo_length))

        results[combo] = []
        for binary_combo in binary_combos:
            true_letters = {letter for letter, flag in zip(combo, binary_combo) if flag}
            false_letters = combo_set - true_letters
            match_count = sum(
                count for word_set, count in word_dict.items()
                if true_letters.issubset(word_set) and word_set.isdisjoint(false_letters)
            )
            results[combo].append({
                "binary_combo": binary_combo,
                "match_count": match_count
            })
    return results


def find_lowest_non_zero_max(results):
    """
    Finds the combo whose maximum match_count across all binary subsets 
    is the lowest among combos that still have a non-zero maximum.
    
    :param results: A dictionary {combo: [{binary_combo, match_count}, ...]}
    :return: (combo, lowest_non_zero_max)
    """
    lowest_max = float('inf')
    best_combo = None
    for combo, binary_results in results.items():
        max_count = max(r['match_count'] for r in binary_results)
        if 0 < max_count < lowest_max:
            lowest_max = max_count
            best_combo = combo
    return best_combo, lowest_max


def parse_wordle_json(json_path):
    """
    Parses a wordle.json file and converts it into a 'criteria' dictionary 
    with four main keys: 'In', 'Out', 'Known', and 'Not'. 
    Positions are treated as indices (0-4) for 'Known' and 'Not'.
    
    :param json_path: Path to the wordle.json file
    :return: Dictionary containing sets/dicts for 'In', 'Out', 'Known', and 'Not'
    """
    with open(json_path, 'r') as file:
        wordle_data = json.load(file)

    # normalize
    wordle_data["known_letters"] = wordle_data["known_letters"].lower()
    wordle_data["unlocated_letters_in_word"] = wordle_data["unlocated_letters_in_word"].lower()
    wordle_data["letters_not_in_word"] = wordle_data["letters_not_in_word"].lower()
    wordle_data["exclusions"] = {k.lower(): v.lower() for k, v in wordle_data["exclusions"].items()}

    criteria = {
        "In": set(wordle_data["unlocated_letters_in_word"]),
        "Out": set(wordle_data["letters_not_in_word"]),
        "Known": {},
        "Not": defaultdict(set)
    }

    # Known letters by position
    for i, ch in enumerate(wordle_data["known_letters"]):
        if ch != '-':
            criteria["Known"][i] = ch

    # position-based exclusions => "Not"
    for pos, excluded_letters in enumerate(wordle_data["exclusions"].values()):
        if excluded_letters:
            criteria["Not"][pos].update(excluded_letters)

    return criteria


def generate_combinations(word_length):
    """
    Generate all possible (X, A, G) patterns for a word of given length.
    X = letter not in the solution
    A = letter in the solution but at a different position
    G = letter in the solution at this exact position
    """
    states = ['X', 'A', 'G']
    return list(product(states, repeat=word_length))


def map_to_constraints(guess, combination):
    """
    Given a guess (string) and a pattern combination (tuple like ('X','G','A','A','X')),
    produce a constraints dict with keys: "In", "Out", "Known", "Not".
    
    :param guess: e.g. "APPLE"
    :param combination: e.g. ('X','G','X','A','X')
    :return: constraints dictionary
    """
    guess = guess.lower()
    constraints = {
        "In": set(),
        "Out": set(),
        "Known": defaultdict(str),
        "Not": defaultdict(set),
    }
    for i, (ch, status) in enumerate(zip(guess, combination)):
        ch = ch.lower()
        if status == "X":
            constraints["Out"].add(ch)
            constraints["Not"][i].add(ch)
        elif status == "A":
            constraints["In"].add(ch)
            constraints["Not"][i].add(ch)
        elif status == "G":
            constraints["In"].add(ch)
            constraints["Known"][i] = ch
    return constraints


def preprocess_candidates(candidates):
    """
    Takes a DataFrame (or Series) of candidate words in column "WORD" 
    and creates index structures for faster filtering.
    
    :param candidates: DataFrame with column "WORD"
    :return: (letter_index, position_index)
    """
    # Normalize to DataFrame
    if isinstance(candidates, (list, pd.Series)):
        candidates_df = pd.DataFrame({"WORD": candidates})
    elif isinstance(candidates, pd.DataFrame):
        if 'WORD' not in candidates.columns:
            raise KeyError("DataFrame must have 'WORD' column.")
        candidates_df = candidates
    else:
        raise TypeError("Unsupported candidates format.")

    candidates_df["WORD"] = candidates_df["WORD"].str.lower()

    letter_index = defaultdict(set)
    position_index = defaultdict(lambda: defaultdict(set))

    for word in candidates_df["WORD"]:
        for i, letter in enumerate(word):
            letter_index[letter].add(word)
            position_index[i][letter].add(word)

    return letter_index, position_index


def fast_count_matching_words(remaining_combos, candidates):
    """
    For each combination in remaining_combos, quickly count how many words 
    in `candidates` match the combination's constraints.
    
    :param remaining_combos: List of dicts with structure 
                             {"combination": tuple, "constraints": {...}}
    :param candidates: DataFrame with a column "WORD"
    :return: List of dicts with "combination", "matching_words_count", "matching_words"
    """
    letter_index, position_index = preprocess_candidates(candidates)
    results = []
    all_words = set(candidates["WORD"].str.lower())

    for combo in remaining_combos:
        c = combo["constraints"]

        in_set = {ch.lower() for ch in c["In"]}
        out_set = {ch.lower() for ch in c["Out"]}
        known = {pos: ch.lower() for pos, ch in c["Known"].items()}
        not_set = {pos: {x.lower() for x in letters} for pos, letters in c["Not"].items()}

        # Start with all words, then filter down
        filtered_words = set(all_words)

        # Must contain all letters in "In"
        for letter in in_set:
            filtered_words &= letter_index[letter]

        # Must exclude all letters in "Out"
        for letter in out_set:
            filtered_words -= letter_index[letter]

        # Must match letters in "Known" at exact positions
        for pos, letter in known.items():
            filtered_words &= position_index[pos][letter]

        # Must exclude letters in "Not" at their positions
        for pos, letters in not_set.items():
            for letter in letters:
                filtered_words -= position_index[pos][letter]

        results.append({
            "combination": combo["combination"],
            "matching_words_count": len(filtered_words),
            "matching_words": list(filtered_words)
        })

    return results


def get_max_non_zero_matches(guesses, candidates_df):
    """
    For each guess word, generate all (X, A, G) combinations, 
    convert them into constraints, and count how many candidate words 
    match those constraints. Return a DataFrame sorted by the 
    smallest maximum matching-words count (ascending).

    :param guesses: An iterable of guess words
    :param candidates_df: A DataFrame with column 'WORD' of candidate words
    :return: DataFrame with each guess and the maximum matching-word count
    """
    results = []
    for guess in guesses:
        word_length = len(guess)
        combinations_list = generate_combinations(word_length)
        remaining_combos = [
            {"combination": combo,
             "constraints": map_to_constraints(guess, combo)}
            for combo in combinations_list
        ]
        filtered_combos = fast_count_matching_words(remaining_combos, candidates_df)

        # Look at all combos that have a non-zero match
        non_zero_combos = [fc for fc in filtered_combos if fc["matching_words_count"] > 0]
        if non_zero_combos:
            max_count = max(nz["matching_words_count"] for nz in non_zero_combos)
        else:
            max_count = 0

        results.append({
            "Guess": guess,
            "Max Matching Words Count": max_count
        })

    results_df = pd.DataFrame(results)
    results_df.sort_values(by="Max Matching Words Count", ascending=True, inplace=True)
    results_df.reset_index(drop=True, inplace=True)
    return results_df


def filter_by_letter_count(
    df: pd.DataFrame, 
    letter: str = 'o', 
    comparator: str = '<', 
    count_threshold: int = 2
) -> pd.DataFrame:
    """
    Filters a DataFrame of words based on how many times a chosen letter appears.
    
    :param df: A pandas DataFrame containing a column named 'WORD'
    :param letter: The letter to count in each word (case-insensitive)
    :param comparator: A string defining the comparison operator.
                       One of: '>', '<', '>=', '<=', '==', '!='
    :param count_threshold: The integer threshold for letter occurrences
    :return: A filtered DataFrame that meets the specified criteria.
    
    Example:
        # Keep words with fewer than 2 'o's:
        new_df = filter_by_letter_count(df, letter='o', comparator='<', count_threshold=2)
        
        # Keep words with exactly 3 'a's:
        new_df = filter_by_letter_count(df, letter='a', comparator='==', count_threshold=3)
        
        # Exclude words with >= 4 'x's:
        new_df = filter_by_letter_count(df, letter='x', comparator='<', count_threshold=4)
    """
    # Map string operators to actual Python operator functions
    ops_map = {
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '==': operator.eq,
        '!=': operator.ne
    }
    
    if comparator not in ops_map:
        raise ValueError(f"Invalid comparator '{comparator}'. Choose from {list(ops_map.keys())}.")
    
    # Count occurrences of `letter` in each word (case-insensitive)
    count_series = df['WORD'].str.lower().str.count(letter.lower())
    
    # Apply the chosen comparison operator
    mask = ops_map[comparator](count_series, count_threshold)
    
    # Return only those rows that match the condition
    return df[mask]


def reset_tool(wordle_json_path):
    """
    Resets the Wordle environment, including the wordle.json file
    and any in-memory variables that track the solver state.
    
    :param wordle_json_path: Path to the wordle.json file
    :return: A dictionary containing the solver variables set to None.
    
    Example usage:
        state = reset_tool('wordle.json')
        # Then assign them locally if you wish:
        candidates = state['candidates']
        combos = state['combos']
        ...
    """
    # 1. Reset the JSON file to its default contents
    reset_wordle_json(wordle_json_path)

    # 2. Return a dictionary of your typical solver variables, set to None
    return {
        'candidates': None,
        'combos': None,
        'results2': None,
        'best': None,
        'all_letters': None,
        'all_letters_string': None,
        'filtered_combos': None,
        'inputs': None,
        'guess_score_df_candidates': None,
        'guess_score_df_wordlist': None,
        'guesses': None,
        'words': None,
        'words_from_candidates': None,
        'words_from_wordlist': None
    }

def word_count_for_each_letter_left(letters, word_list):
    """
    Given a set of letters and a list of words, 
    returns a dictionary with the count of words 
    containing each letter in the set.
    
    :param letters: A set of letters
    :param word_list: A list of words
    :return: A dictionary with letter counts
    """

    num_words = word_list.count()

    # Initialize dictionary to store counts
    letter_counts = {letter: sum(letter in word for word in word_list) for letter in letters}

    # Convert to DataFrame for tabular display
    df = pd.DataFrame(list(letter_counts.items()), columns=["Letter", "Count"]).sort_values("Count", ascending=False)

    # Add percentage column
    df["% of Words"] = (df["Count"] / num_words * 100).round(0).astype(int).astype(str) + "%"

    return df