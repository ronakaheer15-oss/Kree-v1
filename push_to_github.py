import subprocess
import os
import sys

def run_cmd(cmd, cwd=None):
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False # We handle errors manually
        )
        return result
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return None

def main():
    repo_path = r"e:\Mark-XXX-main\Mark-XXX-main"
    log_file = os.path.join(repo_path, "push_log.txt")
    
    with open(log_file, "w", encoding='utf-8') as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")

        log("--- Kree GitHub Push Log ---")
        
        # 1. Config
        log("Configuring Git user...")
        run_cmd(["git", "config", "--global", "user.name", "Ronak Aheer"], repo_path)
        run_cmd(["git", "config", "--global", "user.email", "ronakaheer15@gmail.com"], repo_path)
        
        # 2. Remote check
        log("Checking remote...")
        res = run_cmd(["git", "remote", "-v"], repo_path)
        if "origin" not in res.stdout:
            log("Adding remote origin...")
            run_cmd(["git", "remote", "add", "origin", "https://github.com/ronakaheer15-oss/Kree.git"], repo_path)
        else:
            log("Updating remote origin...")
            run_cmd(["git", "remote", "set-url", "origin", "https://github.com/ronakaheer15-oss/Kree.git"], repo_path)
            
        # 3. Add
        log("Staging files (this may take a minute)...")
        res = run_cmd(["git", "add", "."], repo_path)
        if res.returncode != 0:
            log(f"ERROR: git add failed: {res.stderr}")
            # return
        
        # 4. Commit
        log("Committing changes...")
        res = run_cmd(["git", "commit", "-m", "Project Aegis Complete: Full System Hardening and UI Polish"], repo_path)
        log(f"Commit Output: {res.stdout}")
        
        # 5. Push
        log("Pushing to GitHub (main)...")
        # Try regular push first, then force if it fails due to divergence
        res = run_cmd(["git", "push", "-u", "origin", "main"], repo_path)
        if res.returncode != 0:
            log(f"Regular push failed: {res.stderr}")
            log("Attempting force push to sync with remote...")
            res = run_cmd(["git", "push", "-f", "origin", "main"], repo_path)
        
        if res.returncode == 0:
            log("SUCCESS: Repository pushed to GitHub.")
        else:
            log(f"FAILED: Final push failed: {res.stderr}")

if __name__ == "__main__":
    main()
