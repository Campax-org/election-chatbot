from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import logging
from typing import Optional
from pathlib import Path
import time


# Strukturiertes JSON-Logging
from .json_logger import StructuredLogger


logger = logging.getLogger(__name__)


class DocumentationScheduler:
    """
    Triggert tägliche Auto-Dokumentation um 0700 GMT.
    - Erkennt neue Module
    - Dokumentiert sie automatisch
    - Validiert mit LLM
    """
    
    _instance: Optional['DocumentationScheduler'] = None
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.job_id = "daily_documentation_sync"
        self.is_running = False
    
    @classmethod
    def get_instance(cls) -> 'DocumentationScheduler':
        """Singleton Pattern"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def start(self) -> None:
        """Starte Scheduler mit täglich 0700 GMT Trigger"""
        if self.is_running:
            logger.warning("Scheduler läuft bereits")
            return
        
        try:
            # Cron: 0700 GMT = hour=7, minute=0
            trigger = CronTrigger(hour=7, minute=0, timezone='UTC')
            
            self.scheduler.add_job(
                func=self._daily_documentation_job,
                trigger=trigger,
                id=self.job_id,
                name="Daily Documentation Sync (0700 GMT)",
                replace_existing=True  # Überschreibe alte Jobs mit gleicher ID
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("✅ Scheduler gestartet - täglich 0700 GMT")
            logger.info(f"Nächste Ausführung: {self.scheduler.get_job(self.job_id).next_run_time}")
            
        except Exception as e:
            logger.error(f"❌ Scheduler-Start fehlgeschlagen: {e}")
            raise
    
    def stop(self) -> None:
        """Stoppe Scheduler"""
        if not self.is_running:
            logger.warning("Scheduler läuft nicht")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("✅ Scheduler gestoppt")
        except Exception as e:
            logger.error(f"❌ Scheduler-Stop fehlgeschlagen: {e}")
    
    def _daily_documentation_job(self) -> None:
        """
        Täglicher Job mit strukturiertem JSON-Logging.
        Loggt: Duration, Komponenten-Rate, Fehler, Status
        """
        job_start_time = time.time()
        job_status = "success"
        job_errors = []
        components_processed = 0
        
        try:
            logger.info(f"🚀 Daily Documentation Job gestartet: {datetime.now()} UTC")
            
            from .agent import DocumentationAgent
            from .git_service import GitChangeDetector
            from app.utils.path_utils import get_repo_path
            from .batch_validator import LLMBatchValidator
            import asyncio
            
            # 1️⃣ Git-Change-Detection
            repo_root = get_repo_path()
            git = GitChangeDetector(repo_root)
            
            changes = git.get_changed_components()
            
            if not changes:
                logger.info("ℹ️ Keine neuen Komponenten seit letztem Sync")
            else:
                logger.info(f"🔍 Gefundene Änderungen: {changes}")
            
            # 2️⃣ Dokumentations-Update
            agent = DocumentationAgent()
            
            # run_full_sync mit inkrementellen Updates (force=False)
            # Da APScheduler Jobs synchron sind, müssen wir asyncio.run verwenden
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # force=False → Nur neue/geänderte Komponenten
                loop.run_until_complete(agent.run_full_sync(force=False, component_changes=changes))
                all_components = agent.scanner.scan_all()
                components_processed = len(all_components)
                logger.info(f"✅ {components_processed} Komponenten dokumentiert")
                
                # 3️⃣ Enrichers-Completeness-Check
                enrichers_check = loop.run_until_complete(agent.ensure_all_enrichers_documented())
                logger.info(f"✅ Enrichers-Check: {enrichers_check['status']}")
                
                # 4️⃣ LLM-Batch-Validierung
                try:
                    logger.info("🔬 Starte LLM-Batch-Validierung...")
                    from pathlib import Path
                    
                    validator = LLMBatchValidator(Path(agent.wiki_path))
                    validation_summary = validator.validate_batch_sequential()
                    validator.save_validation_report()
                    
                    logger.info(
                        f"✅ Validierung: {validation_summary['passed']}/{validation_summary['total']} bestanden"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ LLM-Batch-Validierung übersprungen: {e}")
                    job_errors.append(str(e))
                    job_status = "partial"
                
                # 5️⃣ Speichere Sync-Zeitstempel
                git.save_sync_time()
                
                logger.info("✅ Daily Documentation Job erfolgreich abgeschlossen")
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"❌ Daily Documentation Job fehlgeschlagen: {e}", exc_info=True)
            job_status = "failed"
            job_errors.append(str(e))
        
        finally:
            # Strukturiertes Job-Result Logging
            duration = time.time() - job_start_time
            
            StructuredLogger.log_job_result(
                logger=logger,
                job_name="daily_documentation_sync",
                status=job_status,
                duration_seconds=duration,
                components_count=components_processed,
                errors=job_errors if job_errors else None
            )
    
    def get_next_run(self) -> Optional[datetime]:
        """Zeige nächste geplante Ausführung"""
        if not self.is_running:
            return None
        job = self.scheduler.get_job(self.job_id)
        return job.next_run_time if job else None
    
    def get_job_info(self) -> dict:
        """Debugging: Informationen über den geplanten Job"""
        if not self.is_running:
            return {"status": "not_running"}
        
        job = self.scheduler.get_job(self.job_id)
        if not job:
            return {"status": "job_not_found"}
        
        return {
            "status": "running",
            "job_id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        }