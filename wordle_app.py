import streamlit as st
import pandas as pd
import os
import time
import json
from collections import Counter

import wordle_functions as wdl
import expected_value as wev
from second_guess_retrieval import get_top_words_for_pattern

# Version info
version = "2.0.2 CLAUDE"
script_path = os.path.abspath(__file__)
last_modified = wdl.get_last_modified_timestamp(script_path)

###############################################################################
# SIDEBAR UPDATE FUNCTION
###############################################################################
sidebar_placeholder = st.sidebar.empty()

def update_sidebar():
    """Update the sidebar with current state information."""
    sidebar_placeholder.empty()  # Clear sidebar first
    with sidebar_placeholder.container():
        st.subheader("Wordle Criteria")
        st.json(st.session_state["wordle_criteria"])
        st.subheader("Candidate Words")
        if st.session_state["candidates"] is not None:
            st.write(f"Number of candidates: {len(st.session_state['candidates'])}")
            st.dataframe(st.session_state["candidates"])
        else:
            st.write("No candidates available.")
        st.markdown("---")

###############################################################################
# HELPER FUNCTIONS: Workflow shortcuts to run analysis
###############################################################################
def run_analysis(guesses, analysis_type="Max Only"):
    """
    UI wrapper for running analysis with Streamlit progress reporting.
    """
    if guesses is None or (hasattr(guesses, "empty") and guesses.empty):
        st.warning("No words to evaluate.")
        return None
    
    status_placeholder = st.empty()
    status_placeholder.info(f"Running {analysis_type}...")
    
    if analysis_type == "Max Only":
        result_df, elapsed, per_word = wev.perform_max_analysis(guesses, st.session_state["candidates"])
        status_placeholder.success(f"Analysis completed in {elapsed:.2f}s ({per_word:.4f}s/word).")
    else:  # Full Analysis
        result_df, elapsed, per_word = wev.perform_full_analysis(guesses, st.session_state["candidates"])
        status_placeholder.success(f"Analysis completed in {elapsed:.0f}s ({per_word:.2f}s/word).")
    
    st.session_state["summary_df"] = result_df
    update_sidebar()
    return result_df

def run_max_analysis():
    """Run the 'Max Only' analysis on the current guesses."""
    return run_analysis(st.session_state.get("guesses"), "Max Only")

def run_full_analysis():
    """Run the 'Full Analysis' on the current guesses."""
    return run_analysis(st.session_state.get("guesses"), "Full Analysis")

###############################################################################
# SESSION STATE INITIALIZATION
###############################################################################
def initialize_session_state():
    """Initialize all session state variables."""
    # Default Wordle criteria
    default_criteria = {
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
    
    # Try to load from file first for backward compatibility
    try:
        json_criteria = wdl.load_json_file("wordle.json")
        initial_criteria = json_criteria
    except:
        initial_criteria = default_criteria
    
    defaults = {
        "wordle_criteria": initial_criteria,  # Store criteria in session state
        "previous_guesses": initial_criteria.get("previous_guesses", []),
        "word_list": pd.read_csv("word_list.csv"),
        "candidates": None,
        "inputs": None,
        "restrict_to_candidates": True,
        "combo_n": 0,
        "guesses": None,
        "summary_df": None,
        "all_candidates": False,
        "default_guess": "AIDER",
        "default_result": "XXXXX",
        "analysis_choice": "Max Only",
        "aider_recommendations": None  # New state for AIDER recommendations
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

###############################################################################
# UI SECTION RENDERING FUNCTIONS
###############################################################################
def render_reset_section():
    """Render the reset tool section."""
    st.header("1) Reset the Tool")
    if st.button("Reset Wordle Tool"):
        # Reset criteria in session state
        st.session_state["wordle_criteria"] = {
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
        st.session_state["previous_guesses"] = []
        st.session_state["candidates"] = None
        st.session_state["inputs"] = None
        st.session_state["guesses"] = None
        st.session_state["summary_df"] = None
        st.session_state["all_candidates"] = False
        st.session_state["default_guess"] = "AIDER"
        st.session_state["default_result"] = "XXXXX"
        st.session_state["aider_recommendations"] = None  # Reset recommendations
        st.success("Tool has been reset.")
        update_sidebar()
        st.rerun()

def update_wordle_criteria(criteria, word, pattern):
    """
    Updates the wordle criteria with a new guess and its feedback.
    This is an in-memory version of update_wordle_json function.
    """
    word = word.upper()
    pattern = pattern.upper()
    
    # Pre-calculate frequency of 'A' statuses for each letter in the guess.
    a_counts = Counter([ch for ch, s in zip(word, pattern) if s.upper() == "A"])
    
    for idx, (char, status) in enumerate(zip(word, pattern)):
        if status == "G":
            # Place the letter in the correct position.
            criteria["known_letters"] = (
                criteria["known_letters"][:idx] + char + criteria["known_letters"][idx+1:]
            )
            # Remove this letter from unlocated_letters if present.
            criteria["unlocated_letters_in_word"] = criteria["unlocated_letters_in_word"].replace(char, "")
        elif status in ["A", "X"]:
            key = f"{idx+1}{['st','nd','rd'][idx] if idx < 3 else 'th'} char"
            current_exclusions = criteria["exclusions"].get(key, "")
            if char not in current_exclusions:
                criteria["exclusions"][key] = current_exclusions + char
            if status == "A":
                # For an amber, allow additional occurrences beyond those already placed in known_letters.
                count_known = criteria["known_letters"].upper().count(char)
                count_unlocated = criteria["unlocated_letters_in_word"].upper().count(char)
                # If there are more 'A' statuses than what is already known, add one occurrence.
                if count_unlocated < a_counts[char] - count_known:
                    criteria["unlocated_letters_in_word"] += char
            elif status == "X":
                if char not in criteria["letters_not_in_word"]:
                    criteria["letters_not_in_word"] += char
                    
    # Clean up letters_not_in_word by removing letters present in known or unlocated.
    letters_to_keep = set(criteria["known_letters"].replace("-", "")) | set(criteria["unlocated_letters_in_word"])
    criteria["letters_not_in_word"] = "".join(c for c in criteria["letters_not_in_word"] if c not in letters_to_keep)
    
    return criteria

def extract_inputs_from_criteria(criteria):
    """
    Extract the inputs needed for wordle_filter from the criteria.
    """
    return {
        "exclusions": criteria["exclusions"],
        "known_letters": criteria["known_letters"],
        "unlocated_letters_in_word": criteria["unlocated_letters_in_word"],
        "letters_not_in_word": criteria["letters_not_in_word"]
    }

def render_guess_section():
    """Render the guess and result input section."""
    st.header("2) Enter Guess & Result, Then Filter Candidates")

    st.subheader("Previous Guesses:")
    if st.session_state["previous_guesses"]:
        for i, entry in enumerate(st.session_state["previous_guesses"], 1):
            st.write(f"{i}. {entry}")
    else:
        st.write("No previous guesses.")

    current_guess_number = len(st.session_state["previous_guesses"]) + 1
    guess_prompt = f"Enter {wdl.get_ordinal(current_guess_number)} guess"

    with st.form(key="guess_form"):
        user_guess = st.text_input(guess_prompt, value=st.session_state.get("default_guess", ""))
        user_result = st.text_input("Enter result (5 characters: X, A, G):", value=st.session_state.get("default_result", ""))
        submitted = st.form_submit_button("Submit Guess")

    if submitted:
        user_guess = user_guess.strip()
        user_result = user_result.strip()
        if len(user_guess) != 5:
            st.error("Guess word must be exactly 5 letters.")
        elif user_guess.lower() not in st.session_state["word_list"]["WORD"].str.lower().values:
            st.error("Guess word must appear in the word list.")
        elif len(user_result) != 5 or not all(ch.upper() in ['X', 'A', 'G'] for ch in user_result):
            st.error("Guess result must be exactly 5 characters long (only X, A, or G).")
        else:
            # Update criteria in session state
            final_guess = f"{user_guess.upper()} {user_result.upper()}"
            st.session_state["wordle_criteria"] = update_wordle_criteria(
                st.session_state["wordle_criteria"].copy(), 
                user_guess, 
                user_result
            )
            
            # Extract inputs for filtering
            st.session_state["inputs"] = extract_inputs_from_criteria(st.session_state["wordle_criteria"])
            
            # Filter candidates
            st.session_state["candidates"] = wdl.wordle_filter(st.session_state["inputs"], st.session_state["word_list"])
            num_candidates = len(st.session_state["candidates"])
            
            # Update previous guesses
            if "previous_guesses" not in st.session_state["wordle_criteria"]:
                st.session_state["wordle_criteria"]["previous_guesses"] = []
            
            st.session_state["wordle_criteria"]["previous_guesses"].append(
                f"{user_guess.upper()} {user_result.upper()} ({num_candidates})"
            )
            st.session_state["previous_guesses"] = st.session_state["wordle_criteria"]["previous_guesses"]
            
            st.success("Guess submitted and candidates updated.")
            
            # If this was the second guess, clear AIDER recommendations
            if len(st.session_state["previous_guesses"]) > 1:
                st.session_state["aider_recommendations"] = None
            
            update_sidebar()
            st.session_state["default_guess"] = ""
            st.session_state["default_result"] = "XXXXX"
            st.rerun()

    # Display number of candidates regardless of what buttons are shown
    if st.session_state["candidates"] is not None:
        num_candidates = len(st.session_state["candidates"])
        st.write(f"Number of candidates: {num_candidates}")
    
    # Conditional section: Either show AIDER recommendations or shortcut buttons
    is_first_aider_guess = (len(st.session_state["previous_guesses"]) == 1 and 
                          "AIDER" in st.session_state["previous_guesses"][0].upper())
    
    if is_first_aider_guess:
        # AIDER recommendations section
        st.markdown("---")
        st.subheader("AIDER First Guess Recommendations")
        
        # Extract the pattern from the previous guess
        guess_pattern = st.session_state["previous_guesses"][0].split()[1]
        
        if st.button("Show Top 20 Recommended Second Guesses"):
            try:
                recommendations = get_top_words_for_pattern(guess_pattern, n=20)
                if not recommendations.empty:
                    st.session_state["aider_recommendations"] = recommendations
                else:
                    st.error(f"No recommendations found for pattern '{guess_pattern}'")
            except Exception as e:
                st.error(f"Error retrieving recommendations: {str(e)}")
        
        # Display recommendations if available
        if st.session_state["aider_recommendations"] is not None:
            st.dataframe(st.session_state["aider_recommendations"])
            st.info("These are the top 20 recommended second guesses based on analysis of the AIDER first guess pattern.")
    
    # Shortcut Buttons for Analysis – only show if not first AIDER guess and candidates exist
    elif st.session_state["candidates"] is not None:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Shortcut: Run Full Analysis on All Candidates"):
                st.session_state["guesses"] = st.session_state["candidates"]["WORD"]
                st.session_state["analysis_choice"] = "Full Analysis"
                run_full_analysis()
        
        with col2: 
            if st.button("Shortcut: Run Max Analysis on All Candidates"):
                st.session_state["guesses"] = st.session_state["candidates"]["WORD"]
                st.session_state["analysis_choice"] = "Max Only"
                run_max_analysis()

def render_identify_words_section():
    """Render the section for identifying words to evaluate."""
    st.header("3) Identify Words for Evaluation")

    # Display remaining letters & frequency
    if st.session_state["candidates"] is not None:  
        unguessed = wdl.letters_in_candidates(st.session_state["candidates"], st.session_state["inputs"])
        st.write(f"Unguessed letters: {sorted(unguessed)}")
        letter_counts_df = wdl.word_count_for_each_letter_left(unguessed, st.session_state["candidates"]['WORD'])
        st.dataframe(letter_counts_df)

    st.session_state["restrict_to_candidates"] = st.checkbox(
        "Restrict next guess to candidates only?",
        value=st.session_state.get("restrict_to_candidates", True)
    )
    st.session_state["combo_n"] = st.number_input(
        "How many 'unknown' letters to include (combo_n)?",
        min_value=0, max_value=5,
        value=st.session_state.get("combo_n", 0)
    )
    custom_combo = st.text_input("Or enter a custom letter combo (optional):", "").strip().lower()

    if st.button("Identify Words"):
        if st.session_state["candidates"] is None:
            st.warning("No candidates to filter. Please submit at least one guess first.")
        else:
            candidates = st.session_state["candidates"]
            word_list = st.session_state["word_list"]
            inputs = st.session_state["inputs"]
            unknown_letters_set = wdl.letters_in_candidates(candidates, inputs)
            unknown_letters_count = len(unknown_letters_set)
            
            if st.session_state["combo_n"] == 0 and not custom_combo and st.session_state["restrict_to_candidates"]:
                st.info("Evaluating entire candidate list.")
                st.session_state["guesses"] = candidates["WORD"]
                st.session_state["all_candidates"] = True
            elif st.session_state["combo_n"] > unknown_letters_count:
                st.error(f"combo_n ({st.session_state['combo_n']}) exceeds unknown letters ({unknown_letters_count}).")
            else:
                if st.session_state["combo_n"] == 0 and not custom_combo:
                    if st.session_state["restrict_to_candidates"]:
                        st.session_state["guesses"] = candidates["WORD"]
                        st.session_state["all_candidates"] = True
                    else:
                        st.warning("Full word list is too large. Please adjust parameters.")
                        st.session_state["guesses"] = None
                elif custom_combo:
                    source_df = candidates if st.session_state["restrict_to_candidates"] else word_list
                    filtered = wdl.filter_list_for_chosen_letters(source_df, custom_combo)
                    if filtered.empty:
                        st.error(f"No words found containing {custom_combo.upper()}.")
                    else:
                        guess_score_df = wdl.get_max_non_zero_matches(filtered["WORD"], candidates)
                        st.write(f"Custom Combo '{custom_combo.upper()}' Results:")
                        st.dataframe(guess_score_df)
                        st.session_state["guesses"] = filtered["WORD"]
                else:
                    st.session_state["all_candidates"] = False
                    source_df = candidates if st.session_state["restrict_to_candidates"] else word_list
                    all_letters = wdl.letters_in_candidates(source_df, inputs)
                    combos = wdl.get_n_letter_combinations("".join(all_letters), st.session_state["combo_n"])
                    filtered_combos = wdl.filter_combos(source_df["WORD"], combos)
                    results2 = wdl.process_binary_combos_with_optimised_counting(filtered_combos, source_df["WORD"])
                    best_combo, best_score = wdl.find_lowest_non_zero_max(results2)
                    if best_combo is None:
                        st.error("No valid letter combination found.")
                    else:
                        st.write(f"Best Letter Combo: {best_combo} (Worst Case: {best_score})")
                        st.session_state["guesses"] = wdl.filter_list_for_chosen_letters(source_df, best_combo)["WORD"]
            update_sidebar()

def render_evaluate_words_section():
    """Render the section for evaluating words."""
    st.header("4) Evaluate Words")

    # Initialize if needed
    if "analysis_choice" not in st.session_state:
        st.session_state["analysis_choice"] = "Max Only"

    # Determine default index
    default_index = 0 if st.session_state["analysis_choice"] == "Max Only" else 1

    analysis_choice = st.radio("Choose Analysis Type:", 
                            ["Max Only", "Full Analysis"], 
                            index=default_index,
                            key="analysis_choice")

    if st.button("Run Analysis"):
        run_analysis(st.session_state.get("guesses"), analysis_choice)

    if st.session_state["summary_df"] is not None:
        st.subheader("Ranked Words")
        st.dataframe(st.session_state["summary_df"])

###############################################################################
# MAIN APP
###############################################################################
def main():
    """Main app function."""
    st.markdown(f"**Version: {version}** (Last Modified: {last_modified})")
    st.title("Wordle Solver App")
    
    # Initialize session state
    initialize_session_state()
    
    # Update sidebar
    update_sidebar()
    
    # Render UI sections
    render_reset_section()
    render_guess_section()
    render_identify_words_section()
    render_evaluate_words_section()
    
    # Footer
    st.write("---")
    st.write("End of Streamlit App – adjust parameters above to interact with the Wordle solver.")
    update_sidebar()

if __name__ == "__main__":
    main()