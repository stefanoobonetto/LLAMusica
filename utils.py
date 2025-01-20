import re
import os
import json

intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]
PROMPT_NLU = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU.txt")
PROMPT_NLU_intents = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_intents.txt")
PROMPT_NLU_slots = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_slots.txt")
PROMPT_DM = os.path.join(os.path.dirname(__file__), "prompts/prompt_DM.txt")
PROMPT_NLG = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLG.txt")

def split_intent(input_string):
    match = re.match(r"(\w+)\((\w+)\)", input_string)
    if match:
        action = match.group(1)  
        intent = match.group(2) 
        return action, intent
    else:
        raise ValueError("Invalid input string format. Expected format: 'action(intent)'")

    return action, intent
    
def get_current_intent(state_dict):
    next_best_action = state_dict["DM"]["next_best_action"]
    _, intent = split_intent(next_best_action)
    return intent

def get_current_action(state_dict):
    next_best_action = state_dict["DM"]["next_best_action"]
    action, _ = split_intent(next_best_action)
    return action

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

def check_slots(NLU_component):
    errors = []
    required_slots = {
        "artist_info": ["artist_name"],
        "song_info": ["song_name"],
        "album_info": ["album_name"],
    }

    for intent, data in NLU_component.items():
        slots = data.get("slots", {})
        required = required_slots.get(intent, [])
        for slot in required:
            if slot not in slots or not slots[slot]:
                errors.append(f"Missing or invalid slot '{slot}' for intent '{intent}'")

    if errors:
        print("\n".join(errors))
        return False
    return True

def check_args(DM_component_part):
    next_best_action = DM_component_part.get("next_best_action", "")
    match = re.search(r'\((.*?)\)', next_best_action)
    
    if match:
        intent = match.group(1)
    else:
        return False
    print("----------> Intent extracted: ", intent)

    if intent == "artist_info":
        if "artist_name" not in DM_component_part["args"] or DM_component_part["args"]["artist_name"] == None or DM_component_part["args"]["artist_name"] == "null":
            return False
    elif intent == "song_info":
        if "song_name" not in DM_component_part["args"] or DM_component_part["args"]["song_name"] == None or DM_component_part["args"]["song_name"] == "null":
            return False
    elif intent == "album_info":
        if "album_name" not in DM_component_part["args"] or DM_component_part["args"]["album_name"] == None or DM_component_part["args"]["album_name"] == "null":
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

def is_valid_response(response, check_type):
    """Check if the response is valid based on type and arguments."""
    parsed_response = fix_json_string(response)  # Fix and parse the JSON response

    print("Inside validation, now checking response...", parsed_response, "\nwith check type: ", check_type)
    
    # qua bisogna fare un check sull'intent estratto da DM per next_best_action e vedere se è user_top_tracks o user_top_artists va bene che non ci sia details    
    next_best_action = parsed_response["next_best_action"]
    print("Next best action: ", next_best_action)
    match = re.search(r'\((.*?)\)', next_best_action)
    if match:
        intent = match.group(0)
    
    # Safely check if "details" exists and is not empty
    if not parsed_response["args"].get("details"): 
        print("Key 'details' is missing or empty in 'args'.")
        if intent in ["user_top_tracks", "user_top_artists", "out_of_domain"]:
            pass 
        else:           
            return False
    
    if check_type == "request_info":
        return "request_info" in response and check_args(parsed_response)
    elif check_type == "confirmation":
        return "confirmation" in response and check_args(parsed_response)
    
    return False

def check_null_slots_and_update_state_dict(state_dict, out_NLU2, intents_extracted):
    out_NLU2 = fix_json_string(out_NLU2)
    for intent in intents_extracted:
        for slot in out_NLU2["NLU"][f"{intent}"]["slots"]:
            if state_dict["NLU"][f"{intent}"]["slots"][slot] in [None, "null"]:
                state_dict["NLU"][f"{intent}"]["slots"][slot] = out_NLU2["NLU"][f"{intent}"]["slots"][slot]
    return state_dict
            
def get_slot_to_update(state_dict):
    slot_to_update = []
        
    for slot in state_dict["DM"]["args"]["details"]:
        slot_to_update.append(slot)
    
    return slot_to_update