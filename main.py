import re
import json

from spoti import *
from utils import *
from model_query import *
from statedictmanager import *


USER_INPUT = "user_input.txt"
intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]

model_query = ModelQuery()
state_manager = StateDictManager()

def split_intent(input_string):
    match = re.match(r"(\w+)\((\w+)\)", input_string)
    if match:
        action = match.group(1)  
        intent = match.group(2) 
        return action, intent
    else:
        raise ValueError("Invalid input string format. Expected format: 'action(intent)'")


def get_args(DM_component_part):
    args = []
    for elem in DM_component_part.get("args"):
        args.append(elem)
    
    print("\n\nExtracted Args: ", args)
    return args


def check_next_best_action_and_add_GK():
    DM_component_part = state_manager.state_dict.get("DM", {})
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

            info = corresponding_actions.get(intent)(*get_args(DM_component_part))

            if info:
                print(f"\Info fetched for {intent}:")
                print(info)

                if intent != "artist_info":
                    info = {k.replace("artists", "artist_name"): v for k, v in info.items()}
                
                if intent != "user_top_tracks" and intent != "user_top_artists":
                    state_manager.update_section("GK", {intent: info})
                else:
                    state_manager.update_section("GK", {intent: [str(entity) for entity in info]}) # entity may be either an artist or a track
                return state_manager.state_dict
            else:
                print("\nFailed to fetch artist info or no data returned.")
    elif action == "request_info":
        if intent == "song_info" or intent == "album_info" or intent == "comparison":

            info = corresponding_actions.get(intent)(*get_args(DM_component_part))
            
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

def process_NLU_intent_and_slots(user_input):
    print("Processing Input: ", user_input)
        
    # extracting intents...
    out_NLU_intents = model_query.query_model(system_prompt=PROMPT_NLU_intents, input_file=user_input)
    print("\nllama3.2 output [INTENTS]:\n", out_NLU_intents)

    state_manager.state_dict = {"NLU": {}}

    slots_input, intents_extracted, state_manager.state_dict = extract_intents_build_slots_input(state_manager.state_dict, out_NLU_intents) 
    
    out_NLU_slots = model_query.query_model(system_prompt=PROMPT_NLU_slots, input_file=slots_input)
    
    print("\nllama3.2 output [SLOTS]:\n", out_NLU_slots)
    
    for intent in intents_extracted:
        pattern = rf'(?:- )?(?:"{intent}"|{intent}):\s*(\{{.*?\}})'

        match = re.search(pattern, out_NLU_slots, re.DOTALL)
        if match:
            slots_content = match.group(1)
            print("\nExtracted Slots Content: ", slots_content)
            
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
        else:
            print(f"No slots found for {intent} in llama3.2 output.")
    return state_manager.state_dict, intents_extracted

def process_DM():
    out_DM = model_query.query_model(system_prompt=PROMPT_DM, input_file=str(state_manager.state_dict))
 
    if not state_manager.check_null_values():
        while "request_info" in out_DM:
            print("------------> Wrong next_best_action found [request_info]... retrying asking...")    
            out_DM = model_query.query_model(system_prompt=PROMPT_DM, input_file=str(state_manager.state_dict))
    else:
        while "confirmation" in out_DM:
            print("------------> Wrong next_best_action found [confirmation]... retrying asking...")    
            out_DM = model_query.query_model(system_prompt=PROMPT_DM, input_file=str(state_manager.state_dict))
    print("\n\n\nllama3.2 output [DM]:\n", out_DM)
    
    try:
        json_pattern = r'\{.*\}'  # Match anything that starts and ends with braces
        json_match = re.search(json_pattern, out_DM, re.DOTALL)

        if json_match:
            
            json_content = json_match.group()
            json_content = json_content.replace("'", "\"")
            # json_content = json_content.replace(" ", "")
            dm_data = json.loads(json_content)
            print("DM_data: ", dm_data)
            if isinstance(dm_data, dict):
                state_manager.update_section("DM", dm_data)
            else:
                print("Extracted content is not a valid JSON object.")
        else:
            print("No valid JSON content found in DM output.")

        return state_manager.state_dict
    except json.JSONDecodeError as e:
        print(f"Failed to parse DM output as JSON: {e}")
    
    return state_manager.state_dict

def process_NLG():
    out_NLG = model_query.query_model(system_prompt=PROMPT_NLG, input_file=str(state_manager.state_dict))
    print("\n\n\nllama3.2 output [NLG]:\n\n\n", out_NLG)
    
    return out_NLG

if __name__ == "__main__":
    authenticate()
    
    user_input = "When does Sconosciuti by Emma Nolde has been released?" 
    
    
    print("-"*95)
    state_manager.state_dict, _ = process_NLU_intent_and_slots(user_input)
    print("\nState Dictionary after NLU component processing:\n")
    state_manager.display()
    
    
    print("-"*95)
    state_manager.state_dict = process_DM()
    print("\nState Dictionary after DM component processing:\n")
    state_manager.display()
    
    print("-"*95)    
    check_next_best_action_and_add_GK()
    
    print("\n\n\nFINAL STATE DICT WITH GK:\n\n")
    state_manager.display()
    
    print("-"*95)
    output = process_NLG()
