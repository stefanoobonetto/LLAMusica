import re
import json

from spoti import *
from utils import *
from model_query import *
from statedictmanager import *

USER_INPUT = "user_input.txt"
intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]

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
            # print(f"\Info fetched for {intent}:")
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

# def check_duplicates(intents_extracted):
#     to_keep = {}  # Dictionary to store the first occurrence of each unique slot combination
#     to_delete = set()

#     for intent in intents_extracted:
#         virgin_intent = re.sub(r'\d+$', '', intent)  # Remove trailing numbers

#         slot_values = state_manager.state_dict["NLU"][intent]["slots"][correspondences_intents[virgin_intent]]

#         # Convert slot_values to a tuple so it can be used as a key (since dicts are unhashable)
#         slot_tuple = tuple(sorted(slot_values.items()))  

#         # If this slot combination is already seen, mark it for deletion
#         if (virgin_intent, slot_tuple) in to_keep:
#             to_delete.add(intent)
#         else:
#             to_keep[(virgin_intent, slot_tuple)] = intent  # Store the first occurrence

#     # Keep only the necessary intents
#     intents_extracted[:] = [intent for intent in intents_extracted if intent not in to_delete]

#     # Remove duplicates from state_manager
#     for intent in to_delete:
#         del state_manager.state_dict["NLU"][intent]

#     return intents_extracted

def process_NLU_intent_and_slots(user_input):
    print("Processing Input: ", user_input)
        
    # extracting intents...
    out_NLU_intents = model_query.query_model(system_prompt=PROMPT_NLU_INTENTS, input_file=user_input)
    print("\nllama3.2 output [INTENTS]:\n", out_NLU_intents)

    state_manager.state_dict = {"NLU": {}}

    slots_input, intents_extracted, state_manager.state_dict = extract_intents_build_slots_input(user_input, state_manager.state_dict, out_NLU_intents) 
    
    slots = {}
    
    while not check_slots(state_manager.state_dict["NLU"], slots):      # also check if slots == {} return False
    
        slots = {}
        # print("Extracting slots...")
        out_NLU_slots = model_query.query_model(system_prompt=PROMPT_NLU_SLOTS, input_file=slots_input)
        
        for intent in intents_extracted:
            pattern = rf'(?:- )?(?:"{intent}"|{intent}).*?(\{{.*?\}})'

            match = re.search(pattern, out_NLU_slots, re.DOTALL)

            if match:                
                slots_content = match.group(1)
                # print("\nExtracted Slots Content: ", slots_content, " for intent ", intent)                
                try:
                    slots = fix_json_string(slots_content)
                    # if intent in info_intents and "details" in slots and slots["details"]:
                    #     state_manager.update_section("NLU", {intent: slots})
                    # elif intent in ["user_top_tracks", "user_top_artists", "out_of_domain"]:
                    # else:
                        # continue
                except json.JSONDecodeError as e:
                    print(f"Failed to parse slots for {intent}: {e}. Slots Content: {slots_content}")
                    slots = {}
            state_manager.update_section("NLU", {intent: slots})

    # intents_extracted = check_duplicates(intents_extracted)
    
            
    print("\nllama3.2 output [SLOTS]:\n", out_NLU_slots)

    return state_manager.state_dict, intents_extracted

def query_DM_model_with_validation(system_prompt, intents_extracted):

    for intent in intents_extracted:
        if "details" in state_manager.state_dict["NLU"][intent]["slots"]:
            check_type = "request_info" if any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["details"] for intent in intents_extracted) or state_manager.check_none_values() else "confirmation"
        else: 
            check_type = "request_info" if state_manager.check_none_values() else "confirmation"
    
    while True:
        
        # print("\n\n\nGiving to DM as input state_dict: \n\n\n", state_manager.state_dict)
        
        # with open(system_prompt, "r") as file:
        #     content = file.read()
        
        # print("\n\n\n\n\nQuering DM model...with prompt: \n", content, "\n\nand input file: \n", str(state_manager.state_dict), "\n\n")
        
        response = model_query.query_model(system_prompt=system_prompt, input_file=str(state_manager.state_dict))
        
        # print("\n\nDM response to be validated: \n\n\n", response)
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
    
    print("\n\n\nllama3.2 output [NLG]:\n\n")
    print(out_NLG)
    
    state_manager.update_section("NLG", out_NLG)
    
    print("State Dictionary after NLG component processing:\n")
    state_manager.display()    
    return out_NLG

def process_NLU2(slot_to_update, user_input, intents_extracted):
    # while True:

    out_COD = model_query.query_model(system_prompt=build_prompt_for_COD(state_manager.state_dict, intents_extracted), input_file=str(user_input))
    
    print("Analyzing user_input: ", user_input)
    
        # if "same_query" in out_COD or "change_of_query" in out_COD:
        #     break 
        # print(f"Invalid COD output detected \n{out_COD}\n... retrying...")
    print("out_COD --------> ", out_COD, "\n\n")
    
    
    if "change_of_query" in out_COD :     # or any(state_manager.state_dict["NLU"][intent]["slots"][correspondences_intents[intent]] not in out_NLU2 for intent in intents_extracted)
        print("\n\n\n------> Change of domain detected....\n\n\n")
        state_manager.delete_section("NLU")        
        state_manager.delete_section("DM")
        state_manager.delete_section("GK")
        state_manager.delete_section("NLG")
        return False 
    else:
        print("\n\n\nUpdating state_dict with USD output...\n\n\n")
        
        while True:
            if "artist_name" in slot_to_update:
                slot_to_update = ["artist_name"]
            if "confirmation" in user_input:
                slot_to_update.append("details")

            out_USD = model_query.query_model(system_prompt=build_prompt_for_USD(state_manager.state_dict, slot_to_update), input_file=str(user_input))
            print("Analyzing out_SD: \n", out_USD)
            
            if "(request_info)" in user_input and validate_USD(state_manager.state_dict, out_USD, slot_to_update, intents_extracted, "request_info"):
                print("\n\n----> request_info in NLU2 output detected... validated user_input...exiting...")
                break  # Exit the loop if the output is valid
            elif "(confirmation)" in user_input and validate_USD(state_manager.state_dict, out_USD, slot_to_update, intents_extracted, "confirmation"):
                print("\n\n----> confirmation in NLU2 output detected... validated user_input...exiting...")
                break  # Exit the loop if the output is valid
            print(f"Invalid NLU2 output detected \n{out_COD}\n... retrying...")
        
        state_manager.state_dict = check_null_slots_and_update_state_dict(state_manager.state_dict, out_USD, intents_extracted, slot_to_update)
        state_manager.delete_section("DM")
        state_manager.delete_section("GK")
        state_manager.delete_section("NLG")
        return True
    
def final_check_NLU(intents_extracted):
    for intent in intents_extracted:
        if intent in info_intents and "details" not in state_manager.state_dict["NLU"][intent]["slots"]:
            del state_manager.state_dict["NLU"][intent]
            print("\n\n\n------> No details found for ", intent, " intent. Deleting it from the state_dict...")
            
def run_pipeline(user_input):
    
    global state_manager, model_query
    
    model_query = ModelQuery()
    
    exit = False
    new_intent = False
    
    while not exit:
        
        # print("\n\n\n------> Dentro al loop + grande, valore di new_intent: ", new_intent)
        new_intent = False
        state_manager = StateDictManager()

        print("-"*95)
        if state_manager.state_dict == {"NLU": {}, "DM": {}, "GK": {}}:     # initial_state        
            _, intents_extracted = process_NLU_intent_and_slots(user_input)
        # else:
        #     new_input = build_input_with_history(state_manager.state_dict)

        final_check_NLU(intents_extracted)

        while not new_intent and not exit:
            print("-"*95)
            print("\nState Dictionary after NLU component processing:\n")
            state_manager.display()
            
            process_DM(intents_extracted)
            print("-"*95)
            print("\nState Dictionary after DM component processing:\n")
            state_manager.display()
            
            build_GK()
            print("-"*95)
            print("\nState Dictionary after GK component processing:\n")
            state_manager.display()
            
            print("-"*95)
            out_NLG = process_NLG()
            print("\n\n\n")
            
            # a questo punto ci sarà una diramazione:
            # se next_best_action è "request_info" allora si chiede all'utente di fornire gli slot mancanti per poi aggiornare lo state_dict
            # se next_best_action è "confirmation" allora si forniscono le informazioni presenti nella GK per poi chiedere all'utente se desidera altro 
            # se desidera altro si apre una seconda istanza di NLU per rappresentare questa nuova query
            
            slot_to_update = get_slot_to_update(state_manager.state_dict)
            
            user_input = input(out_NLG + "\n")  
            # these slots to update are extracted from the state_dict only if the next_best_action is "request_info"        
            result = process_NLU2(slot_to_update, user_input + f" ({get_current_action(state_manager.state_dict)})", intents_extracted)
                
            if not result:                  # change_of_domain detected
                new_intent = True                
                print("\n\nNew intent detected. Exiting the current loop...\n\n")
                print("-"*95)
                print("-"*95)
                print("-"*95)
            else:
                print("-"*95)
                print("\nState Dictionary after NLU2 component processing:\n")
                state_manager.display()
            
            if user_input == "exit":
                # the main idea is to add an intent "end_conversation" that determine when a user wants to quit his experience with llama platform
                # till now, the conversation will be stuck in this main loop. 
                exit = True
        
if __name__ == "__main__":
    
    print("\n\n\n\nWelcome to LLAMusica platform 🎶🎧")
    
    authenticate()
        
    user_input = "How lasts the song Blinding Lights by The Weeknd?"      # by The Weeknd 
    run_pipeline(user_input)
    
    # with open(USER_INPUT, "r") as file:
    #     USER_INPUTS = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    # for user_input in USER_INPUTS:
        
    #     run_pipeline(user_input)