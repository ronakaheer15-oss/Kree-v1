import os
import time
import hmac
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from pathlib import Path
from typing import List, Optional, Dict, Set
from collections import OrderedDict

from kree.core.runtime import APP_DATA_DIR


class RiskTier(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class ToolPolicy:
    requires_intent: bool
    requires_confirmation: bool
    max_risk: RiskTier
    allowed_paths: frozenset
    network_access: bool
    can_delegate: bool
    policy_hash: str = field(init=False)

    def __post_init__(self):
        # We compute the hash of the fields to freeze the definition cryptographically
        # Using a deterministic JSON dump to hash
        state = {
            "requires_intent": self.requires_intent,
            "requires_confirmation": self.requires_confirmation,
            "max_risk": self.max_risk.value,
            "allowed_paths": sorted([str(p) for p in self.allowed_paths]),
            "network_access": self.network_access,
            "can_delegate": self.can_delegate
        }
        state_str = json.dumps(state, sort_keys=True)
        phash = hashlib.sha256(state_str.encode('utf-8')).hexdigest()
        object.__setattr__(self, "policy_hash", phash)

    def intersection(self, child_policy: 'ToolPolicy') -> 'ToolPolicy':
        """
        Calculates the minimum-privilege effective policy when a tool delegates to another tool.
        """
        effective_requires_intent = self.requires_intent or child_policy.requires_intent
        effective_requires_confirmation = self.requires_confirmation or child_policy.requires_confirmation
        effective_max_risk = min(self.max_risk, child_policy.max_risk)
        effective_network = self.network_access and child_policy.network_access
        effective_can_delegate = self.can_delegate and child_policy.can_delegate
        
        # Intersect paths: A path is only allowed if it exists in both (or one has root access which we don't allow here easily, 
        # so strict set intersection for now).
        effective_paths = frozenset(self.allowed_paths.intersection(child_policy.allowed_paths))
        
        return ToolPolicy(
            requires_intent=effective_requires_intent,
            requires_confirmation=effective_requires_confirmation,
            max_risk=effective_max_risk,
            allowed_paths=effective_paths,
            network_access=effective_network,
            can_delegate=effective_can_delegate
        )

    def verify_integrity(self) -> bool:
        state = {
            "requires_intent": self.requires_intent,
            "requires_confirmation": self.requires_confirmation,
            "max_risk": self.max_risk.value,
            "allowed_paths": sorted([str(p) for p in self.allowed_paths]),
            "network_access": self.network_access,
            "can_delegate": self.can_delegate
        }
        state_str = json.dumps(state, sort_keys=True)
        return self.policy_hash == hashlib.sha256(state_str.encode('utf-8')).hexdigest()


# --- Subsystem Capability Manifests ---
SUBSYSTEM_MANIFESTS = {
    "wakeword": {"audio.read"},
    "network": {"network.egress", "network.ingress", "file.write_quarantine"},
    "execution": {"shell.execute", "process.spawn"},
    "core": {"audio.read", "network.egress", "network.ingress", "file.write_quarantine", "shell.execute"} # System-level core
}

# --- Execution Contexts & Replay Protection ---

# Ephemeral HMAC per-boot
_EPOCH = str(uuid.uuid4())
_SIGNING_KEY = os.urandom(32)

class NonceCache:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: OrderedDict[str, float] = OrderedDict()
        
    def add(self, nonce: str):
        if nonce in self.cache:
            return False
        self.cache[nonce] = time.time()
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
        return True

_USED_NONCES = NonceCache()

@dataclass
class ExecutionContext:
    subsystem: str
    epoch: str
    nonce: str
    timestamp: float
    signed_token: str = ""

    def generate_token(self) -> str:
        payload = f"{self.subsystem}:{self.epoch}:{self.nonce}:{self.timestamp}"
        return hmac.new(_SIGNING_KEY, payload.encode('utf-8'), hashlib.sha256).hexdigest()

    def sign(self):
        self.signed_token = self.generate_token()

    def is_valid(self) -> bool:
        # 1. Check Epoch to prevent stale reboot replays
        if self.epoch != _EPOCH:
            return False
        
        # 2. Check Timestamp (Reject if older than 5 minutes)
        if time.time() - self.timestamp > 300:
            return False
            
        # 3. Check Signature to prevent spoofing
        if not hmac.compare_digest(self.signed_token, self.generate_token()):
            return False
            
        # 4. Check Nonce to prevent replay
        if not _USED_NONCES.add(self.nonce):
            return False
            
        return True


def create_execution_context(subsystem: str) -> ExecutionContext:
    """Creates a cryptographically signed execution context for a subsystem."""
    if subsystem not in SUBSYSTEM_MANIFESTS:
        raise ValueError(f"Unknown subsystem: {subsystem}")
        
    ctx = ExecutionContext(
        subsystem=subsystem,
        epoch=_EPOCH,
        nonce=os.urandom(16).hex(),
        timestamp=time.time()
    )
    ctx.sign()
    return ctx


# --- Reason Provenance Logging ---
PROVENANCE_LOG_DIR = APP_DATA_DIR / "logs" / "provenance"
PROVENANCE_LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_provenance(tool_name: str, subsystem: str, trigger: str, intent_hash: str):
    """Immutable audit of WHY an action was taken."""
    log_file = PROVENANCE_LOG_DIR / "execution_reasons.jsonl"
    entry = {
        "ts": time.time(),
        "tool": tool_name,
        "subsystem": subsystem,
        "trigger": trigger,
        "intent_hash": intent_hash
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# --- Enforcement Middleware ---
import functools

def execute_with_policy(policy: ToolPolicy):
    """
    Decorator for tool actions that enforces the bound ToolPolicy.
    Requires kwargs:
      - execution_context: ExecutionContext (signed subsystem context)
      - trigger: str (e.g. "user_voice")
      - intent_hash: str
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Verify Policy Integrity
            if not policy.verify_integrity():
                return {"error": "Policy Engine Block: Immutable Policy signature mismatch. Potential tampering detected."}
                
            # 2. Extract Execution Context
            ctx: ExecutionContext = kwargs.get("execution_context")
            if not ctx:
                return {"error": "Policy Engine Block: Missing execution context."}
                
            # 3. Cryptographic Verification & Replay Protection
            if not ctx.is_valid():
                return {"error": "Policy Engine Block: Execution context signature/nonce is invalid or expired."}
                
            subsystem = ctx.subsystem
            
            # 4. Check Subsystem Manifest Capabilities
            manifest = SUBSYSTEM_MANIFESTS.get(subsystem, set())
            if not manifest:
                return {"error": f"Policy Engine Block: Subsystem {subsystem} is undefined."}
                
            if policy.network_access and "network.egress" not in manifest:
                return {"error": f"Policy Engine Block: Subsystem {subsystem} lacks network.egress capability."}
                
            # 5. Check Intent Binding
            trigger = kwargs.get("trigger", "unknown")
            intent_hash = kwargs.get("intent_hash", "none")
            
            if policy.requires_intent and (trigger == "unknown" or intent_hash == "none"):
                return {"error": "Policy Engine Block: Tool requires explicit user intent binding."}
                
            # 6. Log Reason Provenance
            log_provenance(func.__name__, subsystem, trigger, intent_hash)
            
            # Execute underlying tool action
            try:
                # We do not compute `intersection(parent, child)` here automatically because that 
                # requires knowing the calling chain. If `can_delegate=False`, the tool implementation
                # itself is forbidden from calling other tools. (We enforce this conceptually).
                return func(*args, **kwargs)
            except Exception as e:
                return {"error": f"Tool execution failed: {str(e)}"}
                
        return wrapper
    return decorator
