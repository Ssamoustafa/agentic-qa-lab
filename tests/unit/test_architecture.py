from __future__ import annotations

import ast
from pathlib import Path

_DOMAIN_DIRECTORY = Path(__file__).parents[2] / "src" / "agentic_qa" / "domain"
_FORBIDDEN_IMPORT_PREFIXES = (
    "agentic_qa.application",
    "agentic_qa.infrastructure",
    "agentic_qa.interfaces",
    "anthropic",
    "boto3",
    "github",
    "httpx",
    "openai",
    "playwright",
    "requests",
    "sqlalchemy",
)


def _imported_modules(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_domain_does_not_depend_on_outer_layers_or_vendor_sdks() -> None:
    imported_modules = set().union(
        *(_imported_modules(source_path) for source_path in _DOMAIN_DIRECTORY.glob("*.py"))
    )

    forbidden_modules = {
        module for module in imported_modules if module.startswith(_FORBIDDEN_IMPORT_PREFIXES)
    }

    assert not forbidden_modules
