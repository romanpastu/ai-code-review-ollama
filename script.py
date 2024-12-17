#!/usr/bin/env python3

import os
import subprocess
from git import Repo
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables with defaults
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:14b')

def is_git_repository(path):
    """Check if the current path is a Git repository."""
    try:
        _ = Repo(path).git_dir
        return True
    except:
        return False

def get_current_branch(repo):
    """Get the name of the current active branch."""
    return repo.active_branch.name

def compare_branches(repo, branch1, branch2):
    """Get the diff between two branches as a unified diff."""
    diff_command = f"git diff {branch1}..{branch2}"
    result = subprocess.run(diff_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.stderr:
        print("Error generating git diff:", result.stderr)
    return result.stdout

def process_with_ollama(diff_output):
    """
    Process the git diff with Ollama using its HTTP API.
    """
    import requests
    import json

    print(f"Diff output length: {len(diff_output)}")
    
    # Combine the system instruction with the diff output
    combined_prompt = (
        "When provided with the differences between two Git branches (in a unified diff or similar format), you should:\n"
        "Examine all code changes and identify any potential issues such as bugs, performance concerns, code smells, or violations of best practices.\n"
        "For each identified issue, classify its severity level as one of:\n"
        "Trivial: Minor issue that may not necessarily require immediate action, such as a small formatting inconsistency or a harmless but redundant line of code.\n"
        "Medium: Notable problem that might lead to incorrect behavior under certain conditions, degrade performance, or reduce code maintainability, but is not immediately catastrophic.\n"
        "Severe: Critical bug or serious design flaw that can cause incorrect results, security vulnerabilities, data loss, or significantly hamper system performance and reliability.\n"
        "After classifying the severity, provide a brief explanation of:\n"
        "What is happening: Describe the nature of the issue and how it might manifest.\n"
        "How to fix it: Suggest a clear, actionable strategy for addressing the problem.\n"
        "Make sure each identified issue is listed separately, with the classification, explanation, and recommendation contained together, so it’s easy to understand each issue at a glance.\n"
        "Example Output Format:\n"
        "1. Issue: [Short description]\n"
        "Severity: Medium\n"
        "What is happening: [Explanation of the problem]\n"
        "How to fix: [Recommended solution steps]\n"
        "2. Issue: [Short description]\n"
        "Severity: Severe\n"
        "What is happening: [Explanation of the problem]\n"
        "How to fix: [Recommended solution steps]\n"
        "...\n\n"
        "Here is the git diff to analyze:\n"
        f"{diff_output}"
    )

    print("Sending prompt to Ollama...")
    print(f"First 100 chars of prompt: {combined_prompt[:100]}")

    try:
        response = requests.post(
            f'{OLLAMA_HOST}/api/generate',
            json={
                'model': OLLAMA_MODEL,
                'prompt': combined_prompt,
                'stream': False
            },
            timeout=120
        )
        

        if response.status_code != 200:
            print(f"Error response body: {response.text}")
            return ""

        result = response.json()
        
        return result.get('response', '').strip()
        
    except requests.exceptions.Timeout:
        print("Ollama processing timed out.")
        return ""
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return ""

def main():
    """Main function to compare branches and analyze diffs."""
    current_path = os.getcwd()

    # Step 1: Check if the current directory is a Git repository
    if not is_git_repository(current_path):
        print("Not a git repository.")
        return

    repo = Repo(current_path)

    # Step 2: Determine branches to compare
    current_branch = get_current_branch(repo)
    main_branch = "main" if "main" in repo.heads else "master"

    if current_branch == main_branch:
        print(f"You are already on the {main_branch} branch.")
        return

    # Step 3: Get the diff between the main branch and the current branch
    print(f"Comparing {current_branch} with {main_branch}...")
    diff_output = compare_branches(repo, main_branch, current_branch)

    if not diff_output:
        print("No differences found.")
        return

    # Step 4: Process the diff with Ollama
    ollama_output = process_with_ollama(diff_output)

    # Step 5: Print the analysis result
    print("Ollama Analysis Reported:")
    print(ollama_output)

if __name__ == "__main__":
    main()
