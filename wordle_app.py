import streamlit as st
import pandas as pd
import json
import importlib
import time
import os

# Import updated Wordle solver functions and evaluation routines
import wordle_functions as wdl
import expected_value as wev

# Update version info
vers = "1.7.0 (POST GPT UPDATE)"

# Get the path of the main Streamlit script
script_path = os.path.abspath(__file__)

# Get last modified time using the updated function
last_modified = wdl.get_last_modified_timestamp(script_path)

###############################################################################
#                          HELPER FUNCTIONS
###############################################################################
def load_json_file(path: str):
    """Read JSON file and return its contents."""
    with open(path, 'r') as f:
        return json.load(f)

def display_json_state(path: str):
    """Display current JSON state."""
    data = load_json_file(path)
    st.json(data)

def reload_module():
    """Reload wordle_functions module."""
    importlib.reload(wdl)

def display_candidates():
    """Display candidate words if available."""
    if st.session_state["candidates"] is not None:
        st.write(f"Number of candidates: {len(st.session_state['candidates'])}")
        st.dataframe(st.session_state["candidates"], height=400)
    else:
        st.write("No candidates available yet. Submit a guess to see possible words.")

###############################################################################
#                    STREAMLIT STATE INITIALIZATION
###############################################################################
if "wordle_json_path" not in st.session_state:
    st.session_state["wordle_json_path"] = "wordle.json"

if "word_list" not in st.session_state:
    st.session_state["word_list"] = pd.read_csv("word_list.csv")

if "candidates" not in st.session_state:
    st.session_state["candidates"] = None

if "inputs" not in st.session_state:
    st.session_state["inputs"] = None

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

###############################################################################
#                            STREAMLIT LAYOUT
###############################################################################
st.markdown(f"Version: {vers} ({last_modified})")
st.title("Wordle Solver App")

sidebar_placeholder = st.sidebar.empty()

def update_persistent_section():
    with sidebar_placeholder.container():
        st.empty()
        st.subheader("Current State")
        st.subheader("wordle.json State")
        display_json_state(st.session_state["wordle_json_path"])
        st.subheader("Current Candidates")
        display_candidates()
        st.markdown("---")

update_persistent_section()

###############################################################################
#                       SECTION 1 - RESET EVERYTHING
###############################################################################
st.header("1) Reset the Tool")

if st.button("Reset Wordle Tool"):
    wdl.reset_tool(st.session_state["wordle_json_path"])
    st.session_state["candidates"] = None
    st.session_state["inputs"] = None
    st.session_state["guesses"] = None
    st.session_state["summary_df"] = None
    st.session_state["all_candidates"] = None
    update_persistent_section()
    st.success("Tool has been reset.")

###############################################################################
#                     SECTION 2 - GUESSES & FILTERING
###############################################################################
st.header("2) Enter Guess & Result, Then Filter Candidates")

guess_word = st.text_input("Guess Word:", value="aider").strip()
guess_result = st.text_input("Guess Result (e.g., XXXXX, XAGAX):", value="xxxxx").strip()

if st.button("Submit Guess"):
    last_guess = (guess_word + " " + guess_result).upper()
    wdl.update_wordle_json(st.session_state["wordle_json_path"], last_guess)
    st.session_state["inputs"] = wdl.load_wordle_inputs(st.session_state["wordle_json_path"])
    st.session_state["candidates"] = wdl.wordle_filter(st.session_state["inputs"], st.session_state["word_list"])
    st.session_state["guesses"] = None
    st.session_state["summary_df"] = None
    update_persistent_section()
    st.success("Guess submitted and candidates updated.")

    # Store outputs in session state
    st.session_state["num_candidates"] = len(st.session_state["candidates"])
    st.session_state["letters_left"] = wdl.letters_in_candidates(st.session_state["candidates"], st.session_state["inputs"])
    st.session_state["word_count_per_letter"] = wdl.word_count_for_each_letter_left(
        st.session_state["letters_left"], st.session_state["candidates"]['WORD']
    )

if "num_candidates" in st.session_state:
    st.write(f"Number of candidates: {st.session_state['num_candidates']}")

if "letters_left" in st.session_state:
    st.write(f"Unguessed letters left in candidates: {sorted(st.session_state['letters_left'])}")

if "word_count_per_letter" in st.session_state:
    st.write(st.session_state["word_count_per_letter"])

###############################################################################
#               SECTION 3 - IDENTIFY WORDS FOR EVALUATION
###############################################################################
st.header("3) Identify Words for Evaluation")

st.session_state["restrict_to_candidates"] = st.checkbox(
    "Restrict next guess to candidates only?",
    value=st.session_state["restrict_to_candidates"]
)

st.session_state["combo_n"] = st.number_input(
    "How many 'unknown' letters to include (combo_n)?",
    min_value=0, max_value=5,
    value=st.session_state["combo_n"]
)

custom_combo = st.text_input("Or enter a custom letter combo (optional):", value="").strip().lower()

if st.button("Identify Words"):
    candidates = st.session_state["candidates"]
    word_list = st.session_state["word_list"]
    inputs = st.session_state["inputs"]

    # Get unknown letters from candidates
    unknown_letters_set = wdl.letters_in_candidates(candidates, inputs)
    unknown_letters_count = len(unknown_letters_set)
    
    if st.session_state["combo_n"] > unknown_letters_count:
        st.error(f"combo_n ({st.session_state['combo_n']}) exceeds the number of unknown letters ({unknown_letters_count}).")
        st.stop()

    if st.session_state["combo_n"] == 0 and custom_combo == "":
        if st.session_state["restrict_to_candidates"]:
            st.session_state["guesses"] = candidates["WORD"]
            st.session_state["all_candidates"] = True
        else:
            st.warning("Full word list is too large. Please adjust parameters.")
            st.session_state["guesses"] = None

    elif custom_combo:
        if st.session_state["restrict_to_candidates"]:
            filtered = wdl.filter_list_for_chosen_letters(candidates, custom_combo)
        else:
            filtered = wdl.filter_list_for_chosen_letters(word_list, custom_combo)

        if filtered.empty:
            st.error(f"No words found containing the custom combo: {custom_combo.upper()}")
            st.stop()
        else:
            guess_score_df = wdl.get_max_non_zero_matches(filtered["WORD"], candidates)
            st.write(f"Custom Combo '{custom_combo.upper()}' Results:")
            st.write(guess_score_df)
            st.session_state["guesses"] = filtered["WORD"]

    else:
        st.session_state["all_candidates"] = False
        source = candidates if st.session_state["restrict_to_candidates"] else word_list
        all_letters = wdl.letters_in_candidates(source, inputs)
        all_letters_string = ''.join(all_letters)
        combos = wdl.get_n_letter_combinations(all_letters_string, st.session_state["combo_n"])
        filtered_combos = wdl.filter_combos(source["WORD"], combos)
        results2 = wdl.process_binary_combos_with_optimised_counting(filtered_combos, source["WORD"])
        best_combo, best_score = wdl.find_lowest_non_zero_max(results2)
        
        if best_combo is None:
            st.error("No valid letter combination found. Please adjust your parameters.")
            st.stop()

        st.write(f"Best Letter Combo: **{best_combo}** (Worst Case: {best_score})")
        st.session_state["guesses"] = wdl.filter_list_for_chosen_letters(source, best_combo)["WORD"]

    num_guesses = len(st.session_state["guesses"]) if st.session_state["guesses"] is not None else 0
    st.write(f"Number of words in guesses: {num_guesses}")
    if not st.session_state.get("all_candidates", False):
        st.write(st.session_state["guesses"])
    else:
        st.write("All candidates are selected; see candidate list in sidebar")

###############################################################################
#                 SECTION 4 - EVALUATE WORDS (MAX ONLY OR FULL)
###############################################################################
st.header("4) Evaluate Words")

analysis_choice = st.radio("Choose Analysis Type:", ["Max Only", "Full Analysis"])

if st.button("Run Analysis"):
    if st.session_state["guesses"] is None or len(st.session_state["guesses"]) == 0:
        st.warning("No words identified. Please run Section 3 first.")
    else:
        status_placeholder = st.empty()
        status_placeholder.info("Computing... Please wait.")
        start_time = time.time()
        num_words = len(st.session_state["guesses"])
        results = []

        if analysis_choice == "Max Only":
            guess_score_df_candidates = wdl.get_max_non_zero_matches(st.session_state["guesses"], st.session_state["candidates"])
            elapsed_time = time.time() - start_time
            time_per_word = elapsed_time / num_words if num_words > 0 else 0
            status_placeholder.success(f"Completed in {elapsed_time:.2f}s ({time_per_word:.4f}s per word).")
            st.session_state["summary_df"] = guess_score_df_candidates
        else:
            for i, word in enumerate(st.session_state["guesses"], start=1):
                _, median, expected, worst_case, percentiles, _ = wev.evaluate_guess_candidates(word, st.session_state["candidates"])
                results.append({
                    "Word": word, "Max": worst_case, "Expected": expected,
                    "Median": median, "25th Perc": percentiles["25th Percentile"], "75th Perc": percentiles["75th Percentile"]
                })
                if i % 5 == 0 or i == num_words:
                    elapsed_time = time.time() - start_time
                    time_per_word = elapsed_time / i
                    estimated_time_remaining = (num_words - i) * time_per_word
                    status_placeholder.info(f"{i} of {num_words} processed in {elapsed_time:.0f}s ({time_per_word:.2f}s per word). Estimated time remaining: {estimated_time_remaining:.0f}s.")
            st.session_state["summary_df"] = pd.DataFrame(results)
            elapsed_time = time.time() - start_time
            status_placeholder.success(f"Completed in {elapsed_time:.0f}s ({elapsed_time / num_words:.2f}s per word).")

if st.session_state["summary_df"] is not None:
    st.subheader("Ranked Words")
    st.dataframe(st.session_state["summary_df"])

###############################################################################
#                          FINAL DISPLAY / FOOTER
###############################################################################
st.write("---")
st.write("End of Streamlit App – adjust parameters above to interact with the Wordle solver.")
