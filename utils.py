import re
import os
import sys
import time
import json
import textwrap

from spoti import *

intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "get_recommendations", "out_of_domain"]
PROMPT_NLU = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU.txt")
PROMPT_NLU_INTENTS = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_intents.txt")
PROMPT_NLU_SLOTS = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_slots.txt")
PROMPT_DM = os.path.join(os.path.dirname(__file__), "prompts/prompt_DM.txt")
PROMPT_NLG = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLG.txt")
PROMPT_USD = os.path.join(os.path.dirname(__file__), "prompts/prompt_USD.txt")
PROMPT_COT_DETECTION = os.path.join(os.path.dirname(__file__), "prompts/prompt_COT_detection.txt")

PRINT_DEBUG = True

info_intents = ["artist_info", "song_info", "album_info"]

correspondences_intents = {
    "artist_info": "artist_name",
    "song_info": "song_name",
    "album_info": "album_name"
}

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

def split_intent(input_string):
    match = re.match(r"(\w+)\((\w+)\)", input_string)
    if match:
        action = match.group(1)  
        intent = match.group(2) 
        return action, intent
    else:
        raise ValueError("Invalid input string format. Expected format: 'action(intent)'")
    
def get_current_intent(state_dict=None, next_best_action=None):
    if state_dict:
        next_best_action = state_dict["DM"]["next_best_action"]
    _, intent = split_intent(next_best_action)
    
    if PRINT_DEBUG:
        print("\n\n\nReturning intent: ", intent, "\n\n")
    return intent

def get_current_action(state_dict=None, next_best_action=None):
    if state_dict:
        next_best_action = state_dict["DM"]["next_best_action"]
    action, _ = split_intent(next_best_action)
    
    if PRINT_DEBUG:
        print("\n\n\nReturning action: ", action, "\n\n")
        return action

def final_check_NLU(state_dict, intents_extracted):
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
    errors = []
    required_slots = {
        "artist_info": ["artist_name"],
        "song_info": ["song_name"],
        "album_info": ["album_name"],
    }

    if not slots or "slots" not in slots:  # Check if 'slots' key exists
        # print("Slots data is missing or invalid.")
        return False

    actual_slots = slots["slots"]  # Extract the actual slots data
    # print("NLU COMPONENT: ", NLU_component)
    # print("SLOTS: ", actual_slots)

    for intent in NLU_component.keys():
        required = required_slots.get(intent, [])
        for slot in required:
            if slot not in actual_slots or not actual_slots[slot]:
                errors.append(f"Missing or invalid slot '{slot}' for intent '{intent}'")

    if errors:
        if PRINT_DEBUG:
            print("\n".join(errors))
        return False
    return True

def check_args(DM_component_part):
    
    if PRINT_DEBUG:
        print("\n\n\nDENTRO CHECK ARGS\n\n\n")
    
    next_best_action = DM_component_part.get("next_best_action", "")
    match = re.search(r'\((.*?)\)', next_best_action)
    
    if match:
        intent = match.group(1)
    else:
        return False
    # print("----------> Intent extracted: ", intent)

    if intent == "artist_info":
        if "artist_name" not in DM_component_part["args"] or DM_component_part["args"]["artist_name"] == None or DM_component_part["args"]["artist_name"] == "null":
            return False
    elif intent == "song_info":
        if "song_name" not in DM_component_part["args"] or DM_component_part["args"]["song_name"] in [None, "null"]:
            return False
        if "artist_name" in DM_component_part["args"] and DM_component_part["args"]["artist_name"] in [None, "null"] and "artist_name" not in DM_component_part["args"]["details"]:
            return False
    elif intent == "album_info":
        if "album_name" not in DM_component_part["args"] or DM_component_part["args"]["album_name"] in [None, "null"]:
            return False
        if "artist_name" in DM_component_part["args"] and DM_component_part["args"]["artist_name"] in [None, "null"] and "artist_name" not in DM_component_part["args"]["details"]:
            return False
    elif intent == "get_recommendations":
        extracted_action = get_current_action(next_best_action=next_best_action)
        if PRINT_DEBUG: 
            print("Extracted action:", extracted_action)  # Debugging

        if extracted_action == "request_info":
            if PRINT_DEBUG:
                print("Args content:", DM_component_part["args"])  # Debugging
                print("Details content:", DM_component_part["args"].get("details"))  # Debugging
            if "details" not in DM_component_part["args"] or DM_component_part["args"]["details"] == []:
                if PRINT_DEBUG:
                    print("❌ Missing 'details' in args")
                return False
        else:
            if PRINT_DEBUG:
                print("Genre value:", DM_component_part["args"].get("genre"))  # Debugging
            if "genre" not in DM_component_part["args"] or DM_component_part["args"]["genre"] in [None, "null"]:
                if PRINT_DEBUG:
                    print("❌ Missing or null 'genre'")
                return False
    return True



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

        # Step 3: Replace Python-specific keywords with JSON equivalents
        json_string = json_string.replace("None", "null").replace("True", "true").replace("False", "false")

        # Step 4: Ensure keys are quoted
        json_string = re.sub(r'(?<!")(\b\w+\b)(?=\s*:)', r'"\1"', json_string)  # Add quotes to keys

        # Step 5: Merge multiple top-level dictionaries into one
        json_string = re.sub(r"}\s*,\s*{", ", ", json_string)  # Merge separate dicts

        # Step 6: Remove trailing commas
        json_string = re.sub(r',\s*([}\]])', r'\1', json_string)  # Remove commas before } or ]

        # Step 7: Ensure balanced braces
        open_braces = json_string.count('{')
        close_braces = json_string.count('}')
        if open_braces > close_braces:
            json_string += '}' * (open_braces - close_braces)

        # Step 8: Parse the corrected JSON
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        if PRINT_DEBUG:
            print(f"Failed to fix JSON: {e}")
        return False
    
def validate_DM(response, check_type):
    """Check if the response is valid based on type and arguments."""

    try:
        parsed_response = fix_json_string(response)  
        if not parsed_response:
            if PRINT_DEBUG:
                print("Failed to parse JSON response.")
            return False
    except json.JSONDecodeError:
        if PRINT_DEBUG:
            print("Failed to parse JSON response.")
        return False
    # print("Inside validation, now checking response...", parsed_response, "\nwith check type: ", check_type)
    
    if "next_best_action" not in parsed_response:
        # print("Key 'next_best_action' is missing in response.")
        return False
    
    # qua bisogna fare un check sull'intent estratto da DM per next_best_action e vedere se è user_top_tracks o user_top_artists va bene che non ci sia details    
    next_best_action = parsed_response["next_best_action"]
    # print("Next best action: ", next_best_action)
    
    intent = get_current_intent(next_best_action=next_best_action)
    
    # Safely check if "details" exists and is not empty
    if not parsed_response["args"].get("details"): 
        # print("Key 'details' is missing or empty in 'args'.")
        if intent in ["user_top_tracks", "user_top_artists", "get_recommendations", "out_of_domain"]:
            pass 
        else:           
            return False
    
    if check_type == "request_info":
        return "request_info" in response and check_args(parsed_response)
    elif check_type == "confirmation":
        return "confirmation" in response and check_args(parsed_response)

    return False

def check_null_slots_and_update_state_dict(state_dict, out_USD, intents_extracted, slot_to_update):
    # out_NLU2 = str(fix_json_string(out_NLU2))  # Ensure the string format is correct
    
    # slot_to_update.append("details")            # Add 'details' to the list of slots to update, so that if the action is confirmation and 
                                                # user asked for something new, it can update the details 
    
    # for intent in intents_extracted:                                                    # nel caso di confirmation voglio aggiornare anche i details
    #     for detail in state_dict["NLU"][intent]["slots"]["details"]:
    #         if detail not in slot_to_update:            
    #             slot_to_update.append(detail)

    if PRINT_DEBUG:
        print("\n\nSlots to update: ", slot_to_update)
        print("\n\nout_USD: ", out_USD)

    for intent in intents_extracted:
            for slot in slot_to_update:
                if intent in info_intents and slot == "details":
                        # Capture everything inside [ ] including brackets
                        match = re.search(rf'.*{slot}.*:\s*(\[[^\]]*\])', str(out_USD))
                else:
                    # Capture standard values
                    match = re.search(rf'.*{slot}.*:\s*["\']?(.+?)["\']?(?=\s|$)', str(out_USD))                
            
                if match:
                    new_value = match.group(1).strip()  # Extract the captured value and remove spaces
                                
                if PRINT_DEBUG:
                    print(f"Catch new value for {slot}: {new_value}")
                state_dict["NLU"][intent]["slots"][slot] = new_value  # Update state_dict

        
    return state_dict

def get_slot_to_update(state_dict):
    slot_to_update = []
    
    if "details" in state_dict["DM"]["args"]:   
        for slot in state_dict["DM"]["args"]["details"]:
            slot_to_update.append(slot)
    
    return slot_to_update

def validate_USD(state_dict, out_NLU2, slot_to_update, intents_extracted, action):
        
    if action == "confirmation":
        for intent in intents_extracted:                                                    # nel caso di confirmation voglio aggiornare anche i details
            if intent in info_intents:
                for detail in state_dict["NLU"][intent]["slots"]["details"]:
                    if detail not in slot_to_update:            
                        slot_to_update.append(detail)
                    
    for slot in slot_to_update:
    # Use regex to extract the value of the slot
        match = re.search(rf'.*{re.escape(slot)}.*:\s*(.+)', str(out_NLU2))

        if not match: 
               return False
    return True     

def build_prompt_for_USD(state_dict, slot_to_update):    
    prefix = "slot_to_update: " + str(slot_to_update) + "\nstate_dict: \n" + str(state_dict)
        
    with open(PROMPT_USD, "r") as file:
        template = file.read()
    
    prompt = prefix + "\n\n" + template
    
    # print("PROMPT: \n\n", str(prompt)) 

    return prompt


def get_terminal_width():
    """Returns the width of the terminal, with a fallback to 80 if unknown."""
    return os.get_terminal_size().columns if sys.stdout.isatty() else 80

def center_text(text):
    """Centers a given text based on terminal width."""
    term_width = get_terminal_width()
    centered_lines = []
    
    for line in text.split("\n"):
        padding = (term_width - len(line)) // 2
        centered_lines.append(" " * max(0, padding) + line)

    return "\n".join(centered_lines)

def clear_last_line():
    """Clears the last line written in the terminal."""
    sys.stdout.write("\033[F")  # Moves the cursor up one line
    sys.stdout.write("\033[K")  # Clears the current line
    sys.stdout.flush()

def print_system(message, auth=False):
    """Prints a system message anchored to the left with a speech bubble, taking half of the terminal width."""
    if auth:
        print(center_text("\nAuthentication successful!\n"))
        
    term_width = get_terminal_width()
    width = term_width // 2 - 4  # Use half the terminal width
    wrapped_message = "\n".join(textwrap.fill(line, width) for line in message.split("\n"))  # Preserve \n
    border = "─" * (width + 2)

    print("\n\n")
    print(f"┌{border}┐")  # Top border
    for line in wrapped_message.split("\n"):
        print(f"│ {line.ljust(width)} │")  # Left-aligned content
    print(f"|/{'─' * (width + 1)}┘")  # Speech bubble tail

def input_user(prompt):
    """Gets user input, clears it, and prints it in a right-aligned speech bubble, taking half of the terminal width."""
    user_message = input(prompt)  # User types message
    clear_last_line()  # Clears the input after pressing Enter

    term_width = get_terminal_width()
    width = term_width // 2 - 4  # Use half the terminal width
    wrapped_message = "\n".join(textwrap.fill(line, width) for line in user_message.split("\n"))
    border = "─" * (width + 2)
    padding = " " * (term_width // 2)  # Right-align bubble to half of the terminal

    print("\n\n")
    print(f"{padding}┌{border}┐")  # Top border
    for line in wrapped_message.split("\n"):
        print(f"{padding}│ {line.ljust(width)} │")  # Right-aligned content
    print(f"{padding}└{'─' * (width + 1)}\|")  # Speech bubble tail

    return user_message  # Return user input if needed

def pretty_print():
    
    welcome_message = """\n\n
 __          __  _                               _        
 \ \        / / | |                             | |       
  \ \  /\  / /__| | ___ ___  _ __ ___   ___     | |_ ___  
   \ \/  \/ / _ \ |/ __/ _ \| '_ ` _ \ / _ \    | __/ _ \ 
    \  /\  /  __/ | (_| (_) | | | | | |  __/    | || (_) |
     \/  \/ \___|_|\___\___/|_| |_| |_|\___|     \__\___/ 
    \n\n
    """

    # Print centered and cleaned message
    print(center_text(welcome_message))
    
    colors = [
        "\033[91m",  # Red
        "\033[93m",  # Yellow
        "\033[92m",  # Green
        "\033[96m",  # Cyan
        "\033[94m",  # Blue
        "\033[95m",  # Magenta
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
        color = colors[i % len(colors)]  # Cycle through colors
        padding = (term_width - len(line)) // 2  # Calculate centering
        print(" " * max(0, padding) + color + line + "\033[0m")  # Centered and colored
        time.sleep(0.05)  # Optional: Adds a small delay for effect
