import subprocess

def run_git_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr

with open("git_push_debug.txt", "w", encoding='utf-8') as f:
    # Set config
    run_git_command(["git", "config", "--global", "user.name", "Ronak Aheer"])
    run_git_command(["git", "config", "--global", "user.email", "ronakaheer15@gmail.com"])
    
    # Try adding remote (ignore error if exists)
    stdout, stderr = run_git_command(["git", "remote", "add", "origin", "https://github.com/ronakaheer15-oss/Kree.git"])
    f.write(f"Remote Add stdout: {stdout}\nstderr: {stderr}\n")
    
    # Git add
    stdout, stderr = run_git_command(["git", "add", "."])
    f.write(f"Add stdout: {stdout}\nstderr: {stderr}\n")
    
    # Git commit
    stdout, stderr = run_git_command(["git", "commit", "-m", "Manual Push from AI"])
    f.write(f"Commit stdout: {stdout}\nstderr: {stderr}\n")
    
    # Git push
    stdout, stderr = run_git_command(["git", "push", "-u", "origin", "main"])
    f.write(f"Push stdout: {stdout}\nstderr: {stderr}\n")
