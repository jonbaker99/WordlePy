import pandas as pd
import json
from collections import Counter, defaultdict
from itertools import combinations, product
import operator
import os
import subprocess
from datetime import datetime
from functools import lru_cache

###############################################################################
# Utility Functions
###############################################################################
def normalize(word: str) -> str:
    """Normalize a word to lowercase."""
    return word.lower()

def get_ordinal(n: int) -> str:
    """Return the ordinal suffix for a number."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def load_json_file(path: str) -> dict:
    """Load and return JSON data from file."""
    with open(path, 'r') as f:
        return json.load(f)

def save_json_file(path: str, data: dict):
    """Save data to JSON file."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def reset_wordle_json(file_path: str):
    """
    Resets the wordle.json file to its default state.
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
        "letters_not_in_word": "",
        "previous_guesses": []
    }
    with open(file_path, "w") as f:
        json.dump(default_data, f, indent=4)
    print(f"{file_path} has been reset.")

def update_wordle_json(wordle_json_name, input_string):
    """
    Updates the wordle.json file with a new guess and its feedback.
    """
    with open(wordle_json_name, "r") as file:
        wordle_data = json.load(file)
    
    word, pattern = input_string.split()
    word = word.upper()
    pattern = pattern.upper()
    
    # Pre-calculate frequency of 'A' statuses for each letter in the guess.
    a_counts = Counter([ch for ch, s in zip(word, pattern) if s.upper() == "A"])
    
    for idx, (char, status) in enumerate(zip(word, pattern)):
        if status == "G":
            # Place the letter in the correct position.
            wordle_data["known_letters"] = (
                wordle_data["known_letters"][:idx] + char + wordle_data["known_letters"][idx+1:]
            )
            # Remove this letter from unlocated_letters if present.
            wordle_data["unlocated_letters_in_word"] = wordle_data["unlocated_letters_in_word"].replace(char, "")
        elif status in ["A", "X"]:
            key = f"{idx+1}{['st','nd','rd'][idx] if idx < 3 else 'th'} char"
            current_exclusions = wordle_data["exclusions"].get(key, "")
            if char not in current_exclusions:
                wordle_data["exclusions"][key] = current_exclusions + char
            if status == "A":
                # For an amber, allow additional occurrences beyond those already placed in known_letters.
                count_known = wordle_data["known_letters"].upper().count(char)
                count_unlocated = wordle_data["unlocated_letters_in_word"].upper().count(char)
                # If there are more 'A' statuses than what is already known, add one occurrence.
                if count_unlocated < a_counts[char] - count_known:
                    wordle_data["unlocated_letters_in_word"] += char
            elif status == "X":
                if char not in wordle_data["letters_not_in_word"]:
                    wordle_data["letters_not_in_word"] += char
    # Clean up letters_not_in_word by removing letters present in known or unlocated.
    letters_to_keep = set(wordle_data["known_letters"].replace("-", "")) | set(wordle_data["unlocated_letters_in_word"])
    wordle_data["letters_not_in_word"] = "".join(c for c in wordle_data["letters_not_in_word"] if c not in letters_to_keep)
    
    with open(wordle_json_name, "w") as file:
        json.dump(wordle_data, file, indent=4)

def load_wordle_inputs(json_file):
    """
    Loads Wordle criteria from a JSON file.
    """
    with open(json_file, "r") as f:
        config = json.load(f)
    return {
        "exclusions": config["exclusions"],
        "known_letters": config["known_letters"],
        "unlocated_letters_in_word": config["unlocated_letters_in_word"],
        "letters_not_in_word": config["letters_not_in_word"]
    }

def get_last_modified_timestamp(script_path):
    """
    Gets the last modified timestamp for a file.
    """
    try:
        timestamp = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%d/%m/%y %H:%M"]
        ).decode("utf-8").strip()
    except:
        timestamp = datetime.fromtimestamp(os.path.getmtime(script_path)).strftime("%d/%m/%y %H:%M")
    return timestamp

###############################################################################
# Candidate Filtering Functions
###############################################################################
def candidates_match_known(word_list: pd.DataFrame, known_letters: str):
    """
    Filters words to match the known letters pattern.
    """
    if word_list.empty:
        return word_list
    pattern = known_letters.replace("-", ".")
    return word_list[word_list['WORD'].str.match(pattern, na=False)]


def filter_words_by_exclusions(word_list: pd.DataFrame, exclusions):
    """
    Filters words based on exclusion criteria.
    """
    if word_list.empty:
        return word_list
    def meets_criteria(word):
        for char_set, char in zip(exclusions.values(), word):
            if char.upper() in char_set.upper():
                return False
        return True
    return word_list[word_list['WORD'].apply(meets_criteria)]


def candidates_all_letters(word_list: pd.DataFrame, known_letters: str, unlocated_letters: str):
    """
    Filters words to contain all required letters.
    """
    if word_list.empty:
        return word_list
    from re import sub
    letters_only = sub('[^A-Za-z]', '', known_letters)
    all_letters = (unlocated_letters + letters_only).upper()
    required_counts = Counter(all_letters)
    def matches_condition(word):
        word_counts = Counter(word.upper())
        return all(word_counts[ch] >= cnt for ch, cnt in required_counts.items())
    return word_list[word_list['WORD'].apply(matches_condition)]


def candidates_ex_excluded(word_list: pd.DataFrame, letters_not_in_word: str):
    """
    Filters words to exclude those containing certain letters.
    """
    if word_list.empty:
        return word_list
    excluded_letters = set(letters_not_in_word.upper())
    def does_not_contain(word):
        return excluded_letters.isdisjoint(set(word.upper()))
    return word_list[word_list['WORD'].apply(does_not_contain)]


def wordle_filter(inputs, word_list: pd.DataFrame):
    """
    Applies all filtering criteria to get candidate words.
    """
    known_letters = inputs['known_letters'].upper()
    unlocated_letters = inputs['unlocated_letters_in_word'].upper()
    exclusions = {k: v.upper() for k, v in inputs['exclusions'].items()}
    letters_not_in_word = inputs['letters_not_in_word'].upper()
    candidates = word_list.copy()
    if known_letters:
        candidates = candidates_match_known(candidates, known_letters)
    if any(bool(chars) for chars in exclusions.values()):
        candidates = filter_words_by_exclusions(candidates, exclusions)
    if unlocated_letters:
        candidates = candidates_all_letters(candidates, known_letters, unlocated_letters)
    if letters_not_in_word:
        candidates = candidates_ex_excluded(candidates, letters_not_in_word)
    return candidates

def letters_in_candidates(candidates_df, inputs):
    """
    Identifies letters not yet guessed in the candidate words.
    """
    # Get all unique letters from candidates
    all_letters = set(''.join(candidates_df['WORD'].str.upper()))
    
    # Get letters we already know about
    known_letters = set((inputs['known_letters'] + inputs['unlocated_letters_in_word']).upper())
    
    # Return the difference
    return all_letters - known_letters

def create_word_index(words):
    """
    Creates comprehensive word indexes for faster filtering.
    """
    if isinstance(words, pd.DataFrame):
        if 'WORD' not in words.columns:
            raise KeyError("DataFrame must have 'WORD' column.")
        word_list = words['WORD'].str.lower()
    else:
        word_list = [w.lower() for w in words]
    
    word_set = set(word_list)
    letter_index = defaultdict(set)
    position_index = defaultdict(lambda: defaultdict(set))
    
    for word in word_list:
        for i, letter in enumerate(word):
            letter_index[letter].add(word)
            position_index[i][letter].add(word)
    
    return word_set, letter_index, position_index

def filter_list_for_chosen_letters(words: pd.DataFrame, required_letters: str) -> pd.DataFrame:
    """
    Filters words to include only those containing all required letters.
    """
    required_set = set(required_letters.upper())
    return words[words['WORD'].apply(lambda w: required_set.issubset(set(w.upper())))]

def get_n_letter_combinations(input_string: str, n: int) -> list:
    """
    Gets all combinations of n letters from the input string.
    """
    unique_chars = ''.join(dict.fromkeys(input_string.upper()))
    return [''.join(combo) for combo in combinations(unique_chars, n)]

def filter_combos(word_list, combos):
    """
    Filters combinations to only those that appear in at least one word.
    """
    word_sets = [set(word) for word in word_list]
    valid = []
    for combo in combos:
        combo_set = set(combo)
        if any(combo_set.issubset(w) for w in word_sets):
            valid.append(combo)
    return valid

def word_count_for_each_letter_left(letters, word_list):
    """
    Counts how many words contain each unguessed letter.
    """
    num_words = len(word_list)
    letter_counts = {letter: sum(letter.upper() in word.upper() for word in word_list) for letter in letters}
    df = pd.DataFrame(list(letter_counts.items()), columns=["Letter", "Count"]).sort_values("Count", ascending=False)
    df["% of Words"] = (df["Count"] / num_words * 100).round(0).astype(int).astype(str) + "%"
    return df

###############################################################################
# Functions for Candidate Scoring / Guess Evaluation
###############################################################################
def process_binary_combos_with_optimised_counting(filtered_combos, word_list):
    """
    Processes binary combinations with optimized counting.
    """
    word_counter = Counter(frozenset(word) for word in word_list)
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
                count for word_set, count in word_counter.items()
                if true_letters.issubset(word_set) and word_set.isdisjoint(false_letters)
            )
            results[combo].append({
                "binary_combo": binary_combo,
                "match_count": match_count
            })
    return results

def find_lowest_non_zero_max(results):
    """
    Finds the combination with the lowest non-zero maximum count.
    """
    lowest_max = float('inf')
    best_combo = None
    for combo, binary_results in results.items():
        max_count = max(r['match_count'] for r in binary_results)
        if 0 < max_count < lowest_max:
            lowest_max = max_count
            best_combo = combo
    return best_combo, lowest_max

def generate_combinations(word_length):
    """
    Generates all possible combinations of feedback statuses.
    """
    states = ['X', 'A', 'G']
    return list(product(states, repeat=word_length))

def map_to_constraints(guess, combination):
    """
    Maps a feedback combination to filtering constraints.
    """
    guess = guess.lower()
    constraints = {
        "In": set(),
        "Out": set(),
        "Known": defaultdict(str),
        "Not": defaultdict(set)
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

def fast_count_matching_words(remaining_combos, candidates):
    """
    Efficiently counts matching words for each combination.
    """
    word_set, letter_index, position_index = create_word_index(candidates)
    
    results = []
    for combo in remaining_combos:
        c = combo["constraints"]
        in_set = {ch.lower() for ch in c["In"]}
        out_set = {ch.lower() for ch in c["Out"]}
        known = {pos: ch.lower() for pos, ch in c["Known"].items()}
        not_set = {pos: {x.lower() for x in letters} for pos, letters in c["Not"].items()}
        
        filtered_words = set(word_set)  # Start with all words
        
        # Apply each constraint using efficient set operations
        for letter in in_set:
            if letter in letter_index:
                filtered_words &= letter_index[letter]
            else:
                filtered_words = set()
                break
        
        if not filtered_words:
            results.append({
                "combination": combo["combination"],
                "matching_words_count": 0,
                "matching_words": []
            })
            continue
        
        for letter in out_set:
            if letter in letter_index:
                filtered_words -= letter_index[letter]
        
        for pos, letter in known.items():
            if pos in position_index and letter in position_index[pos]:
                filtered_words &= position_index[pos][letter]
            else:
                filtered_words = set()
                break
                
        if not filtered_words:
            results.append({
                "combination": combo["combination"],
                "matching_words_count": 0,
                "matching_words": []
            })
            continue
                
        for pos, letters in not_set.items():
            for letter in letters:
                if pos in position_index and letter in position_index[pos]:
                    filtered_words -= position_index[pos][letter]
        
        results.append({
            "combination": combo["combination"],
            "matching_words_count": len(filtered_words),
            "matching_words": list(filtered_words)[:10]  # Limit to 10 for display
        })
        
    return results

def get_max_non_zero_matches(guesses, candidates_df):
    """
    Gets the maximum number of matching words for each guess.
    """
    results = []
    for guess in guesses:
        word_length = len(guess)
        combinations_list = generate_combinations(word_length)
        remaining_combos = [
            {"combination": combo, "constraints": map_to_constraints(guess, combo)}
            for combo in combinations_list
        ]
        filtered_combos = fast_count_matching_words(remaining_combos, candidates_df)
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