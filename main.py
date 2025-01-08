from spoti import *
from spotipy.oauth2 import SpotifyOAuth

from utils import *
from model_query import *
from dict_manager import *
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

        # Return both the string and dictionary versions of dict_status
        return dict_status.to_json(), dict_status.dict_status
    except Exception as e:
        print(f"Failed to process user input: \"{user_input}\".")
        return None, None


def DM_component_processing(response_NLU):
    try:
        # Retry NLU parsing with new ModelQuery instances
        response_DM = ask_DM(model_query, input_data=response_NLU)

        # print("DM RESPONSE: \n", response_DM)
        dict_status.validate_dict(response_DM)
        
        print("\n\nValidated DM Response:")
        print(dict_status.to_json())
        return dict_status.to_json(), dict_status.dict_status  # Returning validated JSON for further use if needed
    except Exception as e:
        print(f"Failed to process NLU output.")
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
    return args

def check_next_best_action_and_do(DM_component_part):
    # Check if the DM component has a "next_best_action" key
    if "next_best_action" in DM_component_part:
        next_best_action = DM_component_part["next_best_action"]
        print(f"\nNext best action: {next_best_action}")  # Next best action: confirmation(artist_info)
        
        action, intent = split_intent(next_best_action)
        print(f"\n- action: {action} \n- intent: {intent}")
        
        if action == "confirmation":
            if intent == "artist_info":
                print("\nArtist info requested. Fetching artist info.")
                args = get_args(DM_component_part)
                
                if args:
                    artist_info = get_artist_info(*args)
                    if artist_info:
                        print("\nArtist Info:")
                        print(artist_info)
                    else:
                        print("\nFailed to fetch artist info or no data returned.")
                else:
                    print("\nNo valid arguments provided for fetching artist info.")
                
                # Mark action as completed
                DM_component_part["next_best_action"] = None
        elif action == "request_info":
            response_NLG = ask_NLG(model_query, input_data=DM_component_part)
            print("\nNLG Response:")
            print(response_NLG)
            
            # Mark action as completed
            DM_component_part["next_best_action"] = None
    else:
        print("\nNo next best action found in DM response.")


def main():

    authenticate()

    with open(USER_INPUT, "r") as file:
        USER_INPUTS = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    print("\n\n\nWelcome to LLAMusica platform 🎧🎶!\n\n\n")

    # Process each user input
    for idx, user_input in enumerate(USER_INPUTS, 1):
        
        print("-"*95)
        print(f"\nProcessing Input {idx}/{len(USER_INPUTS)}: \"{user_input}\"")
        _, json_NLU = NLU_component_processing(user_input)
        while not json_NLU:
            # Retry processing the same input after a failed attempt
            print("\nRetrying the same input after a failed attempt.")
            _, json_NLU = NLU_component_processing(user_input)

        # pass it through DM component
        _, json_DM = DM_component_processing(json_NLU)
        while not json_DM:
            # Retry processing the same input after a failed attempt
            print("\nRetrying the same input after a failed attempt.")
            _, json_DM = DM_component_processing(json_NLU)
                
        DM_component_part = json_DM.get("DM", {})
                
        # print("\n JSON DM: ", DM_component_part)
        
        check_next_best_action_and_do(DM_component_part)
        
            
    print("\nAll inputs have been processed. Exiting.")


if __name__ == "__main__":
    main()
