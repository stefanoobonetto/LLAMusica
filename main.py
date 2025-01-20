import re
import json

from spoti import *
from utils import *
from model_query import *
from statedictmanager import *


USER_INPUT = "user_input.txt"
intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]

# model_query = ModelQuery()
# state_manager = StateDictManager()

def split_intent(input_string):
    match = re.match(r"(\w+)\((\w+)\)", input_string)
    if match:
        action = match.group(1)  
        intent = match.group(2) 
        return action, intent
    else:
        raise ValueError("Invalid input string format. Expected format: 'action(intent)'")

def check_next_best_action_and_add_GK():
    DM_component_part = state_manager.state_dict.get("DM", {})
    
    # { "next_best_action": "confirmation(album_info)", 
    #     "args": {
    #         "album_name": "Red", 
    #         "artist_name": "Taylor Swift", 
    #         "details": ["release_date", "total_tracks"] 
    #     } 
    # }
    # I want to check that if intent is "album_info" then I should have as first argument "album_name" 
    # if intent is "song_info" then I should have as first argument "song_name"
    # if intent is "artist_info" then I should have as first argument "artist_name"
    
    if isinstance(DM_component_part, dict):
        # dict to a JSON string
        DM_component_part = json.dumps(DM_component_part)
    
    DM_component_part = DM_component_part.replace("'", "\"")
    DM_component_part = DM_component_part.replace("artist_name", "artists")
    
    DM_component_part = json.loads(DM_component_part)

    corresponding_actions = {
        "artist_info": get_artist_info,
        "song_info": get_song_info,
        "album_info": get_album_info,
        "user_top_tracks": get_user_top_tracks,
        "user_top_artists": get_user_top_artists
    }

    next_best_action = DM_component_part["next_best_action"]
    print(f"\nNext best action: {next_best_action}")  

    action, intent = split_intent(next_best_action)
    print(f"\n- action: {action} \n- intent: {intent}")

    if action == "confirmation":
        if intent == "comparison":
            print("not already supported")
            # need to implement comparison function in spoti.py
        else:
            print(f"\n{intent} requested. Fetching...")

            info = corresponding_actions.get(intent)(DM_component_part["args"])
            
            if info:
                print(f"\Info fetched for {intent}:")
                print(info)

                if intent != "artist_info":
                    info = {k.replace("artists", "artist_name"): v for k, v in info.items()}
                
                if intent != "user_top_tracks" and intent != "user_top_artists":
                    state_manager.update_section("GK", {intent: str(info)})
                else:
                    state_manager.update_section("GK", {intent: [str(entity) for entity in info]})   # entity may be either an artist or a track
                return state_manager.state_dict
            else:
                print("\nFailed to fetch artist info or no data returned.")
    elif action == "request_info":
        if intent == "song_info" or intent == "album_info" or intent == "comparison":

            info = corresponding_actions.get(intent)(DM_component_part["args"])
            
            if info:
                print(f"\nInfo fetched for {intent}:")
                print(info)

                state_manager.update_section("GK", {intent: info})
                return state_manager.state_dict                    
                
        else:
            return state_manager.state_dict
    else:
        print(f"\nUnsupported action: {action}.")
        return state_manager.state_dict

def extract_intents_build_slots_input(state_dict, out_NLU_intents):
    
    intents_extracted = []
    intent_count = {}
    
    for intent in intents:
        count = out_NLU_intents.count(intent)  # Count occurrences of each intent in the output
        for i in range(count):
            intent_key = f"{intent}{i + 1}" if count > 1 else intent  # Number intents if multiple instances
            intents_extracted.append(intent_key)
            state_dict["NLU"][intent_key] = {}
            intent_count[intent] = intent_count.get(intent, 0) + 1  # Update count for numbering

    # print("Extracted Intents: ", intents_extracted)
    # print("\nState Dictionary:\n", state_dict)

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


def process_NLU_intent_and_slots(user_input):
    print("Processing Input: ", user_input)
        
    # extracting intents...
    out_NLU_intents = model_query.query_model(system_prompt=PROMPT_NLU_intents, input_file=user_input)
    print("\nllama3.2 output [INTENTS]:\n", out_NLU_intents)

    state_manager.state_dict = {"NLU": {}}

    slots_input, intents_extracted, state_manager.state_dict = extract_intents_build_slots_input(state_manager.state_dict, out_NLU_intents) 
    
    slots = {}
    while slots == {}:
        
        
        slots = {}
        while not check_slots(state_manager.state_dict["NLU"]):
            print("Extracting slots...")
            out_NLU_slots = model_query.query_model(system_prompt=PROMPT_NLU_slots, input_file=slots_input)
            
            for intent in intents_extracted:
                pattern = rf'(?:- )?(?:"{intent}"|{intent}).*?(\{{.*?\}})'

                match = re.search(pattern, out_NLU_slots, re.DOTALL)

                if match:                
                    slots_content = match.group(1)
                    print("\nExtracted Slots Content: ", slots_content, " for intent ", intent)
                    
                    # Attempt to validate and correct the JSON string
                    try:
                        # Fix common issues like missing closing braces
                        if slots_content.count('{') > slots_content.count('}'):
                            slots_content += '}'
                        slots = json.loads(slots_content)
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse slots for {intent}: {e}. Slots Content: {slots_content}")
                        slots = {}
                state_manager.update_section("NLU", {intent: slots})
                
    print("\nllama3.2 output [SLOTS]:\n", out_NLU_slots)
                

    return state_manager.state_dict, intents_extracted

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

def is_valid_response(response, check_type):
    """Check if the response is valid based on type and arguments."""
    parsed_response = json.loads(response)
    
    print("DENTRO, now checking response...", parsed_response, "\nwith check type: ", check_type)
    
    if check_type == "request_info":
        return "request_info" in response and check_args(parsed_response)
    elif check_type == "confirmation":
        return "confirmation" in response and check_args(parsed_response)
    return False

def query_model_with_validation(system_prompt, intents_extracted):

    for intent in intents_extracted:
        if state_manager.state_dict["NLU"][intent]["slots"]["details"]:
            check_type = "confirmation" if any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["details"] for intent in intents_extracted) and not state_manager.check_none_values() else "request_info"
        elif state_manager.state_dict["NLU"][intent]["slots"]["detail"]:
            check_type = "confirmation" if any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["detail"] for intent in intents_extracted) and not state_manager.check_none_values() else "request_info"
     
    # Initial query
    response = model_query.query_model(system_prompt=system_prompt, input_file=str(state_manager.state_dict))

    # Retry until the response is valid
    while not is_valid_response(response, check_type):
        print(f"------------> Wrong next_best_action found [{check_type}]... retrying asking...")
        response = model_query.query_model(system_prompt=system_prompt, input_file=str(state_manager.state_dict))

    return response


def process_DM(intents_extracted):
    dm_data = {}
    while dm_data == {}:
        out_DM = query_model_with_validation(PROMPT_DM, intents_extracted)
        print("Extracting DM data...")
        
        try:
            json_match = re.search(r'\{.*\}', out_DM, re.DOTALL)    # Match anything that starts and ends with braces

            if json_match:
                json_content = json_match.group()
                json_content = json_content.replace("'", "\"")
                # json_content = json_content.replace(" ", "")
                dm_data = json.loads(json_content)
            else:
                print("No valid JSON content found in DM output....")
        except json.JSONDecodeError as e:
            print(f"Failed to parse DM output as JSON: {e}")
        
    state_manager.update_section("DM", dm_data)
    return state_manager.state_dict

def process_NLG():
    out_NLG = model_query.query_model(system_prompt=PROMPT_NLG, input_file=str(state_manager.state_dict))    
    return out_NLG

# def update_state_dict():
    

if __name__ == "__main__":
    
    print("\n\n\n\nWelcome to LLAMusica platform 🎶🎧")
    
    authenticate()
        
    # user_input = "How lasts the song All I Want for Christmas by Mariah Carey?" 
    
    with open(USER_INPUT, "r") as file:
        USER_INPUTS = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    for user_input in USER_INPUTS:
        
        model_query = ModelQuery()
        
        global state_manager
        state_manager = StateDictManager()
        
        print("-"*95)
        _, intents_extracted = process_NLU_intent_and_slots(user_input)
        print("\nState Dictionary after NLU component processing:\n")
        state_manager.display()
        
        
        print("-"*95)
        process_DM(intents_extracted)
        print("\nState Dictionary after DM component processing:\n")
        state_manager.display()
        
        print("-"*95)    
        check_next_best_action_and_add_GK()
        print("\nState Dictionary after GK component processing:\n")
        state_manager.display()
        
        print("-"*95)
        out_NLG = process_NLG()
        print("\n\n\nllama3.2 output [NLG]:\n\n", out_NLG)
        print("\n")
        print("-"*95)
        
        # update_state_dict()
        
        print("-"*95)
        print("-"*95)
        print("\n")



