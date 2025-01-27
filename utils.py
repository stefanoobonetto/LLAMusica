import re
import os
import json

intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]
PROMPT_NLU = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU.txt")
PROMPT_NLU_INTENTS = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_intents.txt")
PROMPT_NLU_SLOTS = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_slots.txt")
PROMPT_DM = os.path.join(os.path.dirname(__file__), "prompts/prompt_DM.txt")
PROMPT_NLG = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLG.txt")
info_intents = ["artist_info", "song_info", "album_info"]

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

def check_slots(NLU_component, slots):
    errors = []
    required_slots = {
        "artist_info": ["artist_name"],
        "song_info": ["song_name"],
        "album_info": ["album_name"],
    }

    if not slots or "slots" not in slots:  # Check if 'slots' key exists
        print("Slots data is missing or invalid.")
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
        print(f"Failed to fix JSON: {e}")
        return False
    
def is_valid_response(response, check_type):
    """Check if the response is valid based on type and arguments."""

    try:
        parsed_response = fix_json_string(response)  # Fix and parse the JSON response
        if not parsed_response:
            print("Failed to parse JSON response.")
            return False
    except json.JSONDecodeError:
        print("Failed to parse JSON response.")
        return False
    # print("Inside validation, now checking response...", parsed_response, "\nwith check type: ", check_type)
    
    if "next_best_action" not in parsed_response:
        # print("Key 'next_best_action' is missing in response.")
        return False
    
    # qua bisogna fare un check sull'intent estratto da DM per next_best_action e vedere se è user_top_tracks o user_top_artists va bene che non ci sia details    
    next_best_action = parsed_response["next_best_action"]
    # print("Next best action: ", next_best_action)
    match = re.search(r'\((.*?)\)', next_best_action)
    if match:
        intent = match.group(0)
    
    # Safely check if "details" exists and is not empty
    if not parsed_response["args"].get("details"): 
        # print("Key 'details' is missing or empty in 'args'.")
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
            # Controllo se lo slot non esiste affatto in state_dict
            if slot not in state_dict["NLU"][f"{intent}"]["slots"]:
                state_dict["NLU"][f"{intent}"]["slots"][slot] = out_NLU2["NLU"][f"{intent}"]["slots"][slot]
            # Se lo slot esiste ma è None o "null"
            elif state_dict["NLU"][f"{intent}"]["slots"][slot] in [None, "null"]:
                state_dict["NLU"][f"{intent}"]["slots"][slot] = out_NLU2["NLU"][f"{intent}"]["slots"][slot]
        state_dict["NLU"][f"{intent}"]["slots"]["details"] = out_NLU2["NLU"][f"{intent}"]["slots"]["details"]
    return state_dict    
            
def get_slot_to_update(state_dict):
    slot_to_update = []
        
    for slot in state_dict["DM"]["args"]["details"]:
        slot_to_update.append(slot)
    
    return slot_to_update

def validate_out_NLU2(out_NLU2, slot_to_update, intents_extracted):
    
    print("Validating NLU2 output...\n", out_NLU2, "\n\n\n")
    
    if "change_of_intent" in out_NLU2:
        return True
    
    out_NLU2 = fix_json_string(out_NLU2)
    
    if not out_NLU2:
        return False
    
    mandatory_slots = {
        "artist_info": ["artist_name"],
        "song_info": ["song_name", "artist_name"],
        "album_info": ["album_name", "artist_name"]
    }
    
    for intent in intents_extracted:
        for slot in slot_to_update:
            if "slots" not in out_NLU2["NLU"][f"{intent}"] or not slot in out_NLU2["NLU"][f"{intent}"]["slots"] or out_NLU2["NLU"][f"{intent}"]["slots"][slot] in [None, "null"]:
                return False
            if intent in info_intents and "details" not in out_NLU2["NLU"][f"{intent}"]["slots"]:
                return False
            # if "NLG" in out_NLU2 or "DM" in out_NLU2 or "GK" in out_NLU2:
            #     return False
        if not all(slot in out_NLU2["NLU"][f"{intent}"]["slots"] for slot in mandatory_slots[intent]):
            return False
    return True

def build_prompt_for_NLU2(state_dict, slot_to_update):
    # Properly escape curly braces in the JSON example using double braces {{ }}
    
    PROMPT_NLU2_TEMPLATE = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU2_template.txt")
    prefix = "slot_to_update: " + str(slot_to_update) + "\nstate_dict: \n" + str(state_dict)
    
    with open(PROMPT_NLU2_TEMPLATE, "r") as file:
        template = file.read()
    
    prompt = prefix + "\n\n" + template
    
    # print("PROMPT: \n\n", str(prompt)) 

    return prompt