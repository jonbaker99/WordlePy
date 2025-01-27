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
    st.subheader("Current wordle.json State")
    data = load_json_file(path)
    st.json(data)

def reload_module():
    """Convenience function to reload 'wordle_functions' if needed."""
    importlib.reload(wdl)

###############################################################################
#                    STREAMLIT STATE INITIALIZATION
###############################################################################
# We store important variables in session_state so that they persist
# across Streamlit reruns (e.g. when the user clicks a button).

if "wordle_json_path" not in st.session_state:
    st.session_state["wordle_json_path"] = "wordle.json"

if "word_list" not in st.session_state:
    # Load your initial word list
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
st.title("Wordle Solver App")

# Display the current state of wordle.json
display_json_state(st.session_state["wordle_json_path"])

###############################################################################
#                       SECTION 1 - RESET EVERYTHING
###############################################################################
st.header("1) Reset the Tool")

if st.button("Reset Wordle Tool"):
    # Equivalent to Cell 3 in the notebook
    wdl.reset_tool(st.session_state["wordle_json_path"])
    st.session_state["candidates"] = None
    st.session_state["inputs"] = None
    st.success("Tool has been reset.")

    # Show updated JSON
    display_json_state(st.session_state["wordle_json_path"])

###############################################################################
#                     SECTION 2 - GUESSES & FILTERING
###############################################################################
st.header("2) Enter Guess & Result, Then Filter Candidates")

# Inputs for guess_word and guess_result
guess_word = st.text_input("Guess Word:", value="aider").strip()
guess_result = st.text_input("Guess Result (e.g., XXXXX, XAGAX):", value="xxxxx").strip()

if st.button("Submit Guess"):
    # Equivalent to Cells 5 and 6
    last_guess = (guess_word + " " + guess_result).upper()
    wdl.update_wordle_json(st.session_state["wordle_json_path"], last_guess)
    
    # Reload JSON and filter candidates
    st.session_state["inputs"] = wdl.load_wordle_inputs(st.session_state["wordle_json_path"])
    st.session_state["candidates"] = wdl.wordle_filter(st.session_state["inputs"], st.session_state["word_list"])

    st.write(f"Number of candidates after guess: {len(st.session_state['candidates'])}")
    # Display candidates in a scrollable container
    st.dataframe(st.session_state["candidates"], height=300)

    # Show updated JSON
    display_json_state(st.session_state["wordle_json_path"])

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
            st.success(f"Filtered candidates by: {letter_to_filter} {operator_choice} {count_threshold}")
            st.write(f"Number of candidates: {len(st.session_state['candidates'])}")
            st.dataframe(st.session_state["candidates"], height=300)
        else:
            st.warning("No candidates available to filter. Please submit a guess first.")

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

if st.button("Run Next-Guess Calculation (Cell 7)"):
    if st.session_state["candidates"] is None or len(st.session_state["candidates"]) == 0:
        st.warning("No candidates to work with. Please submit a guess first.")
    else:
        inputs = st.session_state["inputs"]
        
        # If combo_n == 0, skip combos entirely and note that we won't compute a 'best combo'.
        if st.session_state["combo_n"] == 0:
            st.session_state["best_combo"] = None
            st.session_state["best_combo_val"] = None
            st.write("`combo_n = 0`. Will use **all candidate words** in Section 4.")
        else:
            # Normal logic for generating combos and finding best combo
            all_letters = wdl.letters_in_candidates(st.session_state["candidates"], inputs)
            all_letters_string = ''.join(all_letters)
            
            combos = wdl.get_n_letter_combinations(
                all_letters_string, 
                st.session_state["combo_n"]
            )

            # Decide which words to use
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

            # best is a tuple: (combo, lowest_non_zero_max)
            st.session_state["best_combo"] = best[0]
            st.session_state["best_combo_val"] = best[1]

            st.write("Best Combo:", best[0])
            st.write("Lowest Non-Zero Max:", best[1])

            # If find_lowest_non_zero_max() returned (None, inf), warn user
            if best[0] is None or best[1] == float('inf'):
                st.warning("No valid combo found (or all combos had zero matches).")


###############################################################################
#                  SECTION 4 - FIND THE BEST WORDS TO USE
###############################################################################
st.header("4) Show Best Words (Cell 8)")

if st.button("Compute & Display Best Words"):
    if st.session_state["candidates"] is None:
        st.warning("No candidates exist. Please submit a guess or reset first.")
    else:
        restrict_to_candidates = st.session_state["restrict_to_candidates"]
        inputs = st.session_state["inputs"]
        word_list = st.session_state["word_list"]
        candidates = st.session_state["candidates"]
        best_combo_letters = st.session_state.get("best_combo", None)

        # If combo_n was 0, or best_combo was invalid, just use all candidates
        if best_combo_letters is None:
            st.write("No best combo available. Using **all candidates**.")
            # If restricting, we effectively already have that in `candidates`.
            # If not restricting, show the entire word_list.
            if restrict_to_candidates:
                guesses = candidates['WORD']
            else:
                guesses = word_list['WORD']
        else:
            # Filter the chosen letters from either the entire list or just candidates
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
            
            # Always do the candidate path, too
            words_from_candidates = wdl.filter_list_for_chosen_letters(
                candidates,
                best_combo_letters
            ).copy()
            if len(words_from_candidates) > 0:
                guesses = words_from_candidates['WORD']
            else:
                guesses = pd.Series([])  # Empty series

        # Now, if we have guesses, rank them
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
