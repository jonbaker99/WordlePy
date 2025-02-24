import pandas as pd
import numpy as np
from collections import defaultdict

def generate_wordle_feedback(guess, candidate):
    """
    Simulates Wordle feedback for a given guess and candidate.
    Correctly handles duplicate letters.
    """
    guess = guess.lower()
    candidate = candidate.lower()
    feedback = ['X'] * 5  # Default to 'X'
    candidate_counts = defaultdict(int)
    for char in candidate:
        candidate_counts[char] += 1  
    # First pass: mark Greens
    for i in range(5):
        if guess[i] == candidate[i]:
            feedback[i] = 'G'
            candidate_counts[guess[i]] -= 1  
    # Second pass: mark Ambers
    for i in range(5):
        if feedback[i] == 'G':
            continue
        if guess[i] in candidate_counts and candidate_counts[guess[i]] > 0:
            feedback[i] = 'A'
            candidate_counts[guess[i]] -= 1  
    return "".join(feedback)

def apply_updated_criteria(guess, pattern, candidates):
    """
    Updates filtering criteria based on feedback and filters candidates.
    Uses a copy of the candidates DataFrame to avoid in-place modifications.
    """
    guess = guess.lower()
    pattern = pattern.upper()
    candidates_copy = candidates.copy()
    candidates_copy["WORD"] = candidates_copy["WORD"].str.lower()

    known_letters = list("-----")
    unlocated_letters = set()
    letters_not_in_word = set()
    position_exclusions = {i: set() for i in range(5)}

    for i, (char, status) in enumerate(zip(guess, pattern)):
        if status == "G":
            known_letters[i] = char
        elif status == "A":
            unlocated_letters.add(char)
            position_exclusions[i].add(char)
        elif status == "X":
            letters_not_in_word.add(char)

    known_letters = "".join(known_letters)
    letters_not_in_word -= set(known_letters.replace("-", ""))
    letters_not_in_word -= unlocated_letters

    # Filter by known letters using a regex pattern
    regex_pattern = known_letters.replace("-", ".")
    filtered = candidates_copy[candidates_copy["WORD"].str.match(regex_pattern, case=False, na=False)]
    
    # Filter by required (unlocated) letters
    for letter in unlocated_letters:
        filtered = filtered[filtered["WORD"].str.contains(letter, case=False, na=False)]
    
    # Exclude words with letters in forbidden positions
    for i, excluded_letters in position_exclusions.items():
        for letter in excluded_letters:
            filtered = filtered[~filtered["WORD"].str[i].str.contains(letter, case=False, na=False)]
    
    # Exclude words containing letters known not to be in the solution
    for letter in letters_not_in_word:
        filtered = filtered[~filtered["WORD"].str.contains(letter, case=False, na=False)]
    
    return len(filtered)

def evaluate_guess_candidates(guess, candidates):
    """
    Evaluates a guess against all candidate words, computing:
      - Expected (mean) candidates left
      - Median candidates left
      - Worst-case (max) candidates left
      - Distribution statistics and standard deviation
    Works on a copy of the candidates DataFrame.
    """
    guess = guess.lower()
    candidates_copy = candidates.copy()
    candidates_copy["WORD"] = candidates_copy["WORD"].str.lower()

    results = []
    for candidate in candidates_copy["WORD"]:
        pattern = generate_wordle_feedback(guess, candidate)
        remaining_count = apply_updated_criteria(guess, pattern, candidates_copy)
        results.append({
            "Candidate Word": candidate,
            "Feedback Pattern": pattern,
            "Remaining Candidates": remaining_count
        })

    results_df = pd.DataFrame(results)
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
    Evaluates every candidate word and returns a summary DataFrame.
    """
    candidates_copy = candidates.copy()
    candidates_copy["WORD"] = candidates_copy["WORD"].str.lower()
    summary_results = []
    for guess in candidates_copy["WORD"]:
        _, median, expected, worst_case, percentiles, _ = evaluate_guess_candidates(guess, candidates_copy)
        summary_results.append({
            "Word": guess,
            "Max": worst_case,
            "Expected": expected,
            "25th Perc": percentiles["25th Percentile"],
            "Median": median,
            "75th Perc": percentiles["75th Percentile"]
        })
    return pd.DataFrame(summary_results).sort_values(by="Expected", ascending=True)

def summarize_all_candidates_from_wordlist(candidates, words_to_evaluate):
    """
    Evaluates specified words from candidates and returns a summary DataFrame.
    """
    candidates_copy = candidates.copy()
    candidates_copy["WORD"] = candidates_copy["WORD"].str.lower()
    summary_results = []
    if words_to_evaluate is None:
        words_to_evaluate = candidates_copy["WORD"]
    for guess in words_to_evaluate:
        _, median, expected, worst_case, percentiles, _ = evaluate_guess_candidates(guess, candidates_copy)
        summary_results.append({
            "Word": guess,
            "Max": worst_case,
            "Expected": expected,
            "25th Perc": percentiles["25th Percentile"],
            "Median": median,
            "75th Perc": percentiles["75th Percentile"]
        })
    return pd.DataFrame(summary_results).sort_values(by="Expected", ascending=True)
