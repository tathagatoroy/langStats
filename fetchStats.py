import requests
import os
import json
from collections import defaultdict

def getGithubToken():
    """
    Attempts to get the GitHub Personal Access Token (PAT) from:
    1. Environment variable (GITHUB_TOKEN)
    2. A config file named 'config.json' that contains the path to the token file

    Returns:
        str: The GitHub Personal Access Token.
    Raises:
        ValueError: If the token is not found in either location.
    """
    # First try environment variable
    token = os.getenv('GITHUB_TOKEN')
    if token:
        print("Using GitHub token from environment variable 'GITHUB_TOKEN'.")
        return token

    # Then try config file
    configFile = 'config.json'
    if os.path.exists(configFile):
        try:
            with open(configFile, 'r') as f:
                config = json.load(f)
                tokenPath = config.get('githubTokenPath')
                if tokenPath and os.path.exists(tokenPath):
                    try:
                        with open(tokenPath, 'r') as tokenFile:
                            token = tokenFile.read().strip()
                            if token:
                                print(f"Using GitHub token from file: {tokenPath}")
                                return token
                    except Exception as e:
                        print(f"Error reading token file '{tokenPath}': {e}")
                else:
                    print(f"Token path not found in config or file does not exist: {tokenPath}")
        except json.JSONDecodeError:
            print(f"Error reading '{configFile}'. Make sure it's valid JSON.")
        except Exception as e:
            print(f"An error occurred while reading '{configFile}': {e}")

    raise ValueError("GitHub Personal Access Token not found. "
                     "Please either:\n"
                     "1. Set the 'GITHUB_TOKEN' environment variable, or\n"
                     "2. Create a 'config.json' file with the path to your token file:\n"
                     '   {\n'
                     '     "githubTokenPath": "/path/to/your/token/file"\n'
                     '   }')

def getUserPublicRepos(userName, token):
    """
    Fetches all public repositories for a given GitHub user.

    Args:
        userName (str): The GitHub username.
        token (str): The GitHub Personal Access Token.

    Returns:
        list: A list of repository dictionaries.
    """
    repos = []
    pageNum = 1
    perPage = 100  # Max per_page is 100 for GitHub API
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    print(f"Fetching public repositories for user: {userName}...")
    while True:
        url = f"https://api.github.com/users/{userName}/repos?type=public&page={pageNum}&per_page={perPage}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            currentRepos = response.json()
            if not currentRepos:
                break  # No more repositories
            repos.extend(currentRepos)
            pageNum += 1
        else:
            print(f"Error fetching repositories: {response.status_code} - {response.text}")
            break
    print(f"Found {len(repos)} public repositories.")
    return repos

def getRepoLanguages(owner, repoName, token):
    """
    Fetches the language breakdown for a single repository.

    Args:
        owner (str): The repository owner's username.
        repoName (str): The name of the repository.
        token (str): The GitHub Personal Access Token.

    Returns:
        dict: A dictionary where keys are language names and values are byte counts.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    url = f"https://api.github.com/repos/{owner}/{repoName}/languages"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Warning: Could not fetch languages for {owner}/{repoName}. "
              f"Status code: {response.status_code} - {response.text}")
        return {}

def getDefaultUsername():
    """
    Gets the default username from config file if available.
    
    Returns:
        str: The default username or None if not found.
    """
    configFile = 'config.json'
    if os.path.exists(configFile):
        try:
            with open(configFile, 'r') as f:
                config = json.load(f)
                return config.get('defaultUsername')
        except Exception as e:
            print(f"Error reading config file: {e}")
    return None

def main():
    try:
        githubToken = getGithubToken()
    except ValueError as e:
        print(e)
        print("\nPlease generate a Personal Access Token (PAT) on GitHub:")
        print("1. Go to your GitHub Settings -> Developer settings -> Personal access tokens -> Tokens (classic) or Fine-grained tokens.")
        print("2. Click 'Generate new token'.")
        print("3. Give it a descriptive name (e.g., 'RepoLanguageStats').")
        print("4. For 'Tokens (classic)', grant at least the 'public_repo' scope if you only need public repos, or 'repo' for all repos. For 'Fine-grained tokens', grant 'Read' access to 'Contents' for selected repositories or all public repositories.")
        print("5. Copy the generated token to a file.")
        print("6. Create a 'config.json' file with the path to your token file:")
        print('   ```json')
        print('   {')
        print('     "githubTokenPath": "/path/to/your/token/file"')
        print('   }')
        print('   ```')
        return

    # Try to get default username from config
    defaultUsername = getDefaultUsername()
    if defaultUsername:
        print(f"Using default username from config: {defaultUsername}")
        userName = input(f"Enter the GitHub username (press Enter to use {defaultUsername}): ").strip()
        if not userName:
            userName = defaultUsername
    else:
        userName = input("Enter the GitHub username: ").strip()

    if not userName:
        print("Username cannot be empty. Exiting.")
        return

    repositories = getUserPublicRepos(userName, githubToken)

    if not repositories:
        print(f"No public repositories found for user '{userName}' or an error occurred.")
        return

    totalLanguageBreakdown = defaultdict(int)
    repoCount = 0

    print("\nAnalyzing languages for each repository...")
    for repo in repositories:
        repoName = repo['name']
        ownerLogin = repo['owner']['login'] # Use owner from repo object in case it's an org
        print(f"  Fetching languages for {ownerLogin}/{repoName}...")
        languages = getRepoLanguages(ownerLogin, repoName, githubToken)
        
        if languages:
            repoCount += 1 # Only count repos for which we got language data
            for lang, bytesCount in languages.items():
                totalLanguageBreakdown[lang] += bytesCount

    if not totalLanguageBreakdown:
        print("No language data found for any of the public repositories.")
        return

    print(f"\n--- Language Breakdown for all {repoCount} Public Repositories of '{userName}' ---")

    # Calculate total bytes for percentage calculation
    totalBytes = sum(totalLanguageBreakdown.values())

    if totalBytes == 0:
        print("No code bytes found across all repositories.")
        return

    # Sort languages by bytes in descending order
    sortedLanguages = sorted(totalLanguageBreakdown.items(), key=lambda item: item[1], reverse=True)

    for lang, bytesCount in sortedLanguages:
        percentage = (bytesCount / totalBytes) * 100
        # Convert bytes to KB, MB, or GB for readability
        if bytesCount < 1024:
            sizeStr = f"{bytesCount} B"
        elif bytesCount < 1024**2:
            sizeStr = f"{bytesCount / 1024:.2f} KB"
        elif bytesCount < 1024**3:
            sizeStr = f"{bytesCount / (1024**2):.2f} MB"
        else:
            sizeStr = f"{bytesCount / (1024**3):.2f} GB"
        print(f"{lang}: {percentage:.2f}% ({sizeStr})")

    print("\n-----------------------------------------------------------")

if __name__ == "__main__":
    main()