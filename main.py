import re
import json

import time
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
        "user_top_artists": get_user_top_artists,
        "get_recommendations": get_recommendations,
    }

    next_best_action = DM_component_part["next_best_action"]
    # print(f"\nNext best action: {next_best_action}")  

    action, intent = split_intent(next_best_action)
    # print(f"\n- action: {action} \n- intent: {intent}")

    if action == "confirmation":
        if PRINT_DEBUG:
            print(f"\n{intent} requested. Fetching...")
        
        # if intent == "user_top_tracks" or intent == "user_top_artists":
        #     DM_component_part["args"]["limit"] = int(DM_component_part["args"]["limit"])

        info = corresponding_actions.get(intent)(DM_component_part["args"])

        if info:
            # print(f"\Info fetched for {intent}:")
            if PRINT_DEBUG:
                print("Info extracted for intent ", intent, ": ", info)

            if intent in info_intents and intent != "artist_info":
                info = {k.replace("artists", "artist_name"): v for k, v in info.items()}
        
            if intent != "user_top_tracks" and intent != "user_top_artists":
                state_manager.update_section("GK", {intent: str(info)})
            else:
                state_manager.update_section("GK", {intent: [str(entity) for entity in info]})   # entity may be either an artist or a track
            return state_manager.state_dict
        else:
            if PRINT_DEBUG:
                print("\nFailed to fetch info or no data returned.")
    elif action == "request_info":
        if intent in info_intents:

            info = corresponding_actions.get(intent)(DM_component_part["args"])
            
            if info:
                if PRINT_DEBUG:
                    print(f"\nInfo fetched for {intent}:")
                    print(info)

                state_manager.update_section("GK", {intent: info})
                return state_manager.state_dict                    
                
        else:
            return state_manager.state_dict
    else:
        if PRINT_DEBUG:
            print(f"\nUnsupported action: {action}.")
        return state_manager.state_dict

def process_NLU_intent_and_slots(user_input):
    
    if PRINT_DEBUG:
        print("Processing Input: ", user_input)
        
    # extracting intents...
    out_NLU_intents = model_query.query_model(system_prompt=PROMPT_NLU_INTENTS, input_file=user_input)
    
    if PRINT_DEBUG:
        print("-"*95)
        print("llama3.2 output [INTENTS]:\n", out_NLU_intents)

    state_manager.state_dict = {"NLU": {}}

    slots_input, intents_extracted, state_manager.state_dict = extract_intents_build_slots_input(user_input, state_manager.state_dict, out_NLU_intents) 
    
    slots = {}
    
    while not check_slots(state_manager.state_dict["NLU"], slots):      # also check if slots == {} return False
    
        slots = {}
        # print("Extracting slots...")
        out_NLU_slots = model_query.query_model(system_prompt=PROMPT_NLU_SLOTS, input_file=slots_input)
        
        if PRINT_DEBUG:
            print("Checking outpus slots: ", out_NLU_slots)
            print("Intents extracted: ", intents_extracted)

        for intent in intents_extracted:
            pattern = rf'(?:- )?(?:"{intent}"|{intent}).*?(\{{.*?\}})'

            match = re.search(pattern, out_NLU_slots, re.DOTALL)

            if match:                
                slots_content = match.group(1)
                print("\nExtracted Slots Content: ", slots_content, " for intent ", intent)                
                try:
                    slots = fix_json_string(slots_content)
                    # if intent in info_intents and "details" in slots and slots["details"]:
                    #     state_manager.update_section("NLU", {intent: slots})
                    # elif intent in ["user_top_tracks", "user_top_artists", "out_of_domain"]:
                    # else:
                        # continue
                except json.JSONDecodeError as e:
                    if PRINT_DEBUG:
                        print(f"Failed to parse slots for {intent}: {e}. Slots Content: {slots_content}")
                    slots = {}
            state_manager.update_section("NLU", {intent: slots})

    # intents_extracted = check_duplicates(intents_extracted)
    
    if PRINT_DEBUG:
        print("-"*95)
        print("llama3.2 output [SLOTS]:\n", out_NLU_slots)

    intents_extracted = final_check_NLU(intents_extracted)          # check intents extracted if they're valid 
    
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
        
        out_DM = model_query.query_model(system_prompt=system_prompt, input_file=str(state_manager.state_dict))
        
        # print("\n\nDM response to be validated: \n\n\n", response)
        if validate_DM(out_DM, check_type):
            break
        if PRINT_DEBUG:
            print(f"------------> Invalid next_best_action detected \n {out_DM} \n\n... retrying...")

    return out_DM

def process_DM(intents_extracted):
    dm_data = {}
    while dm_data == {}:
        out_DM = query_DM_model_with_validation(PROMPT_DM, intents_extracted)
        if PRINT_DEBUG:
            print("Extracting DM data...")
        
        try:
            json_match = re.search(r'\{.*\}', out_DM, re.DOTALL)    # Match anything that starts and ends with braces

            if json_match:
                json_content = json_match.group()
                dm_data = fix_json_string(json_content)
            else:
                if PRINT_DEBUG:
                    print("No valid JSON content found in DM output....")
        except json.JSONDecodeError as e:
            if PRINT_DEBUG:
                print(f"Failed to parse DM output as JSON: {e}")
        
    state_manager.update_section("DM", dm_data)
    return state_manager.state_dict

def process_NLG():
    out_NLG = model_query.query_model(system_prompt=PROMPT_NLG, input_file=str(state_manager.state_dict))    
    
    if PRINT_DEBUG:
        print("\n\n\nllama3.2 output [NLG]:\n\n")
        print(out_NLG)
    state_manager.update_section("NLG", out_NLG)
    
    if PRINT_DEBUG:
        print("State Dictionary after NLG component processing:\n")
        state_manager.display()    
    return out_NLG

def process_COT_and_USD(slot_to_update, user_input, intents_extracted):
    # while True:
    
    prev_entity = ""    
    
    for intent in intents_extracted:
        if intent in info_intents:
            prev_entity += " - ".join(
                state_manager.state_dict["NLU"][intent]["slots"][elem]
                for intent in intents_extracted
                for elem in info_entity[intent]
                if state_manager.state_dict["NLU"][intent]["slots"][elem] not in [None, "null"] 
            ) 
        else:
            prev_entity += intent

    COT_input = prev_entity + " / " + user_input

    if PRINT_DEBUG:
        print("COT_input: ", COT_input)
    out_COT = model_query.query_model(system_prompt=PROMPT_COT_DETECTION, input_file=str(COT_input))
    
    if PRINT_DEBUG:
        print("\n\nAnalyzing user_input through COT component: ", COT_input)

        
    
        # if "same_query" in out_COD or "change_of_query" in out_COD:
        #     break 
        # print(f"Invalid COD output detected \n{out_COD}\n... retrying...")
    if PRINT_DEBUG:
        print("result COT --------> ", out_COT, "\n\n")
    
    
    if "change_of_query" in out_COT :     # or any(state_manager.state_dict["NLU"][intent]["slots"][correspondences_intents[intent]] not in out_NLU2 for intent in intents_extracted)
        if PRINT_DEBUG:
            print("\n\n\n------> Change of topic detected....\n\n\n")
        state_manager.delete_section("NLU")        
        state_manager.delete_section("DM")
        state_manager.delete_section("GK")
        state_manager.delete_section("NLG")
        return False 
    else:
        while True:
            if "artist_name" in slot_to_update:
                slot_to_update = ["artist_name"]
            if "confirmation" in user_input:
                for intent in intents_extracted:                            # nel caso di confirmation voglio aggiornare anche i details
                    if intent in info_intents:
                        for detail in state_manager.state_dict["NLU"][intent]["slots"]["details"]:
                           if detail not in slot_to_update:            
                                slot_to_update.append(detail)

            out_USD = model_query.query_model(system_prompt=build_prompt_for_USD(state_manager.state_dict, slot_to_update), input_file=str(user_input))
            # print("Analyzing out_USD: \n", out_USD)
            
            if "(request_info)" in user_input and validate_USD(state_manager.state_dict, out_USD, slot_to_update, intents_extracted, "request_info"):
                if PRINT_DEBUG:
                    print("\n\n----> request_info in NLU2 output detected... validated user_input...exiting...")
                break  # Exit the loop if the output is valid
            elif "(confirmation)" in user_input and validate_USD(state_manager.state_dict, out_USD, slot_to_update, intents_extracted, "confirmation"):
                if PRINT_DEBUG:
                    print("\n\n----> confirmation in NLU2 output detected... validated user_input...exiting...")
                break  # Exit the loop if the output is valid
            if PRINT_DEBUG:
                print(f"Invalid USD output detected \n{out_USD}\n... retrying...")
        
        state_manager.state_dict = check_null_slots_and_update_state_dict(state_manager.state_dict, out_USD, intents_extracted, slot_to_update)
        state_manager.delete_section("DM")
        state_manager.delete_section("GK")
        state_manager.delete_section("NLG")
        return True
    
def final_check_NLU(intents_extracted):
    to_delete = []
    for intent in intents_extracted:
        if intent in info_intents and "details" not in state_manager.state_dict["NLU"][intent]["slots"]:
            del state_manager.state_dict["NLU"][intent]
            if PRINT_DEBUG:
                print("\n\n\n------> No details found for ", intent, " intent. Deleting it from the state_dict...")
            to_delete.append(intent)
    intents_extracted = [intent for intent in intents_extracted if intent not in to_delete]
    return intents_extracted        
    
def run_pipeline(user_input):
    
    global state_manager, model_query
    
    exit = False
    new_intent = False
    
    while not exit:
        
        # print("\n\n\n------> Dentro al loop + grande, valore di new_intent: ", new_intent)
        new_intent = False
        state_manager = StateDictManager()
        model_query = ModelQuery()

        if PRINT_DEBUG:
            print("-"*95)
        if state_manager.state_dict == {"NLU": {}, "DM": {}, "GK": {}}:     # initial_state        
            _, intents_extracted = process_NLU_intent_and_slots(user_input)
        # else:
        #     new_input = build_input_with_history(state_manager.state_dict)

        while not new_intent and not exit:
            if PRINT_DEBUG:
                print("-"*95)
                print("\nState Dictionary after NLU component processing:\n")
                state_manager.display()
            
            process_DM(intents_extracted)
            if PRINT_DEBUG:
                print("-"*95)
                print("\nState Dictionary after DM component processing:\n")
                state_manager.display()
            
            build_GK()
            if PRINT_DEBUG:
                print("-"*95)
                print("\nState Dictionary after GK component processing:\n")
                state_manager.display()
                
            out_NLG = process_NLG()
            if PRINT_DEBUG:
                print("-"*95)
                print("\n\n\n")
            
            # a questo punto ci sarà una diramazione:
            # se next_best_action è "request_info" allora si chiede all'utente di fornire gli slot mancanti per poi aggiornare lo state_dict
            # se next_best_action è "confirmation" allora si forniscono le informazioni presenti nella GK per poi chiedere all'utente se desidera altro 
            # se desidera altro si apre una seconda istanza di NLU per rappresentare questa nuova query
            
            slot_to_update = get_slot_to_update(state_manager.state_dict)
            
            print_system(out_NLG)
            user_input = input_user("You: ")
            # these slots to update are extracted from the state_dict only if the next_best_action is "request_info"        
            result = process_COT_and_USD(slot_to_update, user_input + f" ({get_current_action(state_manager.state_dict)})", intents_extracted)
                
            if not result:                  # change_of_domain detected
                new_intent = True                
                if PRINT_DEBUG:
                    print("\n\nNew intent detected. Exiting the current loop...\n\n")
                    print("-"*95)
                    print("-"*95)
                    print("-"*95)
            else:
                if PRINT_DEBUG:
                    print("-"*95)
                    print("\nState Dictionary after NLU2 component processing:\n")
                state_manager.display()
            
            if user_input == "exit":
                # the main idea is to add an intent "end_conversation" that determine when a user wants to quit his experience with llama platform
                # till now, the conversation will be stuck in this main loop. 
                exit = True

if __name__ == "__main__":

    pretty_print()
    
    authenticate(force_auth=False)
    
    print_system(f"Hi {get_username()}, how can I help you?", auth=True)
    user_input = input_user("You: ")
    # "Show me my top artists of the last month."      # by The Weeknd 
    run_pipeline(user_input)
    
    # with open(USER_INPUT, "r") as file:
    #     USER_INPUTS = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    # for user_input in USER_INPUTS:
        
    #     run_pipeline(user_input)