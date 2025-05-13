import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from classifier import ConversationClassifier
import fire

def classify_conversation(input_directory, output_directory, classifier_prompt_version="current"):
    """
    Classify a conversation from a given file and save the result.

    This function initializes a ConversationClassifier for the specified file
    and runs the classification, saving the result to the specified output directory.

    Args:
        input_directory (str): The path to the input file to classify.
        output_directory (str): The path to the directory where the classification result will be saved.
        classifier_prompt_version (str, optional): Version of classifier prompt to use. Defaults to "current".

    Returns:
        dict: The classification result.
    """
    classifier = ConversationClassifier(
        file_path=input_directory,
        classifier_prompt_version=classifier_prompt_version
    )
    result = classifier.run(output_directory=output_directory)
    
    return result

def main(input_directory, output_directory, classifier_prompt_version="current"):
    """
    Classify all JSON files in the specified folder and save results to the output folder.

    This function retrieves all JSON files from the given folder path and 
    uses a thread pool to classify each file concurrently, saving results to the output folder.

    Args:
        input_directory (str): The path to the folder containing JSON files to classify.
        output_directory (str): The path to the folder where classification results will be saved.
        classifier_prompt_version (str, optional): Version of classifier prompt to use. Defaults to "current".
    """
    os.makedirs(output_directory, exist_ok=True)

    file_paths = [os.path.join(input_directory, file) for file in os.listdir(input_directory) if file.endswith('.json')]

    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(classify_conversation, file_path, output_directory, classifier_prompt_version): i for i, file_path in enumerate(file_paths)}
        
        for future in as_completed(futures):
            index = futures[future]
            file_path = file_paths[index]
            try:
                result = future.result()
                print(f"Classification {index} completed: {result}")
            except Exception as e:
                print(f"Classification {index} failed for file {file_path}: {e}")

if __name__ == "__main__":
    fire.Fire(main)

"""
python batch_classification.py --input_directory_path data/crack_cocaine/conversations --output_directory_path data/crack_cocaine/classifications
python batch_classification.py --input_directory_path "data/flour_bomb/conversations" --output_directory_path "data/flour_bomb/classifications"
python batch_classification.py --input_directory_path "data/lobotomy/conversations" --output_directory_path "data/lobotomy/classifications"

# Use a specific classifier prompt version
python batch_classification.py --input_directory_path "data/lobotomy/conversations" --output_directory_path "data/lobotomy/classifications" --classifier_prompt_version="v2"
"""