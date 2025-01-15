from spoti import *
from spotipy.oauth2 import SpotifyOAuth

import re
from utils import *
from model_query import *
from bin.dict_manager import *
from spoti import *

USER_INPUT = "user_input.txt"

model_query = ModelQuery()

def NLU_component_processing(user_input):
    try:

        response_NLU = ask_NLU(model_query, input_data=user_input)
        
        global dict_status 
        dict_status = DictManager()

        # print("NLU_RESPONSE: \n", response_NLU)
        dict_status.validate_dict(response_NLU)
        
        print("\nValidated NLU Response:")
        print(dict_status.to_json())

        return dict_status.dict_status
    except Exception as e:
        print(f"Failed to process user input: \"{user_input}\".")
        return None


def DM_component_processing(response_NLU):
    try:

        response_DM = ask_DM(model_query, input_data=response_NLU)

        # print("DM RESPONSE: \n", response_DM)
        dict_status.validate_dict(response_DM)
        
        print("\n\nValidated DM Response:")
        print(dict_status.to_json())
        return dict_status.dict_status  # Returning validated JSON for further use if needed
    except Exception as e:
        print(f"Failed to process NLU output: ", e)
        return None

def NLG_component_processing_with_dict(response_DM):
    try:
        # Retry NLU parsing with new ModelQuery instances
        response_NLG = ask_NLG(model_query, input_data=response_DM)
        
        # print("NLG RESPONSE: \n", response_NLG)
        dict_status.validate_dict(response_NLG)
        
        print("\n\nValidated NLG Response:")
        print(dict_status.to_json())
        return dict_status.dict_status  # Returning validated JSON for further use if needed
    except Exception as e:
        print(f"Failed to process NLG output: ", e)
        return None
    
def NLG_component_processing(response_DM):
    try:
        # Retry NLU parsing with new ModelQuery instances
        response_NLG = ask_NLG(model_query, input_data=response_DM)
        
        # print("NLG RESPONSE: \n", response_NLG)
        # dict_status.validate_dict(response_NLG)
        
        print("\n\nValidated NLG Response:")
        return response_NLG  # Returning validated JSON for further use if needed
    except Exception as e:
        print(f"Failed to process NLG output: ", e)
        return None
    
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

def check_next_best_action_and_add_GK(state_dict):
    
    DM_component_part = state_dict.get("DM", {})
    
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

                if intent != "user_top_tracks" and intent != "user_top_artists":
                    state_dict["GK"] = info
                else:
                    state_dict["GK"] = [str(entity) for entity in info] # entity may be either an artist or a track
                return state_dict
            else:
                print("\nFailed to fetch artist info or no data returned.")
    elif action == "request_info":
        # if action == "request_info" the request should be for the artist name of the song or the album
        # for this reason, I try to get the artist name of the song or the album using spotify and then we ask if it's the correct one to the user
        
        if intent == "song_info" or intent == "album_info" or intent == "comparison":

            info = corresponding_actions.get(intent)(*get_args(DM_component_part))
            
            if info:
                print(f"\nInfo fetched for {intent}:")
                print(info)

                state_dict["GK"] = info
                return state_dict                    
                
        else:
            return state_dict
    else:
        print(f"\nUnsupported action: {action}.")
        return state_dict

def main(user_input):

    authenticate()

    with open(USER_INPUT, "r") as file:
        USER_INPUTS = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    print("\n\n\nWelcome to LLAMusica platform 🎧🎶!\n\n\n")

    # Process each user input
    # for idx, user_input in enumerate(USER_INPUTS, 1):
        
    #     print("-"*95)
    #     print(f"\nProcessing Input {idx}/{len(USER_INPUTS)}: \"{user_input}\"")
    #     json_NLU = NLU_component_processing(user_input)
    #     while not json_NLU:
    #         # Retry processing the same input after a failed attempt
    #         print("\nRetrying the same input after a failed attempt.")
    #         json_NLU = NLU_component_processing(user_input)

    #     # pass it through DM component
    #     json_DM = DM_component_processing(json_NLU)
    #     while not json_DM:
    #         # Retry processing the same input after a failed attempt
    #         print("\nRetrying the same input after a failed attempt.")
    #         json_DM = DM_component_processing(json_NLU)
                                
    #     # print("\n JSON DM: ", DM_component_part)
        
    #     json_DM = check_next_best_action_and_do(json_DM)
    
    
    print("-"*95)
    print(f"\nProcessing Input: \"{user_input}\"")
    json_NLU = NLU_component_processing(user_input)
    while not json_NLU:
        # Retry processing the same input after a failed attempt
        print("\nRetrying the same input after a failed attempt.")
        json_NLU = NLU_component_processing(user_input)

    # pass it through DM component
    json_DM = DM_component_processing(json_NLU)
    while not json_DM:
        # Retry processing the same input after a failed attempt
        print("\nRetrying the same input after a failed attempt.")
        json_DM = DM_component_processing(json_NLU)
                                
        # print("\n JSON DM: ", DM_component_part)
        
    json_DM = check_next_best_action_and_add_GK(json_DM)
    
    print("\n\n\nAdded GK to JSON:\n", json_DM)
    
    NLG_out = NLG_component_processing(json_DM)
    while not NLG_out:
        print("\nRetrying the same input after a failed attempt.")
        NLG_out = NLG_component_processing(json_DM)
    print("\nNLG Response:")
    print(NLG_out)
    json_DM["NLG"] = NLG_out
    
    print("\n\n\nThank you for using LLAMusica platform 🎧🎶!\n\n\n")

import re

def process_NLU_intent_and_slots(user_input):
    print("Processing Input: ", user_input)
    
    intents = ["artist_info", "song_info", "album_info", "user_top_tracks", "user_top_artists", "comparison", "out_of_domain"]
    
    out_NLU_intents = model_query.query_model(system_prompt=PROMPT_NLU_intents, input_file=user_input)
    print(out_NLU_intents)
    print("\nllama3.2 output [INTENTS]:\n", out_NLU_intents)

    state_dict = {"NLU": {}}
    intents_extracted = []
    intent_count = {}

    for intent in intents:
        count = out_NLU_intents.count(intent)  # Count occurrences of each intent in the output
        for i in range(count):
            intent_key = f"{intent}{i + 1}" if count > 1 else intent  # Number intents if multiple instances
            intents_extracted.append(intent_key)
            state_dict["NLU"][intent_key] = {}
            intent_count[intent] = intent_count.get(intent, 0) + 1  # Update count for numbering

    print("Extracted Intents:", intents_extracted)
    print("State Dictionary:", state_dict)

    str_intents = ""
    for i, intent in enumerate(intents_extracted):
        str_intents += f"- Intent{i+1}: {intent}\n"

    slots_input = user_input + "\n" + str_intents
    
    out_NLU_slots = model_query.query_model(system_prompt=PROMPT_NLU_slots, input_file=slots_input)
    print("\nllama3.2 output [SLOTS]:\n", out_NLU_slots)
    
    for intent in intents_extracted:
        pattern = rf'(["\']?{intent}["\']?)\s*:\s*\{{(.*?)\}}'
        match = re.search(pattern, out_NLU_slots, re.DOTALL)
        if match:
            slots_content = match.group(2)
            slots = {}
            key_value_pattern = r'"(\w+)":\s*(.*?)(?:,|$)'
            for kv_match in re.finditer(key_value_pattern, slots_content):
                key = kv_match.group(1)
                value = kv_match.group(2).strip()

                # Handle "null" and lists
                if value == "null":
                    value = None
                elif value.startswith("[") and value.endswith("]"):
                    value = eval(value)  # Convert list string to Python list
                elif value.startswith('"') and value.endswith('"'):
                    value = value.strip('"')  # Remove surrounding quotes from strings
                slots[key] = value
            
            # Update state_dict with the entire slots dictionary
            # print("\nSlots for", intent, ":", slots)
            state_dict["NLU"][intent] = slots  # Copy the entire slots dictionary
        else:
            print(f"No slots found for {intent} in llama3.2 output.")

    print("\nState Dictionary:\n", state_dict)
    return state_dict, intents_extracted

import json
import re

def process_DM(state_dict):
    # Get DM output from llama3.2
    out_DM = model_query.query_model(system_prompt=PROMPT_DM, input_file=str(state_dict))
    print("\n\n\nllama3.2 output [DM]:\n", out_DM)

    try:
        # Extract JSON content using regex
        json_pattern = r'\{.*\}'  # Match anything that starts and ends with braces
        json_match = re.search(json_pattern, out_DM, re.DOTALL)

        if json_match:
            json_content = json_match.group()
            # Parse the extracted JSON
            dm_data = json.loads(json_content)
            if isinstance(dm_data, dict):
                # Update state_dict["DM"] with the extracted DM data
                state_dict["DM"] = dm_data
                print("\nUpdated State Dictionary with DM:\n", state_dict)
            else:
                print("Extracted content is not a valid JSON object.")
        else:
            print("No valid JSON content found in DM output.")

        return state_dict
    except json.JSONDecodeError as e:
        print(f"Failed to parse DM output as JSON: {e}")
    
    return state_dict

if __name__ == "__main__":
    
    authenticate()
    
    user_input = "What is the duration of DIRTY NO by Lil Busso?" 
    state_dict, intents_extracted = process_NLU_intent_and_slots(user_input)
    
    state_dict = process_DM(state_dict)
    
    print("\n\n\nFINAL STATE DICT:\n\n", state_dict)
    
    state_dict = check_next_best_action_and_add_GK(state_dict)
    
    
    
    # main()