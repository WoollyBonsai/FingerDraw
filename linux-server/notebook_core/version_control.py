import os
from git import Repo

VAULT_DIR = os.path.join(os.path.dirname(__file__), "vault")

def init_repo():
    os.makedirs(VAULT_DIR, exist_ok=True)
    if not os.path.exists(os.path.join(VAULT_DIR, ".git")):
        repo = Repo.init(VAULT_DIR)
        # Create an initial commit
        readme_path = os.path.join(VAULT_DIR, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Notebook Vault\n\nThis directory contains your markdown notes.")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit: Vault created")
        return repo
    return Repo(VAULT_DIR)

def commit_file(file_name: str, message: str = None):
    """Commits a specific file to the vault's local git repository."""
    repo = Repo(VAULT_DIR)
    repo.index.add([file_name])
    if message is None:
        message = f"Auto-commit: Update {file_name}"
    repo.index.commit(message)
