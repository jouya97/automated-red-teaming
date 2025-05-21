import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from conversation_generator import ConversationGenerator
import fire
from datetime import datetime

def generate_conversation(topic, history_path, output_dir, full_output_dir, max_user_turns, planner_model, attacker_model, victim_model, victim_model_provider="openai", planner_prompt_version="current", attacker_prompt_version="current"):
    """Generate a conversation for a given topic.

    Args:
        topic (str): The topic for the conversation.
        history_path (str): The path to save the conversation history.
        output_dir (str): The directory to save the generated conversation output.
        full_output_dir (str): The directory to save full model responses.
        max_user_turns (int): Maximum number of user turns in the conversation.
        planner_model (str): Model used for planning attack strategies.
        attacker_model (str): Model used for generating user messages.
        victim_model (str): Model being red-teamed/evaluated.
        victim_model_provider (str, optional): Provider for victim model ('together' or 'openai'). Defaults to "openai".
        planner_prompt_version (str, optional): Version of planner prompt to use. Defaults to "current".
        attacker_prompt_version (str, optional): Version of attacker prompt to use. Defaults to "current".

    Returns:
        str: The result of the conversation generation process.
    """
    generator = ConversationGenerator(
        topic=topic,
        history_path=history_path,
        output_dir=output_dir,
        full_output_dir=full_output_dir,
        max_user_turns=max_user_turns,
        planner_model=planner_model,
        attacker_model=attacker_model,
        victim_model=victim_model,
        victim_model_provider=victim_model_provider,
        planner_prompt_version=planner_prompt_version,
        attacker_prompt_version=attacker_prompt_version
    )
    result = generator.run()
    return result

def main(topic, num_conversations, output_dir='data', full_output_dir='full_responses', max_workers=25, max_user_turns=10, planner_model="deepseek-ai/DeepSeek-V3", attacker_model="deepseek-ai/DeepSeek-V3", victim_model="deepseek-ai/DeepSeek-V3", victim_model_provider="openai", planner_prompt_version="current", attacker_prompt_version="current"):
    """Run the batch conversation generation process for a single topic.

    Args:
        topic (str): The base topic for conversation generation.
        num_conversations (int): Number of conversations to generate for the topic.
        output_dir (str, optional): Directory to save the generated conversations. Defaults to 'data'.
        full_output_dir (str, optional): Directory to save full model responses. Defaults to 'full_responses'.
        max_workers (int, optional): Maximum number of threads to use. Defaults to 25.
        max_user_turns (int, optional): Maximum number of user turns in the conversation. Defaults to 10.
        planner_model (str, optional): Model used for planning attack strategies. Defaults to "deepseek-ai/DeepSeek-V3".
        attacker_model (str, optional): Model used for generating user messages. Defaults to "deepseek-ai/DeepSeek-V3".
        victim_model (str, optional): Model being red-teamed/evaluated. Defaults to "deepseek-ai/DeepSeek-V3".
        victim_model_provider (str, optional): Provider for victim model ('together' or 'openai'). Defaults to "openai".
        planner_prompt_version (str, optional): Version of planner prompt to use. Defaults to "current".
        attacker_prompt_version (str, optional): Version of attacker prompt to use. Defaults to "current".
    """
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(full_output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    topics = [topic for _ in range(num_conversations)]
    history_paths = [f"conversation_history_{timestamp}_{i}.json" for i in range(len(topics))]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(generate_conversation, topic, history_path, output_dir, full_output_dir, max_user_turns, planner_model, attacker_model, victim_model, victim_model_provider, planner_prompt_version, attacker_prompt_version): i for i, (topic, history_path) in enumerate(zip(topics, history_paths))}
        
        for future in as_completed(futures):
            index = futures[future]
            try:
                result = future.result()
                print(f"Conversation {index} completed: {result}")
            except Exception as e:
                print(f"Conversation {index} generated an exception: {e}")

if __name__ == "__main__":
    fire.Fire(main)