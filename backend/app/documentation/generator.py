"""Documentation generator using LLM for intelligent descriptions."""

import json
import os
from typing import Any

import httpx

from .scanner import ComponentInfo


class DocumentationGenerator:
    """Generates documentation using LLM for intelligent descriptions."""

    SUPPORTED_LANGUAGES = ["de", "en"]

    # Language-specific templates
    LANGUAGE_INSTRUCTIONS = {
        "de": "Schreibe die Antwort auf Deutsch. Verwende eine klare, technische Sprache.",
        "en": "Write the response in English. Use clear, technical language.",
    }

    COMPONENT_TYPE_NAMES = {
        "de": {
            "fetcher": "Fetcher (Datenabruf)",
            "extractor": "Extractor (Datenextraktion)",
            "validator": "Validator (Datenvalidierung)",
            "storage": "Storage (Datenspeicherung)",
            "enricher": "Enricher (Datenanreicherung)",
            "normalizer": "Normalizer (Datennormalisierung)",
            "deduplicator": "Deduplicator (Duplikaterkennung)",
            "classifier": "Classifier (Datenklassifizierung)",
            "notifier": "Notifier (Benachrichtigung)",
            "data_type": "Datentyp",
            "engine": "Engine (Hauptmodul)",
        },
        "en": {
            "fetcher": "Fetcher (Data Retrieval)",
            "extractor": "Extractor (Data Extraction)",
            "validator": "Validator (Data Validation)",
            "storage": "Storage (Data Persistence)",
            "enricher": "Enricher (Data Enrichment)",
            "normalizer": "Normalizer (Data Normalization)",
            "deduplicator": "Deduplicator (Duplicate Detection)",
            "classifier": "Classifier (Data Classification)",
            "notifier": "Notifier (Notifications)",
            "data_type": "Data Type",
            "engine": "Engine (Main Module)",
        },
    }

    def __init__(
        self,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        llm_model: str = "gpt-4o-mini",
    ):
        self.llm_base_url = llm_base_url or os.getenv(
            "LLM_BASE_URL", "https://api.openai.com/v1"
        )
        self.llm_api_key = llm_api_key or os.getenv("OPENAI_API_KEY", "")
        self.llm_model = llm_model

    async def generate_component_documentation(
        self, component: ComponentInfo, language: str = "de"
    ) -> dict[str, Any]:
        """Generate documentation for a single component in the specified language."""
        if language not in self.SUPPORTED_LANGUAGES:
            language = "de"

        prompt = self._build_component_prompt(component, language)
        description = await self._call_llm(prompt)

        return {
            "name": component.name,
            "class_name": component.class_name,
            "type": component.type,
            "type_name": self.COMPONENT_TYPE_NAMES.get(language, {}).get(
                component.type, component.type
            ),
            "file_path": component.file_path,
            "description": description,
            "docstring": component.docstring,
            "methods": component.methods,
            "base_classes": component.base_classes,
            "config_schema": component.config_schema,
            "language": language,
        }

    async def generate_all_languages(
        self, component: ComponentInfo
    ) -> dict[str, dict[str, Any]]:
        """Generate documentation for a component in all supported languages."""
        docs = {}
        for lang in self.SUPPORTED_LANGUAGES:
            docs[lang] = await self.generate_component_documentation(component, lang)
        return docs

    def _build_component_prompt(self, component: ComponentInfo, language: str) -> str:
        """Build the LLM prompt for generating component documentation."""
        type_name = self.COMPONENT_TYPE_NAMES.get(language, {}).get(
            component.type, component.type
        )
        lang_instruction = self.LANGUAGE_INSTRUCTIONS.get(
            language, self.LANGUAGE_INSTRUCTIONS["de"]
        )

        # Truncate source code if too long
        source_code = component.source_code
        if len(source_code) > 3000:
            source_code = source_code[:3000] + "\n... (truncated)"

        if language == "de":
            prompt = f"""Analysiere diesen {type_name}-Code aus einem Scraper-Framework und erstelle eine strukturierte Dokumentation.

Klassenname: {component.class_name}
Dateipfad: {component.file_path}
Basisklassen: {', '.join(component.base_classes) if component.base_classes else 'Keine'}
Vorhandener Docstring: {component.docstring or 'Keiner'}

Quellcode:
```python
{source_code}
```

Erstelle eine Dokumentation mit folgender Struktur:

## Beschreibung
[Eine klare, verständliche Beschreibung was diese Komponente macht]

## Verwendung
[Wann und wie wird diese Komponente verwendet]

## Konfiguration
[Welche Konfigurationsoptionen gibt es]

## Beispiel
[Ein kurzes Beispiel zur Verwendung, falls sinnvoll]

{lang_instruction}"""
        else:
            prompt = f"""Analyze this {type_name} code from a scraper framework and create structured documentation.

Class name: {component.class_name}
File path: {component.file_path}
Base classes: {', '.join(component.base_classes) if component.base_classes else 'None'}
Existing docstring: {component.docstring or 'None'}

Source code:
```python
{source_code}
```

Create documentation with the following structure:

## Description
[A clear, understandable description of what this component does]

## Usage
[When and how this component is used]

## Configuration
[What configuration options are available]

## Example
[A short usage example, if applicable]

{lang_instruction}"""

        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API to generate documentation."""
        if not self.llm_api_key:
            return self._generate_fallback_description(prompt)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.llm_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.llm_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a technical documentation writer for a Python scraper framework. Write clear, concise documentation.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1500,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    print(f"LLM API error: {response.status_code} - {response.text}")
                    return self._generate_fallback_description(prompt)

        except Exception as e:
            print(f"LLM API call failed: {e}")
            return self._generate_fallback_description(prompt)

    def _generate_fallback_description(self, prompt: str) -> str:
        """Generate a basic description when LLM is unavailable."""
        # Extract class name from prompt
        if "Klassenname:" in prompt:
            lines = prompt.split("\n")
            for line in lines:
                if "Klassenname:" in line:
                    class_name = line.split(":")[-1].strip()
                    return f"## Beschreibung\nDokumentation für {class_name}. (Automatisch generiert - LLM nicht verfügbar)\n\n## Verwendung\nSiehe Quellcode für Details.\n\n## Konfiguration\nSiehe Klassenattribute.\n\n## Beispiel\nKein Beispiel verfügbar."
        elif "Class name:" in prompt:
            lines = prompt.split("\n")
            for line in lines:
                if "Class name:" in line:
                    class_name = line.split(":")[-1].strip()
                    return f"## Description\nDocumentation for {class_name}. (Auto-generated - LLM unavailable)\n\n## Usage\nSee source code for details.\n\n## Configuration\nSee class attributes.\n\n## Example\nNo example available."

        return "Documentation unavailable."

    async def generate_overview(self, components: list[ComponentInfo], language: str = "de") -> str:
        """Generate an overview document for all components."""
        lang_instruction = self.LANGUAGE_INSTRUCTIONS.get(
            language, self.LANGUAGE_INSTRUCTIONS["de"]
        )

        # Group components by type
        by_type: dict[str, list[ComponentInfo]] = {}
        for comp in components:
            if comp.type not in by_type:
                by_type[comp.type] = []
            by_type[comp.type].append(comp)

        # Build component summary
        summary_parts = []
        for comp_type, comps in by_type.items():
            type_name = self.COMPONENT_TYPE_NAMES.get(language, {}).get(comp_type, comp_type)
            comp_names = ", ".join([c.class_name for c in comps])
            summary_parts.append(f"- {type_name}: {comp_names}")

        summary = "\n".join(summary_parts)

        if language == "de":
            prompt = f"""Erstelle eine Übersichtsseite für ein Scraper-Framework mit folgenden Komponenten:

{summary}

Die Übersicht soll enthalten:
1. Eine kurze Einführung in das Framework
2. Die 9-Schritte ETL-Pipeline (Fetch, Extract, Normalize, Deduplicate, Validate, Classify, Enrich, Store, Notify)
3. Eine Übersicht der verfügbaren Komponenten nach Typ
4. Einen kurzen Leitfaden für den Einstieg

{lang_instruction}"""
        else:
            prompt = f"""Create an overview page for a scraper framework with the following components:

{summary}

The overview should include:
1. A brief introduction to the framework
2. The 9-step ETL pipeline (Fetch, Extract, Normalize, Deduplicate, Validate, Classify, Enrich, Store, Notify)
3. An overview of available components by type
4. A brief getting started guide

{lang_instruction}"""

        return await self._call_llm(prompt)

    async def generate_preset_documentation(
        self, component: ComponentInfo, language: str = "en"
    ) -> str:
        """Generate specialized documentation for preset modules."""
        if language == "de":
            content = f"""# Pipeline Presets

## Beschreibung

Das Preset-System ermöglicht die Verwendung vordefinierter Pipeline-Konfigurationen für häufige Anwendungsfälle. Presets vereinfachen die YAML-Konfiguration erheblich, indem sie Standard-Plugin-Kombinationen automatisch bereitstellen.

## Verfügbare Presets

"""
            # Extract preset names from config_schema
            if component.config_schema and "presets" in component.config_schema:
                for preset_name in component.config_schema["presets"]:
                    content += f"### `{preset_name}`\n\n"
                    content += f"Beschreibung: Siehe Quellcode für Details.\n\n"
        else:
            content = f"""# Pipeline Presets

## Description

The preset system allows using predefined pipeline configurations for common use cases. Presets significantly simplify YAML configuration by automatically providing standard plugin combinations.

## Available Presets

"""
            if component.config_schema and "presets" in component.config_schema:
                for preset_name in component.config_schema["presets"]:
                    content += f"### `{preset_name}`\n\n"
                    content += f"Description: See source code for details.\n\n"

        content += f"""
## Usage

To use a preset in your YAML configuration, simply add the `preset` field:

```yaml
preset: "real_estate"
source_id: "my_scraper"
base_url: "https://example.com"
# ... rest of config
```

The preset plugins will be automatically merged with your custom configuration. Preset plugins are prepended to any custom plugins you specify.

## Implementation

Presets are defined in `src/scraper_framework/presets.py` and applied automatically by `ScraperEngine` during initialization.

"""
        return content

    async def generate_compatibility_documentation(
        self, component: ComponentInfo, language: str = "en"
    ) -> str:
        """Generate specialized documentation for plugin compatibility module."""
        if language == "de":
            content = f"""# Plugin Compatibility System

## Beschreibung

Das Plugin-Kompatibilitätssystem überprüft, ob Plugins mit den definierten Datenverträgen (Data Contracts) kompatibel sind. Dies hilft, Konfigurationsfehler frühzeitig zu erkennen.

## Funktionalität

Das System validiert, ob Plugins die benötigten Felder im Data Contract vorfinden. Wenn ein Plugin Felder erwartet, die nicht im Contract definiert sind, wird eine Warnung ausgegeben.

## Verwendung

Die Kompatibilitätsprüfung kann in der Job-Config aktiviert werden:

```yaml
validate_compatibility: true
data_contract: "RealEstateItem"
# ... rest of config
```

## Verfügbare Plugins

"""
            if component.config_schema and "plugins" in component.config_schema:
                for plugin_name in component.config_schema["plugins"][:10]:
                    content += f"- `{plugin_name}`\n"
        else:
            content = f"""# Plugin Compatibility System

## Description

The plugin compatibility system checks whether plugins are compatible with defined data contracts. This helps catch configuration errors early.

## Functionality

The system validates whether plugins can find the required fields in the data contract. If a plugin expects fields that are not defined in the contract, a warning is issued.

## Usage

Compatibility checking can be enabled in the job configuration:

```yaml
validate_compatibility: true
data_contract: "RealEstateItem"
# ... rest of config
```

## Available Plugins

"""
            if component.config_schema and "plugins" in component.config_schema:
                for plugin_name in component.config_schema["plugins"][:10]:
                    content += f"- `{plugin_name}`\n"

        content += "\n\n## Implementation\n\nThe compatibility matrix is defined in `src/scraper_framework/plugin_compatibility.py`.\n"
        return content

    def generate_markdown_file(self, doc: dict[str, Any]) -> str:
        """Generate a Markdown file from documentation data."""
        language = doc.get("language", "de")

        if language == "de":
            title = f"# {doc['name']}"
            type_label = "Typ"
            file_label = "Datei"
            methods_label = "Methoden"
        else:
            title = f"# {doc['name']}"
            type_label = "Type"
            file_label = "File"
            methods_label = "Methods"

        md_parts = [
            title,
            "",
            f"**{type_label}:** {doc.get('type_name', doc['type'])}",
            f"**{file_label}:** `{doc['file_path']}`",
            "",
            doc.get("description", ""),
            "",
        ]

        # Add methods section if there are public methods
        public_methods = [m for m in doc.get("methods", []) if not m["name"].startswith("_")]
        if public_methods:
            md_parts.append(f"## {methods_label}")
            md_parts.append("")
            for method in public_methods:
                args = ", ".join(method.get("args", []))
                async_prefix = "async " if method.get("is_async") else ""
                md_parts.append(f"### `{async_prefix}{method['name']}({args})`")
                if method.get("docstring"):
                    md_parts.append("")
                    md_parts.append(method["docstring"])
                md_parts.append("")

        return "\n".join(md_parts)
