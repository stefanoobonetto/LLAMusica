import os
import ollama
# import logging

# Configure logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

class ModelQuery:
    def __init__(self):
        self.history = []

    def add_to_history(self, message):
        """Add a message to the history."""
        self.history.append(message)

    def action_history_str(self):
        """Return the history as a string."""
        return "\n".join(self.history)

    @staticmethod
    def load_content(content):
        """Load content from a file or return the string itself."""
        if os.path.isfile(content):  
            with open(content, 'r') as f:
                return f.read()
        return content  

    def query_model(self, system_prompt, input_file, model_name="llama3.2"):

        system_prompt = self.load_content(system_prompt)
        
        user_input = self.load_content(input_file)

        self.add_to_history(user_input)
            
        messages = [
            {'role': 'system', 'content': self.action_history_str()},
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_input}
        ]
        
        # logger.debug(f"Messages to model: {messages}")
        
        response = ollama.chat(
            model=model_name,
            messages=messages
        )
        return response['message']['content']