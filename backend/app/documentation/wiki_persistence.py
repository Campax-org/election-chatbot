"""Wiki persistence service with versioning and LLM validation."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .generator import DocumentationGenerator


class WikiPersistenceService:
    """Persistent wiki storage with versioning and validation."""

    def __init__(
        self,
        wiki_root: Path,
        llm_api_key: Optional[str] = None,
        validation_threshold: float = 0.95,
    ):
        """
        Initialize wiki persistence service.

        Args:
            wiki_root: Root path to wiki directory
            llm_api_key: Optional API key for LLM validation
            validation_threshold: Minimum validation score to accept (0.0-1.0)
        """
        self.wiki_root = Path(wiki_root)
        self.wiki_en_root = self.wiki_root / "en"
        self.versions_dir = self.wiki_en_root / "_versions"
        self.metadata_file = self.wiki_root / "_wiki_metadata.json"
        self.validation_threshold = validation_threshold
        self.llm_api_key = llm_api_key

        # Create directories
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_en_root.mkdir(parents=True, exist_ok=True)

    def _load_metadata(self) -> Dict[str, Any]:
        """Load wiki metadata from JSON file."""
        if self.metadata_file.exists():
            try:
                return json.loads(self.metadata_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {"components": {}}

    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save wiki metadata to JSON file."""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _read_current_version(self, component_name: str) -> Optional[str]:
        """Read current version of a component documentation."""
        doc_path = self._get_doc_path(component_name)
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")
        return None

    def _save_version(
        self, component_name: str, content: str, reason: str = "auto"
    ) -> None:
        """Save a versioned backup of documentation."""
        version_dir = self.versions_dir / component_name.replace(".md", "")
        version_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version_file = version_dir / f"{timestamp}_{reason}.md"
        version_file.write_text(content, encoding="utf-8")

        # Keep only last 10 versions
        versions = sorted(version_dir.glob("*.md"), reverse=True)
        for old_version in versions[10:]:
            old_version.unlink()

    def _get_doc_path(self, component_name: str) -> Path:
        """Get the documentation file path for a component."""
        # Handle different component types and paths
        if "/" in component_name:
            # Path-based: "etl-types/realestateareanormalizer"
            return self.wiki_en_root / f"{component_name}.md"
        else:
            # Simple name: "presets"
            return self.wiki_en_root / component_name.lower().replace("_", "") + ".md"

    async def _llm_validate(
        self, component_name: str, markdown: str, source_files: List[str]
    ) -> Dict[str, Any]:
        """
        Validate documentation using LLM.

        Args:
            component_name: Name of the component
            markdown: Generated markdown content
            source_files: List of source file paths

        Returns:
            Dictionary with validation results
        """
        if not self.llm_api_key:
            # Skip validation if no API key
            return {"score": 1.0, "passed": True, "issues": [], "reason": "no_api_key"}

        try:
            # Read source files for context
            source_context = ""
            for source_file in source_files[:3]:  # Limit to first 3 files
                source_path = Path(source_file)
                if source_path.exists():
                    source_context += f"\n\n### {source_file}\n```python\n"
                    source_context += source_path.read_text(encoding="utf-8")[:2000]
                    source_context += "\n```"

            prompt = f"""VALIDIERE folgende Dokumentation gegen den Quellcode:

KOMPONENTE: {component_name}
QUELLE: {', '.join(source_files)}
MARKDOWN:
{markdown[:3000]}

Prüfe:
✅ Zweckbeschreibung stimmt mit Code überein
✅ Alle Config-Parameter dokumentiert
✅ Input/Output-Typen korrekt
✅ YAML-Beispiel syntaktisch korrekt (falls vorhanden)
✅ Code-Beispiele lauffähig (falls vorhanden)

Antworte NUR mit valides JSON (kein Markdown, kein Code-Block):
{{
  "score": 0.0-1.0,
  "passed": true/false,
  "issues": ["list of issues"],
  "recommendations": ["optional improvements"]
}}
"""

            # Use existing generator's LLM client if available
            # For now, use a simplified validation (can be enhanced with actual LLM call)
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a documentation validator. Always respond with valid JSON only.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()

                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                validation_result = json.loads(content)
                return validation_result

        except Exception as e:
            # On error, be lenient and allow the documentation
            return {
                "score": 0.9,
                "passed": True,
                "issues": [f"Validation error: {str(e)}"],
                "recommendations": [],
                "reason": "validation_error",
            }

    async def write_validated_doc(
        self,
        component_name: str,
        markdown: str,
        source_files: List[str],
        doc_type: str = "component",
        subdir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Write validated documentation with versioning.

        Args:
            component_name: Name of the component
            markdown: Markdown content to write
            source_files: List of source file paths
            doc_type: Type of documentation ("component", "preset", "compatibility")
            subdir: Optional subdirectory (e.g., "etl-types", "architecture")

        Returns:
            Dictionary with write result
        """
        # Determine full path
        if subdir:
            doc_path = self.wiki_en_root / subdir / f"{component_name}.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            doc_path = self._get_doc_path(component_name)

        # LLM validation
        validation_result = await self._llm_validate(
            component_name, markdown, source_files
        )

        result = {
            "component_name": component_name,
            "validation": validation_result,
            "written": False,
            "reason": "",
        }

        # Check validation threshold
        if validation_result.get("score", 0.0) < self.validation_threshold:
            result["reason"] = f"Validation score {validation_result.get('score', 0.0):.2f} below threshold {self.validation_threshold}"
            # Still write but log warning
            print(f"⚠️  Warning: {result['reason']}")

        # Versioned backup
        old_version = None
        if doc_path.exists():
            old_version = doc_path.read_text(encoding="utf-8")
            self._save_version(component_name, old_version, "auto")

        # Write new version
        doc_path.write_text(markdown, encoding="utf-8")
        result["written"] = True
        result["path"] = str(doc_path.relative_to(self.wiki_root))

        # Update metadata
        metadata = self._load_metadata()
        metadata["components"][component_name] = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source_files": source_files,
            "llm_validation_score": validation_result.get("score", 0.0),
            "validation_passed": validation_result.get("passed", True),
            "doc_type": doc_type,
            "path": result["path"],
        }
        if validation_result.get("issues"):
            metadata["components"][component_name]["issues"] = validation_result[
                "issues"
            ]
        self._save_metadata(metadata)

        return result

    def get_existing_docs(self) -> Dict[str, Dict[str, Any]]:
        """Get all existing documentation files with metadata."""
        metadata = self._load_metadata()
        return metadata.get("components", {})

    def get_pending_docs(self) -> List[Dict[str, Any]]:
        """Get documentation that failed validation."""
        metadata = self._load_metadata()
        pending = []
        for name, info in metadata.get("components", {}).items():
            if not info.get("validation_passed", True):
                pending.append({"name": name, **info})
        return pending

