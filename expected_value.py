import pandas as pd
import numpy as np
from collections import defaultdict

def generate_wordle_feedback(guess, candidate):
    """
    Simulates Wordle feedback for a given guess and candidate word.
    Correctly handles duplicate letters.
    Ensures case insensitivity.
    """
    guess = guess.lower()
    candidate = candidate.lower()

    feedback = ['X'] * 5  # Default all to 'not in word'
    candidate_counts = defaultdict(int)

    # Count occurrences of each letter in candidate
    for char in candidate:
        candidate_counts[char] += 1  

    # First pass: Identify correct letters in the correct position (Green)
    for i in range(5):
        if guess[i] == candidate[i]:
            feedback[i] = 'G'
            candidate_counts[guess[i]] -= 1  # Reduce available count

    # Second pass: Identify correct letters in the wrong position (Amber)
    for i in range(5):
        if feedback[i] == 'G':  
            continue  # Already marked as correct position
        if guess[i] in candidate_counts and candidate_counts[guess[i]] > 0:
            feedback[i] = 'A'
            candidate_counts[guess[i]] -= 1  # Reduce available count

    return "".join(feedback)


def apply_updated_criteria(guess, pattern, candidates):
    """
    Updates filtering criteria based on the feedback pattern and filters candidates.
    Ensures case insensitivity and correct handling of duplicate letters.
    """
    guess = guess.lower()
    pattern = pattern.upper()
    candidates["WORD"] = candidates["WORD"].str.lower()

    known_letters = list("-----")  
    unlocated_letters = set()  
    letters_not_in_word = set()  
    position_exclusions = {i: set() for i in range(5)}

    # Process pattern
    for i, (char, status) in enumerate(zip(guess, pattern)):
        if status == "G":
            known_letters[i] = char  # Fixed letter at this position
        elif status == "A":
            unlocated_letters.add(char)  # Must be in word, but not at this position
            position_exclusions[i].add(char)  # Cannot be at this position
        elif status == "X":
            letters_not_in_word.add(char)  # Must not be in word

    known_letters = "".join(known_letters)  

    # **Quick Fix: Remove conflicting letters from letters_not_in_word**
    letters_not_in_word -= set(known_letters.replace("-", ""))  # Remove known letters
    letters_not_in_word -= unlocated_letters  # Remove unlocated letters

    # Apply filters
    filtered_candidates = candidates.copy()

    # Filter by known letters
    regex_pattern = known_letters.replace("-", ".")
    filtered_candidates = filtered_candidates[filtered_candidates["WORD"].str.match(regex_pattern, case=False, na=False)]

    # Filter by unlocated letters (must be present somewhere)
    for letter in unlocated_letters:
        filtered_candidates = filtered_candidates[filtered_candidates["WORD"].str.contains(letter, case=False, na=False)]

    # Filter by position exclusions (letters marked 'A' cannot be at these positions)
    for i, excluded_letters in position_exclusions.items():
        for letter in excluded_letters:
            filtered_candidates = filtered_candidates[~filtered_candidates["WORD"].str[i].str.contains(letter, case=False, na=False)]

    # **Apply Fix Here: Filter out letters marked 'X' after removing conflicts**
    for letter in letters_not_in_word:
        filtered_candidates = filtered_candidates[~filtered_candidates["WORD"].str.contains(letter, case=False, na=False)]

    return len(filtered_candidates)




def evaluate_guess_candidates(guess, candidates):
    """
    Evaluates a guess against all candidates, computing:
    - Expected (mean) candidates left
    - Median candidates left
    - Worst-case (max) candidates left
    - Distribution statistics
    - Standard deviation
    Ensures case insensitivity.
    """
    guess = guess.lower()
    candidates["WORD"] = candidates["WORD"].str.lower()

    results = []

    for candidate in candidates["WORD"]:
        pattern = generate_wordle_feedback(guess, candidate)
        remaining_count = apply_updated_criteria(guess, pattern, candidates)

        results.append({
            "Candidate Word": candidate,
            "Feedback Pattern": pattern,
            "Remaining Candidates": remaining_count
        })

    results_df = pd.DataFrame(results)

    # Compute summary statistics
    median_candidates_left = results_df["Remaining Candidates"].median()
    expected_candidates_left = results_df["Remaining Candidates"].mean()
    worst_case_candidates_left = results_df["Remaining Candidates"].max()
    standard_deviation = results_df["Remaining Candidates"].std()

    percentiles = {
        "25th Percentile": np.percentile(results_df["Remaining Candidates"], 25),
        "50th Percentile (Median)": median_candidates_left,
        "75th Percentile": np.percentile(results_df["Remaining Candidates"], 75),
        "Worst Case (Max)": worst_case_candidates_left
    }

    return results_df, median_candidates_left, expected_candidates_left, worst_case_candidates_left, percentiles, standard_deviation


def summarize_all_candidates(candidates):
    """
    Runs evaluation for every word in candidates['WORD'] and creates a summary DataFrame.
    Ensures case insensitivity.
    """
    candidates["WORD"] = candidates["WORD"].str.lower()
    summary_results = []

    for guess in candidates["WORD"]:
        _, median, expected, worst_case, percentiles, _ = evaluate_guess_candidates(guess, candidates)

        summary_results.append({
            "Word": guess,
            "Max": worst_case,
            "Expected": expected,
            "Median": median,
            "25th Perc": percentiles["25th Percentile"],
            "75th Perc": percentiles["75th Percentile"]
        })

    return pd.DataFrame(summary_results).sort_values(by="Expected")


def summarize_all_candidates_from_wordlist(candidates, words_to_evaluate):
    """
    Runs evaluation for every word in candidates['WORD'] and creates a summary DataFrame.
    Ensures case insensitivity.
    """
    candidates["WORD"] = candidates["WORD"].str.lower()
    summary_results = []

    if words_to_evaluate is None:
        words_to_evaluate = candidates["WORD"]

    for guess in words_to_evaluate:
        _, median, expected, worst_case, percentiles, _ = evaluate_guess_candidates(guess, candidates)

        summary_results.append({
            "Word": guess,
            "Max": worst_case,
            "Expected": expected,
            "Median": median,
            "25th Perc": percentiles["25th Percentile"],
            "75th Perc": percentiles["75th Percentile"]
        })

    return pd.DataFrame(summary_results).sort_values(by="Expected")