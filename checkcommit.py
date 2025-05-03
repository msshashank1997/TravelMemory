#!/usr/bin/env python3

import os
import requests
import sys
import time

# Configuration
REPO_OWNER = "msshashank1997"  # Replace with your GitHub username
REPO_NAME = "TravelMemory"     # Replace with your repository name
# Get token from environment variable or use None
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
LAST_COMMIT_FILE = "last_commit.txt"

def get_latest_commit():
    """Get the latest commit hash from GitHub API"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    # Only add Authorization if we have a valid token (not a placeholder)
    #if GITHUB_TOKEN and GITHUB_TOKEN != "PAT":
        #headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    try:
        print(f"Fetching commits from {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        commits = response.json()
        if commits and len(commits) > 0:
            return commits[0]["sha"]
        return None
    except requests.RequestException as e:
        print(f"Error fetching commits: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None

def get_stored_commit():
    """Get the stored commit hash from file"""
    if not os.path.exists(LAST_COMMIT_FILE):
        return None
    
    with open(LAST_COMMIT_FILE, "r") as f:
        return f.read().strip()

def store_commit(commit_hash):
    """Store the commit hash to a file"""
    with open(LAST_COMMIT_FILE, "w") as f:
        f.write(commit_hash)

def main():
    """Main function to check for new commits"""
    latest_commit = get_latest_commit()
    if not latest_commit:
        print("Could not get latest commit.")
        sys.exit(1)
    
    stored_commit = get_stored_commit()
    
    # If no stored commit or different commit, report new commit
    if not stored_commit or stored_commit != latest_commit:
        print(f"New commit detected: {latest_commit}")
        store_commit(latest_commit)
        return True
    else:
        print("No new commits detected.")
        return False

if __name__ == "__main__":
    result = main()
    # Exit with appropriate status code for automation
    sys.exit(0 if result else 1)
