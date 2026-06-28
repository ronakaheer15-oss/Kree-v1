import sqlite3
import time
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from kree.core.runtime import APP_DATA_DIR
from kree.core.policy_engine import RiskTier

TRUST_DB_PATH = APP_DATA_DIR / "vault" / "trust_db.sqlite"

def _get_conn():
    TRUST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(TRUST_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS domains(
            domain TEXT PRIMARY KEY,
            success_count INTEGER DEFAULT 0,
            risk_count INTEGER DEFAULT 0,
            trust_score REAL DEFAULT 0.0,
            tier INTEGER DEFAULT 3,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            action TEXT,
            risk INTEGER,
            reason TEXT,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB on load
init_db()

def decay_trust():
    """
    Ages trust scores for domains that haven't been seen recently.
    Trust drops by 10% per day of inactivity after a 7-day grace period.
    """
    conn = _get_conn()
    cursor = conn.cursor()
    
    # 7 days grace period
    grace_cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("SELECT domain, last_seen, trust_score FROM domains WHERE last_seen < ?", (grace_cutoff,))
    rows = cursor.fetchall()
    
    for row in rows:
        last_seen = datetime.strptime(row['last_seen'], '%Y-%m-%d %H:%M:%S')
        days_inactive = (datetime.utcnow() - last_seen).days
        if days_inactive > 0:
            decay_factor = 0.9 ** days_inactive
            new_score = row['trust_score'] * decay_factor
            cursor.execute("UPDATE domains SET trust_score = ? WHERE domain = ?", (new_score, row['domain']))
            
    conn.commit()
    conn.close()


def record_event(domain: str, action: str, risk: RiskTier, reason: str, is_success: bool, is_high_risk_type: bool = False):
    """
    Records an event, logs it to history, and adjusts the weighted trust score.
    """
    conn = _get_conn()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO events(domain, action, risk, reason) 
        VALUES(?, ?, ?, ?)
    """, (domain, action, risk.value, reason))
    
    cursor.execute("SELECT * FROM domains WHERE domain = ?", (domain,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("""
            INSERT INTO domains(domain, success_count, risk_count, trust_score, tier, last_seen)
            VALUES(?, 0, 0, 0.0, 3, CURRENT_TIMESTAMP)
        """, (domain,))
        
    score_delta = 0.0
    if is_success:
        # High risk file types (like .exe) grant less trust on success to prevent trust farming.
        score_delta = +0.2 if is_high_risk_type else +1.0
        cursor.execute("UPDATE domains SET success_count = success_count + 1 WHERE domain = ?", (domain,))
    else:
        # Heavy penalty for failures/risks
        score_delta = -5.0
        cursor.execute("UPDATE domains SET risk_count = risk_count + 1 WHERE domain = ?", (domain,))
        
    cursor.execute("""
        UPDATE domains 
        SET trust_score = trust_score + ?, last_seen = CURRENT_TIMESTAMP 
        WHERE domain = ?
    """, (score_delta, domain))
    
    # Re-evaluate Tier (Dynamic Promotion)
    cursor.execute("SELECT trust_score, risk_count FROM domains WHERE domain = ?", (domain,))
    updated = cursor.fetchone()
    
    new_tier = 3 # UNKNOWN_WEB
    if updated['risk_count'] > 0 and updated['trust_score'] < -5:
        new_tier = 4 # HIGH_RISK
    elif updated['trust_score'] >= 10.0 and updated['risk_count'] == 0:
        new_tier = 2 # KNOWN_TRUSTED
        
    cursor.execute("UPDATE domains SET tier = ? WHERE domain = ?", (new_tier, domain))
    
    conn.commit()
    conn.close()

def get_domain_tier(domain: str) -> int:
    """Returns the dynamic tier for a domain."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT tier FROM domains WHERE domain = ?", (domain,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row['tier']
    return 3 # UNKNOWN_WEB default

# Perform decay check on module load
try:
    decay_trust()
except Exception:
    pass
