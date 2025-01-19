import pandas as pd, json

def rank_words_by_letters(csv_file, letters):
    """
    Rank words in a CSV file by the number of specified letters they contain.

    :param csv_file: Path to the CSV file containing words.
    :param letters: A string of letters to match against.
    :return: A ranked DataFrame with words and their scores.
    """
    # Load the word list from the CSV file
    words_df = pd.read_csv(csv_file, header=None, names=['word'])

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
    words_df['score'] = words_df['word'].apply(calculate_score)

    # Sort the DataFrame by score in descending order
    ranked_words = words_df.sort_values(by='score', ascending=False)

    return ranked_words

# Example usage
if __name__ == "__main__":
    input_letters = "BKCGPVFJPWZ"  # Replace with your input letters
    csv_file_path = "word_list.csv"  # Replace with the path to your CSV file

    ranked_words_df = rank_words_by_letters(csv_file_path, input_letters)
    highest_score_df = ranked_words_df[ranked_words_df['score'] == ranked_words_df['score'].max()]


    # Display the top-ranked words
    print(highest_score_df)  # Show top 20 results


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

# Example usage
#pasted_words = ["apple", "banana", "cherry"]
pasted_words = pd.read_csv("candidates.csv", header=None, names=['word'])
print(pasted_words)
unique_letters = get_unique_letters(pasted_words)
print(unique_letters)
