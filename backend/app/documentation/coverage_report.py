"""Coverage report service for documentation."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .scanner import ComponentInfo, ComponentScanner
from .wiki_persistence import WikiPersistenceService


class CoverageReportService:
    """Generate coverage reports and identify gaps in documentation."""

    def __init__(
        self,
        scanner: ComponentScanner,
        persistence: WikiPersistenceService,
        repo_path: Path,
    ):
        """
        Initialize coverage report service.

        Args:
            scanner: ComponentScanner instance
            persistence: WikiPersistenceService instance
            repo_path: Repository root path
        """
        self.scanner = scanner
        self.persistence = persistence
        self.repo_path = Path(repo_path)

    async def generate_coverage_report(self) -> Dict[str, Any]:
        """
        Generate a coverage report showing documented vs undocumented components.

        Returns:
            Dictionary with coverage statistics and lists
        """
        # Scan all components
        all_components = self.scanner.scan_all()

        # Get documented components
        documented_components = self.persistence.get_existing_docs()

        # Categorize components
        documented_names = set(documented_components.keys())
        all_names = {c.class_name: c for c in all_components}

        # Find undocumented
        undocumented = []
        for comp in all_components:
            # Try different name variations
            names_to_check = [
                comp.class_name,
                comp.class_name.lower(),
                self._get_wiki_filename(comp),
            ]
            if not any(name in documented_names for name in names_to_check):
                undocumented.append(
                    {
                        "class_name": comp.class_name,
                        "type": comp.type,
                        "file_path": comp.file_path,
                        "name": comp.name,
                    }
                )

        # Find stale docs (older than source files)
        stale_docs = await self._find_stale_docs(all_components, documented_components)

        # Calculate coverage
        total = len(all_components)
        documented = len(documented_names)
        coverage_percent = (documented / total * 100) if total > 0 else 0.0

        # Group by type
        by_type: Dict[str, Dict[str, Any]] = {}
        for comp in all_components:
            comp_type = comp.type
            if comp_type not in by_type:
                by_type[comp_type] = {
                    "total": 0,
                    "documented": 0,
                    "undocumented": [],
                }
            by_type[comp_type]["total"] += 1
            wiki_name = self._get_wiki_filename(comp)
            if wiki_name in documented_names:
                by_type[comp_type]["documented"] += 1
            else:
                by_type[comp_type]["undocumented"].append(
                    {
                        "class_name": comp.class_name,
                        "file_path": comp.file_path,
                    }
                )

        return {
            "total_components": total,
            "documented": documented,
            "undocumented_count": len(undocumented),
            "coverage_percent": round(coverage_percent, 2),
            "undocumented": undocumented[:50],  # Limit to first 50
            "stale_docs": stale_docs,
            "by_type": by_type,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def _get_wiki_filename(self, component: ComponentInfo) -> str:
        """Get the expected wiki filename for a component."""
        # Map component type to wiki subdirectory
        type_dir_map = {
            "fetcher": "scrapers",
            "extractor": "etl-types",
            "validator": "validators",
            "storage": "sources",
            "enricher": "etl-types",
            "normalizer": "etl-types",
            "deduplicator": "etl-types",
            "classifier": "etl-types",
            "notifier": "etl-types",
            "data_type": "data-types",
            "engine": "",
        }

        subdir = type_dir_map.get(component.type, "")
        class_name_lower = component.class_name.lower()

        if subdir:
            return f"{subdir}/{class_name_lower}"
        else:
            return class_name_lower

    async def _find_stale_docs(
        self,
        all_components: List[ComponentInfo],
        documented_components: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Find documentation that is older than the source files.

        Args:
            all_components: List of all scanned components
            documented_components: Dictionary of documented components with metadata

        Returns:
            List of stale documentation entries
        """
        stale = []

        for comp in all_components:
            wiki_name = self._get_wiki_filename(comp)
            doc_info = documented_components.get(wiki_name)

            if not doc_info:
                continue

            # Check source file modification time
            source_path = self.repo_path / comp.file_path
            if not source_path.exists():
                continue

            source_mtime = source_path.stat().st_mtime

            # Check doc last updated time
            doc_updated = doc_info.get("last_updated")
            if not doc_updated:
                stale.append(
                    {
                        "component": comp.class_name,
                        "reason": "no_last_updated",
                        "source_file": comp.file_path,
                    }
                )
                continue

            try:
                from dateutil import parser

                doc_updated_ts = parser.parse(doc_updated).timestamp()

                # Doc is stale if source is newer
                if source_mtime > doc_updated_ts:
                    stale.append(
                        {
                            "component": comp.class_name,
                            "reason": "source_newer",
                            "source_file": comp.file_path,
                            "source_mtime": datetime.fromtimestamp(
                                source_mtime, timezone.utc
                            ).isoformat(),
                            "doc_updated": doc_updated,
                        }
                    )
            except Exception:
                # Can't parse date, consider stale
                stale.append(
                    {
                        "component": comp.class_name,
                        "reason": "date_parse_error",
                        "source_file": comp.file_path,
                    }
                )

        return stale

    def get_missing_docs_by_type(self, component_type: str) -> List[str]:
        """
        Get list of undocumented components of a specific type.

        Args:
            component_type: Type of components to check

        Returns:
            List of undocumented component class names
        """
        all_components = self.scanner.scan_all()
        documented = self.persistence.get_existing_docs()

        missing = []
        for comp in all_components:
            if comp.type == component_type:
                wiki_name = self._get_wiki_filename(comp)
                if wiki_name not in documented:
                    missing.append(comp.class_name)

        return missing

