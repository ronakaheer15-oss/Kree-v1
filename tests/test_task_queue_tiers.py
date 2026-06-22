import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kree.agent.task_queue import TaskQueue, TaskPriority, determine_tier_and_timeout

def test_determine_tier_and_timeout():
    # Tier 3
    t3, duration3 = determine_tier_and_timeout("build a full app in nodejs")
    assert t3 == 3
    assert duration3 == 1200.0

    # Tier 2
    t2, duration2 = determine_tier_and_timeout("write code helper script")
    assert t2 == 2
    assert duration2 == 600.0

    # Tier 1
    t1, duration1 = determine_tier_and_timeout("what is the weather today")
    assert t1 == 1
    assert duration1 == 300.0

    print("SUCCESS: determine_tier_and_timeout tests passed.")

if __name__ == "__main__":
    test_determine_tier_and_timeout()
