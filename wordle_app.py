import streamlit as st
import pandas as pd
import json
import importlib

# Import your consolidated Wordle solver functions
import wordle_functions as wdl

###############################################################################
#                          HELPER FUNCTIONS
###############################################################################
def load_json_file(path: str):
    """Utility to read a JSON file and return its contents."""
    with open(path, 'r') as f:
        return json.load(f)

def display_json_state(path: str):
    """Displays the current JSON file in a Streamlit JSON widget."""
    data = load_json_file(path)
    st.json(data)

def reload_module():
    """Convenience function to reload 'wordle_functions' if needed."""
    importlib.reload(wdl)

def display_candidates():
    """Helper function to display candidates if they exist."""
    if st.session_state["candidates"] is not None:
        st.write(f"Number of candidates: {len(st.session_state['candidates'])}")
        # Adjust height to better fit sidebar width
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

###############################################################################
#                            STREAMLIT LAYOUT
###############################################################################
# Version number at the top
st.markdown("**Version: 1.2.0**")

st.title("Wordle Solver App")

# Create an empty sidebar container that we can clear and update
sidebar_placeholder = st.sidebar.empty()

def update_persistent_section():
    with sidebar_placeholder.container():
        # Clear previous content by creating a new container
        st.empty()
        
        st.subheader("Current State")
        
        st.subheader("wordle.json State")
        display_json_state(st.session_state["wordle_json_path"])
        
        st.subheader("Current Candidates")
        display_candidates()
        
        st.markdown("---")

# Initial display
update_persistent_section()

###############################################################################
#                       SECTION 1 - RESET EVERYTHING
###############################################################################
st.header("1) Reset the Tool")

if st.button("Reset Wordle Tool"):
    wdl.reset_tool(st.session_state["wordle_json_path"])
    st.session_state["candidates"] = None
    st.session_state["inputs"] = None
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
    update_persistent_section()
    st.success("Guess submitted and candidates updated.")

st.subheader("Optional: Filter by Letter Count")
col_letter, col_op, col_num, col_btn = st.columns([1, 1, 1, 1])

with col_letter:
    letter_to_filter = st.text_input("Letter:", value="o", max_chars=1).strip()

with col_op:
    operator_choice = st.selectbox("Comparison", [">", "<", ">=", "<=", "==", "!="])

with col_num:
    count_threshold = st.number_input("Threshold", min_value=0, max_value=10, value=2)

with col_btn:
    if st.button("Apply Letter Filter"):
        if st.session_state["candidates"] is not None:
            st.session_state["candidates"] = wdl.filter_by_letter_count(
                st.session_state["candidates"], 
                letter=letter_to_filter, 
                comparator=operator_choice, 
                count_threshold=count_threshold
            )
            update_persistent_section()
            st.success(f"Filtered candidates by: {letter_to_filter} {operator_choice} {count_threshold}")

###############################################################################
#               SECTION 3 - RESTRICT / NARROW DOWN NEXT GUESS
###############################################################################
st.header("3) Narrow Down Next Guess")

st.session_state["restrict_to_candidates"] = st.checkbox(
    "Restrict next guess to candidates only?",
    value=st.session_state["restrict_to_candidates"]
)

st.session_state["combo_n"] = st.number_input(
    "How many 'unknown' letters to include (combo_n)?",
    min_value=0, max_value=5,
    value=st.session_state["combo_n"]
)

if st.button("Run Next-Guess Calculation"):
    if st.session_state["candidates"] is None or len(st.session_state["candidates"]) == 0:
        st.warning("No candidates to work with. Please submit a guess first.")
    else:
        inputs = st.session_state["inputs"]
        
        if st.session_state["combo_n"] == 0:
            st.session_state["best_combo"] = None
            st.session_state["best_combo_val"] = None
            st.write("`combo_n = 0`. Will use **all candidate words** in Section 4.")
        else:
            all_letters = wdl.letters_in_candidates(st.session_state["candidates"], inputs)
            all_letters_string = ''.join(all_letters)
            
            combos = wdl.get_n_letter_combinations(
                all_letters_string, 
                st.session_state["combo_n"]
            )

            if st.session_state["restrict_to_candidates"]:
                words = st.session_state["candidates"]['WORD']
            else:
                words = st.session_state["word_list"]['WORD']

            filtered_combos = wdl.filter_combos(words, combos)
            results2 = wdl.process_binary_combos_with_optimised_counting(
                filtered_combos,
                st.session_state["candidates"]['WORD']
            )
            best = wdl.find_lowest_non_zero_max(results2)

            st.session_state["best_combo"] = best[0]
            st.session_state["best_combo_val"] = best[1]

            st.write("Best Combo:", best[0])
            st.write("Lowest Non-Zero Max:", best[1])

            if best[0] is None or best[1] == float('inf'):
                st.warning("No valid combo found (or all combos had zero matches).")

###############################################################################
#                  SECTION 4 - FIND THE BEST WORDS TO USE
###############################################################################
st.header("4) Show Best Words")

if st.button("Compute & Display Best Words"):
    if st.session_state["candidates"] is None:
        st.warning("No candidates exist. Please submit a guess or reset first.")
    else:
        restrict_to_candidates = st.session_state["restrict_to_candidates"]
        inputs = st.session_state["inputs"]
        word_list = st.session_state["word_list"]
        candidates = st.session_state["candidates"]
        best_combo_letters = st.session_state.get("best_combo", None)

        if best_combo_letters is None:
            st.write("No best combo available. Using **all candidates**.")
            if restrict_to_candidates:
                guesses = candidates['WORD']
            else:
                guesses = word_list['WORD']
        else:
            if not restrict_to_candidates:
                words_from_wordlist = wdl.filter_list_for_chosen_letters(
                    word_list,
                    best_combo_letters
                ).copy()
                if len(words_from_wordlist) > 0:
                    guesses = words_from_wordlist['WORD']
                    guess_score_df_wordlist = wdl.get_max_non_zero_matches(guesses, candidates)
                    st.subheader("Ranked words from whole list")
                    st.dataframe(guess_score_df_wordlist.head(10))
                else:
                    st.write("No scored guesses from wordlist.")
            else:
                words_from_wordlist = None
            
            words_from_candidates = wdl.filter_list_for_chosen_letters(
                candidates,
                best_combo_letters
            ).copy()
            if len(words_from_candidates) > 0:
                guesses = words_from_candidates['WORD']
            else:
                guesses = pd.Series([])

        if guesses is not None and len(guesses) > 0:
            guess_score_df_candidates = wdl.get_max_non_zero_matches(guesses, candidates)
            st.subheader("Ranked Words")
            st.dataframe(guess_score_df_candidates)
        else:
            st.write("No guesses to rank.")

###############################################################################
#                          FINAL DISPLAY / FOOTER
###############################################################################
st.write("---")
st.write("End of Streamlit App – adjust parameters above to interact with the Wordle solver.")