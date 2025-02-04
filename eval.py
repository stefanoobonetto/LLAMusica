import csv
import pandas as pd
from collections import Counter
from difflib import SequenceMatcher

from utils import *
from model_query import ModelQuery
from statedictmanager import StateDictManager


def normalize_intents(intent_str):
    """
    Normalizes intent strings by sorting and removing extra whitespace.

    - Splits intent strings by newline.
    - Removes extra spaces and empty lines.
    - Sorts the extracted intents.

    Args:
        intent_str (str): A string containing multiple intents separated by newlines.

    Returns:
        list: A sorted list of cleaned intent names.
    """
    if not isinstance(intent_str, str):
        return []
    return sorted([intent.strip() for intent in intent_str.split('\n') if intent.strip()])

def evaluate_predictions(df, type):
    """
    Evaluates model predictions against expected outputs.

    - Compares expected and predicted intents or slots.
    - Counts correct predictions and calculates accuracy.

    Args:
        df (pandas.DataFrame): The dataframe containing expected and predicted values.
        type (str): Type of evaluation ("intents" or "slots").

    Returns:
        tuple: (correct predictions, total cases, accuracy percentage).
    """
    correct = 0
    total = len(df)

    for _, row in df.iterrows():
        if type == "intents":
            expected_intents = normalize_intents(row['expected_output'])
            output_intents = normalize_intents(row['output'])
        else:
            expected_intents = normalize_intents(row['expected_slots'])
            output_intents = normalize_intents(row['output_slots'])
            
        if Counter(expected_intents) == Counter(output_intents):
            correct += 1
        else:
            if PRINT_DEBUG:        
                print("\n\n\n[WRONG]: ", row)

    accuracy = correct / total if total > 0 else 0
    return correct, total, accuracy

def eval_NLU_intents():
    """
    Evaluates the intent extraction performance of the NLU component.

    - Reads a test dataset of user inputs and expected intents.
    - Queries the NLU model to extract intents.
    - Compares the model's output with expected intents.
    - Saves results to a CSV file and prints accuracy.

    Returns:
        None
    """

    PATH_TESTSET = os.path.join(os.path.dirname(__file__), "evaluation/intent_test_input.csv")
    df = pd.read_csv(PATH_TESTSET, quoting=3)  # quoting=3 means QUOTE_NONE
    df.columns = df.columns.str.replace('"', '').str.strip()

    outputs = []

    for index, row in df.iterrows():

        state_manager = StateDictManager()
        model_query = ModelQuery()


        user_input = row['user_input']

        # extracting intents...
        out_NLU_intents = model_query.query_model(system_prompt=PROMPT_NLU_INTENTS, input_file=user_input)

        state_manager.state_dict = {"NLU": {}}

        _, intents_extracted, _ = extract_intents_build_slots_input(user_input, state_manager.state_dict, out_NLU_intents)

        out_intent = "\n".join([f"- Intent{i+1}: {intent}" for i, intent in enumerate(intents_extracted)])

        outputs.append(out_intent)

    df['output'] = outputs  

    output_file = os.path.join(os.path.dirname(__file__), "evaluation/intent_test_output.csv")

    df.to_csv(output_file, index=False, quoting=csv.QUOTE_ALL, escapechar="\\")

    print(f"Updated file saved: {output_file}\n\n")

    correct, total, accuracy = evaluate_predictions(df, "intents")

    print(f"[INTENTS] Correct Predictions: {correct}/{total}")
    print(f"[INTENTS] Accuracy: {accuracy * 100:.2f}%")

def similar(a, b):
    """
    Calculates similarity ratio between two strings using SequenceMatcher.

    Args:
        a (str): First string.
        b (str): Second string.

    Returns:
        float: Similarity ratio between 0 and 1.
    """
    
    return SequenceMatcher(None, a, b).ratio()

def eval_NLU_slots():
    """
    Evaluates the slot extraction performance of the NLU component.

    - Reads a test dataset of user inputs and expected slots.
    - Queries the NLU model to extract slots.
    - Compares the model's output with expected slots.
    - Saves results to a CSV file and calculates similarity accuracy.

    Returns:
        None
    """

    PATH_TESTSET = os.path.join(os.path.dirname(__file__), "evaluation/slots_test_input.csv")
    df = pd.read_csv(PATH_TESTSET, quoting=3)  # quoting=3 means QUOTE_NONE
    df.columns = df.columns.str.replace('"', '').str.strip()

    outputs = []
    
    for index, row in df.iterrows():

        state_manager = StateDictManager()
        model_query = ModelQuery()

        user_input = row["user_input"]
        out_NLU_intents = row['expected_intent']

        state_manager.state_dict = {"NLU": {}}

        slots_input, intents_extracted, state_manager.state_dict = extract_intents_build_slots_input(user_input, state_manager.state_dict, out_NLU_intents)

        slots = {}

        while not check_slots(state_manager.state_dict["NLU"], slots):      
            
            slots = {}
            
            # extracting slots...
            out_NLU_slots = model_query.query_model(system_prompt=PROMPT_NLU_SLOTS, input_file=slots_input)

            for intent in intents_extracted:
                pattern = rf'(?:- )?(?:"{intent}"|{intent}).*?(\{{.*?\}})'

                match = re.search(pattern, out_NLU_slots, re.DOTALL)

                if match:
                    slots_content = match.group(1)
                    try:
                        slots = fix_json_string(slots_content)
                    except json.JSONDecodeError as e:
                        if PRINT_DEBUG:
                            print(f"Failed to parse slots for {intent}: {e}. Slots Content: {slots_content}")
                        slots = {}
                state_manager.update_section("NLU", {intent: slots})
            
        outputs.append(out_NLU_slots.replace(",", ";"))

    df['output_slots'] = outputs  

    output_file = os.path.join(os.path.dirname(__file__), "evaluation/slots_test_output.csv")

    df.to_csv(output_file, index=False, quoting=csv.QUOTE_ALL, escapechar="\\")

    print(f"Updated file saved: {output_file}\n\n")

    similarity_threshold = 0.8              # similarity threshold to consider a response as correct
    correct_count = 0

    for index, row in df.iterrows():
        expected = str(row["expected_slots"]).strip()
        output = str(row["output_slots"]).strip()

        if similar(expected, output) >= similarity_threshold:           # if the similarity is above the threshold, we consider it correct
            correct_count += 1

    total_cases = len(df)

    correct_count, total_cases, correct_count / total_cases

def check_none_values(input_string):
    """
    Checks if a given entry of the dict contains 'None' or 'null' values.

    Args:
        input_string (str): The string to check.

    Returns:
        bool: True if the string contains 'None' or 'null', otherwise False.
    """
    
    if "None" in str(input_string) or "null" in str(input_string):
        return True
    else:
        return False
        
def validate_DM_eval(response, intent, action):
    """
    Validates the output of the Dialogue Manager (DM) component.

    - Parses the response as JSON.
    - Ensures the response contains the correct action and required arguments.
    - Checks for the presence of required details in the output.

    Args:
        response (str): The raw response from the DM model.
        intent (str): The intent being processed.
        action (str): The expected action type.

    Returns:
        bool: True if the response is valid, otherwise False.
    """

    try:
        parsed_response = fix_json_string(response)  
        if not parsed_response:
            if PRINT_DEBUG:
                print("Failed to parse JSON response.")
            return False
    except json.JSONDecodffeError:
        if PRINT_DEBUG:
            print("Failed to parse JSON response.")
        return False
    
    if "next_best_action" not in parsed_response:
        return False
    
    args_key = f"args({intent})"  
    
    if not parsed_response[args_key].get("details") and intent not in ["user_top_tracks", "user_top_artists", "get_recommendations", "out_of_domain"]:
            return False
    
    return action in response and check_args(parsed_response, intent, action)

def extract_intent(input):
    """
    Extracts the intent name from a JSON-like input string.

    - Uses regex to find the first dictionary key in the input.

    Args:
        input (str): JSON-like string containing intent information.

    Returns:
        str: Extracted intent name.
    """
        
    pattern = r'"(\w+)": \{'

    match = re.search(pattern, input)

    if match:
        extracted_key = match.group(1)
        
    return extracted_key


def query_DM_model_with_validation(system_prompt, intent_and_slots):
    """
    Queries the Dialogue Manager (DM) model while ensuring valid output.

    - Extracts the intent from the input.
    - Determines expected action type (confirmation or request_info).
    - Queries the DM model for a response.
    - Validates the extracted response against expected values.
    - Retries the query if validation fails.

    Args:
        system_prompt (str): The system prompt for the DM model.
        intent_and_slots (str): JSON string containing intent and slot data.

    Returns:
        str: Validated DM model response in JSON format.
    """
    
    model_query = ModelQuery()
    
    intent = extract_intent(intent_and_slots)
    
    intent_and_slots = fix_json_string(intent_and_slots)
    
    # here we check which is the expected type of the next_best_action, we'll use it then to validate the output of the DM
    if "details" in intent_and_slots[intent]["slots"]:
        check_type = "request_info" if "artist_name" in intent_and_slots[intent]["slots"]["details"] or check_none_values(intent_and_slots) else "confirmation"
    else: 
        check_type = "request_info" if check_none_values(intent_and_slots) else "confirmation"
    
    input_file = intent_and_slots
        
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
        
        
        if validate_DM_eval(new_out_DM, intent, check_type):
            if PRINT_DEBUG:
                print(f"Validated DM output...exiting...")
            break
        if PRINT_DEBUG:
            print(f"------------> Invalid next_best_action detected \n {new_out_DM} \n\n... retrying...")

    return new_out_DM

def eval_DM():
    """
    Evaluates the performance of the Dialogue Manager (DM) component.

    - Reads a test dataset of user inputs and expected DM outputs.
    - Queries the DM model for each test case.
    - Validates and saves the output.
    - Writes results to a CSV file.

    Returns:
        None
    """

    PATH_TESTSET = os.path.join(os.path.dirname(__file__), "evaluation/DM_input.csv")
    OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "evaluation/DM_output.csv")

    df = pd.read_csv(PATH_TESTSET, quoting=3)  
    df.columns = df.columns.str.replace('"', '').str.strip()

    if os.path.exists(OUTPUT_FILE) and os.stat(OUTPUT_FILE).st_size > 0:
        df_output = pd.read_csv(OUTPUT_FILE, quoting=3)
        df_output.columns = df_output.columns.str.replace('"', '').str.strip()
        
        if "user_input" in df_output.columns:
            processed_inputs = set(df_output["user_input"].astype(str))
        else:
            processed_inputs = set()
    else:
        df_output = pd.DataFrame(columns=["user_input", "expected_slots", "DM_output"])
        processed_inputs = set()

    with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL, escapechar="\\")

        if os.stat(OUTPUT_FILE).st_size == 0:
            writer.writerow(["user_input", "expected_slots", "DM_output"])

        for index, row in df.iterrows():
            user_input = str(row["user_input"]).strip()  

            if user_input in processed_inputs:
                print(f"Skipping already processed input: {user_input}")
                continue

            if row["expected_slots"].replace(";", ",")[1] == "[":  # Multi-intent case
                out_DM_list = []

                for elem in json.loads(row["expected_slots"].replace(";", ",")):
                    out_DM = query_DM_model_with_validation(PROMPT_DM, elem)
                    out_DM_list.append(out_DM)

                str_out_DM = "[" + ", ".join(out_DM_list) + "]"
            else:
                str_out_DM = query_DM_model_with_validation(PROMPT_DM, row["expected_slots"].replace(";", ","))

            writer.writerow([user_input, row["expected_slots"], str_out_DM])

    print(f"Updated file saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    """
    Runs the evaluation pipeline for NLU intents, NLU slots, and DM components.
    """
    
    eval_NLU_intents()

    eval_NLU_slots()
    
    eval_DM()