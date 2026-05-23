from datetime import datetime


def test_time_trigger_fires_once_per_matching_minute(monkeypatch, tmp_path):
    from kree.core import trigger_engine

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 5, 23, 14, 30, 10)

    calls = []
    engine = trigger_engine.TriggerEngine(lambda action, bypass_voice=False: calls.append(action))
    engine.memory_path = tmp_path / "smart_triggers.json"
    monkeypatch.setattr(trigger_engine, "datetime", FixedDateTime)

    trigger = {
        "id": "daily",
        "name": "Daily",
        "type": "time",
        "condition": {"time": "14:30"},
        "action": {"type": "speak", "payload": "hello"},
        "cooldown_seconds": 0,
        "last_fired": 0,
    }

    engine._evaluate_trigger(trigger, now=1_000)
    engine._evaluate_trigger(trigger, now=1_005)

    assert calls == [{"type": "speak", "payload": "hello"}]
    assert trigger["last_fired_minute"] == "2026-05-23 14:30"
