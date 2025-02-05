import streamlit as st
import pandas as pd
import json
import importlib
import time  # Import time module for timing

# Import your consolidated Wordle solver functions
import wordle_functions as wdl, expected_value as wev

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

if "summary_df" not in st.session_state:
    st.session_state["summary_df"] = None

###############################################################################
#                            STREAMLIT LAYOUT
###############################################################################
# **Updated Version Number**
st.markdown("**Version: 1.3.1**")

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
    st.session_state["summary_df"] = None
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
    st.session_state["summary_df"] = None
    update_persistent_section()
    st.success("Guess submitted and candidates updated.")

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

###############################################################################
#                  SECTION 4 - FIND THE BEST WORDS TO USE
###############################################################################
st.header("4) Show Best Words")

if st.button("Compute & Display Best Words"):
    if st.session_state["candidates"] is None:
        st.warning("No candidates exist. Please submit a guess or reset first.")
    else:
        restrict_to_candidates = st.session_state["restrict_to_candidates"]
        candidates = st.session_state["candidates"]

        if restrict_to_candidates:
            guesses = candidates['WORD']
        else:
            guesses = st.session_state["word_list"]['WORD']

        if guesses is not None and len(guesses) > 0:
            guess_score_df_candidates = wev.summarize_all_candidates(candidates)
            st.subheader("Ranked Words")
            st.dataframe(guess_score_df_candidates)
        else:
            st.write("No guesses to rank.")

###############################################################################
#                   SECTION 5 - SHOW SUMMARY DATAFRAME
###############################################################################
st.header("5) Compute & Display Summary Statistics")

if st.button("Generate Summary Statistics"):
    if st.session_state["candidates"] is None:
        st.warning("No candidates exist. Please submit a guess or reset first.")
    else:
        # Show a message to indicate that computation has started
        status_placeholder = st.empty()
        status_placeholder.info("Computing summary statistics... Please wait.")

        # Capture start time
        start_time = time.time()

        # Get the candidate words
        candidate_words = st.session_state["candidates"]["WORD"].tolist()
        num_candidates = len(candidate_words)

        # Initialize an empty DataFrame to store results
        summary_results = []

        # Loop through each word, computing summary
        for i, word in enumerate(candidate_words, start=1):
            _, median, expected, worst_case, percentiles, _ = wev.evaluate_guess_candidates(word, st.session_state["candidates"])
            
            summary_results.append({
                "Word": word,
                "Max": worst_case,
                "Expected": expected,
                "Median": median,
                "25th Perc": percentiles["25th Percentile"],
                "75th Perc": percentiles["75th Percentile"]
            })

            # Update progress every 5 words to avoid slowing down UI
            if i % 5 == 0 or i == num_candidates:
                elapsed_time = time.time() - start_time
                avg_time_per_word = elapsed_time / i
                estimated_time_remaining = (num_candidates - i) * avg_time_per_word

                status_placeholder.info(
                    f"{i} of {num_candidates} words processed in {elapsed_time:.2f} seconds "
                    f"({avg_time_per_word:.4f} seconds per word)\n"
                    f"Estimated time remaining: {estimated_time_remaining:.2f} seconds"
                )

        # Store results in session state
        st.session_state["summary_df"] = pd.DataFrame(summary_results).sort_values(by="Expected")

        # Final status message
        elapsed_time = time.time() - start_time
        status_placeholder.success(f"{num_candidates} candidates evaluated in {elapsed_time:.2f} seconds "
                                   f"({elapsed_time / num_candidates:.4f} seconds per candidate).")

# Display the summary DataFrame if it exists
if st.session_state["summary_df"] is not None:
    st.subheader("Summary Statistics for Candidates")
    st.dataframe(st.session_state["summary_df"])

###############################################################################
#                          FINAL DISPLAY / FOOTER
###############################################################################
st.write("---")
st.write("End of Streamlit App – adjust parameters above to interact with the Wordle solver.")
