import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from classifier import ConversationClassifier
import fire

def classify_conversation(input_dir, output_dir, classifier_prompt_version="current"):
    """
    Classify a conversation from a given file and save the result.

    This function initializes a ConversationClassifier for the specified input directory.
    and runs the classification, saving the result to the specified output directory.

    Args:
        input_dir (str): The path to the input directory to classify.
        output_dir (str): The path to the directory where the classification result will be saved.
        classifier_prompt_version (str, optional): Version of classifier prompt to use. Defaults to "current".

    Returns:
        dict: The classification result.
    """
    classifier = ConversationClassifier(
        file_path=input_dir,
        classifier_prompt_version=classifier_prompt_version
    )
    result = classifier.run(output_directory=output_dir)
    
    return result

def main(input_dir, output_dir, max_workers=25, classifier_prompt_version="current"):
    """
    Classify all JSON files in the specified folder and save results to the output folder.

    This function retrieves all JSON files from the given folder path and 
    uses a thread pool to classify each file concurrently, saving results to the output folder.

    Args:
        input_directory (str): The path to the folder containing JSON files to classify.
        output_directory (str): The path to the folder where classification results will be saved.
        max_workers (int, optional): The number of workers to use for classification. Defaults to 25.
        classifier_prompt_version (str, optional): Version of classifier prompt to use. Defaults to "current".
    """
    os.makedirs(output_dir, exist_ok=True)

    file_paths = [os.path.join(input_dir, file) for file in os.listdir(input_dir) if file.endswith('.json')]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(classify_conversation, file_path, output_dir, classifier_prompt_version): i for i, file_path in enumerate(file_paths)}
        
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