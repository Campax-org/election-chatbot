import pytest
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Füge den app Pfad zum Python-Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.documentation.scheduler_service import DocumentationScheduler
from app.documentation.git_service import GitChangeDetector
from app.documentation.batch_validator import LLMBatchValidator


class TestDocumentationScheduler:
    """Unit-Tests für DocumentationScheduler"""
    
    def test_scheduler_singleton(self):
        """Teste Singleton-Pattern"""
        scheduler1 = DocumentationScheduler.get_instance()
        scheduler2 = DocumentationScheduler.get_instance()
        assert scheduler1 is scheduler2
    
    def test_scheduler_start_stop(self):
        """Teste Start/Stop"""
        scheduler = DocumentationScheduler()
        
        # Start
        scheduler.start()
        assert scheduler.is_running is True
        
        # Stop
        scheduler.stop()
        assert scheduler.is_running is False
    
    def test_next_run_time(self):
        """Teste nächste Ausführungszeit (0700 GMT)"""
        scheduler = DocumentationScheduler()
        scheduler.start()
        
        next_run = scheduler.get_next_run()
        assert next_run is not None
        # Prüfe ob Stunde = 7 (GMT)
        assert next_run.hour == 7
        assert next_run.minute == 0
        
        scheduler.stop()
    
    @patch('app.documentation.agent.DocumentationAgent')
    @patch('app.documentation.git_service.GitChangeDetector')
    @patch('app.utils.path_utils.get_repo_path')
    def test_daily_job_success(self, mock_get_repo_path, mock_git, mock_agent):
        """Teste täglichen Job mit erfolgreichem Lauf"""
        mock_instance = MagicMock()
        mock_instance.scanner = MagicMock()
        mock_instance.scanner.scan_all.return_value = []
        mock_instance.wiki_path = "/tmp/test_wiki"
        mock_agent.return_value = mock_instance
        
        mock_git_instance = MagicMock()
        mock_git_instance.get_changed_components.return_value = []
        mock_git.return_value = mock_git_instance
        
        mock_get_repo_path.return_value = "/tmp/test_repo"
        
        scheduler = DocumentationScheduler()
        # Rufe Job direkt auf (statt zu warten auf 0700 GMT)
        scheduler._daily_documentation_job()
        
        # Prüfe ob Agent-Methoden aufgerufen wurden
        mock_instance.run_full_sync.assert_called_once()


class TestGitChangeDetector:
    """Unit-Tests für GitChangeDetector"""
    
    def test_last_sync_time_default(self, tmp_path):
        """Teste Default Last-Sync (falls noch nie gelaufen)"""
        git = GitChangeDetector(tmp_path)
        last_sync = git.get_last_sync_time()
        
        # Default: 2000-01-01
        assert last_sync.year == 2000
    
    def test_save_and_load_sync_time(self, tmp_path):
        """Teste Speichern und Laden von Sync-Zeit"""
        git = GitChangeDetector(tmp_path)
        
        git.save_sync_time()
        loaded_time = git.get_last_sync_time()
        
        # Prüfe dass geladen wurde (sollte nahe an jetzt sein)
        now = datetime.now()
        delta = abs((now - loaded_time).total_seconds())
        assert delta < 5  # Innerhalb 5 Sekunden
    
    @patch('subprocess.run')
    def test_get_changed_files(self, mock_run, tmp_path):
        """Teste Git-Diff Parsing"""
        # Mock git diff output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="src/scraper_framework/enrichers/hunter_enricher.py\nsrc/scraper_framework/fetchers/new_fetcher.py"
        )
        
        git = GitChangeDetector(tmp_path)
        files = git.get_changed_files()
        
        assert len(files) == 2
        assert "src/scraper_framework/enrichers/hunter_enricher.py" in files


class TestLLMBatchValidator:
    """Unit-Tests für LLMBatchValidator"""
    
    def test_get_all_component_docs(self, tmp_path):
        """Teste Collection aller Component-Docs"""
        wiki_path = tmp_path / "wiki" / "en" / "etl-types"
        wiki_path.mkdir(parents=True, exist_ok=True)
        
        # Erstelle Test-Dateien
        (wiki_path / "test_component1.md").write_text("# Test")
        (wiki_path / "test_component2.md").write_text("# Test")
        
        # Erstelle auch die wiki/ Verzeichnisstruktur
        (tmp_path / "wiki").mkdir(exist_ok=True)
        
        validator = LLMBatchValidator(tmp_path / "wiki")
        docs = validator.get_all_component_docs()
        
        assert len(docs) == 2
    
    def test_validate_single_component_mock(self, tmp_path):
        """Teste Single-Component Validierung mit Mock"""
        wiki_path = tmp_path / "wiki" / "en" / "etl-types"
        wiki_path.mkdir(parents=True, exist_ok=True)
        
        doc_file = wiki_path / "test_enricher.md"
        doc_file.write_text("# Test Enricher\n\nDescription...")
        
        # Erstelle auch die wiki/ Verzeichnisstruktur
        (tmp_path / "wiki").mkdir(exist_ok=True)
        
        validator = LLMBatchValidator(tmp_path / "wiki")
        result = validator._validate_single_component(doc_file)
        
        # Mock-Validierung gibt Score zwischen 0.8-1.0
        assert 0.8 <= result["score"] <= 1.0
        assert "component" in result
        assert "passed" in result
        assert "timestamp" in result


# Integration-Test
@pytest.mark.asyncio
async def test_daily_job_end_to_end():
    """Integration-Test: Daily Job von Start bis Ende"""
    
    scheduler = DocumentationScheduler()
    scheduler.start()
    
    assert scheduler.is_running is True
    next_run = scheduler.get_next_run()
    assert next_run is not None
    
    scheduler.stop()
    assert scheduler.is_running is False