import subprocess
import os
import sys

def run_cmd(cmd, cwd=None):
    print(f"Running: {' '.join(cmd)}")
    try:
        # Use shell=True to fix Windows executable resolving problems
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True,
            check=False
        )
        return result
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return None

def main():
    # Use parent.parent since script is inside scripts/
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_file = os.path.join(repo_path, "logs", "push_log.txt")
    os.makedirs(os.path.join(repo_path, "logs"), exist_ok=True)
    
    with open(log_file, "w", encoding='utf-8') as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")

        log("--- Kree GitHub Push Engine Start ---")
        
        # 1. Config
        log("Configuring Git user...")
        run_cmd(["git", "config", "--global", "user.name", '"Ronak Aheer"'], repo_path)
        run_cmd(["git", "config", "--global", "user.email", '"ronakaheer15@gmail.com"'], repo_path)
        
        # 2. Remote check
        log("Checking remote...")
        res = run_cmd(["git", "remote", "-v"], repo_path)
        if "origin" not in res.stdout:
            log("Adding remote origin...")
            run_cmd(["git", "remote", "add", "origin", "https://github.com/ronakaheer15-oss/Kree.git"], repo_path)
        else:
            log("Updating remote origin...")
            run_cmd(["git", "remote", "set-url", "origin", "https://github.com/ronakaheer15-oss/Kree.git"], repo_path)
            
        # 3. Synchronize with Remote to prevent divegence
        log("Fetching remote state...")
        run_cmd(["git", "fetch", "origin", "main"], repo_path)
        
        # 4. Add
        log("Staging files (cleaning up Git index)...")
        res = run_cmd(["git", "add", ".", "--all"], repo_path)
        if res and res.returncode != 0:
            log(f"ERROR: git add failed: {res.stderr}")
        
        # 5. Commit
        log("Committing changes...")
        res = run_cmd(["git", "commit", "-m", '"Production Readiness: Project structure optimized, heavy binaries ignored, initialization bug fixes"'], repo_path)
        log(f"Commit Output: {res.stdout if res else ''}")
        
        # 6. Push
        log("Pushing to GitHub (main)...")
        res = run_cmd(["git", "push", "origin", "main"], repo_path)
        if res and res.returncode != 0:
            log(f"Regular push failed: {res.stderr}")
            log("Attempting hard sync push (allowing updates)...")
            res = run_cmd(["git", "push", "origin", "main", "--force"], repo_path)
        
        if res and res.returncode == 0:
            log("SUCCESS: Repository pushed to GitHub securely.")
        else:
            log(f"FAILED: Final push failed: {res.stderr if res else 'Unknown error'}")

if __name__ == "__main__":
    main()
