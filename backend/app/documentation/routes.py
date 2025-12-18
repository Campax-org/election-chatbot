"""API routes for the documentation system."""

import hashlib
import hmac
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from app.auth.db import async_session_maker
from app.auth.users import current_active_user
from app.auth.models import User
from app.utils.path_utils import get_repo_path, get_wiki_path

from .agent import DocumentationAgent, run_documentation_agent
from .logging_service import DocumentationLogService
from .scheduler import get_scheduler_status
from .scheduler_service import DocumentationScheduler

router = APIRouter(prefix="/docs", tags=["documentation"])

# Configuration
REPO_PATH = get_repo_path()
WIKI_PATH = get_wiki_path()
WEBHOOK_SECRET = os.getenv("GIT_WEBHOOK_SECRET", "")


class GenerateRequest(BaseModel):
    """Request model for documentation generation."""

    force: bool = False
    language: str | None = None


class WebhookPayload(BaseModel):
    """Git webhook payload model."""

    ref: str | None = None
    commits: list[dict[str, Any]] | None = None
    repository: dict[str, Any] | None = None


def get_agent() -> DocumentationAgent:
    """Get a configured DocumentationAgent instance."""
    return DocumentationAgent(
        repo_path=REPO_PATH,
        wiki_path=WIKI_PATH,
        llm_api_key=os.getenv("OPENAI_API_KEY"),
    )


@router.get("/status")
async def get_documentation_status() -> dict[str, Any]:
    """Get the current documentation status and sync information."""
    agent = get_agent()
    return agent.get_sync_status()


@router.post("/generate")
async def generate_documentation(
    request: GenerateRequest, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Trigger documentation generation."""

    async def run_generation():
        try:
            result = await run_documentation_agent(
                repo_path=REPO_PATH,
                wiki_path=WIKI_PATH,
                force=request.force,
            )
            print(f"Documentation generation completed: {result}")
        except Exception as e:
            print(f"Documentation generation failed: {e}")

    background_tasks.add_task(run_generation)
    return {"status": "started", "message": "Documentation generation started in background"}


@router.post("/webhook/git")
async def git_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
) -> dict[str, str]:
    """Webhook endpoint for Git commits (GitHub format)."""
    body = await request.body()

    # Verify webhook signature if secret is configured
    if WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing signature header")

        expected_signature = "sha256=" + hmac.new(
            WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Only process push events
    if x_github_event and x_github_event != "push":
        return {"status": "ignored", "message": f"Event type {x_github_event} ignored"}

    # Extract changed files from commits
    changed_files: set[str] = set()
    commits = payload.get("commits", [])
    for commit in commits:
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))

    # Filter for scraper framework files
    scraper_files = [
        f for f in changed_files if f.startswith("src/scraper_framework/") and f.endswith(".py")
    ]

    if not scraper_files:
        return {"status": "ignored", "message": "No scraper framework changes detected"}

    # Process changes in background
    async def process_changes():
        try:
            agent = get_agent()
            result = await agent.process_git_changes(list(scraper_files))
            print(f"Git webhook processing completed: {result}")
        except Exception as e:
            print(f"Git webhook processing failed: {e}")

    background_tasks.add_task(process_changes)
    return {
        "status": "processing",
        "message": f"Processing {len(scraper_files)} changed files",
    }


@router.get("/components")
async def list_components() -> dict[str, Any]:
    """List all documented components."""
    agent = get_agent()
    components = agent.scanner.scan_all()

    # Group by type
    by_type: dict[str, list[dict[str, str]]] = {}
    for comp in components:
        if comp.type not in by_type:
            by_type[comp.type] = []
        by_type[comp.type].append({
            "name": comp.name,
            "class_name": comp.class_name,
            "file_path": comp.file_path,
        })

    return {
        "total": len(components),
        "by_type": by_type,
    }


@router.get("/component/{class_name}")
async def get_component(class_name: str, language: str = "de") -> dict[str, Any]:
    """Get documentation for a specific component."""
    agent = get_agent()
    components = agent.scanner.scan_all()

    component = None
    for comp in components:
        if comp.class_name == class_name:
            component = comp
            break

    if not component:
        raise HTTPException(status_code=404, detail=f"Component {class_name} not found")

    # Generate documentation on-demand
    doc = await agent.generator.generate_component_documentation(component, language)
    return doc


@router.get("/wiki/{language}/{path:path}")
async def get_wiki_content(language: str, path: str) -> dict[str, Any]:
    """Get wiki content for a specific path and language."""
    if language not in ["de", "en"]:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")

    # Sanitize path to prevent directory traversal
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    # Add .md extension if not present
    if not path.endswith(".md"):
        path = f"{path}.md"

    # Construct full path
    wiki_file_path = os.path.join(WIKI_PATH, language, path)

    # Check if file exists
    if not os.path.isfile(wiki_file_path):
        # Return default content if file doesn't exist
        return {
            "content": get_default_content(language, path),
            "path": path,
            "language": language,
            "exists": False,
        }

    # Read and return file content
    try:
        with open(wiki_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "content": content,
            "path": path,
            "language": language,
            "exists": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading wiki file: {e}")


class UpdateWikiRequest(BaseModel):
    """Request model for updating wiki content."""

    content: str


@router.put("/wiki/{language}/{path:path}")
async def update_wiki_content(
    language: str,
    path: str,
    body: UpdateWikiRequest,
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Update wiki content (admin only)."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    if language not in ["de", "en"]:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")

    # Sanitize path to prevent directory traversal
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    # Add .md extension if not present
    if not path.endswith(".md"):
        path = f"{path}.md"

    # Construct full path
    wiki_file_path = os.path.join(WIKI_PATH, language, path)

    # Create parent directories if they don't exist
    try:
        os.makedirs(os.path.dirname(wiki_file_path), exist_ok=True)
        with open(wiki_file_path, "w", encoding="utf-8") as f:
            f.write(body.content)
        return {
            "status": "success",
            "message": f"Wiki content updated: {path}",
            "path": path,
            "language": language,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing wiki file: {e}")


def get_default_content(language: str, path: str) -> str:
    """Get default content for a wiki page that doesn't exist yet."""
    if language == "de":
        return f"""# {path.replace('.md', '').replace('-', ' ').title()}

Diese Dokumentation wird automatisch generiert und aktualisiert.

Die Dokumentation wird stündlich während der Arbeitszeit (Mo-Fr, 8:00-18:00) auf Änderungen geprüft.
"""
    else:
        return f"""# {path.replace('.md', '').replace('-', ' ').title()}

This documentation is automatically generated and updated.

Documentation is checked hourly during business hours (Mon-Fri, 8:00-18:00) for changes.
"""


# Helper function to get log service
def get_log_service() -> DocumentationLogService:
    """Get a configured DocumentationLogService instance."""
    return DocumentationLogService(async_session_maker)


# Admin Panel API Endpoints for Documentation Logs

@router.get("/admin/logs")
async def get_documentation_logs(
    limit: int = 100,
    offset: int = 0,
    category: str | None = None,
    status: str | None = None,
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Get documentation generation logs (admin only)."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    log_service = get_log_service()
    logs = await log_service.get_logs(
        limit=limit,
        offset=offset,
        category=category,
        status=status,
    )
    
    return {
        "logs": logs,
        "limit": limit,
        "offset": offset,
        "count": len(logs),
    }


@router.get("/admin/statistics")
async def get_documentation_statistics(
    hours: int = 24,
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Get documentation generation statistics (admin only)."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    log_service = get_log_service()
    stats = await log_service.get_statistics(hours=hours)
    
    # Add scheduler status
    scheduler_status = get_scheduler_status()
    stats["scheduler"] = scheduler_status
    
    return stats


@router.get("/admin/errors")
async def get_documentation_errors(
    limit: int = 10,
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Get recent documentation generation errors (admin only)."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    log_service = get_log_service()
    errors = await log_service.get_recent_errors(limit=limit)
    
    return {
        "errors": errors,
        "count": len(errors),
    }


@router.get("/scheduler/status")
async def get_scheduler_status_endpoint() -> dict[str, Any]:
    """Get the current status of the documentation scheduler."""
    return get_scheduler_status()


# New Scheduler Management Endpoints for 0700 GMT daily schedule
@router.get("/scheduler/daily-status")
async def get_daily_scheduler_status():
    """Zeige Scheduler-Status für tägliche 0700 GMT Ausführung"""
    scheduler = DocumentationScheduler.get_instance()
    return {
        "running": scheduler.is_running,
        "job_info": scheduler.get_job_info(),
        "next_run": scheduler.get_next_run().isoformat() if scheduler.get_next_run() else None
    }


@router.post("/scheduler/daily-start")
async def start_daily_scheduler():
    """Starte Scheduler für tägliche 0700 GMT Ausführung"""
    scheduler = DocumentationScheduler.get_instance()
    scheduler.start()
    return {"status": "started", "next_run": scheduler.get_next_run().isoformat() if scheduler.get_next_run() else None}


@router.post("/scheduler/daily-stop")
async def stop_daily_scheduler():
    """Stoppe Scheduler für tägliche 0700 GMT Ausführung"""
    scheduler = DocumentationScheduler.get_instance()
    scheduler.stop()
    return {"status": "stopped"}


@router.post("/scheduler/force-sync")
async def force_documentation_sync():
    """Triggere sofort Dokumentations-Update (für Tests)"""
    from documentation.agent import DocumentationAgent
    from datetime import datetime
    
    try:
        agent = DocumentationAgent()
        result = await agent.run_full_sync(force=True)
        
        return {
            "status": "success",
            "message": "Force-sync completed",
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/scheduler/completeness-check")
async def check_documentation_completeness():
    """Prüfe ob ALLE Komponenten + Enrichers dokumentiert sind"""
    from documentation.agent import DocumentationAgent
    from datetime import datetime
    
    try:
        agent = DocumentationAgent()
        
        # 1. Scanne alle Komponenten
        all_comps = agent.scanner.scan_all()
        
        # 2. Prüfe Enrichers speziell
        enrichers_check = await agent.ensure_all_enrichers_documented()
        
        # 3. Komplett-Status
        total_components = len(all_comps)
        enricher_components = [c for c in all_comps if c.get('type') == 'enricher']
        
        return {
            "status": "complete",
            "total_components": total_components,
            "enricher_components": len(enricher_components),
            "enrichers": enrichers_check,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/scheduler/validate-batch")
async def validate_documentation_batch():
    """Triggere LLM-Batch-Validierung für alle Komponenten"""
    from documentation.batch_validator import LLMBatchValidator
    from app.utils.path_utils import get_wiki_path
    from pathlib import Path
    from datetime import datetime
    
    try:
        wiki_path = Path(get_wiki_path())
        
        validator = LLMBatchValidator(wiki_path)
        summary = validator.validate_batch_sequential()
        
        # Speichere Report
        report_path = validator.save_validation_report()
        
        return {
            "status": "success",
            "total": summary['total'],
            "passed": summary['passed'],
            "failed": summary['failed'],
            "avg_score": summary['avg_score'],
            "report_path": str(report_path),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/scheduler/validation-report")
async def get_validation_report():
    """Lese letzten Validierungs-Report"""
    from app.utils.path_utils import get_wiki_path
    from pathlib import Path
    import json
    
    try:
        wiki_path = Path(get_wiki_path())
        report_path = wiki_path / "validation_report.json"
        
        if not report_path.exists():
            return {"status": "not_found", "message": "Kein Report vorhanden"}
        
        with open(report_path) as f:
            report = json.load(f)
        
        return {
            "status": "success",
            "report": report
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/scheduler/logs/latest")
async def get_latest_logs(lines: int = 50):
    """Lese letzte N Zeilen aus heutigem Log"""
    from pathlib import Path
    from datetime import datetime
    import json
    
    try:
        log_dir = Path.cwd() / "logs"
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"documentation_{today}.json"
        
        if not log_file.exists():
            return {"status": "not_found", "message": f"Log-Datei {log_file.name} nicht gefunden"}
        
        # Lese letzte N Zeilen
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
        
        latest_logs = []
        for line in all_lines[-lines:]:
            try:
                latest_logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
        
        return {
            "status": "success",
            "file": log_file.name,
            "lines_shown": len(latest_logs),
            "logs": latest_logs
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/scheduler/logs/summary")
async def get_logs_summary():
    """Zusammenfassung aller Logs der letzten 7 Tage"""
    from pathlib import Path
    from datetime import datetime
    import json
    
    try:
        log_dir = Path.cwd() / "logs"
        
        summary = {
            "total_files": 0,
            "total_entries": 0,
            "errors": 0,
            "successful_jobs": 0,
            "files": []
        }
        
        for log_file in sorted(log_dir.glob("documentation_*.json")):
            with open(log_file) as f:
                entries = [json.loads(line) for line in f if line.strip()]
            
            file_info = {
                "name": log_file.name,
                "entries": len(entries),
                "errors": sum(1 for e in entries if e.get("level") in ["ERROR", "WARNING"])
            }
            
            summary["total_files"] += 1
            summary["total_entries"] += len(entries)
            summary["errors"] += file_info["errors"]
            summary["files"].append(file_info)
        
        return {"status": "success", "summary": summary}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/auto-update-info")
async def get_auto_update_info(language: str = "de") -> dict[str, Any]:
    """Get information about automatic documentation updates."""
    scheduler_status = get_scheduler_status()
    
    if language == "de":
        return {
            "enabled": scheduler_status.get("running", False),
            "schedule": "Stündlich während der Arbeitszeit (Mo-Fr, 8:00-18:00)",
            "timezone": scheduler_status.get("timezone", "Europe/Zurich"),
            "next_check": scheduler_status.get("next_run"),
            "message": "Die Dokumentation wird automatisch aktualisiert, wenn Änderungen am Scraper-Framework erkannt werden.",
        }
    else:
        return {
            "enabled": scheduler_status.get("running", False),
            "schedule": "Hourly during business hours (Mon-Fri, 8:00-18:00)",
            "timezone": scheduler_status.get("timezone", "Europe/Zurich"),
            "next_check": scheduler_status.get("next_run"),
            "message": "Documentation is automatically updated when changes to the scraper framework are detected.",
        }


@router.get("/coverage")
async def get_coverage_report() -> dict[str, Any]:
    """Get documentation coverage report."""
    agent = get_agent()
    report = await agent.coverage_service.generate_coverage_report()
    return report


@router.post("/full-sync")
async def trigger_full_sync(
    request: GenerateRequest, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Trigger full synchronization with validation."""
    
    async def run_full_sync():
        try:
            agent = get_agent()
            result = await agent.run_full_sync(force=request.force)
            print(f"Full sync completed: {result}")
        except Exception as e:
            print(f"Full sync failed: {e}")
    
    background_tasks.add_task(run_full_sync)
    return {"status": "started", "message": "Full sync started in background"}


@router.get("/pending")
async def get_pending_docs() -> dict[str, Any]:
    """Get documentation that failed validation."""
    agent = get_agent()
    pending = agent.persistence.get_pending_docs()
    return {"pending": pending, "count": len(pending)}


@router.post("/validate/{component_name:path}")
async def validate_single_component(component_name: str) -> dict[str, Any]:
    """Validate documentation for a specific component."""
    agent = get_agent()
    components = agent.scanner.scan_all()
    
    # Find component
    component = None
    for comp in components:
        if comp.class_name == component_name or comp.class_name.lower() == component_name.lower():
            component = comp
            break
    
    if not component:
        raise HTTPException(status_code=404, detail=f"Component {component_name} not found")
    
    # Generate and validate
    if component.type == "architecture":
        if component.class_name == "PIPELINE_PRESETS":
            markdown = await agent.generator.generate_preset_documentation(component, "en")
        elif component.class_name == "PLUGIN_FIELD_REQUIREMENTS":
            markdown = await agent.generator.generate_compatibility_documentation(component, "en")
        else:
            markdown = "No specialized generator available"
    else:
        doc = await agent.generator.generate_component_documentation(component, "en")
        markdown = agent.generator.generate_markdown_file(doc)
    
    # Validate
    validation_result = await agent.persistence._llm_validate(
        component.class_name, markdown, [component.file_path]
    )
    
    return {
        "component": component.class_name,
        "validation": validation_result,
        "passed": validation_result.get("score", 0.0) >= agent.persistence.validation_threshold,
    }
