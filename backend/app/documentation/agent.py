"""Main documentation agent that orchestrates scanning and generation."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .coverage_report import CoverageReportService
from .generator import DocumentationGenerator
from .scanner import ComponentInfo, ComponentScanner
from .wiki_persistence import WikiPersistenceService

logger = logging.getLogger(__name__)


class DocumentationAgent:
    """Main agent that orchestrates documentation scanning and generation."""

    SUPPORTED_LANGUAGES = ["de", "en"]

    def __init__(
        self,
        repo_path: str,
        wiki_path: str,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        llm_model: str = "gpt-4o-mini",
    ):
        self.repo_path = Path(repo_path)
        self.wiki_path = Path(wiki_path)
        self.scanner = ComponentScanner(repo_path)
        self.generator = DocumentationGenerator(
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
        )
        self.persistence = WikiPersistenceService(
            wiki_root=Path(wiki_path),
            llm_api_key=llm_api_key,
        )
        self.coverage_service = CoverageReportService(
            scanner=self.scanner,
            persistence=self.persistence,
            repo_path=self.repo_path,
        )
        self.metadata_path = self.wiki_path / "_metadata.json"

    def _load_metadata(self) -> dict[str, Any]:
        """Load metadata from _metadata.json."""
        if self.metadata_path.exists():
            try:
                return json.loads(self.metadata_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "last_scan": None,
            "last_full_generation": None,
            "components": {},
            "sync_status": {},
        }

    def _save_metadata(self, metadata: dict[str, Any]) -> None:
        """Save metadata to _metadata.json."""
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    async def scan_and_generate_all(self, force: bool = False) -> dict[str, Any]:
        """Scan all components and generate documentation for all languages."""
        metadata = self._load_metadata()
        results = {
            "scanned": 0,
            "generated": 0,
            "errors": [],
            "components": [],
        }

        # Scan components
        print("Scanning components...")
        components = self.scanner.scan_all()
        results["scanned"] = len(components)
        print(f"Found {len(components)} components")

        # Determine which components need documentation
        components_to_document = []
        if force:
            components_to_document = components
        else:
            last_scan = metadata.get("last_scan")
            if last_scan:
                try:
                    last_scan_ts = float(last_scan)
                    components_to_document = self.scanner.get_changed_components(
                        last_scan_ts
                    )
                except ValueError:
                    components_to_document = components
            else:
                components_to_document = components

        print(f"Generating documentation for {len(components_to_document)} components...")

        # Generate documentation for each component in all languages
        for component in components_to_document:
            try:
                # For architecture components (presets, compatibility), generate specialized docs
                if component.type == "architecture":
                    # Generate in English only for now
                    for lang in ["en"]:
                        write_result = await self._write_component_doc(component, {}, lang)
                        if write_result.get("written"):
                            results["generated"] += 1
                            results["components"].append(component.class_name)
                            print(f"  Generated: {component.class_name}")
                        else:
                            results["errors"].append(
                                f"Validation failed for {component.class_name}: {write_result.get('reason', 'unknown')}"
                            )
                else:
                    docs = await self.generator.generate_all_languages(component)

                    # Write documentation files for each language using persistence service
                    for lang, doc in docs.items():
                        write_result = await self._write_component_doc(component, doc, lang)
                        if not write_result.get("written"):
                            results["errors"].append(
                                f"Failed to write {component.class_name} ({lang}): {write_result.get('reason', 'unknown')}"
                            )

                    # Update metadata (now handled by persistence service)
                    results["generated"] += 1
                    results["components"].append(component.class_name)
                    print(f"  Generated: {component.class_name}")

            except Exception as e:
                error_msg = f"Error generating docs for {component.class_name}: {e}"
                results["errors"].append(error_msg)
                print(f"  Error: {error_msg}")

        # Generate overview pages
        print("Generating overview pages...")
        await self._generate_overview_pages(components)

        # Generate index pages
        print("Generating index pages...")
        self._generate_index_pages(components)

        # Update metadata
        metadata["last_scan"] = str(datetime.now(timezone.utc).timestamp())
        metadata["last_full_generation"] = datetime.now(timezone.utc).isoformat()
        self._save_metadata(metadata)

        return results

    async def _write_component_doc(
        self, component: ComponentInfo, doc: dict[str, Any], language: str
    ) -> dict[str, Any]:
        """Write a component documentation file with validation."""
        # Determine the directory based on component type
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
            "architecture": "architecture",
        }

        subdir = type_dir_map.get(component.type, "")

        # Generate markdown content
        if component.type == "architecture" and component.class_name == "PIPELINE_PRESETS":
            content = await self.generator.generate_preset_documentation(component, language)
        elif component.type == "architecture" and component.class_name == "PLUGIN_FIELD_REQUIREMENTS":
            content = await self.generator.generate_compatibility_documentation(component, language)
        else:
            content = self.generator.generate_markdown_file(doc)

        # Use persistence service for validated writing
        result = await self.persistence.write_validated_doc(
            component_name=component.class_name.lower(),
            markdown=content,
            source_files=[component.file_path],
            doc_type=component.type,
            subdir=subdir if subdir else None,
        )

        return result

    async def _generate_overview_pages(self, components: list[ComponentInfo]) -> None:
        """Generate overview pages for each language."""
        for lang in self.SUPPORTED_LANGUAGES:
            overview_content = await self.generator.generate_overview(components, lang)

            # Write architecture.md
            arch_path = self.wiki_path / lang / "architecture.md"
            arch_path.parent.mkdir(parents=True, exist_ok=True)
            arch_path.write_text(overview_content, encoding="utf-8")

    def _generate_index_pages(self, components: list[ComponentInfo]) -> None:
        """Generate index pages for each language."""
        # Group components by type
        by_type: dict[str, list[ComponentInfo]] = {}
        for comp in components:
            if comp.type not in by_type:
                by_type[comp.type] = []
            by_type[comp.type].append(comp)

        for lang in self.SUPPORTED_LANGUAGES:
            self._generate_main_index(lang, by_type)
            self._generate_section_indexes(lang, by_type)

    def _generate_main_index(
        self, language: str, by_type: dict[str, list[ComponentInfo]]
    ) -> None:
        """Generate the main index.md file."""
        if language == "de":
            content = """# Scraper Framework Dokumentation

Willkommen zur automatisch generierten Dokumentation des Scraper-Frameworks.

## Inhaltsverzeichnis

- [Architektur](architecture.md) - Systemübersicht und ETL-Pipeline
- [ETL-Typen](etl-types/) - Extractors, Enrichers, Normalizers, etc.
- [Scrapers](scrapers/) - Verfügbare Fetcher und Datenquellen
- [Validatoren](validators/) - Datenvalidierung
- [Datentypen](data-types/) - Definierte Datenmodelle
- [Quellen](sources/) - Storage-Backends

## Komponenten-Übersicht

"""
        else:
            content = """# Scraper Framework Documentation

Welcome to the automatically generated documentation for the Scraper Framework.

## Table of Contents

- [Architecture](architecture.md) - System overview and ETL pipeline
- [ETL Types](etl-types/) - Extractors, Enrichers, Normalizers, etc.
- [Scrapers](scrapers/) - Available fetchers and data sources
- [Validators](validators/) - Data validation
- [Data Types](data-types/) - Defined data models
- [Sources](sources/) - Storage backends

## Components Overview

"""

        # Add component counts
        type_names = self.generator.COMPONENT_TYPE_NAMES.get(language, {})
        for comp_type, comps in sorted(by_type.items()):
            type_name = type_names.get(comp_type, comp_type)
            content += f"- **{type_name}**: {len(comps)} components\n"

        # Add last updated timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if language == "de":
            content += f"\n---\n*Zuletzt aktualisiert: {timestamp}*\n"
        else:
            content += f"\n---\n*Last updated: {timestamp}*\n"

        index_path = self.wiki_path / language / "index.md"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(content, encoding="utf-8")

    def _generate_section_indexes(
        self, language: str, by_type: dict[str, list[ComponentInfo]]
    ) -> None:
        """Generate index files for each section."""
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
        }

        # Group by directory
        by_dir: dict[str, list[ComponentInfo]] = {}
        for comp_type, comps in by_type.items():
            dir_name = type_dir_map.get(comp_type)
            if dir_name:
                if dir_name not in by_dir:
                    by_dir[dir_name] = []
                by_dir[dir_name].extend(comps)

        type_names = self.generator.COMPONENT_TYPE_NAMES.get(language, {})

        for dir_name, comps in by_dir.items():
            if language == "de":
                content = f"# {dir_name.replace('-', ' ').title()}\n\n"
                content += "## Verfügbare Komponenten\n\n"
            else:
                content = f"# {dir_name.replace('-', ' ').title()}\n\n"
                content += "## Available Components\n\n"

            for comp in sorted(comps, key=lambda c: c.class_name):
                type_name = type_names.get(comp.type, comp.type)
                content += f"- [{comp.class_name}]({comp.class_name.lower()}.md) - {type_name}\n"

            index_path = self.wiki_path / language / dir_name / "index.md"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(content, encoding="utf-8")

    async def process_git_changes(self, changed_files: list[str]) -> dict[str, Any]:
        """Process changes from a git webhook."""
        results = {
            "processed": 0,
            "regenerated": [],
            "errors": [],
        }

        # Filter for Python files in the scraper framework
        scraper_files = [
            f
            for f in changed_files
            if f.startswith("src/scraper_framework/") and f.endswith(".py")
        ]

        if not scraper_files:
            return results

        # Rescan components
        components = self.scanner.scan_all()

        # Find components that match changed files
        for component in components:
            if component.file_path in scraper_files:
                try:
                    docs = await self.generator.generate_all_languages(component)
                    for lang, doc in docs.items():
                        self._write_component_doc(component, doc, lang)
                    results["regenerated"].append(component.class_name)
                    results["processed"] += 1
                except Exception as e:
                    results["errors"].append(f"{component.class_name}: {e}")

        # Update metadata
        metadata = self._load_metadata()
        metadata["last_scan"] = str(datetime.now(timezone.utc).timestamp())
        self._save_metadata(metadata)

        return results

    async def run_full_sync(self, force: bool = False, component_changes: dict = None) -> dict[str, Any]:
        """
        Run full synchronization with validation and persistence.
        
        Args:
            force: If True, regenerate all documentation regardless of changes.
            component_changes: Dict with changed components {"fetchers": ["new_fetcher.py"], ...}
            
        Returns:
            Dictionary with sync results including coverage information.
        """
        logger.info(f"📚 Dokumentations-Sync gestartet (force={force})")
        
        # Wenn force=False und component_changes vorhanden:
        # Nur diese Komponenten dokumentieren
        if not force and component_changes:
            logger.info(f"⚡ Inkrementelles Update für: {component_changes}")
            await self._update_changed_components(component_changes)
            await self._update_changelog(component_changes)
            scan_results = {
                "scanned": sum(len(files) for files in component_changes.values()),
                "generated": sum(len(files) for files in component_changes.values()),
                "errors": [],
                "components": list(component_changes.keys()),
            }
        else:
            # Vollständiger Scan (wie bisher)
            scan_results = await self.scan_and_generate_all(force=force)
        
        # Generate coverage report
        coverage_report = await self.coverage_service.generate_coverage_report()
        
        return {
            **scan_results,
            "coverage": coverage_report,
            "summary": {
                "total_components": coverage_report["total_components"],
                "documented": coverage_report["documented"],
                "coverage_percent": coverage_report["coverage_percent"],
                "undocumented_count": coverage_report["undocumented_count"],
            },
        }
    
    async def _update_changed_components(self, component_changes: dict) -> None:
        """Dokumentiere nur geänderte Komponenten"""
        for comp_type, files in component_changes.items():
            logger.info(f"  Updating {comp_type}: {files}")
            # Hier müsste die Logik implementiert werden, um spezifische Komponenten zu scannen
            # Für jetzt verwenden wir den bestehenden Scanner
            components = self.scanner.scan_all()
            # Filtere Komponenten nach Typ und Dateinamen
            filtered_components = [
                comp for comp in components 
                if comp.get("type") == comp_type and comp.get("file_name") in files
            ]
            if filtered_components:
                await self.generator.generate_all(filtered_components)
    
    async def _update_changelog(self, component_changes: dict) -> None:
        """Aktualisiere CHANGELOG.md mit neuen Komponenten"""
        from pathlib import Path
        from datetime import datetime
        
        changelog_path = Path(self.wiki_path) / "CHANGELOG.md"
        
        # Formatiere Änderungen
        changes_text = "\n".join([
            f"- **{comp_type}**: {', '.join(files)}"
            for comp_type, files in component_changes.items()
        ])
        
        # Lese bestehenden Changelog
        if changelog_path.exists():
            existing = changelog_path.read_text()
        else:
            existing = "# Changelog\n\n"
        
        # Füge neuen Entry hinzu (oben)
        today = datetime.now().strftime("%Y-%m-%d")
        new_entry = f"""## [{today}]
{changes_text}


"""
        
        updated = existing.replace("# Changelog\n\n", f"# Changelog\n\n{new_entry}")
        changelog_path.write_text(updated)
        logger.info(f"✅ CHANGELOG.md aktualisiert")
    
    async def ensure_all_enrichers_documented(self) -> dict:
        """
        Verifikation: Stelle sicher, dass ALLE Enrichers dokumentiert sind.
        Falls welche fehlen, generiere sie automatisch.
        
        Rückgabe:
        {
            "total_enrichers": X,
            "documented": X,
            "missing": [],
            "generated": [...]
        }
        """
        logger.info("🔍 Enrichers-Completeness Check...")
        
        # Scanne alle Enricher-Klassen
        # Enrichers sind in plugins/enrichers/ Verzeichnis
        enrichers_path = Path(self.repo_path) / "src" / "scraper_framework" / "plugins" / "enrichers"
        
        # Verwende den Scanner, um Enrichers zu finden
        all_components = self.scanner.scan_all()
        enricher_components = [c for c in all_components if c.get("type") == "enricher"]
        
        # Prüfe welche bereits dokumentiert sind
        wiki_docs_de = list(Path(self.wiki_path) / "de" / "etl-types").glob("*enricher*.md")
        wiki_docs_en = list(Path(self.wiki_path) / "en" / "etl-types").glob("*enricher*.md")
        documented_names = {doc.stem for doc in wiki_docs_de + wiki_docs_en}
        
        total = len(enricher_components)
        missing = []
        generated = []
        
        for enricher in enricher_components:
            class_name = enricher.get("class_name", "").lower()
            file_name = enricher.get("file_name", "").lower().replace('.py', '')
            
            # Suche nach dokumentierter Datei (mit unterschiedlichen Naming-Varianten)
            found = False
            for doc_name in documented_names:
                if class_name in doc_name or doc_name in class_name or file_name in doc_name:
                    found = True
                    break
            
            if not found:
                logger.warning(f"  ❌ Fehlend dokumentiert: {enricher.get('class_name')}")
                missing.append(enricher)
                
                # Auto-generiere Dokumentation
                try:
                    # Generiere für beide Sprachen
                    for language in self.SUPPORTED_LANGUAGES:
                        await self.generator.generate_component_documentation(enricher, language)
                    generated.append(enricher.get("class_name"))
                    logger.info(f"  ✅ Generiert: {enricher.get('class_name')}")
                except Exception as e:
                    logger.error(f"  ❌ Fehler bei Generation: {e}")
        
        result = {
            "total_enrichers": total,
            "documented": total - len(missing) + len(generated),
            "missing": [e.get("class_name") for e in missing],
            "generated": generated,
            "status": "complete" if not missing else "incomplete"
        }
        
        logger.info(f"✅ Enrichers-Check Ergebnis: {result}")
        return result

    def get_sync_status(self) -> dict[str, Any]:
        """Get the synchronization status between languages."""
        metadata = self._load_metadata()
        status = {
            "last_scan": metadata.get("last_scan"),
            "last_full_generation": metadata.get("last_full_generation"),
            "components": {},
        }

        for comp_name, comp_data in metadata.get("components", {}).items():
            status["components"][comp_name] = {
                "languages": comp_data.get("languages", []),
                "last_generated": comp_data.get("last_generated"),
                "synced": len(comp_data.get("languages", [])) == len(
                    self.SUPPORTED_LANGUAGES
                ),
            }

        return status


async def run_documentation_agent(
    repo_path: str | None = None,
    wiki_path: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run the documentation agent as a standalone function."""
    if repo_path is None:
        repo_path = os.getenv("REPO_PATH", os.getcwd())
    if wiki_path is None:
        wiki_path = os.getenv("WIKI_PATH", os.path.join(os.getcwd(), "wiki"))

    agent = DocumentationAgent(
        repo_path=repo_path,
        wiki_path=wiki_path,
        llm_api_key=os.getenv("OPENAI_API_KEY"),
    )

    return await agent.scan_and_generate_all(force=force)


if __name__ == "__main__":
    # Run as standalone script
    import sys

    force = "--force" in sys.argv
    result = asyncio.run(run_documentation_agent(force=force))
    print(json.dumps(result, indent=2))
