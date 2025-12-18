import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import logging


logger = logging.getLogger(__name__)


class GitChangeDetector:
    """Erkennt neue/geänderte Komponenten via Git."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.last_sync_file = repo_root / ".last_sync"
    
    def get_last_sync_time(self) -> datetime:
        """Liest Zeit des letzten Syncs aus .last_sync"""
        if not self.last_sync_file.exists():
            # Falls noch nie gelaufen: alle Dateien sind "neu"
            return datetime(2000, 1, 1)
        
        try:
            timestamp = float(self.last_sync_file.read_text().strip())
            return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.warning(f"Fehler beim Lesen .last_sync: {e}")
            return datetime(2000, 1, 1)
    
    def save_sync_time(self) -> None:
        """Speichert aktuellen Timestamp in .last_sync"""
        try:
            self.last_sync_file.write_text(str(datetime.now().timestamp()))
        except Exception as e:
            logger.error(f"Fehler beim Speichern .last_sync: {e}")
    
    def get_changed_files(self) -> List[str]:
        """
        Gibt Liste von geänderten Dateien seit letztem Sync zurück.
        Nutzt: git diff --name-only
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1..HEAD"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return [f.strip() for f in result.stdout.split('\n') if f.strip()]
            else:
                logger.warning(f"Git diff fehlgeschlagen: {result.stderr}")
                return []
        
        except Exception as e:
            logger.error(f"Fehler beim git diff: {e}")
            return []
    
    def get_new_component_files(self) -> List[Path]:
        """
        Gibt neue/geänderte .py Dateien in src/scraper_framework/*/
        zurück, die seit letztem Sync hinzugekommen sind.
        """
        changed_files = self.get_changed_files()
        component_files = []
        
        # Pfade zu Component-Verzeichnissen
        component_dirs = [
            "src/scraper_framework/fetchers",
            "src/scraper_framework/extractors",
            "src/scraper_framework/validators",
            "src/scraper_framework/storages",
            "src/scraper_framework/enrichers",
            "src/scraper_framework/normalizers",
            "src/scraper_framework/deduplicators",
            "src/scraper_framework/classifiers",
            "src/scraper_framework/notifiers",
            "src/scraper_framework/plugins/captcha",
        ]
        
        for file in changed_files:
            # Prüfe ob Datei in Component-Verzeichnis liegt
            if any(dir in file for dir in component_dirs):
                if file.endswith('.py') and not file.endswith('__init__.py'):
                    component_files.append(Path(file))
                    logger.info(f"✅ Neue Komponente erkannt: {file}")
        
        return component_files
    
    def get_changed_components(self) -> Dict[str, List[str]]:
        """
        Gibt Übersicht über geänderte Komponenten-Typen zurück.
        
        Rückgabe:
        {
            "fetchers": ["google_sheets_fetcher.py"],
            "enrichers": ["hunter_enricher.py", "zefix_enricher.py"],
            ...
        }
        """
        new_files = self.get_new_component_files()
        components_by_type = {}
        
        for file in new_files:
            # Extrahiere Komponenten-Typ aus Pfad
            # z.B. "src/scraper_framework/fetchers/..." → "fetchers"
            parts = file.parts
            if "scraper_framework" in parts:
                idx = parts.index("scraper_framework")
                if idx + 1 < len(parts):
                    comp_type = parts[idx + 1]
                    if comp_type == "plugins":
                        # Spezial-Fall: src/scraper_framework/plugins/captcha/...
                        if idx + 2 < len(parts):
                            comp_type = parts[idx + 2]  # "captcha"
                    
                    if comp_type not in components_by_type:
                        components_by_type[comp_type] = []
                    components_by_type[comp_type].append(file.name)
        
        return components_by_type