import subprocess

def run_git_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

with open("git_output.txt", "w") as f:
    f.write("Git Status:\n")
    f.write(run_git_command(["git", "status"]))
    f.write("\nGit Remotes:\n")
    f.write(run_git_command(["git", "remote", "-v"]))
    f.write("\nGit Branch:\n")
    f.write(run_git_command(["git", "branch", "--show-current"]))
