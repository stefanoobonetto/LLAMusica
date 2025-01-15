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
PROMPT_NLU_intents = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_intents.txt")
PROMPT_NLU_slots = os.path.join(os.path.dirname(__file__), "prompts/prompt_NLU_slots.txt")
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
    
def ask_NLU(model_query, input_data):
    return model_query.query_model( system_prompt=PROMPT_NLU, input_file=input_data )

def ask_DM(model_query, input_data):
    if isinstance(input_data, dict):
        input_data_str = json.dumps(input_data, indent=2)  # Convert to JSON string for querying
    elif isinstance(input_data, str):
        input_data_str = input_data  # Already a string
    else:
        raise ValueError("input_data must be a dictionary or a string.")

    return model_query.query_model(system_prompt=PROMPT_DM, input_file=input_data_str)

def ask_NLG(model_query, input_data):
    if isinstance(input_data, dict):
        input_data_str = json.dumps(input_data, indent=2)  # Convert to JSON string for querying
    elif isinstance(input_data, str):
        input_data_str = input_data  # Already a string
    else:
        raise ValueError("input_data must be a dictionary or a string.")

    return model_query.query_model(system_prompt=PROMPT_NLG, input_file=input_data_str)