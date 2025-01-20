import json
import re

# json_input = " {'NLU': {'song_info': {'slots': {'artist_name': 'Billie Eilish', 'song_name': 'Bad Guy', 'details': ['artist_name']}}}}, {'DM': {'next_best_action': 'request_info(song_info)', 'args': {'song_name': 'Bad Guy', 'details': ['artist_name']}},  'GK': {'song_info': {'artists': ['Billie Eilish']}}, 'NLG': 'Did you mean the song Bad Guy by Billie Eilish?'} "
# correct: "{'NLU': {'song_info': {'slots': {'artist_name': 'Billie Eilish', 'song_name': 'Bad Guy', 'details': ['artist_name']}}}, 'DM': {'next_best_action': 'request_info(song_info)', 'args': {'song_name': 'Bad Guy', 'details': ['artist_name']}}, 'GK': {'song_info': {'artists': ['Billie Eilish']}}, 'NLG': 'Did you mean the song Bad Guy by Billie Eilish?'}"

json_input = """ {'NLU': {'song_info': {'slots': {'song_name': 'Bad Guy', 'artist_name': ['Billie Eilish'], 'details': ['artist_name']}}}}, 
'DM': {'next_best_action': 'request_info(song_info)', 'args': {'song_name': 'Bad Guy', 'details': ['artist_name']}}, 
'GK': {'song_info': {'artists': ['Billie Eilish']}}, 
'NLG': 'Did you mean the song Bad Guy by Billie Eilish?'} """

import json
import re

def fix_json_string(json_string):
    """
    Fixes and parses a malformed JSON string, ensuring it is a single dictionary object.
    """
    try:
        # Step 1: Remove extraneous text outside JSON-like content
        json_string = re.sub(r"^[^{]*", "", json_string)  # Remove anything before the first '{'
        json_string = re.sub(r"[^}]*$", "", json_string)  # Remove anything after the last '}'

        # Step 2: Replace single quotes with double quotes (only outside brackets or braces)
        json_string = re.sub(r"(?<!\\)'", '"', json_string)  # Replace ' with "

        # Step 3: Ensure keys are quoted
        json_string = re.sub(r'(?<!")(\b\w+\b)(?=\s*:)', r'"\1"', json_string)  # Add quotes to keys

        # Step 4: Merge multiple top-level dictionaries into one
        json_string = re.sub(r"}\s*,\s*{", ", ", json_string)  # Merge separate dicts

        # Step 5: Remove trailing commas
        json_string = re.sub(r',\s*([}\]])', r'\1', json_string)  # Remove commas before } or ]

        # Step 6: Ensure balanced braces
        open_braces = json_string.count('{')
        close_braces = json_string.count('}')
        if open_braces > close_braces:
            json_string += '}' * (open_braces - close_braces)

        # Step 7: Parse the corrected JSON
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        print(f"Failed to fix JSON: {e}")
        raise ValueError("Unable to fix and parse the JSON string.") from e

try:
    dict = fix_json_string(json_input)
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
    dict = None

print(dict)