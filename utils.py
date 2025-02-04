import re
import os
import sys
import time
import json
import textwrap

from spoti import *


# PROMPTS' paths
PROMPT_NLU_INTENTS = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_intents.txt")
PROMPT_NLU_SLOTS = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_slots.txt")
PROMPT_DM = os.path.join(os.path.dirname(__file__), "prompts/prompt_DM.txt")
PROMPT_NLG = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLG.txt")
PROMPT_USD = os.path.join(os.path.dirname(__file__), "prompts/prompt_USD.txt")
PROMPT_COT_DETECTION = os.path.join(os.path.dirname(__file__), "prompts/prompt_COT_detection.txt")

PRINT_DEBUG = True

intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "get_recommendations", "out_of_domain"]
info_intents = ["artist_info", "song_info", "album_info"]

corresponding_actions = {
    "artist_info": get_artist_info,
    "song_info": get_song_info,
    "album_info": get_album_info,
    "user_top_tracks": get_user_top_tracks,
    "user_top_artists": get_user_top_artists,
    "get_recommendations": get_recommendations,
}

info_entity = {
    "artist_info": ["artist_name"],
    "song_info": ["song_name", "artist_name"],
    "album_info": ["album_name", "artist_name"]
}

required_slots = {
    "artist_info": ["artist_name"],
    "song_info": ["song_name"],
    "album_info": ["album_name"],
    "user_top_tracks": [],
    "user_top_artists": [],
    "out_of_domain": [],
    "get_recommendations": ["genre"]
}

def split_intent(input_string):
    """
    Parses an action-intent string and extracts the action and intent.

    - The expected format is "action(intent)" (e.g., "confirmation(artist_info)").
    - Uses regex to match and separate the action and intent components.
    - Raises a ValueError if the input format is invalid.

    Args:
        input_string (str): A string in the format "action(intent)".

    Returns:
        tuple: (action, intent) extracted from the input string.

    Raises:
        ValueError: If the input string does not match the expected format.
    """
    
    match = re.match(r"(\w+)\((\w+)\)", input_string)
    if match:
        action = match.group(1)  
        intent = match.group(2) 
        return action, intent
    else:
        raise ValueError("Invalid input string format. Expected format: 'action(intent)'")
    
def get_current_intent(state_dict=None, next_best_action=None):
    """
    Extracts the current intent from the state dictionary or a given action string.

    - If a state dictionary is provided, retrieves the `next_best_action` from the DM component.
    - Uses `split_intent` to extract the intent from the action string.

    Args:
        state_dict (dict, optional): The state dictionary containing DM data.
        next_best_action (str, optional): A string representing the next best action.

    Returns:
        str: The extracted intent.
    """
    
    if state_dict:
        next_best_action = state_dict["DM"]["next_best_action"]
    _, intent = split_intent(next_best_action)
    
    if PRINT_DEBUG:
        print("\n\n\nReturning intent: ", intent, "\n\n")
    return intent

def get_current_action(intent, state_dict=None, next_best_action=None):
    """
    Retrieves the current action for a given intent from the state dictionary.

    - Iterates through the DM component to find the matching intent.
    - Extracts and returns the action associated with that intent.

    Args:
        intent (str): The intent for which the action is needed.
        state_dict (dict, optional): The state dictionary containing DM data.
        next_best_action (str, optional): A string representing the next best action.

    Returns:
        str: The extracted action.
    """
    
    if state_dict:
        next_best_action_list = state_dict["DM"]
    for elem in next_best_action_list:
        act_intent, action = split_intent(elem["next_best_action"]) 
        if act_intent == intent:
            if PRINT_DEBUG:
                print("\n\n\nReturning next_best_action: ", elem["next_best_action"], "\n\n")
            return elem["next_best_action"]

def final_check_NLU(state_dict, intents_extracted):
    """
    Performs a final validation of extracted intents and updates the state dictionary.

    - Checks if required slot details exist for each extracted intent.
    - Removes intents with missing details from the state dictionary.

    Args:
        state_dict (dict): The current state dictionary.
        intents_extracted (list): List of extracted intents.

    Returns:
        list: Updated list of extracted intents.
    """
    
    to_delete = []
    for intent in intents_extracted:
        if intent in info_intents and "details" not in state_dict["NLU"][intent]["slots"]:
            del state_dict["NLU"][intent]
            if PRINT_DEBUG:
                print("\n\n\n------> No details found for ", intent, " intent. Deleting it from the state_dict...")
            to_delete.append(intent)
    intents_extracted = [intent for intent in intents_extracted if intent not in to_delete]
    return intents_extracted        

def extract_intents_build_slots_input(user_input, state_dict, out_NLU_intents):
    """
    Extracts intents from NLU output and prepares input for slot extraction.

    - Counts occurrences of each intent and assigns unique keys if necessary.
    - Updates the state dictionary with extracted intents.
    - Constructs input for slot extraction.

    Args:
        user_input (str): The original user input.
        state_dict (dict): The current state dictionary.
        out_NLU_intents (str): The output from the NLU model.

    Returns:
        tuple: (slots_input, intents_extracted, updated state_dict)
    """

    intents_extracted = []
    intent_count = {}
    
    for intent in intents:
        count = out_NLU_intents.count(intent)  # Count occurrences of each intent in the output
        for i in range(count):
            intent_key = f"{intent}{i + 1}" if count > 1 else intent  # Number intents if multiple instances
            intents_extracted.append(intent_key)
            state_dict["NLU"][intent_key] = {}
            intent_count[intent] = intent_count.get(intent, 0) + 1  # Update count for numbering

    str_intents = ""
    for i, intent in enumerate(intents_extracted):
        str_intents += f"- Intent{i+1}: {intent}\n"

    slots_input = user_input + "\n" + str_intents
    
    return slots_input, intents_extracted, state_dict

def check_slots(NLU_component, slots):
    """
    Validates if the required slots for each intent are present and properly filled.

    - Ensures required slots exist and contain valid data.
    - Checks if "details" exist for applicable intents.

    Args:
        NLU_component (dict): The NLU component of the state dictionary.
        slots (dict): Extracted slot values.

    Returns:
        bool: True if slots are valid, False otherwise.
    """

    if not slots or "slots" not in slots:  # Check if 'slots' key exists
        return False

    for intent in NLU_component.keys():
        required = required_slots.get(intent, [])
        
        actual_slots = NLU_component[intent]["slots"]  # Extract the actual slots data
        
        # Check required slots
        for slot in required:
            if slot not in actual_slots or (actual_slots[slot] is None and intent != "song_info"):  # Check if required slot exists and is not empty
                if PRINT_DEBUG:
                    print(f"Missing or invalid slot '{slot}' for intent '{intent}'")
                return False

        if intent in info_intents:
            if "details" not in actual_slots:  # Check if details exists
                if PRINT_DEBUG:
                    print(f"Missing slot 'details' for intent '{intent}'")
                return False
            if not actual_slots["details"]:  # Check if details list is empty (fixing the precedence issue)
                if PRINT_DEBUG:
                    print(f"Empty slot 'details' for intent '{intent}'")
                return False
                
    return True  

def check_args(parsed_response, intent):
    """
    Validates if required arguments in a DM output exist in the parsed response for a given intent.

    - Ensures mandatory keys are present and not null.
    - Handles different validation logic based on intent type.

    Args:
        parsed_response (dict): The parsed response from the DM.
        intent (str): The intent to validate.

    Returns:
        bool: True if all required arguments exist, False otherwise.
    """
    
    if intent == "artist_info":
        if "artist_name" not in parsed_response["args(artist_info)"] or parsed_response["args(artist_info)"]["artist_name"] == None or parsed_response["args(artist_info)"]["artist_name"] == "null":
            return False
    elif intent == "song_info":
        if "song_name" not in parsed_response["args(song_info)"] or parsed_response["args(song_info)"]["song_name"] in [None, "null"]:
            return False
        if "artist_name" in parsed_response["args(song_info)"] and parsed_response["args(song_info)"]["artist_name"] in [None, "null"] and "artist_name" not in parsed_response["args(song_info)"]["details"]:
            return False
    elif intent == "album_info":
        if "album_name" not in parsed_response["args(album_info)"] or parsed_response["args(album_info)"]["album_name"] in [None, "null"]:
            return False
        if "artist_name" in parsed_response["args(album_info)"] and parsed_response["args(album_info)"]["artist_name"] in [None, "null"] and "artist_name" not in parsed_response["args(album_info)"]["details"]:
            return False
    elif intent == "get_recommendations":
        
        extracted_action = get_current_action(parsed_response)

        if extracted_action == "request_info":
            if PRINT_DEBUG:
                print("Args content:", parsed_response["args(get_recommendations)"])  
                print("Details content:", parsed_response["args(get_recommendations)"].get("details"))  
            if "details" not in parsed_response["args(get_recommendations)"] or parsed_response["args(get_recommendations)"]["details"] == []:
                if PRINT_DEBUG:
                    print("Missing 'details' in args")
                return False
        else:
            if PRINT_DEBUG:
                print("Genre value:", parsed_response["args(get_recommendations)"].get("genre"))  
            if "genre" not in parsed_response["args(get_recommendations)"] or parsed_response["args(get_recommendations)"]["genre"] in [None, "null"]:
                if PRINT_DEBUG:
                    print("Missing or null 'genre'")
                return False
    return True


def fix_json_string(json_string):
    """
    Cleans and parses a malformed JSON string into a valid dictionary.

    - Removes extraneous text outside JSON structures.
    - Fixes incorrect quotes and replaces Python keywords with JSON equivalents.
    - Ensures keys are properly quoted and handles missing brackets.

    Args:
        json_string (str): The malformed JSON string.

    Returns:
        dict: Parsed JSON object or False if parsing fails.
    """

    if not isinstance(json_string, str):
        if PRINT_DEBUG:
            print(f"❌ Error: Expected string but got {type(json_string)} instead.")
        return False  # Return False instead of processing non-string input

    try:
        # Step 1: Remove extraneous text outside JSON-like content
        json_string = re.sub(r"^[^{\[]*", "", json_string)  # Remove anything before '{' or '['
        json_string = re.sub(r"[^}\]]*$", "", json_string)  # Remove anything after '}' or ']'

        # Step 2: Replace single quotes with double quotes (only outside brackets or braces)
        json_string = re.sub(r"(?<!\\)'", '"', json_string)  # Replace ' with "

        # Step 3: Replace Python-specific keywords with JSON equivalents
        json_string = json_string.replace("None", "null").replace("True", "true").replace("False", "false")

        # Step 4: Ensure keys are properly quoted
        json_string = re.sub(r'(?<!")(\b\w+\b)(?=\s*:)', r'"\1"', json_string)  

        # Step 5: Merge multiple top-level dictionaries into one
        json_string = re.sub(r"}\s*,\s*{", ", ", json_string)  

        # Step 6: Remove trailing commas
        json_string = re.sub(r',\s*([}\]])', r'\1', json_string)  

        # Step 7: Ensure balanced braces
        open_braces = json_string.count('{')
        close_braces = json_string.count('}')
        if open_braces > close_braces:
            json_string += '}' * (open_braces - close_braces)

        # Step 8: Parse the corrected JSON
        return json.loads(json_string)
    
    except json.JSONDecodeError as e:
        if PRINT_DEBUG:
            print(f"Failed to fix JSON: \n\n{json_string}\nwith error: {e}")
        return False
        
def validate_DM(response, intent, action):
    """
    Validates the DM response by checking structure, arguments, and expected action.

    - Parses and verifies JSON format.
    - Ensures the response contains valid arguments for the given intent.
    - Checks if the expected action is present in the response.

    Args:
        response (str): The raw response from the DM model.
        intent (str): The intent being processed.
        action (str): The expected action type.

    Returns:
        bool: True if the response is valid, False otherwise.
    """

    try:
        parsed_response = fix_json_string(response)  
        if not parsed_response:
            if PRINT_DEBUG:
                print("Failed to parse JSON response.")
            return False
    except json.JSONDecodffeError:
        if PRINT_DEBUG:
            print("Failed to parse JSON response.")
        return False
    
    if "next_best_action" not in parsed_response:
        return False
    
    args_key = f"args({intent})"  
    
    if not parsed_response[args_key].get("details") and intent not in ["user_top_tracks", "user_top_artists", "get_recommendations", "out_of_domain"]:
            return False
    
    return action in response and check_args(parsed_response, intent)

def check_null_slots_and_update_state_dict(state_dict, out_USD, intents_extracted, slot_to_update):
    """
    Updates the state dictionary by filling in missing slot values. It extracts and assigns 
    values to required slots from the USD model output.

    Args:
        state_dict (dict): The current state dictionary.
        out_USD (str): Output from the User Slot Detection (USD) model.
        intents_extracted (list): Extracted intents.
        slot_to_update (dict): Slots that need updating.

    Returns:
        dict: Updated state dictionary.
    """
    
    for intent in intents_extracted:
        for intent, slots in slot_to_update.items():            
            for slot in slots:
                new_value = None  # Default to None if no match is found
                
                # try to match values inside quotes, with or without a leading `-`
                match = re.search(rf'-?\s*"{re.escape(slot)}"\s*:\s*"([^"]+)"', str(out_USD))

                if not match:
                    # if no match found, try without quotes (integers or single-word strings)
                    match = re.search(rf'-?\s*"{re.escape(slot)}"\s*:\s*([^"\s]+)', str(out_USD))

                if match:
                    new_value = match.group(1).strip()  # extract and clean the value

                    if PRINT_DEBUG:
                        print(f"Found value for {slot}: {new_value}")

                    # update state_dict with the extracted value
                    state_dict["NLU"][intent]["slots"][slot] = new_value  
                else:
                    if PRINT_DEBUG:
                        print(f"No match found for {slot}")

    return state_dict

def get_slot_to_update(state_dict, intents_extracted):
    """
    Determines which slots need to be updated based on the DM's next best action.

    - Extracts required slot details for each intent.
    - Identifies slots that need to be filled.
    
    Args:
        state_dict (dict): The current state dictionary.
        intents_extracted (list): Extracted intents.

    Returns:
        dict: Mapping of intents to slots that need updates.
    """

    slot_to_update = {intent: [] for intent in intents_extracted}

    for best_action in state_dict["DM"]:
        next_best_action = best_action["next_best_action"]
        
        intent = get_current_intent(next_best_action)
        
        args_key = f"args({intent})"  # Correct key formatting
        
        if intent in intents_extracted and args_key in best_action:
            if "details" in best_action[args_key]:
                slot_to_update[intent] = best_action[args_key]["details"]  

    return slot_to_update

def validate_USD(state_dict, out_USD, slot_to_update, intents_extracted, action):
    """
    Validates the extracted slot values from the USD model.

    - Ensures all required slots are present in the output.
    - Add details to slot validation if action type is confirmation.

    Args:
        state_dict (dict): The current state dictionary.
        out_USD (str): Output from the USD model.
        slot_to_update (dict): Slots that need validation.
        intents_extracted (list): Extracted intents.
        action (str): The current action being processed.

    Returns:
        bool: True if validation passes, False otherwise.
    """

    if action == "confirmation":
        for intent in intents_extracted:
            if intent in info_intents:
                for detail in state_dict["NLU"][intent]["slots"]["details"]:
                    if detail not in slot_to_update:
                        slot_to_update.append(detail)

    # check if required slots exist in out_USD
    for intent, slots in slot_to_update.items():
        for slot in slots:
            if slot not in out_USD:
                if PRINT_DEBUG:
                    print(f"Missing slot: {slot}")
                return False  

    return True  


def build_prompt_for_USD(state_dict, slot_to_update):
    """
    Constructs a prompt for the User Slot Detection (USD) model bsade on a template.

    - Formats the state dictionary and slots that need updating.
    - Reads the USD prompt template and appends the formatted data.
    
    Args:
        state_dict (dict): The current state dictionary.
        slot_to_update (dict): Slots that require updates.

    Returns:
        str: The formatted USD prompt.
    """

    prefix = "slot_to_update: " + str(slot_to_update) + "\nstate_dict: \n" + str(state_dict)
        
    with open(PROMPT_USD, "r") as file:
        template = file.read()
    
    prompt = prefix + "\n\n" + template
    
    return prompt

def clear_last_line():
    """Clears the last line written in the terminal."""
    sys.stdout.write("\033[F")  
    sys.stdout.write("\033[K")  
    sys.stdout.flush()

def print_system(message, auth=False):
    """Prints a system message anchored to the left with a speech bubble, taking half of the terminal width."""
    if auth:
        print(center_text("\nAuthentication successful!\n"))
        
    term_width = get_terminal_width()
    width = term_width // 2 - 4  
    wrapped_message = "\n".join(textwrap.fill(line, width) for line in message.split("\n"))  
    border = "─" * (width + 2)

    print("\n\n")
    print(f"┌{border}┐")  
    for line in wrapped_message.split("\n"):
        print(f"│ {line.ljust(width)} │")  
    print(f"|/{'─' * (width + 1)}┘")  

def input_user(prompt):
    """Gets user input, clears it, and prints it in a right-aligned speech bubble, taking half of the terminal width."""
    user_message = input(prompt)  
    clear_last_line()  

    term_width = get_terminal_width()
    width = term_width // 2 - 4  
    wrapped_message = "\n".join(textwrap.fill(line, width) for line in user_message.split("\n"))
    border = "─" * (width + 2)
    padding = " " * (term_width // 2)  

    print("\n\n")
    print(f"{padding}┌{border}┐")  
    for line in wrapped_message.split("\n"):
        print(f"{padding}│ {line.ljust(width)} │")  
    print(f"{padding}└{'─' * (width + 1)}\|")  

    return user_message  

def pretty_print():
    """
    Displays a stylized welcome message and ASCII art banner.

    - Prints a centered welcome message with colored ASCII art.
    - Uses a delay for visual effect.
    """
    
    welcome_message = """\n\n
 __          __  _                               _        
 \ \        / / | |                             | |       
  \ \  /\  / /__| | ___ ___  _ __ ___   ___     | |_ ___  
   \ \/  \/ / _ \ |/ __/ _ \| '_ ` _ \ / _ \    | __/ _ \ 
    \  /\  /  __/ | (_| (_) | | | | | |  __/    | || (_) |
     \/  \/ \___|_|\___\___/|_| |_| |_|\___|     \__\___/ 
    \n\n
    """

    print(center_text(welcome_message))
    
    colors = [
        "\033[91m",  
        "\033[93m",  
        "\033[92m",  
        "\033[96m",  
        "\033[94m",  
        "\033[95m",  
    ]

    ascii_art = [
        " ___      ___      _______  __   __  __   __  _______  ___   _______  _______ ",
        "|   |    |   |    |   _   ||  |_|  ||  | |  ||       ||   | |       ||   _   |",
        "|   |    |   |    |  |_|  ||       ||  | |  ||  _____||   | |       ||  |_|  |",
        "|   |    |   |    |       ||       ||  |_|  || |_____ |   | |       ||       |",
        "|   |___ |   |___ |       ||       ||       ||_____  ||   | |      _||       |",
        "|       ||       ||   _   || ||_|| ||       | _____| ||   | |     |_ |   _   |",
        "|_______||_______||__| |__||_|   |_||_______||_______||___| |_______||__| |__|",
    ]

    term_width = get_terminal_width()

    for i, line in enumerate(ascii_art):
        color = colors[i % len(colors)]  
        padding = (term_width - len(line)) // 2 
        print(" " * max(0, padding) + color + line + "\033[0m") 
        time.sleep(0.05)  
