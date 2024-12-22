#!/usr/bin/env python3

import os
import subprocess
from git import Repo
import requests
import json
from dotenv import load_dotenv
import time
import sys

# Load environment variables from .env file
load_dotenv()

# Get environment variables with defaults
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
SSH_HOST = os.getenv('SSH_HOST', '192.168.31.18')
SSH_USER = os.getenv('SSH_USER', 'roman')
SSH_PORT = os.getenv('SSH_PORT', '22')

# Update the check to verify if any of them are explicitly set to None
if None in [OLLAMA_HOST, OLLAMA_MODEL, SSH_HOST, SSH_USER, SSH_PORT]:
    print("Please set all required environment variables in .env file:")
    print(f"OLLAMA_HOST (current: {OLLAMA_HOST})")
    print(f"OLLAMA_MODEL (current: {OLLAMA_MODEL})")
    print(f"SSH_HOST (current: {SSH_HOST})")
    print(f"SSH_USER (current: {SSH_USER})")
    print(f"SSH_PORT (current: {SSH_PORT})")
    sys.exit(1)

def setup_ssh_tunnel():
    """Setup SSH tunnel to the Ollama server"""
    try:
        # Kill any existing tunnels on port 11434
        subprocess.run("lsof -ti:11434 | xargs kill -9", shell=True, stderr=subprocess.PIPE)
        
        # Create new SSH tunnel
        cmd = f"ssh -f -N -L 11434:localhost:11434 {SSH_USER}@{SSH_HOST} -p {SSH_PORT}"
        result = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            print(f"Failed to create SSH tunnel: {result.stderr.decode()}")
            return False
            
        # Give the tunnel a moment to establish
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Error setting up SSH tunnel: {e}")
        return False

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
    """Get the diff between two branches as a dictionary of file paths and their diffs."""
    # Get list of changed files
    diff_command = f"git diff --name-only {branch1}..{branch2}"
    result = subprocess.run(diff_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.stderr:
        print("Error getting changed files:", result.stderr)
        return {}
    
    changed_files = result.stdout.strip().split('\n')
    if not changed_files or (len(changed_files) == 1 and not changed_files[0]):
        return {}
    
    # Get diff for each file
    file_diffs = {}
    for file in changed_files:
        diff_command = f"git diff {branch1}..{branch2} -- {file}"
        result = subprocess.run(diff_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stderr:
            print(f"Error generating git diff for {file}:", result.stderr)
        else:
            file_diffs[file] = result.stdout
    
    return file_diffs

def process_with_ollama(diff_output, filename=None):
    """
    Process a single file's git diff with Ollama using its HTTP API.
    """
    import requests
    import json

    file_context = f"File: {filename}\n" if filename else ""
    print(f"Processing diff for {filename} (length: {len(diff_output)})")
    
    # Combine the system instruction with the diff output
    combined_prompt = (
        "Your ONLY purpose is to analyze Git diff output for issues. You are a strict issue detector that CANNOT provide any other type of response.\n\n"
        
        "YOU MUST ONLY OUTPUT IN THIS FORMAT:\n"
        "1. Issue: [One line description]\n"
        "Severity: [ONLY use: Trivial/Medium/Severe]\n"
        "What is happening: [Brief explanation]\n"
        "How to fix: [Brief solution]\n\n"
        
        "OR IF NO ISSUES:\n"
        "No issues found\n\n"
        
        "CRITICAL RULES:\n"
        "- NO markdown\n"
        "- NO summaries\n"
        "- NO explanations\n"
        "- NO additional text\n"
        "- NO analysis outside of the strict format\n"
        "- NO documentation\n"
        "- NO suggestions beyond issue format\n"
        "- NO other response types allowed\n"
        "- NEVER deviate from format\n\n"
        
        "FORBIDDEN RESPONSES (DO NOT OUTPUT LIKE THESE):\n"
        "❌ 'Here's a summary of changes...'\n"
        "❌ 'The provided diff shows...'\n"
        "❌ 'Key modifications include...'\n"
        "❌ Any markdown formatting\n"
        "❌ Any high-level analysis\n\n"
        
        f"{file_context}"
        "Here is the git diff to analyze:\n"
        f"{diff_output}"
    )

    print(f"Sending prompt to Ollama for {filename}...")

    try:
        response = requests.post(
            f'{OLLAMA_HOST}/api/generate',
            json={
                'model': OLLAMA_MODEL,
                'prompt': combined_prompt,
                'stream': False
            },
            timeout=360
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

def get_config_mode():
    """Get the mode (ssh/http) from the bundled config file"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.txt')
        if hasattr(sys, '_MEIPASS'):  # If running as PyInstaller bundle
            config_path = os.path.join(sys._MEIPASS, 'config.txt')
        
        with open(config_path, 'r') as f:
            for line in f:
                if line.startswith('MODE='):
                    return line.strip().split('=')[1]
    except:
        return 'http'  # Default to http mode if config file not found
    return 'http'

def validate_env_vars(mode):
    """Validate environment variables based on mode"""
    required_vars = ['OLLAMA_HOST', 'OLLAMA_MODEL']
    if mode == 'ssh':
        required_vars.extend(['SSH_HOST', 'SSH_USER', 'SSH_PORT'])
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("Please set the following required environment variables in .env file:")
        for var in missing_vars:
            print(f"{var} (current: {os.getenv(var)})")
        sys.exit(1)

def main():
    """Main function to compare branches and analyze diffs."""
    mode = get_config_mode()
    
    # Validate environment variables based on mode
    validate_env_vars(mode)
    
    if mode == 'ssh':
        # Setup SSH tunnel first
        if not setup_ssh_tunnel():
            print("Failed to setup SSH tunnel. Exiting.")
            return
    else:
        # In HTTP mode, we'll just verify we can reach the Ollama server
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/version")
            if response.status_code != 200:
                print(f"Cannot connect to Ollama server at {OLLAMA_HOST}")
                return
        except requests.exceptions.RequestException:
            print(f"Cannot connect to Ollama server at {OLLAMA_HOST}")
            return
    
    print(f"Using Ollama model: {OLLAMA_MODEL} in {mode} mode")

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

    # Step 3: Get the diff between the main branch and the current branch for each file
    print(f"Comparing {current_branch} with {main_branch}...")
    file_diffs = compare_branches(repo, main_branch, current_branch)

    if not file_diffs:
        print("No differences found.")
        return

    # Step 4: Process each file's diff with Ollama and collect results
    print("\nAnalyzing changes in each file:")
    all_results = []
    
    for filename, diff in file_diffs.items():
        print(f"\nAnalyzing {filename}...")
        result = process_with_ollama(diff, filename)
        if result and result.strip() != "No issues found":
            all_results.append(f"\nFile: {filename}\n{result}")

    # Step 5: Print the combined analysis results
    print("\nOllama Analysis Report:")
    if all_results:
        print("\n".join(all_results))
    else:
        print("No issues found in any of the changed files.")

if __name__ == "__main__":
    main()
