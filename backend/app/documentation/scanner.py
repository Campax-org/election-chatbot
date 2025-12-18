"""Component scanner for analyzing the scraper framework codebase."""

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ComponentInfo:
    """Information about a discovered component."""

    name: str
    type: str  # 'fetcher', 'extractor', 'validator', 'storage', 'enricher', etc.
    file_path: str
    class_name: str
    docstring: str | None = None
    methods: list[dict[str, Any]] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] | None = None
    source_code: str = ""
    last_modified: str = ""


class ComponentScanner:
    """Scans the scraper framework repository for components."""

    # Component type mappings based on directory structure
    COMPONENT_TYPES = {
        "fetchers": "fetcher",
        "extractors": "extractor",
        "validators": "validator",
        "storages": "storage",
        "enrichers": "enricher",
        "normalizers": "normalizer",
        "deduplicators": "deduplicator",
        "classifiers": "classifier",
        "notifiers": "notifier",
    }

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.scraper_framework_path = self.repo_path / "src" / "scraper_framework"
        self.components: list[ComponentInfo] = []

    def scan_all(self) -> list[ComponentInfo]:
        """Scan all components in the scraper framework."""
        self.components = []

        for dir_name, component_type in self.COMPONENT_TYPES.items():
            dir_path = self.scraper_framework_path / dir_name
            if dir_path.exists():
                self._scan_directory(dir_path, component_type)

        # Also scan contracts.py for data types
        contracts_path = self.scraper_framework_path / "contracts.py"
        if contracts_path.exists():
            self._scan_contracts(contracts_path)

        # Scan engine.py for main engine documentation
        engine_path = self.scraper_framework_path / "engine.py"
        if engine_path.exists():
            self._scan_engine(engine_path)

        # Scan special modules (presets.py, plugin_compatibility.py)
        special_components = self.scan_special_modules()
        self.components.extend(special_components)

        return self.components

    def _scan_directory(self, dir_path: Path, component_type: str) -> None:
        """Scan a directory for Python components."""
        for py_file in dir_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            if py_file.name == "__init__.py":
                continue

            self._scan_file(py_file, component_type)

    def _scan_file(self, file_path: Path, component_type: str) -> None:
        """Scan a Python file for class definitions."""
        try:
            source_code = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_code)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Skip private classes
                    if node.name.startswith("_"):
                        continue

                    # Extract class information
                    component = self._extract_class_info(
                        node, file_path, component_type, source_code
                    )
                    if component:
                        self.components.append(component)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Error scanning {file_path}: {e}")

    def _extract_class_info(
        self, node: ast.ClassDef, file_path: Path, component_type: str, source_code: str
    ) -> ComponentInfo | None:
        """Extract information from a class definition."""
        # Get base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(base.attr)

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get methods
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = {
                    "name": item.name,
                    "docstring": ast.get_docstring(item),
                    "args": [arg.arg for arg in item.args.args if arg.arg != "self"],
                    "is_async": False,
                }
                methods.append(method_info)
            elif isinstance(item, ast.AsyncFunctionDef):
                method_info = {
                    "name": item.name,
                    "docstring": ast.get_docstring(item),
                    "args": [arg.arg for arg in item.args.args if arg.arg != "self"],
                    "is_async": True,
                }
                methods.append(method_info)

        # Extract class source code
        class_source = ast.get_source_segment(source_code, node) or ""

        # Get file modification time
        stat = file_path.stat()
        last_modified = str(stat.st_mtime)

        # Generate a readable name from class name
        name = self._class_name_to_readable(node.name)

        return ComponentInfo(
            name=name,
            type=component_type,
            file_path=str(file_path.relative_to(self.repo_path)),
            class_name=node.name,
            docstring=docstring,
            methods=methods,
            base_classes=base_classes,
            source_code=class_source,
            last_modified=last_modified,
        )

    def _scan_contracts(self, contracts_path: Path) -> None:
        """Scan contracts.py for data type definitions."""
        try:
            source_code = contracts_path.read_text(encoding="utf-8")
            tree = ast.parse(source_code)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Look for Pydantic models (BaseModel subclasses)
                    base_names = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_names.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_names.append(base.attr)

                    if "BaseModel" in base_names or any(
                        "Config" in name or "Contract" in name for name in base_names
                    ):
                        component = self._extract_class_info(
                            node, contracts_path, "data_type", source_code
                        )
                        if component:
                            # Extract field definitions for data types
                            component.config_schema = self._extract_pydantic_fields(
                                node, source_code
                            )
                            self.components.append(component)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Error scanning contracts: {e}")

    def _scan_engine(self, engine_path: Path) -> None:
        """Scan engine.py for main engine documentation."""
        try:
            source_code = engine_path.read_text(encoding="utf-8")
            tree = ast.parse(source_code)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "ScraperEngine":
                    component = self._extract_class_info(
                        node, engine_path, "engine", source_code
                    )
                    if component:
                        self.components.append(component)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Error scanning engine: {e}")

    def _extract_pydantic_fields(
        self, node: ast.ClassDef, source_code: str
    ) -> dict[str, Any]:
        """Extract Pydantic field definitions from a class."""
        fields = {}

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                field_type = ast.get_source_segment(source_code, item.annotation) or "Any"

                # Get default value if present
                default = None
                if item.value:
                    default = ast.get_source_segment(source_code, item.value)

                fields[field_name] = {
                    "type": field_type,
                    "default": default,
                }

        return fields

    def _class_name_to_readable(self, class_name: str) -> str:
        """Convert CamelCase class name to readable format."""
        # Insert spaces before uppercase letters
        readable = re.sub(r"([A-Z])", r" \1", class_name).strip()
        return readable

    def get_components_by_type(self, component_type: str) -> list[ComponentInfo]:
        """Get all components of a specific type."""
        return [c for c in self.components if c.type == component_type]

    def get_component_by_name(self, name: str) -> ComponentInfo | None:
        """Get a component by its class name."""
        for component in self.components:
            if component.class_name == name:
                return component
        return None

    def get_changed_components(
        self, since_timestamp: float
    ) -> list[ComponentInfo]:
        """Get components that have changed since a given timestamp."""
        changed = []
        for component in self.components:
            try:
                if float(component.last_modified) > since_timestamp:
                    changed.append(component)
            except ValueError:
                pass
        return changed
