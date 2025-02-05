import streamlit as st
import pandas as pd
import json
import importlib

# Import your consolidated Wordle solver functions
import wordle_functions as wdl, expected_value as wev


wordle_json_path = "wordle.json"
word_list = pd.read_csv("word_list.csv")

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
    importlib.reload(wev)

def display_candidates():
    """Helper function to display candidates if they exist."""
    if st.session_state["candidates"] is not None:
        st.write(f"Number of candidates: {len(st.session_state['candidates'])}")
        # Adjust height to better fit sidebar width
        st.dataframe(st.session_state["candidates"], height=400)
    else:
        st.write("No candidates available yet. Submit a guess to see possible words.")


def update_for_guess(guess: str = "aider", score: str = "xxxxx", wordle_json_path: str = "wordle.json"):
    json_to_update = wordle_json_path
    last_guess = guess + ' ' + score
    last_guess = last_guess.upper()
    wdl.update_wordle_json(json_to_update, last_guess)
    print("Updated wordle.json with last guess")

def update_candidates(wordle_json_path: str = "wordle.json", word_list: pd.DataFrame = word_list):
    inputs = wdl.load_wordle_inputs("wordle.json")
    candidates = wdl.wordle_filter(inputs, word_list)
    print(len(candidates))
    return candidates

def print_criteria(worldle_json_path: str = "wordle.json"):
    with open(worldle_json_path, "r") as file:
        data = json.load(file)  # Load JSON data as a Python dictionary

    # Print formatted JSON
    print(json.dumps(data, indent=4))  # Pretty-print with indentation


###############################################################################
# UPDATING CANDIDATES AND CRITERIA BASED ON A GUESS


reload_modules = True
if reload_modules:
    reload_module()

run_this_section = False

if run_this_section:

    reset = False
    update_guess = False
    get_candidates = False
    print_crit_pre_reset = False
    print_crit_pre_guess = False
    print_crit_post_guess = False


    if print_crit_pre_reset:
        print("\ncriteria before reset")
        print_criteria(wordle_json_path)

    if reset:
        wdl.reset_tool(wordle_json_path)
        print ("\nreset successful\n")
        
    if print_crit_pre_guess:
        print("\ncriteria before guess\n")
        print_criteria(wordle_json_path)


    guess = "aider"
    score = "xxxxa"


    if update_guess:
        update_for_guess(guess, score, wordle_json_path)
        print("\nguess updated")


    if print_crit_post_guess:
        print("\ncriteria after guess")
        print_criteria(wordle_json_path)

    if get_candidates:
        candidates = update_candidates(wordle_json_path, word_list)
        print("\ncandidates updated\n")
        #print(candidates)

# TESTING THE GUESS

run_check_feedback = False

if run_check_feedback:
    temp_guess = "EMCEE"
    temp_answer = "begem"
    print("Guess:", temp_guess, "\nAnswer:", temp_answer)
    print(wev.generate_wordle_feedback(temp_guess, temp_answer))


run_test_guess_section = False

if run_test_guess_section:

    candidates = update_candidates(wordle_json_path, word_list)
    guess = "emcee"

    results_df, median_candidates, expected_candidates, worst_case, percentiles, std_dev = wev.evaluate_guess_candidates(guess, candidates)
    print("guess:", guess)
    print("Median Candidates Left:", median_candidates)
    print("Expected Candidates Left:", expected_candidates)
    print("Worst-Case Candidates Left:", worst_case)
    print("Percentiles:", percentiles)
    print("Standard Deviation:", std_dev)
    print(results_df)


run_test__whole_list_section = True

if run_test__whole_list_section:

    candidates = update_candidates(wordle_json_path, word_list)
    #guess = "CUTEY"

    summary_df = wev.summarize_all_candidates(candidates)
    print(summary_df)
