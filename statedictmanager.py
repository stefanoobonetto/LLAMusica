import re
import json
from utils import PRINT_DEBUG

class StateDictManager:
    """
    Manages the state dictionary for LLAMusica system pipeline, providing utilities for validation, 
    updating, extracting, and displaying structured data.
    """

    def __init__(self, initial_state=None):
        """
        Initializes the state dictionary with predefined sections or a given initial state.

        Args:
            initial_state (dict, optional): A dictionary to initialize the state. 
                                            Defaults to {"NLU": {}, "DM": {}, "GK": {}}.
        """
        
        self.state_dict = initial_state if initial_state else {"NLU": {}, "DM": {}, "GK": {}}

    def check_none_values(self):
        """
        Checks if the state dictionary contains 'None' as a string representation.

        Returns:
            bool: True if 'None' is found in the state dictionary, otherwise False.
        """
        
        if "None" in str(self.state_dict):
            return True
        else:
            return False

    def validate_structure(self):
        """
        Validates whether the state dictionary is a properly structured JSON object.

        - Attempts to serialize and deserialize the dictionary.
        - Prints debug messages if the structure is invalid.

        Returns:
            bool: True if the state dictionary is valid JSON, otherwise False.
        """
        
        try:
            json_string = json.dumps(self.state_dict)
            json.loads(json_string)
            return True
        except (TypeError, ValueError) as e:
            if PRINT_DEBUG:
                print(f"State dictionary is invalid: {e}")
            return False

    def correct_structure(self):
        """
        Attempts to correct the state dictionary structure by serializing and deserializing it.

        - This helps ensure that the state dictionary remains a valid JSON object.
        """
        
        try:
            json_string = json.dumps(self.state_dict)
            self.state_dict = json.loads(json_string)
        except Exception as e:
            if PRINT_DEBUG:
                print(f"Failed to correct state dictionary: {e}")

    def update_section(self, section, data):
        """
        Updates or adds a section in the state dictionary.

        - If the section exists, it merges new data into it.
        - If the section doesn't exist, it creates a new section.

        Args:
            section (str): The section name to update (e.g., "NLU", "DM", "GK").
            data (dict): The data to update or insert into the section.
        """
        
        if section in self.state_dict:
            self.state_dict[section].update(data)
        else:
            if PRINT_DEBUG:
                print(f"Section '{section}' not found in state_dict, adding it.")
            self.state_dict[section] = data

    def extract_valid_json(self, raw_string):
        """
        Extracts a valid JSON object from a raw string.

        - Searches for JSON content within the string using regex.
        - Attempts to parse and return the extracted JSON.

        Args:
            raw_string (str): The raw input string potentially containing JSON data.

        Returns:
            dict | None: The extracted JSON as a dictionary if valid, otherwise None.
        """
        
        json_pattern = r'\{.*\}'
        json_match = re.search(json_pattern, raw_string, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                if PRINT_DEBUG:
                    print("Extracted content is not valid JSON.")
                return None
        if PRINT_DEBUG:
            print("No valid JSON content found.")
        return None

    def empty_section(self, section):
        """
        Empties all data from a specified section in the state dictionary.

        Args:
            section (str): The section name to be emptied.
        """
        
        if section in self.state_dict:
            self.state_dict[section] = {}
        else:
            if PRINT_DEBUG:
                print(f"Section '{section}' not found in state_dict.")

    def delete_section(self, section):
        """
        Deletes a section completely from the state dictionary.

        Args:
            section (str): The section name to be removed.
        """
        
        if section in self.state_dict:
            del self.state_dict[section]
        else:
            if PRINT_DEBUG:
                print(f"Section '{section}' not found in state_dict. Nothing to delete.")

    def display(self):
        """
        Prints the state dictionary in a formatted JSON structure for debugging purposes.

        - Only prints if `PRINT_DEBUG` is enabled.
        """
        
        if PRINT_DEBUG:
            print(json.dumps(self.state_dict, indent=4))
