import streamlit as st
import pandas as pd
import json
import os
import time

import wordle_functions as wdl
import expected_value as wev

# Version info
version = "1.8.2"
script_path = os.path.abspath(__file__)
last_modified = wdl.get_last_modified_timestamp(script_path)

###############################################################################
# HELPER FUNCTIONS FOR JSON OPERATIONS
###############################################################################
def load_json_file(path: str) -> dict:
    with open(path, 'r') as f:
        return json.load(f)

def save_json_file(path: str, data: dict):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

###############################################################################
# SIDEBAR UPDATE FUNCTION
###############################################################################
sidebar_placeholder = st.sidebar.empty()

def update_sidebar():
    sidebar_placeholder.empty()  # Clear sidebar first
    with sidebar_placeholder.container():
        st.subheader("Wordle JSON Criteria")
        st.json(load_json_file(st.session_state["wordle_json_path"]))
        st.subheader("Candidate Words")
        if st.session_state["candidates"] is not None:
            st.write(f"Number of candidates: {len(st.session_state['candidates'])}")
            st.dataframe(st.session_state["candidates"])
        else:
            st.write("No candidates available.")
        st.markdown("---")

###############################################################################
# UTILITY: Get Ordinal (for guess number prompts)
###############################################################################
def get_ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

###############################################################################
# STREAMLIT STATE INITIALIZATION
###############################################################################
if "wordle_json_path" not in st.session_state:
    st.session_state["wordle_json_path"] = "wordle.json"  # Make sure wordle.json has a "previous_guesses": [] key.

data = load_json_file(st.session_state["wordle_json_path"])
if "previous_guesses" not in st.session_state:
    st.session_state["previous_guesses"] = data.get("previous_guesses", [])

if "word_list" not in st.session_state:
    st.session_state["word_list"] = pd.read_csv("word_list.csv")

if "candidates" not in st.session_state:
    st.session_state["candidates"] = None

if "inputs" not in st.session_state:
    st.session_state["inputs"] = None

# Initialize additional keys.
if "restrict_to_candidates" not in st.session_state:
    st.session_state["restrict_to_candidates"] = True
if "combo_n" not in st.session_state:
    st.session_state["combo_n"] = 0
if "guesses" not in st.session_state:
    st.session_state["guesses"] = None
if "summary_df" not in st.session_state:
    st.session_state["summary_df"] = None
if "all_candidates" not in st.session_state:
    st.session_state["all_candidates"] = False

# ---- Change 1: Set default guess values on reset ----
if "default_guess" not in st.session_state:
    st.session_state["default_guess"] = "AIDER"
if "default_result" not in st.session_state:
    st.session_state["default_result"] = "XXXXX"

###############################################################################
# MAIN LAYOUT HEADER
###############################################################################
st.markdown(f"**Version: {version}** (Last Modified: {last_modified})")
st.title("Wordle Solver App")
update_sidebar()

##########################
# SECTION 1: RESET TOOL
##########################
st.header("1) Reset the Tool")
if st.button("Reset Wordle Tool"):
    wdl.reset_wordle_json(st.session_state["wordle_json_path"])
    data = load_json_file(st.session_state["wordle_json_path"])
    st.session_state["previous_guesses"] = data["previous_guesses"]
    st.session_state["candidates"] = None
    st.session_state["inputs"] = None
    st.session_state["guesses"] = None
    st.session_state["summary_df"] = None
    st.session_state["all_candidates"] = False
    # ---- Change 1: Set defaults on reset ----
    st.session_state["default_guess"] = "AIDER"
    st.session_state["default_result"] = "XXXXX"
    st.success("Tool has been reset.")
    update_sidebar()
    st.rerun()

##########################
# SECTION 2: ENTER GUESS & UPDATE CRITERIA
##########################
st.header("2) Enter Guess & Result, Then Filter Candidates")

st.subheader("Previous Guesses:")
if st.session_state["previous_guesses"]:
    for i, entry in enumerate(st.session_state["previous_guesses"], 1):
        st.write(f"{i}. {entry}")
else:
    st.write("No previous guesses.")

current_guess_number = len(st.session_state["previous_guesses"]) + 1
guess_prompt = f"Enter {get_ordinal(current_guess_number)} guess"

with st.form(key="guess_form"):
    # ---- Change 1: Prepopulate with default values from session state ----
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
        final_guess = f"{user_guess.upper()} {user_result.upper()}"
        wdl.update_wordle_json(st.session_state["wordle_json_path"], final_guess)
        st.session_state["inputs"] = wdl.load_wordle_inputs(st.session_state["wordle_json_path"])
        st.session_state["candidates"] = wdl.wordle_filter(st.session_state["inputs"], st.session_state["word_list"])
        num_candidates = len(st.session_state["candidates"])
        data = load_json_file(st.session_state["wordle_json_path"])
        if "previous_guesses" not in data:
            data["previous_guesses"] = []
        data["previous_guesses"].append(f"{user_guess.upper()} {user_result.upper()} ({num_candidates})")
        save_json_file(st.session_state["wordle_json_path"], data)
        st.session_state["previous_guesses"] = data["previous_guesses"]
        st.success("Guess submitted and candidates updated.")
        update_sidebar()
        # ---- Clear default so next guess starts empty (except result resets to XXXXX) ----
        st.session_state["default_guess"] = ""
        st.session_state["default_result"] = "XXXXX"
        st.rerun()

if st.session_state["candidates"] is not None:
    st.write(f"Number of candidates: {len(st.session_state['candidates'])}")
    unguessed = wdl.letters_in_candidates(st.session_state["candidates"], st.session_state["inputs"])
    st.write(f"Unguessed letters: {sorted(unguessed)}")
    letter_counts_df = wdl.word_count_for_each_letter_left(unguessed, st.session_state["candidates"]['WORD'])
    st.dataframe(letter_counts_df)

##########################
# SECTION 3: IDENTIFY WORDS FOR EVALUATION
##########################
st.header("3) Identify Words for Evaluation")

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
        # ---- Change 2: Add info message if evaluating the entire candidate list ----
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

##########################
# SECTION 4: EVALUATE WORDS
##########################
st.header("4) Evaluate Words")
analysis_choice = st.radio("Choose Analysis Type:", ["Max Only", "Full Analysis"])
if st.button("Run Analysis"):
    guesses = st.session_state.get("guesses")
    if guesses is None or (hasattr(guesses, "empty") and guesses.empty):
        st.warning("No words to evaluate. Please run Section 3 first.")
    else:
        status_placeholder = st.empty()
        status_placeholder.info("Computing... Please wait.")
        start_time = time.time()
        num_words = len(guesses)
        results = []
        if analysis_choice == "Max Only":
            guess_score_df_candidates = wdl.get_max_non_zero_matches(guesses, st.session_state["candidates"])
            elapsed = time.time() - start_time
            per_word = elapsed / num_words if num_words else 0
            status_placeholder.success(f"Completed in {elapsed:.2f}s ({per_word:.4f}s/word).")
            st.session_state["summary_df"] = guess_score_df_candidates
        else:
            for i, word in enumerate(guesses, start=1):
                _, median, expected, worst_case, perc, _ = wev.evaluate_guess_candidates(word, st.session_state["candidates"])
                results.append({
                    "Word": word,
                    "Max": worst_case,
                    "Expected": expected,
                    "Median": median,
                    "25th Perc": perc["25th Percentile"],
                    "75th Perc": perc["75th Percentile"]
                })
                if i % 5 == 0 or i == num_words:
                    elapsed = time.time() - start_time
                    per_word = elapsed / i
                    remaining = (num_words - i) * per_word
                    status_placeholder.info(f"{i}/{num_words} processed in {elapsed:.0f}s ({per_word:.2f}s/word). Est. {remaining:.0f}s remaining.")
            st.session_state["summary_df"] = pd.DataFrame(results).sort_values(by="Expected", ascending=True)
            elapsed = time.time() - start_time
            status_placeholder.success(f"Completed in {elapsed:.0f}s ({elapsed/num_words:.2f}s/word).")
        update_sidebar()

if st.session_state["summary_df"] is not None:
    st.subheader("Ranked Words")
    st.dataframe(st.session_state["summary_df"])

##########################
# FOOTER
##########################
st.write("---")
st.write("End of Streamlit App – adjust parameters above to interact with the Wordle solver.")
update_sidebar()
