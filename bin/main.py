import re
import json
from spoti import *
from utils import *
from model_query import *
from statedictmanager import *

USER_INPUT = "user_input.txt"
INTENTS = [
    "artist_info", "song_info", "album_info", 
    "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"
]

CORRESPONDING_ACTIONS = {
    "artist_info": get_artist_info,
    "song_info": get_song_info,
    "album_info": get_album_info,
    "user_top_tracks": get_user_top_tracks,
    "user_top_artists": get_user_top_artists
}

# Utility functions
def split_intent(input_string):
    match = re.match(r"(\w+)\((\w+)\)", input_string)
    if not match:
        raise ValueError("Invalid input string format. Expected format: 'action(intent)'")
    return match.group(1), match.group(2)

def validate_args(intent, args):
    required_arg_map = {
        "artist_info": "artist_name",
        "song_info": "song_name",
        "album_info": "album_name"
    }
    
    print("intent: ", intent, " - required_arg: ", required_arg_map[intent], " - args: ", args, "\n\n")
    
    required_arg = required_arg_map.get(intent)
    return required_arg in args and args[required_arg]

def validate_response(response, check_type):
    try:
        parsed_response = fix_json_string(response)

        print("check_type: ", check_type, "\nvalidate_args: ", validate_args(parsed_response.get("next_best_action", ""), parsed_response.get("args", {})), "\n\n")

        if check_type == "request_info":
            return "request_info" in parsed_response and validate_args(parsed_response.get("next_best_action", ""), parsed_response.get("args", {}))
        elif check_type == "confirmation":
            
            return "confirmation" in parsed_response and validate_args(parsed_response.get("next_best_action", ""), parsed_response.get("args", {}))
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Failed to parse response: {e}")
        return False
    return False

# Core processing functions
def check_next_best_action_and_add_GK():
    dm_data = state_manager.state_dict.get("DM", {})
    if not isinstance(dm_data, dict):
        dm_data = json.loads(json.dumps(dm_data).replace("'", "\""))

    next_best_action = dm_data.get("next_best_action", "")
    action, intent = split_intent(next_best_action)

    if action == "confirmation":
        if intent not in CORRESPONDING_ACTIONS:
            print(f"Unsupported intent: {intent}")
            return

        print(f"Fetching information for intent: {intent}")
        info = CORRESPONDING_ACTIONS[intent](dm_data.get("args", {}))

        if info:
            print(f"Fetched info for {intent}: {info}")
            if intent != "artist_info":
                info = {k.replace("artists", "artist_name"): v for k, v in info.items()}

            gk_data = {intent: str(info) if isinstance(info, dict) else [str(i) for i in info]}
            state_manager.update_section("GK", gk_data)
        else:
            print(f"Failed to fetch data for {intent}")

    elif action == "request_info":
        print(f"Requesting additional info for intent: {intent}")
        if intent in CORRESPONDING_ACTIONS:
            info = CORRESPONDING_ACTIONS[intent](dm_data.get("args", {}))
            if info:
                state_manager.update_section("GK", {intent: info})

    else:
        print(f"Unsupported action: {action}")

def extract_intents_and_build_slots_input(state_dict, detected_intents):
    extracted_intents = []
    for intent in INTENTS:
        count = detected_intents.count(intent)
        for i in range(count):
            intent_key = f"{intent}{i + 1}" if count > 1 else intent
            extracted_intents.append(intent_key)
            state_dict["NLU"][intent_key] = {}

    slots_input = f"{user_input}\n" + "\n".join(f"- Intent{i+1}: {intent}" for i, intent in enumerate(extracted_intents))
    return slots_input, extracted_intents

def validate_slots(state_dict):
    for intent, data in state_dict.get("NLU", {}).items():
        slots = data.get("slots", {})
        required_slot = {
            "artist_info": "artist_name",
            "song_info": "song_name",
            "album_info": "album_name"
        }.get(intent)

        if required_slot and required_slot not in slots:
            return False
    return True

def fix_json_string(json_string):
    try:
        # Try to load the JSON as-is
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        # Fix common issues like missing closing braces
        if json_string.count('{') > json_string.count('}'):
            json_string += '}'
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as inner_e:
            print(f"Failed to fix JSON: {inner_e}")
            raise e  # Raise the original exception if fixing fails


def process_nlu(user_input):
    print(f"Processing input: {user_input}")

    detected_intents = model_query.query_model(system_prompt=PROMPT_NLU_intents, input_file=user_input)
    
    # print("\nDetected intents: ", detected_intents, "\n\n")
    
    state_manager.state_dict = {"NLU": {}}

    slots_input, intents_extracted = extract_intents_and_build_slots_input(
        state_manager.state_dict, detected_intents
    )

    while not validate_slots(state_manager.state_dict):
        out_nlu_slots = model_query.query_model(system_prompt=PROMPT_NLU_slots, input_file=slots_input)

        # print("\nExtracted slots: ", out_nlu_slots, "\n\n")
        
        for intent in intents_extracted:
            slots_data = re.search(rf'(?:- )?(?:"{intent}"|{intent}).*?(\{{.*?\}})', out_nlu_slots, re.DOTALL)
            if slots_data:
                                
                slots_content = slots_data.group(1)
                slots_content = fix_json_string(slots_content)
                
                try:
                    state_manager.update_section("NLU", {intent: slots_content})
                except json.JSONDecodeError as e:
                    print(f"Failed to parse slots for {intent} for error ", e)

    return intents_extracted

def query_model_with_retry(prompt, intents_extracted):
    response = model_query.query_model(system_prompt=prompt, input_file=str(state_manager.state_dict))
    
    for intent in intents_extracted:
        if state_manager.state_dict["NLU"][intent]["slots"]["details"]:
            check_type = "confirmation" if any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["details"] for intent in intents_extracted) and not state_manager.check_none_values() else "request_info"
        elif state_manager.state_dict["NLU"][intent]["slots"]["detail"]:
            check_type = "confirmation" if any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["detail"] for intent in intents_extracted) and not state_manager.check_none_values() else "request_info"
     
    while not validate_response(response, check_type):
        print("Invalid response: \n", response, "\n retrying...")
        response = model_query.query_model(system_prompt=prompt, input_file=str(state_manager.state_dict))
    return response

def process_dm(intents_extracted):
    dm_data = {}
    while not dm_data:
        response = query_model_with_retry(PROMPT_DM, intents_extracted)
        json_content = re.search(r'\{.*\}', response, re.DOTALL)

        if json_content:
            try:
                dm_data = json.loads(json_content.group())
            except json.JSONDecodeError:
                print("Invalid JSON in DM response")

    state_manager.update_section("DM", dm_data)
    return state_manager.state_dict

def process_nlg():
    return model_query.query_model(system_prompt=PROMPT_NLG, input_file=str(state_manager.state_dict))

if __name__ == "__main__":
    print("\nWelcome to LLAMusica platform 🎶🎧")
    authenticate()

    with open(USER_INPUT, "r") as file:
        user_inputs = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    for user_input in user_inputs:
        model_query = ModelQuery()
        state_manager = StateDictManager()

        intents_extracted = process_nlu(user_input)
        print("\nState after NLU:")
        state_manager.display()

        process_dm(intents_extracted)
        print("\nState after DM:")
        state_manager.display()

        check_next_best_action_and_add_GK()
        print("\nState after GK:")
        state_manager.display()

        output_nlg = process_nlg()
        print("\nGenerated response:")
        print(output_nlg)
