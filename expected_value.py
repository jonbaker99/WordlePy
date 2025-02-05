import pandas as pd
from itertools import product
from collections import defaultdict

def generate_wordle_feedback(guess, candidate):
    """
    Simulates Wordle feedback for a given guess and candidate word.
    """
    feedback = ['X'] * 5  
    candidate_counts = defaultdict(int)
    
    # Identify correct letters in the correct position (Green)
    for i in range(5):
        if guess[i] == candidate[i]:
            feedback[i] = 'G'
        else:
            candidate_counts[candidate[i]] += 1  

    # Identify correct letters in the wrong position (Amber)
    for i in range(5):
        if feedback[i] == 'G':
            continue
        if guess[i] in candidate_counts and candidate_counts[guess[i]] > 0:
            feedback[i] = 'A'
            candidate_counts[guess[i]] -= 1

    return "".join(feedback)


def apply_updated_criteria(guess, pattern, candidates):
    """
    Updates filtering criteria based on the feedback pattern and filters candidates.
    """
    known_letters = list("-----")
    unlocated_letters = set()
    letters_not_in_word = set()
    position_exclusions = {i: set() for i in range(5)}

    # Process pattern
    for i, (char, status) in enumerate(zip(guess, pattern)):
        if status == "G":
            known_letters[i] = char
        elif status == "A":
            unlocated_letters.add(char)
            position_exclusions[i].add(char)
        elif status == "X":
            letters_not_in_word.add(char)

    # Convert known_letters to string for filtering
    known_letters = "".join(known_letters)

    # Apply filters
    filtered_candidates = candidates

    # Filter by known letters
    regex_pattern = known_letters.replace("-", ".")
    filtered_candidates = filtered_candidates[filtered_candidates["WORD"].str.match(regex_pattern)]

    # Filter by unlocated letters
    for letter in unlocated_letters:
        filtered_candidates = filtered_candidates[filtered_candidates["WORD"].str.contains(letter)]

    # Filter by position exclusions
    for i, excluded in position_exclusions.items():
        for letter in excluded:
            filtered_candidates = filtered_candidates[~filtered_candidates["WORD"].str[i].str.contains(letter)]

    # Filter by letters not in the word
    for letter in letters_not_in_word:
        filtered_candidates = filtered_candidates[~filtered_candidates["WORD"].str.contains(letter)]

    return len(filtered_candidates)


def evaluate_guess_candidates(guess, candidates):
    """
    Evaluates the given guess against all candidate words, calculating
    how many candidates would remain for each possible feedback pattern.
    """
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

    # Calculate median and expected (weighted average) candidates left
    median_candidates_left = results_df["Remaining Candidates"].median()
    expected_candidates_left = results_df["Remaining Candidates"].mean()

    return results_df, median_candidates_left, expected_candidates_left
