"""Scheduler for automatic documentation updates during business hours."""

import asyncio
import os
from datetime import datetime
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .git_change_detection import run_git_change_detection
from .initial_generator import run_initial_documentation_if_needed


# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def get_documentation_scheduler() -> AsyncIOScheduler | None:
    """Get the global documentation scheduler instance."""
    return _scheduler


async def _run_git_check_job():
    """Job function for scheduled git change detection."""
    print(f"[{datetime.now()}] Running scheduled Git change detection...")
    try:
        result = await run_git_change_detection()
        print(f"[{datetime.now()}] Git change detection completed: {result.get('status')}")
        if result.get("status") == "updated":
            print(f"  - Updated {len(result.get('regenerated', []))} components")
        elif result.get("status") == "error":
            print(f"  - Error: {result.get('error')}")
    except Exception as e:
        print(f"[{datetime.now()}] Git change detection failed: {e}")


def start_documentation_scheduler(timezone: str = "Europe/Zurich") -> AsyncIOScheduler:
    """Start the documentation scheduler for hourly checks during business hours.
    
    Schedule: Monday-Friday, 8:00-18:00 (hourly at minute 0)
    Timezone: Europe/Zurich (default)
    """
    global _scheduler
    
    if _scheduler is not None:
        print("Documentation scheduler already running")
        return _scheduler
    
    _scheduler = AsyncIOScheduler(timezone=timezone)
    
    # Add job for hourly git change detection during business hours
    # CronTrigger: day_of_week='mon-fri', hour='8-17', minute=0
    # This runs at 8:00, 9:00, 10:00, ..., 17:00 on Monday-Friday
    _scheduler.add_job(
        _run_git_check_job,
        CronTrigger(
            day_of_week='mon-fri',  # Monday to Friday
            hour='8-17',            # 8:00 to 17:59 (runs at start of each hour)
            minute=0,               # At minute 0
            timezone=timezone,
        ),
        id='documentation_git_check',
        name='Documentation Git Change Detection',
        replace_existing=True,
    )
    
    _scheduler.start()
    print(f"Documentation scheduler started (timezone: {timezone})")
    print("  - Git change detection: Mon-Fri, 8:00-17:00 (hourly)")
    
    return _scheduler


def stop_documentation_scheduler():
    """Stop the documentation scheduler."""
    global _scheduler
    
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("Documentation scheduler stopped")


def get_next_scheduled_run() -> datetime | None:
    """Get the next scheduled run time for git change detection."""
    if _scheduler is None:
        return None
    
    job = _scheduler.get_job('documentation_git_check')
    if job:
        return job.next_run_time
    return None


def get_scheduler_status() -> dict[str, Any]:
    """Get the current status of the documentation scheduler."""
    if _scheduler is None:
        return {
            "running": False,
            "next_run": None,
            "jobs": [],
        }
    
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    
    return {
        "running": _scheduler.running,
        "timezone": str(_scheduler.timezone),
        "next_run": get_next_scheduled_run().isoformat() if get_next_scheduled_run() else None,
        "jobs": jobs,
    }


async def run_initial_documentation_on_startup():
    """Run initial documentation generation on startup if needed.
    
    This should be called from the FastAPI lifespan context.
    """
    print("Checking if initial documentation generation is needed...")
    try:
        result = await run_initial_documentation_if_needed()
        if result:
            print(f"Initial documentation generation completed: {result}")
        else:
            print("Documentation already exists, skipped initial generation")
    except Exception as e:
        print(f"Initial documentation generation failed: {e}")
