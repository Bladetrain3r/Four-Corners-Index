import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = {"eurostat", "eia", "ember", "ecb", "worldbank"}


def _imports(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
    return names


def test_no_adapter_imports_another_adapter():
    for name in ADAPTERS:
        seen = _imports(ROOT / "pipeline" / f"{name}.py")
        others = {f"pipeline.{o}" for o in ADAPTERS - {name}}
        assert not seen & others, f"{name} imports another adapter: {seen & others}"


def test_modules_stay_under_400_lines():
    for f in list((ROOT / "pipeline").glob("*.py")) + list((ROOT / "checks").glob("*.py")):
        assert len(f.read_text().splitlines()) < 400, f"{f.name} is 400 lines or more"


def test_pipeline_is_stdlib_only():
    third_party = {"requests", "pandas", "numpy", "yaml", "jsonschema", "openpyxl"}
    for f in (ROOT / "pipeline").glob("*.py"):
        used = {i.split(".")[0] for i in _imports(f)}
        assert not used & third_party, f"{f.name} imports {used & third_party}"
