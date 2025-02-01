import re
import json

from spoti import *
from utils import *
from model_query import *
from statedictmanager import *

USER_INPUT = "user_input.txt"
intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]

def build_GK():
    DM_component_list = json.dumps(state_manager.state_dict.get("DM", {}))
    
    # this substitution step is crucial since the spotify API requires the key "artists" instead of "artist_name"    
    DM_component_list = DM_component_list.replace("artist_name", "artists") 
    
    list_GK = {}
    
    
    
    for element_new_best_option in json.loads(DM_component_list):
        # element_new_best_option = fix_json_string(element_new_best_option)
        # element_new_best_option = json.loads(element_new_best_option)
        next_best_action = element_new_best_option["next_best_action"]
        # if PRINT_DEBUG:
        #       print(f"\nNext best action: {next_best_action}")  

        action, intent = split_intent(next_best_action)
        # if PRINT_DEBUG:
        #       print(f"\n- action: {action} \n- intent: {intent}")

        if action == "confirmation":
            if PRINT_DEBUG:
                print(f"\n{intent} requested. Fetching...")

            info = corresponding_actions.get(intent)(element_new_best_option[f"args({intent})"])

            if info:
                # print(f"\Info fetched for {intent}:")
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
                if PRINT_DEBUG:
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

    intents_extracted = final_check_NLU(state_manager.state_dict, intents_extracted)          # check intents extracted if they're valid 
    
    return state_manager.state_dict, intents_extracted

# def extract_DM_output(text):
#     """Extracts and fixes JSON content from a string, keeping it simple."""
#     try:
#         # Extract anything that looks like a JSON list
#         json_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
#         if json_match:
#             json_text = json_match.group(0).strip()  # Extract the JSON-like content
            
#             # Convert Python-style booleans and None to JSON format
#             json_text = json_text.replace("None", "null").replace("True", "true").replace("False", "false")

#             # Load as JSON
#             return json.loads(json_text)
#         else:
#             print("No valid JSON found.")
#             return None
#     except json.JSONDecodeError as e:
#         print(f"JSON decoding failed: {e}")
#         return None

def query_DM_model_with_validation(system_prompt, intents_extracted):

    action_intents = {}
    
    # here we check which is the expected type of the next_best_action, we'll use it then to validate the output of the DM
    for intent in intents_extracted:
        if "details" in state_manager.state_dict["NLU"][intent]["slots"]:
            check_type = "request_info" if any("artist_name" in state_manager.state_dict["NLU"][intent]["slots"]["details"] for intent in intents_extracted) or state_manager.check_none_values() else "confirmation"
        else: 
            check_type = "request_info" if state_manager.check_none_values() else "confirmation"
        action_intents[intent] = check_type
    
    list_of_new_best_actions = []
    
    if PRINT_DEBUG:
        print("\n\n\n--------> Intents extracted: ", intents_extracted, "\n\n\n")
    
    for intent in intents_extracted:
        
        input_file = {intent: state_manager.state_dict["NLU"][intent]}
        # if PRINT_DEBUG:
            # print("\n\n\nGiving as input to DM (intent: ", intent, "): ", input_file)
        
        if PRINT_DEBUG:
            print(f"\n\n\nQuerying DM model with validation...(intent: {intent})\n")
        
        while True:
            out_DM = model_query.query_model(system_prompt=system_prompt, input_file=str(input_file))
            
            match = re.search(r'\{(?:[^{}]*|\{(?:[^{}]*|\{[^{}]*\})*\})*\}', out_DM, re.DOTALL)
            if match:
                new_out_DM = match.group()
            # if "next_best_action" not in list_out_DM:
            #     list_out_DM = re.findall(r'\[[^\[\]]*\]', out_DM)
            #     print("-"*95)
            #     print("----------> Ora estratto contenuto tra \{\}:\n\n", list_out_DM)                
            
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
    out_NLG = model_query.query_model(system_prompt=PROMPT_NLG, input_file=str(state_manager.state_dict))    
        
    state_manager.update_section("NLG", out_NLG)
    
    if PRINT_DEBUG:
        print("State Dictionary after NLG component processing:\n")
        state_manager.display()   
         
    return out_NLG

def process_COT_and_USD(slot_to_update, user_input, intents_extracted):
        
    # COT component will use the previous entity extracted from the NLU component and the current user input to compute the alignement
    # between the two and determine if there's a change of topic
    
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
            if "confirmation" in user_input:                    # nel caso di confirmation voglio aggiornare anche i details
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
                print(f"Invalid USD output detected \n{out_USD}\n... retrying...")
        
        state_manager.state_dict = check_null_slots_and_update_state_dict(state_manager.state_dict, out_USD, intents_extracted, slot_to_update)
        state_manager.delete_section("DM")
        state_manager.delete_section("GK")
        state_manager.delete_section("NLG")
        return True
        
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
            
            slot_to_update = get_slot_to_update(state_manager.state_dict, intents_extracted)            # dict {intent1: [slot1, slot2, ...], intent2: [slot1, slot2, ...]}
            
            if PRINT_DEBUG:
                print("\n\n\n----> SLOTS to UPDATE: ", slot_to_update)
            
            print_system(out_NLG)
            user_input = input_user("You: ")
            # these slots to update are extracted from the state_dict only if the next_best_action is "request_info"     
            
            string_actions = "( "
            for intent in intents_extracted:
                string_actions += f"{get_next_best_action(intent, state_manager.state_dict)}, "
            string_actions = string_actions[:-2] + " )" 
            
            if PRINT_DEBUG:
                print("\n\n\n----> Current actions: ", string_actions, "\n\n")
               
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
                    print("\nState Dictionary after NLU2 component processing:\n")
                state_manager.display()
            
            if user_input == "exit":
                # the main idea is to add an intent "end_conversation" that determine when a user wants to quit his experience with llama platform
                # till now, the conversation will be stuck in this main loop. 
                exit = True

if __name__ == "__main__":

    pretty_print()
    
    authenticate(force_auth=True)
    
    print_system(f"Hi {get_username()}, how can I help you?", auth=True)
    user_input = input_user("You: ")
    # user_input = "When has been released Imagine by John Lennon?"
    # user_input = "When has been released the song Blinding Lights by The Weeknd? How many followers does Ed Sheeran have?"
    # "Show me my top artists of the last month."      # by The Weeknd 
    run_pipeline(user_input)
    
    # with open(USER_INPUT, "r") as file:
    #     USER_INPUTS = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    # for user_input in USER_INPUTS:
        
    #     run_pipeline(user_input)