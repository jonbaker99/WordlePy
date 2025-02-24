import pandas as pd
import json
from collections import Counter, defaultdict
from itertools import combinations, product
import operator
import os
import subprocess
from datetime import datetime

# Helper for normalization
def normalize(word: str) -> str:
    return word.lower()

# Explicit ordinal mapping for positions
ORDINAL_MAP = {0: "1st char", 1: "2nd char", 2: "3rd char", 3: "4th char", 4: "5th char"}

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
        "letters_not_in_word": ""
    }
    with open(file_path, "w") as f:
        json.dump(default_data, f, indent=4)
    print(f"{file_path} has been reset.")

def update_wordle_json(wordle_json_name, input_string):
    """
    Updates the wordle.json file with a new guess and its feedback.
    Uses 'G' for correct letter/position, 'A' for letter present in wrong position, and 'X' for absent.
    """
    with open(wordle_json_name, "r") as file:
        wordle_data = json.load(file)

    word, pattern = input_string.split()
    word = word.upper()
    pattern = pattern.upper()

    for idx, (char, status) in enumerate(zip(word, pattern)):
        if status == "G":
            # Update known_letters at the correct position
            wordle_data["known_letters"] = (
                wordle_data["known_letters"][:idx] + char +
                wordle_data["known_letters"][idx + 1:]
            )
            # Remove from unlocated if present
            wordle_data["unlocated_letters_in_word"] = wordle_data["unlocated_letters_in_word"].replace(char, "")
        elif status in ["A", "X"]:
            key = ORDINAL_MAP[idx]
            current_exclusions = wordle_data["exclusions"].get(key, "")
            if char not in current_exclusions:
                wordle_data["exclusions"][key] = current_exclusions + char
            if status == "A" and char not in wordle_data["unlocated_letters_in_word"]:
                wordle_data["unlocated_letters_in_word"] += char
            elif status == "X" and char not in wordle_data["letters_not_in_word"]:
                wordle_data["letters_not_in_word"] += char

    # Ensure letters in known or unlocated are not in letters_not_in_word
    letters_to_keep = set(wordle_data["known_letters"].replace("-", "")) | set(wordle_data["unlocated_letters_in_word"])
    wordle_data["letters_not_in_word"] = "".join(c for c in wordle_data["letters_not_in_word"] if c not in letters_to_keep)

    with open(wordle_json_name, "w") as file:
        json.dump(wordle_data, file, indent=4)

def load_wordle_inputs(json_file):
    """
    Loads the Wordle configuration from a JSON file.
    """
    with open(json_file, "r") as f:
        config = json.load(f)

    return {
        "exclusions": config["exclusions"],
        "known_letters": config["known_letters"],
        "unlocated_letters_in_word": config["unlocated_letters_in_word"],
        "letters_not_in_word": config["letters_not_in_word"]
    }

def candidates_match_known(word_list: pd.DataFrame, known_letters: str):
    """
    Filters words matching the known_letters pattern (using '-' as a wildcard).
    """
    known_pattern = pd.Series([known_letters]).str.replace(r"[^A-Za-z]", ".", regex=True).iloc[0]
    candidates = word_list[word_list['WORD'].str.match(known_pattern, na=False)]
    return candidates

def filter_words_by_exclusions(word_list, exclusions):
    """
    Filters words based on position-specific exclusions.
    """
    def meets_criteria(word):
        for char_set, char in zip(exclusions.values(), word):
            if char.upper() in char_set.upper():
                return False
        return True
    return word_list[word_list['WORD'].apply(meets_criteria)]

def candidates_all_letters(word_list: pd.DataFrame, known_letters: str, unlocated_letters: str):
    """
    Filters words to include all required letters (both known and unlocated).
    """
    all_letters_in_word = unlocated_letters + pd.Series([known_letters]).str.replace(r"[^A-Za-z]", "", regex=True).iloc[0]
    required_counts = Counter(all_letters_in_word.upper())

    def matches_condition(word):
        word_counts = Counter(word.upper())
        return all(word_counts[ch] >= cnt for ch, cnt in required_counts.items())

    return word_list[word_list['WORD'].apply(matches_condition)]

def candidates_ex_excluded(word_list: pd.DataFrame, letters_not_in_word: str):
    """
    Excludes words containing any letters known not to be in the solution.
    """
    if word_list.empty:
        return word_list
    excluded_letters = set(letters_not_in_word.upper())
    def does_not_contain(word):
        return excluded_letters.isdisjoint(set(word.upper()))
    if "WORD" not in word_list.columns:
        print("Warning: 'WORD' column missing before filtering. Returning empty DataFrame.")
        return pd.DataFrame(columns=["WORD"])
    return word_list[word_list['WORD'].apply(does_not_contain)]

def wordle_filter(inputs, word_list: pd.DataFrame):
    """
    Applies filters (known letters, exclusions, required letters, and letters to exclude)
    to narrow down candidate words.
    """
    known_letters = inputs['known_letters'].upper()
    unlocated_letters = inputs['unlocated_letters_in_word'].upper()
    exclusions = inputs['exclusions']
    letters_not_in_word = inputs['letters_not_in_word'].upper()

    candidates = word_list.copy()

    if len(known_letters) > 0:
        candidates = candidates_match_known(candidates, known_letters)

    if any(bool(chars) for chars in exclusions.values()):
        exclusions = {k: v.upper() for k, v in exclusions.items()}
        candidates = filter_words_by_exclusions(candidates, exclusions)

    if len(unlocated_letters) > 0:
        candidates = candidates_all_letters(candidates, known_letters, unlocated_letters)

    if len(letters_not_in_word) > 0:
        candidates = candidates_ex_excluded(candidates, letters_not_in_word)

    return candidates

def get_unique_letters(word_list):
    """
    Returns a set of unique letters from the words.
    """
    all_letters = ''.join(word_list).upper()
    return set(all_letters)

def letters_in_candidates(word_list, inputs):
    """
    Returns the set of letters still unaccounted for among candidate words.
    """
    unique_letters = get_unique_letters(word_list['WORD'])
    known_letters = inputs['known_letters'] + inputs['unlocated_letters_in_word']
    return unique_letters.difference(set(known_letters.upper()))

def filter_list_for_chosen_letters(words: pd.DataFrame, required_letters: str) -> pd.DataFrame:
    """
    Filters words to include only those containing all required letters.
    """
    required_set = set(required_letters.upper())
    def contains_all(word):
        return required_set.issubset(set(word.upper()))
    return words[words['WORD'].apply(contains_all)]

def preprocess_word_list(word_list):
    """
    Converts a list of words into a Counter keyed by frozenset(letters) for efficient queries.
    """
    return Counter(frozenset(word) for word in word_list)

def get_n_letter_combinations(input_string: str, n: int) -> list:
    """
    Returns all unique n-letter combinations from the input string.
    """
    unique_chars = ''.join(dict.fromkeys(input_string.upper()))
    return [''.join(combo) for combo in combinations(unique_chars, n)]

def filter_combos(word_list, combos):
    """
    Filters combos to include only those where at least one word contains every letter in the combo.
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
    For each viable combo, computes match counts for all binary subsets using a preprocessed word dictionary.
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
    Finds the letter combo whose maximum matching candidate count is lowest (but non-zero).
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
    Parses wordle.json into a criteria dictionary with keys: 'In', 'Out', 'Known', and 'Not'.
    """
    with open(json_path, 'r') as file:
        wordle_data = json.load(file)

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

    for i, ch in enumerate(wordle_data["known_letters"]):
        if ch != '-':
            criteria["Known"][i] = ch

    for pos, excluded_letters in enumerate(wordle_data["exclusions"].values()):
        if excluded_letters:
            criteria["Not"][pos].update(excluded_letters)

    return criteria

def generate_combinations(word_length):
    """
    Generates all possible (X, A, G) patterns for a word of given length.
    """
    states = ['X', 'A', 'G']
    return list(product(states, repeat=word_length))

def map_to_constraints(guess, combination):
    """
    Maps a guess and its feedback combination to constraint dictionaries.
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
    Creates index structures for faster filtering on candidate words.
    """
    if isinstance(candidates, (list, pd.Series)):
        candidates_df = pd.DataFrame({"WORD": candidates})
    elif isinstance(candidates, pd.DataFrame):
        if 'WORD' not in candidates.columns:
            raise KeyError("DataFrame must have 'WORD' column.")
        candidates_df = candidates.copy()
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
    For each combo in remaining_combos, quickly counts how many candidate words match its constraints.
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
        filtered_words = set(all_words)
        for letter in in_set:
            filtered_words &= letter_index[letter]
        for letter in out_set:
            filtered_words -= letter_index[letter]
        for pos, letter in known.items():
            filtered_words &= position_index[pos][letter]
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
    For each guess, generates all (X, A, G) combinations, counts candidate matches,
    and returns a DataFrame sorted by the lowest maximum matching-word count.
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

def filter_by_letter_count(df: pd.DataFrame, letter: str = 'o', comparator: str = '<', count_threshold: int = 2) -> pd.DataFrame:
    """
    Filters words based on the occurrence count of a chosen letter.
    """
    ops_map = {
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '==': operator.eq,
        '!=': operator.ne
    }
    if comparator not in ops_map:
        raise ValueError(f"Invalid comparator '{comparator}'.")
    count_series = df['WORD'].str.lower().str.count(letter.lower())
    mask = ops_map[comparator](count_series, count_threshold)
    return df[mask]

def reset_tool(wordle_json_path):
    """
    Resets the Wordle environment, including the JSON file and solver state.
    """
    reset_wordle_json(wordle_json_path)
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
    Returns a DataFrame showing how many words contain each letter from the set.
    """
    num_words = word_list.count()
    letter_counts = {letter: sum(letter in word for word in word_list) for letter in letters}
    df = pd.DataFrame(list(letter_counts.items()), columns=["Letter", "Count"]).sort_values("Count", ascending=False)
    df["% of Words"] = (df["Count"] / num_words * 100).round(0).astype(int).astype(str) + "%"
    return df

def get_last_modified_timestamp(script_path):
    """Returns last modification timestamp from Git (if available) or file modification time."""
    try:
        timestamp = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%d/%m/%y %H:%M"]
        ).decode("utf-8").strip()
    except:
        timestamp = datetime.fromtimestamp(os.path.getmtime(script_path)).strftime("%d/%m/%y %H:%M")
    return timestamp
