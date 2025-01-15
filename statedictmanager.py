import re
import json

class StateDictManager:
    def __init__(self, initial_state=None):
        self.state_dict = initial_state if initial_state else {"NLU": {}, "DM": {}, "GK": {}}

    def check_null_values(self):
        if "null" in self.state_dict.values():
            print("Null values found in state dictionary.")
            return True
        else:
            return False
    def validate_structure(self):
        try:
            json_string = json.dumps(self.state_dict)
            json.loads(json_string)
            # print("State dictionary is valid.")
            return True
        except (TypeError, ValueError) as e:
            print(f"State dictionary is invalid: {e}")
            return False

    def correct_structure(self):
        try:
            json_string = json.dumps(self.state_dict)
            self.state_dict = json.loads(json_string)
            # print("State dictionary corrected.")
        except Exception as e:
            print(f"Failed to correct state dictionary: {e}")

    def update_section(self, section, data):
        if section in self.state_dict:
            self.state_dict[section].update(data)
            # print(f"Updated section '{section}' with data: {data}")
        else:
            print(f"Section '{section}' not found in state_dict, adding it.")
            self.state_dict[section] = data
        
    def extract_valid_json(self, raw_string):
        json_pattern = r'\{.*\}'
        json_match = re.search(json_pattern, raw_string, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                print("Extracted content is not valid JSON.")
                return None
        print("No valid JSON content found.")
        return None

    def display(self):
        print(json.dumps(self.state_dict, indent=4))