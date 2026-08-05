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
