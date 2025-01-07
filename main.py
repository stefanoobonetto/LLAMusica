from spoti import *
from spotipy.oauth2 import SpotifyOAuth

from utils import *
from model_query import *
from dict_manager import *

USER_INPUT = "user_input.txt"

def retry_with_new_instance(func, input_data, instance_generator, max_attempts=2, **kwargs):
    for attempt in range(max_attempts):
        try:
            instance = instance_generator()  # Generate a fresh instance for each attempt
            return func(instance, input_data, **kwargs)
        except Exception as e:
            print(f"Error during attempt {attempt + 1}/{max_attempts}: {e}")
            if attempt + 1 == max_attempts:
                raise  # Re-raise the last exception if all attempts fail


def process_user_input(user_input):
    try:
        # Retry NLU parsing with new ModelQuery instances
        response_NLU = retry_with_new_instance(
            func=ask_NLU,
            input_data=user_input,
            instance_generator=ModelQuery,
            max_attempts=3
        )

        # Validate the NLU response
        dict_status = DictManager()
        # print("NLU_RESPONSE: \n", response_NLU)
        dict_status.validate_dict(response_NLU)
        
        print("\nValidated NLU Response:")
        print(dict_status.to_json())

        return dict_status.to_json()  # Returning validated JSON for further use if needed
    except Exception as e:
        print(f"Failed to process user input: \"{user_input}\".")
        return None


def main():
    # Authenticate Spotify (assuming `authenticate` function handles this)
    authenticate()

    # Read and parse user inputs from the file
    with open(USER_INPUT, "r") as file:
        USER_INPUTS = [line.strip() for line in file.read().split("\n\n") if line.strip()]

    print("\n\n\nWelcome to LLAMusica platform 🎧🎶!\n\n\n")

    # Process each user input
    for idx, user_input in enumerate(USER_INPUTS, 1):
        
        print("-"*95)
        print(f"\nProcessing Input {idx}/{len(USER_INPUTS)}: \"{user_input}\"")
        response = process_user_input(user_input)
        while not response:
            # Retry processing the same input after a failed attempt
            print("\nRetrying the same input after a failed attempt.")
            response = process_user_input(user_input)
            
    print("\nAll inputs have been processed. Exiting.")


if __name__ == "__main__":
    main()
