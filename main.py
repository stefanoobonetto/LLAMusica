import re
import csv
import json
import pandas as pd
from collections import Counter

from spoti import *
from utils import *
from model_query import *
from statedictmanager import *

intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]

def build_GK():
    """
    Populates the GK (General Knowledge) section by processing the Dialogue Manager (DM) output.

    - Retrieves and formats the DM component's state.
    - Adjusts key names to match API requirements.
    - Extracts relevant information for each intent based on the "next_best_action."
    - Updates the state dictionary with the gathered data.

    Returns:
        dict: Updated state dictionary with the GK component.
    """
    
    DM_component_list = json.dumps(state_manager.state_dict.get("DM", {}))
    
    DM_component_list = DM_component_list.replace("artist_name", "artists")             # this substitution step is crucial since the spotify API requires the key "artists" instead of "artist_name"    
    
    list_GK = {}
    
    for element_new_best_option in json.loads(DM_component_list):
        next_best_action = element_new_best_option["next_best_action"]
        action, intent = split_intent(next_best_action)

        if intent != "out_of_domain":
                if action == "confirmation":
                    if PRINT_DEBUG:
                        print(f"\n{intent} requested. Fetching...")

                    info = corresponding_actions.get(intent)(element_new_best_option[f"args({intent})"])

                    if info:
                        if PRINT_DEBUG:
                            print("Info extracted for intent ", intent, ": ", info)

                        if intent in info_intents and intent != "artist_info":
                            info = {k.replace("artists", "artist_name"): v for k, v in info.items()}
                    
                        if intent != "user_top_tracks" and intent != "user_top_artists":
                            list_GK[intent] = str(info)
                        else:
                            list_GK[intent] = [str(entity) for entity in info]              # entity may be either an artist or a track
                    else:
                        if PRINT_DEBUG:
                            print("\nFailed to fetch info or no data returned.")
                elif action == "request_info":
                    if intent in info_intents:

                        info = corresponding_actions.get(intent)(element_new_best_option[f"args({intent})"])
                        
                        if info:
                            if PRINT_DEBUG:
                                print("Info extracted for intent ", intent, ": ", info)
                            list_GK[intent] = info                
                else:
                    if PRINT_DEBUG:
                        print(f"\nUnsupported action: {action}.")
    
    state_manager.update_section("GK", list_GK)
    return state_manager.state_dict

def process_NLU_intent_and_slots(user_input):
    """
    Extracts intents and slots from user input using the NLU model.

    - Queries the model to identify intents.
    - Builds slot extraction input based on detected intents.
    - Iteratively extracts and validates slot values.
    - Updates the state dictionary with extracted intents and slots.

    Returns:
        tuple: Updated state dictionary and extracted intents.
    """
    
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
    
    while not check_slots(state_manager.state_dict["NLU"], slots):      
    
        slots = {}
        
        # extracting slots...
        out_NLU_slots = model_query.query_model(system_prompt=PROMPT_NLU_SLOTS, input_file=slots_input)
        
        if PRINT_DEBUG:
            print("Checking outpus slots: ", out_NLU_slots)
            print("Intents extracted: ", intents_extracted)

        for intent in intents_extracted:
            pattern = rf'(?:- )?(?:"{intent}"|{intent}).*?(\{{.*?\}})'

            match = re.search(pattern, out_NLU_slots, re.DOTALL)

            if match:                
                slots_content = match.group(1)
                if PRINT_DEBUG:
                    print("\nExtracted Slots Content: ", slots_content, " for intent ", intent)                
                try:
                    slots = fix_json_string(slots_content)
                except json.JSONDecodeError as e:
                    if PRINT_DEBUG:
                        print(f"Failed to parse slots for {intent}: {e}. Slots Content: {slots_content}")
                    slots = {}
            state_manager.update_section("NLU", {intent: slots})
    
    if PRINT_DEBUG:
        print("-"*95)
        print("llama3.2 output [SLOTS]:\n", out_NLU_slots)

    intents_extracted = final_check_NLU(state_manager.state_dict, intents_extracted)          # check intents extracted if they're valid aftre slot extraction
    
    return state_manager.state_dict, intents_extracted

def query_DM_model_with_validation(system_prompt, intents_extracted):
    """
    Queries the Dialogue Manager (DM) model while ensuring valid actions.

    - Determines expected action type (confirmation or request_info) based on slot values.
    - Queries the DM model for each intent and extracts a structured response.
    - Validates the extracted action against expected behavior.
    - Retries until a valid response is obtained.

    Returns:
        list: Validated next_best_action responses for each intent.
    """
    
    action_intents = {}
    
    # here we check which is the expected type of the next_best_action, we'll use it then to validate the output of the DM
    # the logic is simple, if some slots are null, the action will obbligatory be a request_info
    
    for intent in intents_extracted:
        if "details" in state_manager.state_dict["NLU"][intent]["slots"]:
            if PRINT_DEBUG:
                print("intent: ", intent, " - details: ", state_manager.state_dict["NLU"][intent]["slots"]["details"])
            check_type = "request_info" if "artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["details"] or state_manager.check_none_values() else "confirmation"
        else: 
            check_type = "request_info" if state_manager.check_none_values() else "confirmation"
        action_intents[intent] = check_type
    
    list_of_new_best_actions = []
        
    for intent in intents_extracted:
        
        input_file = {intent: state_manager.state_dict["NLU"][intent]}
        
        if PRINT_DEBUG:
            print(f"\n\n\nQuerying DM model with validation...(intent: {intent})\n")
        
        while True:
            out_DM = model_query.query_model(system_prompt=system_prompt, input_file=str(input_file))
            
            match = re.search(r'\{(?:[^{}]*|\{(?:[^{}]*|\{[^{}]*\})*\})*\}', out_DM, re.DOTALL)
            if match:
                new_out_DM = match.group()

            if new_out_DM:
                if PRINT_DEBUG:
                    print("\n\n\nExtracted DM output: \n\n", new_out_DM, "\n from virgin output. \n", out_DM, "\n")
            else:
                if PRINT_DEBUG:
                    print(f"Failed to extract JSON from DM output: {out_DM}")
                continue
            
            
            if validate_DM(new_out_DM, intent, action_intents[intent]):
                list_of_new_best_actions.append(new_out_DM)
                
                if PRINT_DEBUG:
                    print(f"Validated DM output...exiting...")
                break
            if PRINT_DEBUG:
                print(f"------------> Invalid next_best_action detected \n {new_out_DM} \n\n... retrying...")

    return list_of_new_best_actions

def process_DM(intents_extracted):
    """
    Run the Dialogue Manager (DM) component to determine the next best actions.

    - Queries the DM model with validated intents and slots.
    - Ensures the output is correctly formatted and parsed as JSON.
    - Updates the state dictionary with the extracted DM responses.

    Returns:
        dict: Updated state dictionary with DM results.
    """
    
    new_fixed_list = []    
    
    while new_fixed_list == []:
        
        out_DM_list = query_DM_model_with_validation(PROMPT_DM, intents_extracted)
        
        try:
            for elem in out_DM_list:
                new_fixed_list.append(fix_json_string(elem))
                
        except json.JSONDecodeError as e:
            if PRINT_DEBUG:
                print(f"Failed to parse DM output as JSON: {e}")
        
    state_manager.update_section("DM", new_fixed_list)
    return state_manager.state_dict

def process_NLG():
    """
    Generates a natural language response based on the current state dictionary.

    - Queries the NLG model using the processed state data.
    - Updates the state dictionary with the generated response.
    - Displays the updated state if debugging is enabled.

    Returns:
        str: The generated NLG response.
    """
    
    out_NLG = model_query.query_model(system_prompt=PROMPT_NLG, input_file=str(state_manager.state_dict))    
        
    state_manager.update_section("NLG", out_NLG)
    
    if PRINT_DEBUG:
        print("State Dictionary after NLG component processing:\n")
        state_manager.display()   
         
    return out_NLG

def process_COT_and_USD(slot_to_update, user_input, intents_extracted):
    """
    Handles Context Tracking (COT) and User Slot Detection (USD) to ensure conversation continuity.

    - Uses previous entities and current input to detect topic changes.
    - If a change of topic is detected, resets relevant state sections.
    - Otherwise, updates missing slot values using the USD model.
    - Ensures extracted slot values are valid before updating the state dictionary.

    Returns:
        bool: False if a topic change is detected, otherwise True.
    """ 
    
    prev_entity = []    
    
    for intent in intents_extracted:
        if intent in info_intents:
            prev_entity.append(intent + " - ".join(
                state_manager.state_dict["NLU"][intent]["slots"][elem]
                for intent in intents_extracted
                for elem in info_entity[intent]
                if state_manager.state_dict["NLU"][intent]["slots"][elem] not in [None, "null"] 
            ) )
        else:
            prev_entity += intent

    COT_input = str(prev_entity) + " / " + user_input

    if PRINT_DEBUG:
        print("COT_input: ", COT_input)
        
    out_COT = model_query.query_model(system_prompt=PROMPT_COT_DETECTION, input_file=str(COT_input))
    
    if PRINT_DEBUG:
        print("\n\nAnalyzing user_input through COT component: ", COT_input)
        print("result COT --------> ", out_COT, "\n\n")
    
    if "change_of_query" in out_COT :     
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
            if "confirmation" in user_input:                    # if action is confirmation i want to update also the details list
                for intent in intents_extracted:                            
                    if intent in info_intents:
                        for detail in state_manager.state_dict["NLU"][intent]["slots"]["details"]:
                           if detail not in slot_to_update:            
                                slot_to_update.append(detail)

            out_USD = model_query.query_model(system_prompt=build_prompt_for_USD(state_manager.state_dict, slot_to_update), input_file=str(user_input))
            
            if validate_USD(state_manager.state_dict, out_USD, slot_to_update, intents_extracted, f"{get_current_action(state_manager.state_dict)}"):
                if PRINT_DEBUG:
                    print("\n\n----> request_info in NLU2 output detected... validated user_input...exiting...")
                break  # Exit the loop if the output is valid
            if PRINT_DEBUG:
                print(f"\n... retrying...")
        
        state_manager.state_dict = check_null_slots_and_update_state_dict(state_manager.state_dict, out_USD, intents_extracted, slot_to_update)
        state_manager.delete_section("DM")
        state_manager.delete_section("GK")
        state_manager.delete_section("NLG")
        return True
        
def run_pipeline(user_input):
    """
    Executes the full conversational pipeline, handling user input through all components.

    - Initializes state management and model querying.
    - Processes NLU for intent and slot extraction.
    - Iteratively processes DM, GK, and NLG components.
    - Handles user input updates via COT and USD, detecting topic changes.
    - Loops until a new intent is detected or the user exits.

    Args:
        user_input (str): The initial user input.
    """
    
    global state_manager, model_query
    
    exit = False
    new_intent = False
    
    while not exit:
        new_intent = False
        state_manager = StateDictManager()
        model_query = ModelQuery()

        if PRINT_DEBUG:
            print("-"*95)
        if state_manager.state_dict == {"NLU": {}, "DM": {}, "GK": {}}:     # initial_state        
            _, intents_extracted = process_NLU_intent_and_slots(user_input)

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

            slot_to_update = get_slot_to_update(state_manager.state_dict, intents_extracted)            
            
            print_system(out_NLG)
            user_input = input_user("You: ")
            
            string_actions = "( "
            for intent in intents_extracted:
                string_actions += f"{get_next_best_action(intent, state_manager.state_dict)}, "
            string_actions = string_actions[:-2] + " )" 
               
            result = process_COT_and_USD(slot_to_update, user_input + f" ({get_current_action(intent, state_manager.state_dict)})", intents_extracted)
                
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
                    print("\nState Dictionary after USD component processing:\n")
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
    
    run_pipeline(user_input)

    