import pytest
from app.sandbox import compile_skill, run_with_timeout, SkillExecutionError

GOOD_SOURCE = '''
def double(x):
    return x * 2
'''

SLOW_SOURCE = '''
def slow():
    while True:
        pass
'''

def test_compile_and_run_valid_skill():
    func = compile_skill(GOOD_SOURCE, "double")
    result = run_with_timeout(func, args=(21,))
    assert result == 42

def test_compiled_skill_has_no_import_builtin():
    func = compile_skill(GOOD_SOURCE, "double")
    assert "__import__" not in func.__globals__["__builtins__"]

def test_run_with_timeout_raises_on_infinite_loop():
    func = compile_skill(SLOW_SOURCE, "slow")
    with pytest.raises(SkillExecutionError):
        run_with_timeout(func, timeout_seconds=0.5)

def test_daemon_thread_exits_cleanly():
    """Regression test: verify timeout doesn't block subsequent operations."""
    func = compile_skill(SLOW_SOURCE, "slow")
    # First timeout should complete
    with pytest.raises(SkillExecutionError) as exc_info:
        run_with_timeout(func, timeout_seconds=0.1)
    assert "exceeded" in str(exc_info.value)

    # Second normal operation should work immediately (daemon thread doesn't block)
    func2 = compile_skill(GOOD_SOURCE, "double")
    result = run_with_timeout(func2, args=(21,), timeout_seconds=5.0)
    assert result == 42

def test_safe_builtins_isolation_between_skills():
    """Regression test: verify SAFE_BUILTINS is not shared/corrupted between skills."""
    # Skill A attempts to mutate __builtins__
    skill_a = '''
def poison():
    __builtins__["len"] = lambda x: "poisoned"
    return "done"
'''
    func_a = compile_skill(skill_a, "poison")
    result_a = run_with_timeout(func_a, timeout_seconds=5.0)
    assert result_a == "done"

    # Skill B should see untouched len (not poisoned)
    skill_b = '''
def check_len():
    return len([1, 2, 3])
'''
    func_b = compile_skill(skill_b, "check_len")
    result_b = run_with_timeout(func_b, timeout_seconds=5.0)
    assert result_b == 3  # Should be 3, not "poisoned"
