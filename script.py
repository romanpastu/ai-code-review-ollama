#!/usr/bin/env python3

import os
import subprocess
import requests
import json
import time
import sys
import logging
from git import Repo
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load .env file
if hasattr(sys, '_MEIPASS'):
    # Running as a compiled binary
    env_path = os.path.join(sys._MEIPASS, '.env')
else:
    # Running as a script
    env_path = '.env'

load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get environment variables with defaults
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
SSH_HOST = os.getenv('SSH_HOST', '192.168.31.18')
SSH_USER = os.getenv('SSH_USER', 'roman')
SSH_PORT = os.getenv('SSH_PORT', '22')

def get_config_mode():
    """Get the mode (ssh/http) from the bundled config file."""
    try:
        if hasattr(sys, '_MEIPASS'):
            # Running as a compiled binary
            config_path = os.path.join(sys._MEIPASS, 'config.txt')
        else:
            # Running as a script
            config_path = 'config.txt'
        
        with open(config_path, 'r') as f:
            for line in f:
                if line.startswith('MODE='):
                    return line.strip().split('=')[1]
    except Exception:
        return 'http'  # Default to http mode if config file not found
    return 'http'

def validate_env_vars():
    """Validate environment variables."""
    required_vars = ['OLLAMA_HOST', 'OLLAMA_MODEL']
    if get_config_mode() == 'ssh':
        required_vars.extend(['SSH_HOST', 'SSH_USER', 'SSH_PORT'])
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logging.error("Please set the following required environment variables in .env file:")
        for var in missing_vars:
            logging.error(f"{var} (current: {os.getenv(var)})")
        sys.exit(1)

def setup_ssh_tunnel():
    """Setup SSH tunnel to the Ollama server."""
    try:
        subprocess.run("lsof -ti:11434 | xargs kill -9", shell=True, stderr=subprocess.PIPE)
        cmd = f"ssh -f -N -L 11434:localhost:11434 {SSH_USER}@{SSH_HOST} -p {SSH_PORT}"
        result = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logging.error(f"Failed to create SSH tunnel: {result.stderr.decode()}")
            return False
        time.sleep(2)
        return True
    except Exception as e:
        logging.error(f"Error setting up SSH tunnel: {e}")
        return False

def is_git_repository(path):
    """Check if the current path is a Git repository."""
    try:
        _ = Repo(path).git_dir
        return True
    except Exception:
        return False

def get_current_branch(repo):
    """Get the name of the current active branch."""
    return repo.active_branch.name

def compare_branches(repo, branch1, branch2):
    """Get the diff between two branches as a dictionary of file paths and their diffs."""
    diff_command = f"git diff --name-only {branch1}..{branch2}"
    result = subprocess.run(diff_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.stderr:
        logging.error(f"Error getting changed files: {result.stderr}")
        return {}
    
    changed_files = result.stdout.strip().split('\n')
    if not changed_files or (len(changed_files) == 1 and not changed_files[0]):
        return {}
    
    file_diffs = {}
    for file in changed_files:
        diff_command = f"git diff {branch1}..{branch2} -- {file}"
        result = subprocess.run(diff_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stderr:
            logging.error(f"Error generating git diff for {file}: {result.stderr}")
        else:
            file_diffs[file] = result.stdout
    
    return file_diffs

def get_file_context(file_path):
    """Extract context about a file, such as imported modules or dependencies."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Example: Extract imports for Python files
        if file_path.endswith('.py'):
            imports = [line.strip() for line in content.split('\n') if line.startswith('import') or line.startswith('from')]
            return {"imports": imports, "file_type": "Python"}
        
        # Add more file type handlers here (e.g., JavaScript, Java, etc.)
        return {"file_type": "Unknown"}
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return {}

def process_with_ollama(diff_output, filename=None, context=None):
    """Process a single file's git diff with Ollama using its HTTP API."""
    file_context = f"File: {filename}\n" if filename else ""
    if context:
        file_context += f"Context: {json.dumps(context, indent=2)}\n"
    
    logging.info(f"Processing diff for {filename} (length: {len(diff_output)})")
    
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

    logging.info(f"Sending prompt to Ollama for {filename}...")

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
            logging.error(f"Error response body: {response.text}")
            return ""

        result = response.json()
        return result.get('response', '').strip()
        
    except requests.exceptions.Timeout:
        logging.error("Ollama processing timed out.")
        return ""
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        logging.error(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return ""

def main():
    """Main function to compare branches and analyze diffs."""
    mode = get_config_mode()
    validate_env_vars()
    
    if mode == 'ssh':
        if not setup_ssh_tunnel():
            logging.error("Failed to setup SSH tunnel. Exiting.")
            return
    else:
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/version")
            if response.status_code != 200:
                logging.error(f"Cannot connect to Ollama server at {OLLAMA_HOST}")
                return
        except requests.exceptions.RequestException:
            logging.error(f"Cannot connect to Ollama server at {OLLAMA_HOST}")
            return
    
    logging.info(f"Using Ollama model: {OLLAMA_MODEL} in {mode} mode")

    current_path = os.getcwd()
    if not is_git_repository(current_path):
        logging.error("Not a git repository.")
        return

    repo = Repo(current_path)
    current_branch = get_current_branch(repo)
    main_branch = "main" if "main" in repo.heads else "master"

    if current_branch == main_branch:
        logging.info(f"You are already on the {main_branch} branch.")
        return

    logging.info(f"Comparing {current_branch} with {main_branch}...")
    file_diffs = compare_branches(repo, main_branch, current_branch)

    if not file_diffs:
        logging.info("No differences found.")
        return

    logging.info("\nAnalyzing changes in each file:")
    all_results = []
    
    with ThreadPoolExecutor() as executor:
        future_to_file = {executor.submit(process_with_ollama, diff, filename, get_file_context(filename)): filename for filename, diff in file_diffs.items()}
        for future in as_completed(future_to_file):
            filename = future_to_file[future]
            try:
                result = future.result()
                if result and result.strip() != "No issues found":
                    all_results.append(f"\nFile: {filename}\n{result}")
            except Exception as e:
                logging.error(f"Error processing {filename}: {e}")

    logging.info("\nOllama Analysis Report:")
    if all_results:
        logging.info("\n".join(all_results))
    else:
        logging.info("No issues found in any of the changed files.")

if __name__ == "__main__":
    main()