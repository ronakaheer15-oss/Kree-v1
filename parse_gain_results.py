import re

scores = []
with open(r"C:\Users\HP\.gemini\antigravity\brain\bc156d27-4ab9-4588-9489-c1adc7976763\.system_generated\tasks\task-423.log", "r") as f:
    for line in f:
        if "[WAKE SCORE]" in line:
            match = re.search(r"'hey_jarvis':\s*(?:np\.float32\()?([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)", line)
            if match:
                scores.append(float(match.group(1)))

if scores:
    scores.sort(reverse=True)
    peak = scores[0]
    top_20 = scores[:20]
    avg = sum(top_20) / len(top_20)
    gt_08 = sum(1 for s in scores if s > 0.08)
    gt_20 = sum(1 for s in scores if s > 0.20)
    gt_50 = sum(1 for s in scores if s > 0.50)
    
    print(f"Peak confidence: {peak:.5f}")
    print(f"Average confidence (top 20): {avg:.5f}")
    print(f"Scores > 0.08: {gt_08}")
    print(f"Scores > 0.20: {gt_20}")
    print(f"Scores > 0.50: {gt_50}")
else:
    print("No scores parsed.")
