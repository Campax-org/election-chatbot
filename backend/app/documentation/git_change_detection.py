"""Git change detection service for automatic documentation updates."""

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent import DocumentationAgent
from .logging_service import DocumentationLogService


class GitChangeDetectionService:
    """Service for detecting Git changes and updating documentation accordingly."""

    # Map file paths to documentation categories
    PATH_TO_CATEGORY = {
        "src/scraper_framework/fetchers/": "scrapers",
        "src/scraper_framework/extractors/": "etl_types",
        "src/scraper_framework/validators/": "validators",
        "src/scraper_framework/storages/": "sources",
        "src/scraper_framework/enrichers/": "etl_types",
        "src/scraper_framework/normalizers/": "etl_types",
        "src/scraper_framework/deduplicators/": "etl_types",
        "src/scraper_framework/classifiers/": "etl_types",
        "src/scraper_framework/notifiers/": "etl_types",
        "src/scraper_framework/contracts.py": "data_types",
        "src/scraper_framework/engine.py": "architecture",
    }

    def __init__(
        self,
        repo_path: str,
        wiki_path: str,
        log_service: DocumentationLogService,
        llm_api_key: str | None = None,
    ):
        self.repo_path = Path(repo_path)
        self.wiki_path = Path(wiki_path)
        self.log_service = log_service
        self.llm_api_key = llm_api_key
        self.agent = DocumentationAgent(
            repo_path=repo_path,
            wiki_path=wiki_path,
            llm_api_key=llm_api_key,
        )
        self._last_check_file = self.wiki_path / "_last_git_check.txt"

    def _run_git_command(self, *args: str) -> tuple[bool, str]:
        """Run a git command and return success status and output."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Git command timed out"
        except Exception as e:
            return False, str(e)

    def _get_last_check_timestamp(self) -> str | None:
        """Get the timestamp of the last git check."""
        if self._last_check_file.exists():
            try:
                return self._last_check_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return None

    def _save_last_check_timestamp(self, timestamp: str) -> None:
        """Save the timestamp of the current git check."""
        try:
            self._last_check_file.parent.mkdir(parents=True, exist_ok=True)
            self._last_check_file.write_text(timestamp, encoding="utf-8")
        except Exception as e:
            print(f"Failed to save last check timestamp: {e}")

    def _get_current_commit_hash(self) -> str | None:
        """Get the current HEAD commit hash."""
        success, output = self._run_git_command("rev-parse", "HEAD")
        return output if success else None

    def _get_commits_since(self, since_hash: str) -> list[str]:
        """Get list of commit hashes since a given commit."""
        success, output = self._run_git_command(
            "log", f"{since_hash}..HEAD", "--pretty=%H"
        )
        if success and output:
            return output.split("\n")
        return []

    def _get_changed_files_in_commit(self, commit_hash: str) -> list[str]:
        """Get list of changed files in a specific commit."""
        success, output = self._run_git_command(
            "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash
        )
        if success and output:
            return output.split("\n")
        return []

    def _get_changed_files_since(self, since_hash: str) -> list[str]:
        """Get all changed files since a given commit."""
        success, output = self._run_git_command(
            "diff", "--name-only", since_hash, "HEAD"
        )
        if success and output:
            return output.split("\n")
        return []

    def _identify_affected_categories(self, changed_files: list[str]) -> set[str]:
        """Map changed files to documentation categories."""
        categories = set()
        
        for file_path in changed_files:
            # Skip non-Python files
            if not file_path.endswith(".py"):
                continue
            
            # Check against path mappings
            for path_prefix, category in self.PATH_TO_CATEGORY.items():
                if file_path.startswith(path_prefix):
                    categories.add(category)
                    break
        
        return categories

    def _filter_scraper_framework_files(self, files: list[str]) -> list[str]:
        """Filter files to only include scraper framework Python files."""
        return [
            f for f in files
            if f.startswith("src/scraper_framework/") and f.endswith(".py")
        ]

    async def check_for_changes(self) -> dict[str, Any]:
        """Check for Git changes and update documentation if needed."""
        start_time = datetime.now(timezone.utc)
        
        # Log start of check
        await self.log_service.log_generation(
            category="git_check",
            action="start",
            status="in_progress",
            details={"message": "Starting Git change detection"}
        )
        
        try:
            # Get current commit hash
            current_hash = self._get_current_commit_hash()
            if not current_hash:
                raise Exception("Failed to get current commit hash - git may not be available")
            
            # Get last check hash
            last_hash = self._get_last_check_timestamp()
            
            if not last_hash:
                # First run - just save current hash and skip
                self._save_last_check_timestamp(current_hash)
                
                await self.log_service.log_generation(
                    category="git_check",
                    action="complete",
                    status="success",
                    details={"message": "First run - saved current commit hash", "hash": current_hash}
                )
                
                return {
                    "status": "first_run",
                    "message": "Saved current commit hash for future comparisons",
                    "current_hash": current_hash,
                }
            
            if last_hash == current_hash:
                # No changes
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                await self.log_service.log_generation(
                    category="git_check",
                    action="complete",
                    status="success",
                    duration_ms=duration_ms,
                    details={"message": "No changes detected", "hash": current_hash}
                )
                
                return {
                    "status": "no_changes",
                    "message": "No changes detected since last check",
                    "current_hash": current_hash,
                }
            
            # Get changed files
            changed_files = self._get_changed_files_since(last_hash)
            scraper_files = self._filter_scraper_framework_files(changed_files)
            
            if not scraper_files:
                # No relevant changes
                self._save_last_check_timestamp(current_hash)
                duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                await self.log_service.log_generation(
                    category="git_check",
                    action="complete",
                    status="success",
                    duration_ms=duration_ms,
                    details={
                        "message": "No scraper framework changes",
                        "total_changed": len(changed_files),
                        "hash": current_hash
                    }
                )
                
                return {
                    "status": "no_relevant_changes",
                    "message": "No scraper framework changes detected",
                    "total_changed_files": len(changed_files),
                    "current_hash": current_hash,
                }
            
            # Identify affected categories
            categories = self._identify_affected_categories(scraper_files)
            
            # Update documentation for changed files
            result = await self.agent.process_git_changes(scraper_files)
            
            # Save current hash
            self._save_last_check_timestamp(current_hash)
            
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Log successful update
            await self.log_service.log_generation(
                category="git_update",
                action="complete",
                status="success",
                components_affected=result.get("processed", 0),
                duration_ms=duration_ms,
                details={
                    "changed_files": scraper_files,
                    "categories": list(categories),
                    "regenerated": result.get("regenerated", []),
                    "errors": result.get("errors", []),
                    "hash": current_hash,
                }
            )
            
            return {
                "status": "updated",
                "message": f"Updated documentation for {result.get('processed', 0)} components",
                "changed_files": scraper_files,
                "categories": list(categories),
                "regenerated": result.get("regenerated", []),
                "errors": result.get("errors", []),
                "current_hash": current_hash,
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Log failure
            await self.log_service.log_generation(
                category="git_check",
                action="complete",
                status="failed",
                duration_ms=duration_ms,
                error_message=str(e),
                details={"error": str(e)}
            )
            
            return {
                "status": "error",
                "error": str(e),
                "duration_ms": duration_ms,
            }


async def run_git_change_detection(
    repo_path: str | None = None,
    wiki_path: str | None = None,
    log_service: DocumentationLogService | None = None,
) -> dict[str, Any]:
    """Run git change detection as a standalone function."""
    if repo_path is None:
        repo_path = os.getenv("REPO_PATH", os.getcwd())
    if wiki_path is None:
        wiki_path = os.getenv("WIKI_PATH", os.path.join(os.getcwd(), "wiki"))
    
    # Create log service if not provided
    if log_service is None:
        from app.auth.db import async_session_maker
        log_service = DocumentationLogService(async_session_maker)
    
    service = GitChangeDetectionService(
        repo_path=repo_path,
        wiki_path=wiki_path,
        log_service=log_service,
        llm_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    return await service.check_for_changes()
