# automated-red-teaming
This project contains scripts to facilitate and analyze automated red teaming conversations with AI chatbots. The goal is to test LLM guardrails and see if they can be manipulated into discussing sensitive or unsafe topics by another LLM.

## Files

- `conversation_generator.py`: Manages a conversation between a "planning DeepSeek v3", a "conversational DeepSeek v3" and an LLM that will be the victim of automated red teaming. Planning DeepSeek formulates a plan and Conversational DeepSeek is responsible for conversing with the attacked model. The division of labor is a way around DeepSeek v3's own guardrails as attempting to do this in one prompt will make DeepSeek hesitant in performing red teaming.
- `classifier.py`: Analyzes a conversation to determine if any unsafe information was provided by the chatbot.

## Requirements

- Python 3.x
- Together API key (set as an environment variable `TOGETHER_API_KEY`)

## Installation

Together is the only dependency.

1. Install the required Python packages:
   ```bash
   pip install together
   ```

## Usage

### Running the Conversation Generator

The `conversation_generator.py` script manages the conversation with the chatbot.

```bash
python conversation_generator.py --topic <topic> --history_path <path_to_history_file> --max_user_turns <max_turns> --model_name <model_name>
```

- `--topic`: The topic for automated red teaming.
- `--history_path`: Path to the conversation history file (default: `conversation_history.json`).
- `--max_user_turns`: Maximum number of user turns in the conversation (default: 10).
- `--model_name`: The model name for the attack (default: `deepseek-ai/DeepSeek-V3`).

### Running the Classifier

The `classifier.py` script analyzes the conversation to check for unsafe information.

```bash
python classifier.py --file_path <path_to_conversation_history>
```

- `--file_path`: Path to the JSON file containing the conversation history.

## Output

- The conversation history and full responses are saved in JSON files.
- Full responses allow you to view reasoning performed by Planning DeepSeek and Conversational DeepSeek.
- The classifier outputs a JSON file with the analysis and verdict on the safety of the conversation.

## Example Conversations and Evals
Example conversations and classifications are available for viewing in the "example_convos_and_evals" folder. In these conversations, Planning DeepSeek and Conversational DeepSeek attacked a "victim" instance of DeepSeek to elicit information on how to:
- Cook crack cocaine at home.
- Create a flour bomb at home.
- Perform lobotomies at home.

A non red teaming conversation about how to have a nice day is included to sanity check the classifier.
