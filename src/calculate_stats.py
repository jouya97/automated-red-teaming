"""
Calculate statistics for classification files.

Usage:
    # For basic statistics on a single directory:
    python calculate_stats.py --mode=stats --directory=/path/to/classification/files

    # For comparing two sets of classification files:
    python calculate_stats.py --mode=compare --dir1=/path/to/first/set --dir2=/path/to/second/set

The script analyzes JSON files ending with '_classification.json' in the specified directories.
It calculates statistics like mean, median, standard deviation, and quartiles for Q&A scores,
and can perform statistical comparisons between two sets of classifications.
"""

from pydantic import BaseModel
import json
import os
from pathlib import Path
from statistics import mean, median, stdev
from typing import Dict, List, Tuple
import fire
from scipy import stats



def count_verdicts(directory_path: str) -> Dict[str, int]:
    """
    Count the number of 'Yes' and 'No' verdicts in classification files.
    
    Args:
        directory_path: Path to directory containing classification JSON files
        
    Returns:
        Dictionary with counts of 'Yes', 'No', and total verdicts
    """
    yes_count = 0
    no_count = 0
    
    for file_path in Path(directory_path).glob("*_classification.json"):
        with open(file_path, 'r') as f:
            data = json.load(f)
            verdict = data.get("Verdict", "").strip()
            if verdict == "Yes":
                yes_count += 1
            elif verdict == "No":
                no_count += 1
    
    total = yes_count + no_count
    return {
        "Yes": yes_count,
        "No": no_count,
        "Total": total
    }

def calculate_qa_statistics(directory_path: str) -> Dict[str, float]:
    """
    Calculate various statistics for Q&A scores from classification files.
    
    Args:
        directory_path: Path to directory containing classification JSON files
        
    Returns:
        Dictionary containing mean, median, standard deviation, and quartiles
    """
    scores = []
    
    # Collect all scores
    for file_path in Path(directory_path).glob("*_classification.json"):
        with open(file_path, 'r') as f:
            data = json.load(f)
            score = int(data.get("Q&A Score", "0"))
            scores.append(score)
    
    if not scores:
        return {
            "mean": 0,
            "median": 0,
            "stdev": 0,
            "q1": 0,
            "q3": 0,
            "max_score": 0
        }
    
    # Sort scores for quartile calculation
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    
    # Calculate quartiles
    q1_idx = n // 4
    q3_idx = (3 * n) // 4
    
    q1 = sorted_scores[q1_idx]
    q3 = sorted_scores[q3_idx]
    
    return {
        "mean": mean(scores),
        "median": median(scores),
        "stdev": stdev(scores),
        "q1": q1,
        "q3": q3,
        "max_score": max(scores)
    }

def print_statistics(directory_path: str) -> None:
    """
    Print all statistics in a readable format.
    
    Args:
        directory_path: Path to directory containing classification JSON files
    """
    verdicts = count_verdicts(directory_path)
    stats = calculate_qa_statistics(directory_path)
    
    print("\nVerdict Statistics:")
    print(f"Total verdicts: {verdicts['Total']}")
    print(f"Yes verdicts: {verdicts['Yes']} ({verdicts['Yes']/verdicts['Total']*100:.1f}%)")
    print(f"No verdicts: {verdicts['No']} ({verdicts['No']/verdicts['Total']*100:.1f}%)")
    
    print("\nQ&A Score Statistics:")
    print(f"Mean: {stats['mean']:.2f}")
    print(f"Median: {stats['median']:.2f}")
    print(f"Standard Deviation: {stats['stdev']:.2f}")
    print(f"First Quartile (Q1): {stats['q1']}")
    print(f"Third Quartile (Q3): {stats['q3']}")
    print(f"Interquartile Range: {stats['q3'] - stats['q1']}")
    print(f"Q1 Range: 0 to {stats['q1']}")
    print(f"Q2 Range: {stats['q1']} to {stats['median']}")
    print(f"Q3 Range: {stats['median']} to {stats['q3']}")
    print(f"Q4 Range: {stats['q3']} to {stats['max_score']}")

def compare_classification_sets(dir1: str, dir2: str) -> Dict[str, float]:
    """
    Perform T-test comparison between two sets of classification scores.
    
    Args:
        dir1: Path to first directory containing classification JSON files
        dir2: Path to second directory containing classification JSON files
        
    Returns:
        Dictionary containing t-statistic and p-value
    """
    def get_scores(directory: str) -> List[int]:
        scores = []
        for file_path in Path(directory).glob("*_classification.json"):
            with open(file_path, 'r') as f:
                data = json.load(f)
                score = int(data.get("Q&A Score", "0"))
                scores.append(score)
        return scores
    
    scores1 = get_scores(dir1)
    scores2 = get_scores(dir2)
    
    if len(scores1) != len(scores2):
        raise ValueError("Both directories must contain the same number of files")
    
    t_stat, p_value = stats.ttest_ind(scores1, scores2)
    
    return {
        "t_statistic": t_stat,
        "p_value": p_value,
        "mean1": mean(scores1),
        "mean2": mean(scores2),
        "std1": stdev(scores1),
        "std2": stdev(scores2)
    }

def print_comparison(dir1: str, dir2: str) -> None:
    """
    Print T-test comparison results in a readable format.
    
    Args:
        dir1: Path to first directory containing classification JSON files
        dir2: Path to second directory containing classification JSON files
    """
    results = compare_classification_sets(dir1, dir2)
    
    print("\nT-test Comparison Results:")
    print(f"T-statistic: {results['t_statistic']:.4f}")
    print(f"P-value: {results['p_value']:.4f}")
    print(f"\nSet 1 Statistics:")
    print(f"Mean: {results['mean1']:.2f}")
    print(f"Standard Deviation: {results['std1']:.2f}")
    print(f"\nSet 2 Statistics:")
    print(f"Mean: {results['mean2']:.2f}")
    print(f"Standard Deviation: {results['std2']:.2f}")
    
    # Interpret p-value
    alpha = 0.05
    if results['p_value'] < alpha:
        print(f"\nThe difference is statistically significant (p < {alpha})")
    else:
        print(f"\nThe difference is not statistically significant (p >= {alpha})")

def main(
    mode: str = "stats",
    dir1: str = None,
    dir2: str = None,
    directory: str = None
) -> None:
    """
    Calculate statistics for classification files.
    
    Args:
        mode: Type of calculation to perform
            - "stats": Basic statistics for a single directory
            - "compare": T-test comparison between two directories
        dir1: First directory path (required for compare mode)
        dir2: Second directory path (required for compare mode)
        directory: Directory path (required for stats mode)
    """
    if mode == "stats":
        if not directory:
            raise ValueError("Directory path is required for stats mode")
        print_statistics(directory)
    elif mode == "compare":
        if not dir1 or not dir2:
            raise ValueError("Both dir1 and dir2 are required for compare mode")
        print_comparison(dir1, dir2)
    else:
        raise ValueError("Invalid mode. Use 'stats' or 'compare'")

if __name__ == "__main__":
    fire.Fire(main)