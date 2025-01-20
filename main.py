import re
import json

from spoti import *
from utils import *
from model_query import *
from statedictmanager import *

USER_INPUT = "user_input.txt"
intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]
info_intents = ["artist_info", "song_info", "album_info"]

def build_GK():
    DM_component_part = state_manager.state_dict.get("DM", {})
        
    if isinstance(DM_component_part, dict):
        # dict to a JSON string
        DM_component_part = json.dumps(DM_component_part)
    
    # this substitution step is crucial since the spotify API requires the key "artists" instead of "artist_name"    
    DM_component_part = DM_component_part.replace("artist_name", "artists") 
    
    DM_component_part = fix_json_string(DM_component_part)

    corresponding_actions = {
        "artist_info": get_artist_info,
        "song_info": get_song_info,
        "album_info": get_album_info,
        "user_top_tracks": get_user_top_tracks,
        "user_top_artists": get_user_top_artists
    }

    next_best_action = DM_component_part["next_best_action"]
    # print(f"\nNext best action: {next_best_action}")  

    action, intent = split_intent(next_best_action)
    # print(f"\n- action: {action} \n- intent: {intent}")

    if action == "confirmation":
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
            print("\nFailed to fetch info or no data returned.")
    elif action == "request_info":
        if intent in info_intents:

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

def process_NLU_intent_and_slots(user_input):
    print("Processing Input: ", user_input)
        
    # extracting intents...
    out_NLU_intents = model_query.query_model(system_prompt=PROMPT_NLU_intents, input_file=user_input)
    print("\nllama3.2 output [INTENTS]:\n", out_NLU_intents)

    state_manager.state_dict = {"NLU": {}}

    slots_input, intents_extracted, state_manager.state_dict = extract_intents_build_slots_input(user_input, state_manager.state_dict, out_NLU_intents) 
    
    slots = {}
    
    while not check_slots(state_manager.state_dict["NLU"], slots):      # also check if slots == {} return False
    
        slots = {}
        # print("Extracting slots...")
        out_NLU_slots = model_query.query_model(system_prompt=PROMPT_NLU_slots, input_file=slots_input)
        
        for intent in intents_extracted:
            pattern = rf'(?:- )?(?:"{intent}"|{intent}).*?(\{{.*?\}})'

            match = re.search(pattern, out_NLU_slots, re.DOTALL)

            if match:                
                slots_content = match.group(1)
                # print("\nExtracted Slots Content: ", slots_content, " for intent ", intent)                
                try:
                    slots = fix_json_string(slots_content)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse slots for {intent}: {e}. Slots Content: {slots_content}")
                    slots = {}
            state_manager.update_section("NLU", {intent: slots})
            
    print("\nllama3.2 output [SLOTS]:\n", out_NLU_slots)

    return state_manager.state_dict, intents_extracted

def query_DM_model_with_validation(system_prompt, intents_extracted):

    for intent in intents_extracted:
        if state_manager.state_dict["NLU"][intent]["slots"]["details"]:
            print("\n\nCheck none values: ", not state_manager.check_none_values())
            print("\n\nartist_name? : ", any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["details"] for intent in intents_extracted))
            check_type = "request_info" if any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["details"] for intent in intents_extracted) or state_manager.check_none_values() else "confirmation"
        # elif state_manager.state_dict["NLU"][intent]["slots"]["detail"]:
        #     check_type = "confirmation" if any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["detail"] for intent in intents_extracted) and not state_manager.check_none_values() else "request_info"

        print("\n\n------> Check type extracted: ", check_type, "\n\n")
        
    while True:
        response = model_query.query_model(system_prompt=system_prompt, input_file=str(state_manager.state_dict))
        if is_valid_response(response, check_type):
            break
        print(f"------------> Invalid next_best_action detected [{check_type}]... retrying...")

    return response

def process_DM(intents_extracted):
    dm_data = {}
    while dm_data == {}:
        out_DM = query_DM_model_with_validation(PROMPT_DM, intents_extracted)
        print("Extracting DM data...")
        
        try:
            json_match = re.search(r'\{.*\}', out_DM, re.DOTALL)    # Match anything that starts and ends with braces

            if json_match:
                json_content = json_match.group()
                dm_data = fix_json_string(json_content)
            else:
                print("No valid JSON content found in DM output....")
        except json.JSONDecodeError as e:
            print(f"Failed to parse DM output as JSON: {e}")
        
    state_manager.update_section("DM", dm_data)
    return state_manager.state_dict

def process_NLG():
    out_NLG = model_query.query_model(system_prompt=PROMPT_NLG, input_file=str(state_manager.state_dict))    
    state_manager.update_section("NLG", out_NLG)
    return out_NLG

def process_NLU2(slot_to_update, prompt, user_input, intents_extracted):
    while True:
        out_NLU2 = model_query.query_model(system_prompt=prompt, input_file=str(user_input))
        
        # Check the condition for continuing or exiting
        if validate_out_NLU2(out_NLU2, slot_to_update, intents_extracted):
            break  # Exit the loop if the output is valid
        
    print("\n\n\nllama3.2 output [NLU2]:\n\n")
    print(out_NLU2)
    
    state_manager.state_dict = check_null_slots_and_update_state_dict(state_manager.state_dict, out_NLU2, intents_extracted)
    state_manager.empty_section("DM")
    state_manager.empty_section("GK")
    state_manager.empty_section("NLG")
        
# def build_input_with_history(state_dict):
#     info_slots = {
#         "artist_info": ["artist_name"],
#         "song_info": ["song_name", "artist_name"],
#         "album_info": ["album_name", "artist_name"],
#         "user_top_tracks": ["time_frame", "limit"],
#         "user_top_artists": ["time_frame", "limit"]
#     }
    
#     state_dict[]
    
def run_pipeline(user_input):
    
    global state_manager, model_query
    
    state_manager = StateDictManager()
    model_query = ModelQuery()
    
    
    
    while True:
    
        print("-"*95)
        if state_manager.state_dict == {"NLU": {}, "DM": {}, "GK": {}}:     # initial_state        
            _, intents_extracted = process_NLU_intent_and_slots(user_input)
        # else:
        #     new_input = build_input_with_history(state_manager.state_dict)

        
        print("\nState Dictionary after NLU component processing:\n")
        state_manager.display()
        
        print("-"*95)
        process_DM(intents_extracted)
        print("\nState Dictionary after DM component processing:\n")
        state_manager.display()
        
        print("-"*95)    
        build_GK()
        print("\nState Dictionary after GK component processing:\n")
        state_manager.display()
        
        print("-"*95)
        out_NLG = process_NLG()
        print("\n\n\n")
        
        # a questo punto ci sarà una diramazione:
        # se next_best_action è "request_info" allora si chiede all'utente di fornire gli slot mancanti per poi aggiornare lo state_dict
        # se next_best_action è "confirmation" allora si forniscono le informazioni presenti nella GK per poi chiedere all'utente se desidera altro 
        # se desidera altro si apre una seconda istanza di NLU per rappresentare questa nuova query
        
        if get_current_action(state_manager.state_dict) == "request_info":
            user_input = input(out_NLG + "\n")  
            # these slots to update are extracted from the state_dict only if the next_best_action is "request_info"
            if get_current_action(state_manager.state_dict) == "request_info":
                slot_to_update = get_slot_to_update(state_manager.state_dict)
        
            process_NLU2(slot_to_update, build_prompt_for_NLU2(state_manager.state_dict, slot_to_update), user_input, intents_extracted)
            print("\nState Dictionary after NLU2 component processing:\n")
            state_manager.display()
            
            # here we should repass it through the DM component to arrive till a confirmation next_best_action
            
        elif get_current_action(state_manager.state_dict) == "confirmation":
            user_input = input(out_NLG + "\n")
            
            if user_input == "no":
                break
            
    # the main idea is to add an intent "end_conversation" that determine when a user wants to quit his experience with llama platform
    # till now, the conversation will be stuck in this main loop. 
        
if __name__ == "__main__":
    
    print("\n\n\n\nWelcome to LLAMusica platform 🎶🎧")
    
    authenticate()
        
    user_input = "How lasts the song All I Want for Christmas by Mariah Carey?" 
    run_pipeline(user_input)
    
    # with open(USER_INPUT, "r") as file:
    #     USER_INPUTS = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    # for user_input in USER_INPUTS:
        
    #     run_pipeline(user_input)