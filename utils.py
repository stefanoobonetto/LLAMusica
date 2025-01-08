import re
import json
from model_query import *
from argparse import Namespace
from typing import Tuple

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BatchEncoding,
    PreTrainedTokenizer,
    PreTrainedModel,
)

MODELS = {
    "llama2": "meta-llama/Llama-2-7b-chat-hf",
    "llama3": "meta-llama/Meta-Llama-3-8B-Instruct",
}

TEMPLATES = {
    "llama2": "<s>[INST] <<SYS>>\n{}\n<</SYS>>\n\n{} [/INST]",
    "llama3": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{}<|eot_id|><|start_header_id|>assistant<|end_header_id|>",
}

PROMPT_NLU = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU.txt")
PROMPT_DM = os.path.join(os.path.dirname(__file__), "prompts/prompt_DM.txt")
PROMPT_NLG = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLG.txt")

# print("----> ", PROMPT_NLU)

def load_model(args: Namespace) -> Tuple[PreTrainedModel, PreTrainedTokenizer]:
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        device_map="auto" if args.parallel else args.device, 
        torch_dtype=torch.float32 if args.dtype == "f32" else torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    return model, tokenizer  # type: ignore


def generate(
    model: PreTrainedModel,
    inputs: BatchEncoding,
    tokenizer: PreTrainedTokenizer,
    args: Namespace,
) -> str:
    output = model.generate(
        inputs.input_ids,
        attention_mask=inputs.attention_mask,
        max_new_tokens=args.max_new_tokens,
        pad_token_id=tokenizer.eos_token_id
    )
    return tokenizer.decode(
        output[0][len(inputs.input_ids[0]) :], skip_special_tokens=True
    )
    
def ask_NLU(model_query, user_input):
    return model_query.query_model( system_prompt=PROMPT_NLU, input_file=user_input )

def ask_DM(model_query, dict_status):
    # Serialize the dictionary into a JSON string
    if isinstance(dict_status, dict):
        dict_status_str = json.dumps(dict_status, indent=2)  # Convert to JSON string for querying
    elif isinstance(dict_status, str):
        dict_status_str = dict_status  # Already a string
    else:
        raise ValueError("dict_status must be a dictionary or a string.")

    # Pass the serialized string to `query_model`
    return model_query.query_model(system_prompt=PROMPT_DM, input_file=dict_status_str)

def ask_NLG(model_query, dict_status):
    # Serialize the dictionary into a JSON string
    if isinstance(dict_status, dict):
        dict_status_str = json.dumps(dict_status, indent=2)  # Convert to JSON string for querying
    elif isinstance(dict_status, str):
        dict_status_str = dict_status  # Already a string
    else:
        raise ValueError("dict_status must be a dictionary or a string.")

    # Pass the serialized string to `query_model`
    return model_query.query_model(system_prompt=PROMPT_NLG, input_file=dict_status_str)