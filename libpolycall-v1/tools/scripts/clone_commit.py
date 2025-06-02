import os
import subprocess
import argparse

def get_commit_range(repo_path, start_commit=None, end_commit=None, count=10):
    """Retrieve a specific range of commit hashes and messages from the repository."""
    if start_commit and end_commit:
        # Get commits between start and end (inclusive)
        cmd = ["git", "log", "--pretty=format:%h %s", f"{end_commit}..{start_commit}"]
    elif start_commit:
        # Get count commits before start_commit
        cmd = ["git", "log", "--pretty=format:%h %s", f"{start_commit}~{count}..{start_commit}"]
    elif end_commit:
        # Get count commits up to end_commit
        cmd = ["git", "log", "--pretty=format:%h %s", f"-{count}", end_commit]
    else:
        # Get most recent count commits
        cmd = ["git", "log", "--pretty=format:%h %s", f"-{count}"]
    
    result = subprocess.run(
        cmd,
        cwd=repo_path,
        stdout=subprocess.PIPE,
        text=True,
        stderr=subprocess.PIPE
    )
    
    if result.returncode != 0:
        print(f"Error getting commits: {result.stderr}")
        return []
    
    return result.stdout.splitlines()

def clone_single_commit(repo_path, commit_hash, branch_name=None):
    """Clone a specific commit to a new branch."""
    if not branch_name:
        # Generate branch name based on commit if not provided
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%s", commit_hash],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            text=True,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            print(f"Error getting commit message: {result.stderr}")
            return False
            
        commit_message = result.stdout
        safe_message = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in commit_message[:40])
        branch_name = f"checkout-{commit_hash[:8]}-{safe_message}"
    
    # Check if branch already exists
    result = subprocess.run(
        ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    if result.returncode == 0:
        print(f"Branch {branch_name} already exists. Choose a different name or delete the existing branch.")
        return False
    
    # Create and checkout new branch at the specified commit
    try:
        subprocess.run(
            ["git", "checkout", "-b", branch_name, commit_hash],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Created and checked out branch '{branch_name}' at commit {commit_hash}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating branch from commit {commit_hash}: {e.stderr}")
        return False

def clone_specific_commits(repo_path, output_dir, start_commit=None, end_commit=None, count=10):
    """Clone a range of commits into separate directories for analysis."""
    # Get the specified range of commits
    commits = get_commit_range(repo_path, start_commit, end_commit, count)
    
    for commit in commits:
        try:
            commit_hash, commit_message = commit.split(" ", 1)
        except ValueError:
            print(f"Warning: Could not parse commit '{commit}', skipping")
            continue
            
        # Sanitize the commit message for directory naming
        safe_message = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in commit_message[:40])
        commit_dir = os.path.join(output_dir, f"commit-{commit_hash}-{safe_message}")
        
        if os.path.exists(commit_dir):
            print(f"Directory already exists for {commit_hash}, skipping")
            continue
            
        os.makedirs(commit_dir, exist_ok=True)
        
        # Create a worktree for this commit
        try:
            subprocess.run(
                ["git", "worktree", "add", "--detach", commit_dir, commit_hash],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error creating worktree for {commit_hash}: {e.stderr}")
            continue
        
        print(f"Created worktree for {commit_hash} - {commit_message} at {commit_dir}")
    
    return len(commits)

def rename_branch(repo_path, old_name, new_name):
    """Rename a git branch."""
    try:
        subprocess.run(
            ["git", "branch", "-m", old_name, new_name],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Renamed branch '{old_name}' to '{new_name}'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error renaming branch: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Clone specific commits or ranges.")
    parser.add_argument("repo_path", help="Path to the local Git repository")
    parser.add_argument("--output-dir", help="Directory to output the cloned commits (for multiple commits)")
    parser.add_argument("--start", help="Starting commit hash")
    parser.add_argument("--end", help="Ending commit hash (for commit range)")
    parser.add_argument("--count", help="Number of commits to analyze", type=int, default=10)
    parser.add_argument("--commit", help="Specific commit hash to check out into a new branch")
    parser.add_argument("--branch-name", help="Name for the new branch when checking out a specific commit")
    parser.add_argument("--rename", nargs=2, metavar=('OLD_BRANCH', 'NEW_BRANCH'), help="Rename a branch")
    
    args = parser.parse_args()
    
    # Handle branch renaming if requested
    if args.rename:
        old_branch, new_branch = args.rename
        rename_branch(args.repo_path, old_branch, new_branch)
        return
    
    # Handle specific commit checkout
    if args.commit:
        clone_single_commit(args.repo_path, args.commit, args.branch_name)
        return
    
    # For multiple commits analysis, we need an output directory
    if not args.output_dir:
        if not (args.start or args.end):
            print("Error: For multiple commits analysis, please specify an output directory")
            return
        args.output_dir = "./commit_analysis"
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Clone the specified commits
    num_cloned = clone_specific_commits(
        args.repo_path, 
        args.output_dir, 
        args.start, 
        args.end, 
        args.count
    )
    print(f"Successfully cloned {num_cloned} commits")

if __name__ == "__main__":
    main()
