import ast

FORBIDDEN_CALL_NAMES = {"eval", "exec", "open", "__import__", "compile", "input"}
FORBIDDEN_NAME_PREFIXES = {"os", "sys", "subprocess", "socket", "shutil", "importlib"}


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
        if isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAME_PREFIXES or node.id in FORBIDDEN_CALL_NAMES):
            return False, f"forbidden reference: {node.id}"
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in FORBIDDEN_NAME_PREFIXES:
                return False, f"forbidden reference: {node.value.id}"

    return True, "ok"
