import json
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime, timedelta
import gzip
from typing import Optional


class JSONFormatter(logging.Formatter):
    """
    Formatiert Log-Einträge als JSON für strukturiertes Logging.
    Ziel: Maschinenlesbarkeit + Monitoring-Dashboard-Integration
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Konvertiere LogRecord zu JSON"""
        
        # Basis-Struktur
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Füge Funktion/Zeile hinzu
        if record.funcName:
            log_data["function"] = record.funcName
            log_data["line"] = record.lineno
        
        # Füge Exception hinzu (falls vorhanden)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Füge extra Fields hinzu (z.B. aus logger.info(..., extra={...}))
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data, ensure_ascii=False)


class RotatingJSONFileHandler(logging.handlers.RotatingFileHandler):
    """
    Rotating File Handler mit JSON-Formatter.
    Rotation: 1 pro Tag, Aufbewahrung: 7 Tage
    """
    
    def __init__(self, log_dir: Path, retention_days: int = 7):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.retention_days = retention_days
        
        # Dateiname: documentation_YYYY-MM-DD.json
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"documentation_{today}.json"
        
        super().__init__(
            filename=str(log_file),
            maxBytes=100 * 1024 * 1024,  # 100 MB pro Datei
            backupCount=7  # Behalte 7 Backups
        )
        
        self.setFormatter(JSONFormatter())
        self._cleanup_old_logs()
    
    def _cleanup_old_logs(self) -> None:
        """Lösche Logs älter als retention_days"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for log_file in self.log_dir.glob("documentation_*.json*"):
            try:
                # Parse Datum aus Dateinamen
                date_str = log_file.stem.replace("documentation_", "")
                log_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Lösche wenn älter als cutoff
                if log_date < cutoff_date:
                    log_file.unlink()
                    logging.info(f"🗑️ Alte Log-Datei gelöscht: {log_file.name}")
            except Exception as e:
                logging.warning(f"Fehler beim Löschen von {log_file}: {e}")
    
    def doRollover(self) -> None:
        """Überschreibe für tägliche Rotation"""
        # Archiviere aktuelle Datei
        if self.stream:
            self.stream.close()
            self.stream = None
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.baseFilename = str(self.log_dir / f"documentation_{today}.json")
        
        # Cleanup alte Logs
        self._cleanup_old_logs()
        
        # Öffne neue Datei
        self.stream = self._open()


class StructuredLogger:
    """Hilfsmethoden für strukturiertes Logging"""
    
    @staticmethod
    def setup_logging(log_dir: Optional[Path] = None) -> logging.Logger:
        """Konfiguriere strukturiertes JSON-Logging"""
        
        if log_dir is None:
            log_dir = Path.cwd() / "logs"
        
        logger = logging.getLogger("documentation")
        logger.setLevel(logging.DEBUG)
        
        # JSON File Handler
        file_handler = RotatingJSONFileHandler(log_dir, retention_days=7)
        logger.addHandler(file_handler)
        
        # Auch zu Console ausgeben (während Entwicklung)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JSONFormatter())
        logger.addHandler(console_handler)
        
        return logger
    
    @staticmethod
    def log_job_result(
        logger: logging.Logger,
        job_name: str,
        status: str,  # "success", "failed", "partial"
        duration_seconds: float,
        components_count: int = None,
        errors: list = None
    ) -> None:
        """Strukturiertes Logging für Job-Abschluss"""
        
        extra_data = {
            "job_name": job_name,
            "status": status,
            "duration_seconds": round(duration_seconds, 2),
        }
        
        if components_count is not None:
            extra_data["components_processed"] = components_count
            extra_data["rate_per_second"] = round(components_count / duration_seconds, 1) if duration_seconds > 0 else 0
        
        if errors:
            extra_data["errors"] = errors
        
        # Erstelle Log-Eintrag mit extra Daten
        log_record = logging.LogRecord(
            name=logger.name,
            level=logging.INFO if status == "success" else logging.WARNING,
            pathname="",
            lineno=0,
            msg=f"Job completed: {job_name}",
            args=(),
            exc_info=None
        )
        log_record.extra_data = extra_data
        
        logger.handle(log_record)