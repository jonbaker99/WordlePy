import pandas as pd, json
from collections import Counter

def reset_wordle_json(file_path: str):
    """
    Resets the wordle.json file to its default state.

    :param file_path: Path to the wordle.json file
    """
    # Define the default structure
    default_data = {
        "exclusions": {
            "1st char": "",
            "2nd char": "",
            "3rd char": "",
            "4th char": "",
            "5th char": ""
        },
        "known_letters": "-----",
        "unlocated_letters_in_word": "",
        "letters_not_in_word": ""
    }
    

    # Overwrite the file with the default structure
    with open(file_path, "w") as f:
        json.dump(default_data, f, indent=4)
    print(f"{file_path} has been reset.")


def load_wordle_inputs(json_file):
    """
    Loads inputs for the Wordle helper tool from a JSON file.

    :param json_file: Path to the JSON file
    :return: Dictionary with exclusions, known_letters, letters_in_word, and letters_not_in_word
    """
    # Load the JSON file
    with open(json_file, "r") as f:
        config = json.load(f)

    # Extract inputs
    exclusions = config["exclusions"]
    known_letters = config["known_letters"]
    unlocated_letters_in_word = config["unlocated_letters_in_word"]
    letters_not_in_word = config["letters_not_in_word"]

    # # Convert exclusions dictionary into a list for easier use
    # exclusions_list = [
    #     exclusions["1st char"],
    #     exclusions["2nd char"],
    #     exclusions["3rd char"],
    #     exclusions["4th char"],
    #     exclusions["5th char"]
    # ]



    # Return structured inputs
    return {
        # "exclusions": exclusions_list,
         "exclusions": exclusions,
        "known_letters": known_letters,
        "unlocated_letters_in_word": unlocated_letters_in_word,
        "letters_not_in_word": letters_not_in_word
    }


# FIRSTLY MATCH THE KNOWN LETTER PATTERN

def candidates_match_known(word_list: pd.DataFrame, known_letters: str): 
    """
    Filters the word list based on the known_letters pattern.

    :param word_list: DataFrame containing the words
    :param known_letters: String representing the known letters with wildcards (e.g., "---NY")
    :return: Filtered DataFrame with matching words
    """
    known_pattern = pd.Series([known_letters]).str.replace(r"[^A-Za-z]", ".", regex=True).iloc[0]
    candidates = word_list[word_list['WORD'].str.match(known_pattern,na=False)]
    return candidates


# WORDS WITH ALL KNOWN AND UNLOCATED LETTERS

def candidates_all_letters(word_list: pd.DataFrame, known_letters: str, unlocated_letters: str):

    # Add the known letters (GREEN) to the unlocated letters (AMBER)
    letters_in_known_letters = pd.Series([known_letters]).str.replace(r"[^A-Za-z]", "", regex=True).iloc[0]
    all_letters_in_word = unlocated_letters + letters_in_known_letters
    
    # Count the occurrences of each letter in letters_in_word
    required_counts = Counter(all_letters_in_word.upper())

    # Define a function to check if a word satisfies the condition
    def matches_condition(word):
        word_counts = Counter(word.upper())
        return all(word_counts[char] >= count for char, count in required_counts.items())

    # Apply the filter to the word list
    candidates = word_list[word_list['WORD'].apply(matches_condition)]

    return candidates


# REMOVE WORDS WITH LETTERS IN THE WRONG PLACE

def filter_words_by_exclusions(word_list, exclusions):
    """
    Filters a DataFrame of 5-letter words based on exclusion criteria.
    
    Args:
        word_list (pd.DataFrame): A DataFrame with a single column 'WORD' containing 5-letter words.
        exclusions (dict): A dictionary with keys like '1st char', '2nd char', etc., and values as strings of excluded characters.
    
    Returns:
        pd.DataFrame: A filtered DataFrame containing words that meet the criteria.
    """
    # Function to check exclusion criteria for a single word
    def meets_criteria(word):
        for idx, (char_set, char) in enumerate(zip(exclusions.values(), word), start=1):
            if char in char_set:
                return False
        return True

    # Filter the DataFrame based on the criteria
    filtered_df = word_list[word_list['WORD'].apply(meets_criteria)]
    return filtered_df

# REMOVE WORDS WITH ANY OF THE EXCLUDED LETTERS

def candidates_ex_excluded(word_list: pd.DataFrame, letters_not_in_word: str):
    
    excluded_letters = set(letters_not_in_word.upper())

    # function that returns true if word does not include any of the excluded letters
    # NB disjoint is TRUE if there is no overlap between the two sets
    def does_not_contain_excluded_letters(word):
        return excluded_letters.isdisjoint(set(word.upper()))  # True if no overlap, False otherwise

    candidates = word_list[word_list['WORD'].apply(does_not_contain_excluded_letters)]

    return candidates

def wordle_filter(inputs, word_list: pd.DataFrame):
    
    known_letters = inputs['known_letters'].upper()
    unlocated_letters = inputs['unlocated_letters_in_word'].upper()
    exclusions = inputs['exclusions']
    # print(exclusions)
    letters_not_in_word = inputs['letters_not_in_word'].upper()

    candidates = word_list

    # ONLY INCLUDE KNOWN LETTERS
    if len(known_letters)>0:
        candidates = candidates_match_known(word_list, known_letters)


    if any(bool(chars) for chars in exclusions.values()):
        exclusions = {key: value.upper() for key, value in exclusions.items()}
        # print(exclusions)
        candidates = filter_words_by_exclusions(candidates, exclusions)
        exclusion_letters = "".join(exclusions.values())
        additional_letters = set(exclusion_letters) - set(known_letters) - set(unlocated_letters)
        unlocated_letters = "".join(sorted(set(unlocated_letters) | additional_letters))

    # ONLY INCLUDE WORDS CONTAINING KNOWN AND UNLOCATED LETTERS
    if len(unlocated_letters) > 0:
        print(unlocated_letters)
        candidates = candidates_all_letters(candidates, known_letters,unlocated_letters)

    # REMOVE WORDS CONTAINING ANY LETTERS KNOWN NOT TO BE IN THE WORD
    if len(letters_not_in_word) > 0:
        candidates = candidates_ex_excluded(candidates, letters_not_in_word)

    return candidates

def get_unique_letters(word_list):
    """
    Returns all unique letters from a list of words.

    :param word_list: List of words (strings)
    :return: Set of unique letters
    """
    # Concatenate all words into one string
    all_letters = ''.join(word_list).upper()
    
    # Return the set of unique letters
    return set(all_letters)


def letters_in_candidates(word_list, inputs):

    unique_letters = get_unique_letters(word_list['WORD'])

    known_letters = inputs['known_letters'] + inputs['unlocated_letters_in_word']
    letters_to_remove_set = set(known_letters.upper())  # Ensure consistency with uppercase

    unique_letters_ex_known = unique_letters.difference(letters_to_remove_set)

    return unique_letters_ex_known

def most_common_letters(word_list, inputs):

    # unique_letters = get_unique_letters(word_list['WORD'])

    # known_letters = inputs['known_letters'] + inputs['unlocated_letters_in_word']
    # letters_to_remove_set = set(known_letters.upper())  # Ensure consistency with uppercase

    # unique_letters_ex_known = unique_letters.difference(letters_to_remove_set)

    unique_letters_ex_known = letters_in_candidates(word_list, inputs)

    letters_with_word_count = count_words_with_letters(word_list, unique_letters_ex_known)
    
    return letters_with_word_count

def count_words_with_letters(word_list: pd.DataFrame, letters: set) -> pd.DataFrame:
    """
    Counts how many words in the candidates DataFrame contain each letter in the given set.

    :param candidates: DataFrame with a column 'WORD' containing words
    :param letters: Set of letters to count occurrences for
    :return: DataFrame with each letter and the count of words containing it
    """
    # Initialize a dictionary to store the counts
    letter_counts = {}

    # Loop through each letter in the set
    for letter in letters:
        # Count words containing the letter
        count = word_list['WORD'].str.contains(letter, case=False).sum()
        letter_counts[letter] = count

    # Convert the counts dictionary to a DataFrame
    result = pd.DataFrame(list(letter_counts.items()), columns=['Letter', 'Count'])
    return result.sort_values(by='Count', ascending=False)


def rank_words_by_letters_dumb(word_list, letters):
    
    # Convert the list of letters to a set for quick lookup
    letter_set = set(letters.upper())

    # Function to calculate the score for each word
    # Function to calculate the score for each word
    def calculate_score(word):
        # Use a set to track unique letters in the word
        word_letters = set(word.upper())
        # Count how many letters from the input set are in the word
        return sum(1 for letter in letter_set if letter in word_letters)

    # Add a column for scores
    words_df = word_list
    words_df['SCORE'] = words_df['WORD'].apply(calculate_score)

    # Sort the DataFrame by score in descending order
    ranked_words = words_df.sort_values(by='SCORE', ascending=False)

    return ranked_words

def filter_list_for_chosen_letters(words: pd.DataFrame, required_letters: str) -> pd.DataFrame:
    """
    Filters a list of words to include only those that contain all letters from the input string.

    :param words: DataFrame containing the words (in a column named 'WORD').
    :param required_letters: String of letters that must be included in each word.
    :return: Filtered DataFrame with matching words.
    """
    # Convert required letters to a set for efficient lookup
    required_set = set(required_letters.upper())

    # Define a function to check if all required letters are in a word
    def contains_all_letters(word):
        return required_set.issubset(set(word.upper()))

    # Filter the DataFrame
    filtered_df = words[words['WORD'].apply(contains_all_letters)]

    return filtered_df
import json

def update_wordle_json(wordle_json_name, input_string):
    # Load the current wordle.json file
    with open(wordle_json_name, "r") as file:
        wordle_data = json.load(file)

    # Parse the input string
    word, pattern = input_string.split()

    # Track occurrences of letters already processed for A or G
    processed_letters = set()

    # Process each character in the word and pattern
    for idx, (char, status) in enumerate(zip(word, pattern)):
        if status == "G":
            # Update known_letters for correct placement
            wordle_data["known_letters"] = (
                wordle_data["known_letters"][:idx]
                + char
                + wordle_data["known_letters"][idx + 1:]
            )
            if char in wordle_data["unlocated_letters_in_word"]:
                wordle_data["unlocated_letters_in_word"] = wordle_data["unlocated_letters_in_word"].replace(char, "")
            processed_letters.add(char)
        elif status == "A":
            # Update exclusions and unlocated_letters_in_word
            exclusion_key = f"{idx + 1}{['st', 'nd', 'rd'][idx] if idx < 3 else 'th'} char"
            if exclusion_key not in wordle_data["exclusions"]:
                wordle_data["exclusions"][exclusion_key] = ""
            if char not in wordle_data["exclusions"][exclusion_key]:
                wordle_data["exclusions"][exclusion_key] += char
            if char not in wordle_data["unlocated_letters_in_word"]:
                wordle_data["unlocated_letters_in_word"] += char
            processed_letters.add(char)
        elif status == "X":
            # Only add to letters_not_in_word if not already processed as A or G
            if char not in processed_letters and char not in wordle_data["letters_not_in_word"]:
                wordle_data["letters_not_in_word"] += char

    # Save the updated wordle.json
    with open(wordle_json_name, "w") as file:
        json.dump(wordle_data, file, indent=4)

# Example usage
#update_wordle_json("AMPLE XGXAX")
