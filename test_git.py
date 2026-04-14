import subprocess
out = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
print("STDOUT:", out.stdout)
print("STDERR:", out.stderr)
print("CODE:", out.returncode)
