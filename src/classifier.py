import json
import os
from typing import Dict, List, Optional, Any
import fire
from together import Together
import prompt
import time
from pydantic import BaseModel, Field

class ClassificationResponse(BaseModel):
    conversation_analysis: str = Field(..., description="Detailed analysis of the conversation")
    qa: str = Field(..., description="Q&A section evaluating the conversation's safety")
    qa_score: str = Field(..., description="Numerical score aggregating the safety evaluation")
    verdict: str = Field(..., description="Final determination of whether the conversation contains unsafe information")

class ConversationClassifier:
    """Classify conversations to determine if they contain unsafe content.
    
    This class uses LLMs to analyze conversation history and determine if the content
    is potentially unsafe according to safety guidelines.
    
    Attributes:
        file_path (Optional[str]): Path to the conversation JSON file to be classified.
        model (str): The LLM model to use for classification.
        client (Together): The API client for making requests to the model provider.
        classifier_prompt_version (str): Version of the classifier prompt to use.
    """

    def __init__(self, file_path: Optional[str] = None, model: str = "deepseek-ai/DeepSeek-V3", classifier_prompt_version: str = "current") -> None:
        """Initialize the conversation classifier.
        
        Args:
            file_path (Optional[str]): Path to the conversation JSON file. Defaults to None.
            model (str): Model used for classification. Defaults to "deepseek-ai/DeepSeek-V3".
            classifier_prompt_version (str): Version of classifier prompt to use. Defaults to "v3".
        """
        self.file_path = file_path
        self.model = model
        self.classifier_prompt_version = classifier_prompt_version
        self.client = Together(api_key=os.environ.get("TOGETHER_API_KEY"))
        
    def classify_conversation(self, conversation_history: str) -> Dict[str, str]:
        """Analyze a conversation using an LLM to determine if it contains unsafe content.
        
        Args:
            conversation_history (str): Formatted conversation history as a string.
            
        Returns:
            Dict[str, str]: Dictionary containing the conversation analysis and safety verdict.
        """
        max_retries = 5
        retry_delay = 3  # seconds
        attempt = 0

        while attempt < max_retries:
            try:
                classifier_prompt_func = getattr(prompt, f"get_classifier_system_prompt_{self.classifier_prompt_version}")
                user_prompt_func = getattr(prompt, f"get_classifier_user_prompt_{self.classifier_prompt_version}")
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    response_format={
                        "type": "json_object",
                        "schema": ClassificationResponse.model_json_schema()
                    },
                    messages=[
                        {"role": "system", "content": classifier_prompt_func()},
                        {"role": "user", "content": user_prompt_func(conversation_history)}
                    ]
                )
                output = json.loads(response.choices[0].message.content)
                print(f"Raw response content: {output}")  # Debug log
                
                if not output:
                    raise ValueError("Empty response received from model")
                
                return output
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                attempt += 1
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Max retries reached. Failing with error.")
                    raise e

    @staticmethod
    def format_conversation_history(file_path: str) -> Optional[str]:
        """
        Load the conversation history from a JSON file and convert it to a formatted string.
        
        Args:
            file_path (str): Path to the JSON file containing the conversation history.
            
        Returns:
            Optional[str]: Formatted conversation history as a string, or None if loading fails.
        """
        try:
            with open(file_path, 'r') as file:
                conversation_history: List[Dict[str, str]] = json.load(file)
        except FileNotFoundError:
            print(f"Error: The file {file_path} was not found.")
            return None
        except json.JSONDecodeError:
            print(f"Error: The file {file_path} is not a valid JSON.")
            return None

        formatted_history: List[str] = []
        for message in conversation_history:
            role: str = message['role']
            content: str = message['content']
            formatted_history.append(f"[{role}] {content}")
        
        return "\n".join(formatted_history)
    
    def save_classification(self, classification_result: Dict[str, str], output_directory: str) -> str:
        """Save the classification result to a JSON file in the specified output directory."""
        base_name: str = os.path.splitext(os.path.basename(self.file_path))[0]
        output_file_name: str = f"{base_name}_classification.json"
        output_file_path: str = os.path.join(output_directory, output_file_name)

        with open(output_file_path, 'w') as outfile:
            json.dump(classification_result, outfile, indent=4)
        
        return output_file_path

    def run(self, output_directory: str = 'data/classifications') -> Dict[str, Any]:
        """Run the classifier on the provided file path and save the result to the specified output directory."""
        if not self.file_path:
            return {"error": "No file path provided. Use --file_path parameter."}
            
        os.makedirs(output_directory, exist_ok=True)
            
        formatted_history: Optional[str] = self.format_conversation_history(self.file_path)
        if formatted_history is None:
            return {"error": f"Failed to format conversation history from {self.file_path}"}
            
        classification_result: Dict[str, str] = self.classify_conversation(formatted_history)
        
        output_file: str = self.save_classification(classification_result, output_directory)
        
        result: Dict[str, Any] = dict(classification_result)
        result["output_file"] = output_file
        
        print(json.dumps(result, indent=4))
        return result


def main() -> None:
    """Run the conversation classifier from the command line."""
    fire.Fire(ConversationClassifier)


if __name__ == "__main__":
    main()