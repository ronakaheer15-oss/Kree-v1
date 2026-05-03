def test_get_queue_returns_queue_instance():
    from kree.agent.task_queue import get_queue
    q = get_queue()
    assert q is not None


def test_get_queue_is_singleton():
    from kree.agent.task_queue import get_queue
    assert get_queue() is get_queue()
