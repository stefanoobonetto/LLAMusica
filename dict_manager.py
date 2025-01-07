import json
import re

def extract_json(response):
    """Extract and parse the JSON-like structure from a response string."""
    try:
        # Locate the JSON-like structure using regex to find the first curly brace
        match = re.search(r'({.*})', response, re.DOTALL)
        if match:
            json_part = match.group(1)

            # Ensure compliance with JSON format
            json_part = re.sub(r"'", r'"', json_part)  # Convert single quotes to double quotes
            json_part = re.sub(r'\bNone\b', 'null', json_part)  # Replace None with null
            json_part = re.sub(r'\bTrue\b', 'true', json_part)  # Replace True with true
            json_part = re.sub(r'\bFalse\b', 'false', json_part)  # Replace False with false

            # Parse the sanitized JSON
            return json.loads(json_part)
        else:
            raise ValueError("No JSON-like object found in the response.")
    except json.JSONDecodeError as e:
        print("Failed to parse JSON:", e)
        raise ValueError(f"Failed to parse JSON: {e}")

def validate_json_structure(parsed_json):
    """Validate the extracted JSON against supported intents and slots."""
    supported_intents = {
        "song_info", "artist_info", "album_info", 
        "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"
    }

    if not isinstance(parsed_json, dict):
        raise ValueError("The extracted structure is not a valid dictionary.")

    for intent, details in parsed_json.items():
        if intent not in supported_intents:
            raise ValueError(f"Unsupported intent: {intent}")

        if "slots" not in details or not isinstance(details["slots"], dict):
            raise ValueError(f"Invalid or missing slots for intent: {intent}")

    return True

def check_response_dict(response):
    """Check if the response is a dictionary."""
    if isinstance(response, str):
        try:
            dict_status = extract_json(response)
        except ValueError as e:
            raise ValueError(f"Response is not valid JSON: {e}")
    elif not isinstance(response, dict):
        raise ValueError(f"Expected a dictionary but got {type(response)}")
    else:
        dict_status = response  # Already a dictionary

    # print("\n\nValidated response (as dictionary):\n\n", dict_status)
    return dict_status

def update_dict_status(existing_status, new_status):
    """Recursively update the existing dictionary with new data."""
    for key, value in new_status.items():
        if isinstance(value, dict) and key in existing_status:
            # Recursively update nested dictionaries
            update_dict_status(existing_status[key], value)
        else:
            # Overwrite or add new keys
            existing_status[key] = value


class DictManager:
    """Manages operations on the dictionary status."""
    
    def __init__(self, initial_dict=None):
        self.dict_status = initial_dict or {}

    def validate_dict(self, response):
        """Validate and update dict_status with a new response."""
        parsed_response = check_response_dict(response)  
        self.dict_status.update(parsed_response)
        return self.dict_status

    def update_slot(self, slot_name, slot_value):
        """Update a specific slot in the dictionary."""
        if "NLU" not in self.dict_status:
            self.dict_status["NLU"] = {"slots": {}}
        self.dict_status["NLU"]["slots"][slot_name] = slot_value

    def get_next_best_action(self):
        """Retrieve the next best action from the dictionary."""
        return self.dict_status.get("DM", {}).get("next_best_action", "No action available")

    def get_slot_value(self, slot_name):
        """Get the value of a specific slot."""
        return self.dict_status.get("NLU", {}).get("slots", {}).get(slot_name)

    def to_json(self):
        """Return the dictionary as a JSON string."""
        return json.dumps(self.dict_status, indent=2)
