import builtins
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

SAFE_BUILTINS = {
    name: getattr(builtins, name)
    for name in [
        "len", "range", "str", "int", "float", "bool", "list", "dict", "set",
        "tuple", "sum", "min", "max", "sorted", "enumerate", "zip", "map",
        "filter", "next", "abs", "round", "isinstance", "ValueError", "TypeError",
        "StopIteration",
    ]
}


class SkillExecutionError(Exception):
    pass


def compile_skill(source: str, func_name: str):
    namespace = {"__builtins__": SAFE_BUILTINS}
    try:
        exec(source, namespace)
    except Exception as e:
        raise SkillExecutionError(f"failed to compile skill: {e}")
    func = namespace.get(func_name)
    if func is None:
        raise SkillExecutionError(f"function '{func_name}' not found after exec")
    return func


def run_with_timeout(func, args=(), kwargs=None, timeout_seconds: float = 5.0):
    kwargs = kwargs or {}
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            raise SkillExecutionError(f"skill execution exceeded {timeout_seconds}s timeout")
        except Exception as e:
            raise SkillExecutionError(f"skill execution failed: {e}")
    finally:
        executor.shutdown(wait=False)
