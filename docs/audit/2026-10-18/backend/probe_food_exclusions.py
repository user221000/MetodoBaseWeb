"""Executes the original filtering loop with synthetic catalog data only.

Does not import the app, generate nutrition plans, access a DB, or use network.
"""
import ast
import copy
import json
from pathlib import Path

source = Path(__file__).resolve().parents[4] / "web/routes/planes.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
function = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "_do_generar_plan")
loop = next(node for node in ast.walk(function)
            if isinstance(node, ast.For)
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Attribute)
            and isinstance(node.iter.func.value, ast.Name)
            and node.iter.func.value.id == "categorias_local")
original = {"proteina": ["synthetic_protein_a", "synthetic_protein_b"],
            "carbs": ["synthetic_carb_a"]}
excluded = set(original["proteina"])
filtered = copy.deepcopy(original)
compiled = compile(ast.Module(body=[loop], type_ignores=[]), str(source), "exec")
exec(compiled, {"categorias_local": filtered, "excluidos_cliente": excluded})
result = {
    "scope": "Original filtering loop only; synthetic catalog; no final plan generated",
    "source_file": "web/routes/planes.py",
    "source_line": loop.lineno,
    "all_items_in_category_excluded": True,
    "category_after_filtering": filtered["proteina"],
    "excluded_items_remain_available": bool(set(filtered["proteina"]) & excluded),
}
assert result["excluded_items_remain_available"]
print(json.dumps(result, indent=2))
