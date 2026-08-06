import ast

FORBIDDEN_CALL_NAMES = {
    "eval", "exec", "open", "__import__", "compile", "input",
    # str.format/format_map perform attribute+index traversal at runtime
    # (e.g. "{0.__self__.__globals__[os]}".format(x)), reaching real module
    # globals and builtins.os.environ without any dunder syntax in the
    # source and without a blocked call target other than format itself.
    "format", "format_map",
}
FORBIDDEN_NAME_PREFIXES = {"os", "sys", "subprocess", "socket", "shutil", "importlib"}

# Non-dunder reflection attributes on generators/coroutines/frames/tracebacks.
# A running generator can walk gi_frame -> f_back -> f_globals/f_builtins to
# reach a real module's __builtins__ and from there __import__("os"), escaping
# the SAFE_BUILTINS sandbox. None of these are dunders, so the dunder check
# below does not catch them.
FORBIDDEN_FRAME_ATTRS = {
    "gi_frame", "gi_code", "gi_yieldfrom", "cr_frame", "cr_code", "cr_await",
    "ag_frame", "ag_code", "f_back", "f_globals", "f_locals", "f_builtins",
    "f_code", "f_trace", "tb_frame", "tb_next", "co_consts", "func_globals",
}


def _is_dunder(name: str) -> bool:
    """Check if name is a dunder (starts and ends with __)."""
    return name.startswith("__") and name.endswith("__")


def validate_skill_source(source: str, expected_func_name: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, f"syntax error: {e}"

    func_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not any(f.name == expected_func_name for f in func_defs):
        return False, f"no function named '{expected_func_name}' found"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "imports are not allowed in generated skills"
        if isinstance(node, ast.Call):
            func_name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if func_name in FORBIDDEN_CALL_NAMES:
                return False, f"forbidden call: {func_name}"
        if isinstance(node, ast.Name):
            if _is_dunder(node.id):
                return False, f"forbidden reference: dunder attribute access ({node.id})"
            if node.id in FORBIDDEN_NAME_PREFIXES or node.id in FORBIDDEN_CALL_NAMES:
                return False, f"forbidden reference: {node.id}"
        if isinstance(node, ast.Attribute):
            if _is_dunder(node.attr):
                return False, f"forbidden reference: dunder attribute access ({node.attr})"
            if node.attr in FORBIDDEN_FRAME_ATTRS:
                return False, f"forbidden reference: frame/generator attribute ({node.attr})"
            if node.attr in FORBIDDEN_CALL_NAMES:
                return False, f"forbidden reference: {node.attr}"
            if isinstance(node.value, ast.Name):
                if node.value.id in FORBIDDEN_NAME_PREFIXES:
                    return False, f"forbidden reference: {node.value.id}"

    return True, "ok"
