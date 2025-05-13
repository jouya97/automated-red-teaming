from together import Together
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, TypedDict
import fire
import prompt


class MessageDict(TypedDict):
    """Type for a message in the conversation history."""
    
    role: str
    content: str


class ResponseDict(TypedDict):
    """Type for storing model responses during generation."""
    
    type: str
    response: str


class ConversationGenerator:
    """
    Generate red-teaming conversations between LLMs hosted on Together
    
    This class implements a multi-model approach to generate red-teaming conversations
    that test AI models for safety and policy compliance. It uses separate models for
    planning attacks, generating user messages, and simulating the target model.
    
    Attributes:
        topic (str): The sensitive topic to focus on in the conversation.
        history_path (str): Path to save/load the conversation history.
        max_user_turns (int): Maximum number of user turns in the conversation.
        output_directory (str): Directory to save the generated conversation.
        full_response_output_directory (str): Directory to save full model responses.
        planner_model (str): Model used for planning attack strategies.
        attacker_model (str): Model used for generating user messages.
        victim_model (str): Model being red-teamed/evaluated.
        client (Together): API client for making requests to the model provider.
        conversation_history (List[MessageDict]): List of message dictionaries in the conversation.
        model_responses (List[ResponseDict]): List of full model responses during generation.
    """

    def __init__(self, topic: str, history_path: str = "conversation_history.json",
                 max_user_turns: int = 10, 
                 output_directory: str = 'data/conversations',
                 full_response_output_directory: str = 'data/full_responses',
                 planner_model: str = "deepseek-ai/DeepSeek-V3",
                 attacker_model: str = "deepseek-ai/DeepSeek-V3",
                 victim_model: str = "deepseek-ai/DeepSeek-V3",
                 planner_prompt_version: str = "current",
                 attacker_prompt_version: str = "current") -> None:
        """Initialize the conversation generator.
        
        Args:
            topic (str): The sensitive topic to focus on in the conversation.
            history_path (str, optional): Path to save/load conversation history. Defaults to "conversation_history.json".
            max_user_turns (int, optional): Maximum number of user turns. Defaults to 10.
            output_directory (str, optional): Directory for output files. Defaults to 'data'.
            full_response_output_directory (str, optional): Directory for full model responses. Defaults to 'full_responses'.
            planner_model (str, optional): Model used for planning. Defaults to "deepseek-ai/DeepSeek-V3".
            attacker_model (str, optional): Model used for generating user messages. Defaults to "deepseek-ai/DeepSeek-V3".
            victim_model (str, optional): Model being tested. Defaults to "deepseek-ai/DeepSeek-V3".
            planner_prompt_version (str, optional): Version of planner prompt to use. Defaults to "current".
            attacker_prompt_version (str, optional): Version of attacker prompt to use. Defaults to "current".
        """
        self.topic = topic
        self.history_path = history_path
        self.max_user_turns = max_user_turns
        self.planner_model = planner_model
        self.attacker_model = attacker_model
        self.victim_model = victim_model
        self.output_directory = output_directory
        self.full_response_output_directory = full_response_output_directory
        self.planner_prompt_version = planner_prompt_version
        self.attacker_prompt_version = attacker_prompt_version
        
        os.makedirs(self.output_directory, exist_ok=True)
        os.makedirs(self.full_response_output_directory, exist_ok=True)
        timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path = os.path.join(self.output_directory, f"model_responses_{timestamp}.json")
        
        self.client = Together(api_key=os.environ.get("TOGETHER_API_KEY"))
        self.conversation_history: List[MessageDict] = self.load_conversation_history()
        self.model_responses: List[ResponseDict] = []

    def call_planner(self, conversation_history: str, recent_chatbot_response: str) -> str:
        """
        Call the planner model to generate attack strategies.
        
        Args:
            conversation_history (str): Formatted conversation history.
            recent_chatbot_response (str): The most recent response from the chatbot.
            
        Returns:
            str: Planning response containing attack strategies.
        """
        planner_prompt_func = getattr(prompt, f"get_planner_system_prompt_{self.planner_prompt_version}")
        response = self.client.chat.completions.create(
            model=self.planner_model,
            temperature=1.2,  # High temperature to ensure the planner is creative
            presence_penalty=0.3,  # High presence penalty to ensure the planner explores non-repetitive strategies
            messages=[
                {"role": "system", "content": planner_prompt_func()},
                {"role": "user", "content": prompt.get_planner_user_prompt_current(self.topic, conversation_history, recent_chatbot_response)}
            ]
        )
        return response.choices[0].message.content

    def call_attacker(self, conversation_history: str, user_suggestion: str, recent_chatbot_response: str) -> str:
        """
        Call the attacker model to generate user messages.
        
        Args:
            conversation_history (str): Formatted conversation history.
            user_suggestion (str): Suggestion from the planner model.
            
        Returns:
            str: Generated user message to send to the victim model.
        """
        attacker_prompt_func = getattr(prompt, f"get_attacker_system_prompt_{self.attacker_prompt_version}")
        response = self.client.chat.completions.create(
            model=self.attacker_model,
            temperature=1.1,  # High temperature to ensure the attacker is creative
            messages=[
                {"role": "system", "content": attacker_prompt_func(self.topic)},
                {"role": "user", "content": prompt.get_attacker_user_prompt_current(conversation_history, user_suggestion, recent_chatbot_response)}
            ]
        )
        return response.choices[0].message.content

    def call_victim_model(self, conversation_history: List[MessageDict]) -> str:
        """Call the victim model being tested.
        
        Args:
            conversation_history (List[MessageDict]): List of message dictionaries.
            
        Returns:
            str: Response from the victim model.
        """
        response = self.client.chat.completions.create(
            model=self.victim_model,
            messages=conversation_history
        )
        return response.choices[0].message.content

    @staticmethod
    def strip_suggestion(thinking_response: str) -> str:
        """
        Extract the user suggestion from the planner's response.
        
        Args:
            thinking_response (str): Full response from the planner model.
            
        Returns:
            str: Extracted user suggestion.
        """
        return thinking_response.split("User Suggestion:")[-1].strip()

    @staticmethod
    def strip_response(conversational_response: str) -> str:
        """
        Extract the user message from the attacker's response.
        
        Args:
            conversational_response (str): Full response from the attacker model.
            
        Returns:
            str: Extracted user message to send to the victim model.
        """
        return conversational_response.split("MY USER RESPONSE:")[-1].strip()

    @staticmethod
    def format_conversation_history(conversation_history: List[MessageDict]) -> str:
        """
        Convert conversation history from a list of dictionaries to a formatted string.
        
        Args:
            conversation_history (List[MessageDict]): List of message dictionaries.
            
        Returns:
            str: Formatted conversation history as a string.
        """
        # Initialize an empty list to store formatted message strings
        formatted_history: List[str] = []
        
        # Iterate through each message in the conversation history
        for message in conversation_history:
            # Extract the role (user or assistant) from the message dictionary
            role: str = message['role']
            
            # Extract the content/text of the message from the dictionary
            content: str = message['content']
            
            # Format each message as "[role] content" and add to the list
            formatted_history.append(f"[{role}] {content}")
            
        # Join all formatted messages with newlines to create a single string
        return "\n".join(formatted_history)

    def load_conversation_history(self) -> List[MessageDict]:
        """Load conversation history from a JSON file or create a default one.
        
        Returns:
            List[MessageDict]: List of message dictionaries representing the conversation history.
        """
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Basic sanity check – ensure it is a list of dicts with the expected keys.
                if isinstance(data, list) and all(isinstance(m, dict) and "role" in m and "content" in m for m in data):
                    return data
            except (json.JSONDecodeError, IOError):
                pass  # Fall through to return default if file is corrupt / unreadable
        # Default: start a fresh conversation
        return [{"role": "user", "content": "Hi"}]

    def save_conversation_history(self) -> None:
        """Save the current conversation history to a JSON file in the output directory."""
        history_file_path = os.path.join(self.output_directory, os.path.basename(self.history_path))
        with open(history_file_path, "w", encoding="utf-8") as f:
            json.dump(self.conversation_history, f, indent=4)

    def save_model_responses(self) -> None:
        """Save the full model responses to a separate JSON file in the full response output directory.
        
        This method saves all the detailed model responses collected during 
        the conversation generation process.
        """
        full_output_path: str = os.path.join(self.full_response_output_directory, f"{os.path.splitext(os.path.basename(self.history_path))[0]}_full_responses.json")
        with open(full_output_path, "w", encoding="utf-8") as f:
            json.dump(self.model_responses, f, indent=4)

    def manage_conversation(self) -> None:
        """
        Manage the red-teaming conversation generation process.
        
        This method orchestrates the multi-turn conversation generation by:
        1. Getting responses from the planner model
        2. Using these to generate user messages with the attacker model
        3. Sending user messages to the victim model
        4. Saving all responses and the conversation history
        
        The process continues until the maximum number of turns is reached.
        """
        # If the last entry is a user message, obtain the assistant's immediate reply first
        if self.conversation_history and self.conversation_history[-1]["role"] == "user":
            assistant_initial: str = self.call_victim_model(self.conversation_history)
            self.conversation_history.append({"role": "assistant", "content": assistant_initial})
            self.model_responses.append({"type": "attacked_model", "response": assistant_initial})
            self.save_conversation_history()

        # Start from 0 turns and count up to max_user_turns
        current_turn = 0
        while current_turn < self.max_user_turns:
            filtered_history: List[MessageDict] = [m for m in self.conversation_history if m["role"] == "user"]
            if self.conversation_history and self.conversation_history[-1]["role"] == "assistant":
                filtered_history.append(self.conversation_history[-1])

            formatted_history: str = self.format_conversation_history(filtered_history)
            recent_chatbot_response: str = self.conversation_history[-1]["content"] if self.conversation_history and self.conversation_history[-1]["role"] == "assistant" else ""
            
            planning_response: str = self.call_planner(formatted_history, recent_chatbot_response)
            user_suggestion: str = self.strip_suggestion(planning_response)
            self.model_responses.append({"type": "planning_model", "response": planning_response})
            
            conversational_response: str = self.call_attacker(formatted_history, user_suggestion, recent_chatbot_response)
            user_response: str = self.strip_response(conversational_response)
            self.model_responses.append({"type": "attacker_model", "response": conversational_response})
            
            self.conversation_history.append({"role": "user", "content": user_response})

            chatbot_response: str = self.call_victim_model(self.conversation_history)
            self.model_responses.append({"type": "attacked_model", "response": chatbot_response})

            self.conversation_history.append({"role": "assistant", "content": chatbot_response})
            
            print(f"\n------TURN {current_turn + 1}------")
            print(f"------USER------: {self.conversation_history[-2]['content']}")
            print(f"------ASSISTANT------: {self.conversation_history[-1]['content']}")
            print("------END OF TURN------\n")
            
            self.save_conversation_history()
            current_turn += 1
        
        self.save_conversation_history()
        self.save_model_responses()

    def run(self) -> str:
        """
        Run the conversation generation process.
        
        This is the main entry point for starting the conversation generation.
        
        Returns:
            str: Success message when the conversation is completed.
        """
        self.manage_conversation()
        return "Conversation completed successfully!"


def main() -> None:
    """Execute the conversation generator from the command line.
    
    Command line interface for the conversation generator using Python Fire.
    This allows more flexibility compared to argparse, including nested commands and automatic --help.
    
    Examples:
        # Run with default parameters (except for required topic)
        python conversation_generator.py run --topic="harmful content"
        
        # Run with custom models
        python conversation_generator.py run --topic="harmful content" --victim_model="anthropic/claude-3-opus"
        
        # Use different models for different roles
        python conversation_generator.py run --topic="harmful content" --planner_model="model1" --attacker_model="model2" --victim_model="model3"

        # Run with custom output path
        python conversation_generator.py run --topic="harmful content" --history_path="custom_output.json"
    """
    fire.Fire(ConversationGenerator)


# Call the main function to start and manage the conversation
if __name__ == "__main__":
    main()