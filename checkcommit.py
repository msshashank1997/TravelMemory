import os
import requests
import subprocess
import sys
import time

# Configuration
REPO_OWNER = "msshashank1997"  # Replace with your GitHub username
REPO_NAME = "TravelMemory"         # Replace with your repository name
GITHUB_TOKEN = "PAT"                    # Add your GitHub token if needed for private repos
LAST_COMMIT_FILE = "last_commit.txt"
DEPLOY_SCRIPT = os.path.join(os.path.dirname(__file__), "deploy.sh")

def get_latest_commit():
    """Get the latest commit hash from GitHub API"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        commits = response.json()
        if commits and len(commits) > 0:
            return commits[0]["sha"]
        return None
    except requests.RequestException as e:
        print(f"Error fetching commits: {e}")
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

def deploy():
    """Run the deployment script"""
    try:
        subprocess.run(["bash", DEPLOY_SCRIPT], check=True)
        print("Deployment successful!")
        return True
    except subprocess.SubprocessError as e:
        print(f"Deployment failed: {e}")
        return False

def main():
    """Main function to check for new commits and deploy if needed"""
    latest_commit = get_latest_commit()
    if not latest_commit:
        print("Could not get latest commit.")
        sys.exit(1)
    
    stored_commit = get_stored_commit()
    
    # If no stored commit or different commit, deploy
    if not stored_commit or stored_commit != latest_commit:
        print(f"New commit detected: {latest_commit}")
        if deploy():
            store_commit(latest_commit)
    else:
        print("No new commits detected.")

if __name__ == "__main__":
    main()
