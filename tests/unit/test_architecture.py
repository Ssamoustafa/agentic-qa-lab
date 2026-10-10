from __future__ import annotations

import ast
from pathlib import Path

import pytest

_PACKAGE = Path(__file__).parents[2] / "src" / "agentic_qa"
_VENDOR_SDKS = (
    "anthropic",
    "boto3",
    "github",
    "httpx",
    "openai",
    "playwright",
    "requests",
    "sqlalchemy",
)
_OUTER_LAYERS = {
    "domain": ("agentic_qa.application", "agentic_qa.infrastructure", "agentic_qa.interfaces"),
    "application": ("agentic_qa.infrastructure", "agentic_qa.interfaces"),
}


def _imported_modules(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layers_do_not_depend_on_outer_layers_or_vendor_sdks(layer: str) -> None:
    forbidden = (*_OUTER_LAYERS[layer], *_VENDOR_SDKS)
    sources = list((_PACKAGE / layer).rglob("*.py"))

    violations = {
        f"{source.relative_to(_PACKAGE)} imports {module}"
        for source in sources
        for module in _imported_modules(source)
        if module.startswith(forbidden)
    }

    assert sources
    assert not violations


def test_domain_does_not_touch_the_filesystem_or_network() -> None:
    forbidden = ("pathlib", "socket", "subprocess", "shutil", "os", "urllib.request")
    sources = list((_PACKAGE / "domain").rglob("*.py"))

    violations = {
        f"{source.name} imports {module}"
        for source in sources
        for module in _imported_modules(source)
        if module in forbidden
    }

    assert not violations
