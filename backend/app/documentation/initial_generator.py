"""Initial documentation generator that runs on application startup."""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent import DocumentationAgent
from .logging_service import DocumentationLogService


class InitialDocumentationGenerator:
    """Generates complete documentation on application startup if none exists."""

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

    async def should_generate(self) -> bool:
        """Check if initial documentation generation is needed."""
        # Check if wiki directories exist and have content
        de_index = self.wiki_path / "de" / "index.md"
        en_index = self.wiki_path / "en" / "index.md"
        
        # Check if index files exist and have substantial content
        if not de_index.exists() or not en_index.exists():
            return True
        
        # Check if the index files have actual generated content (not just placeholders)
        try:
            de_content = de_index.read_text(encoding="utf-8")
            en_content = en_index.read_text(encoding="utf-8")
            
            # If files are too small, they're probably placeholders
            if len(de_content) < 500 or len(en_content) < 500:
                return True
            
            # Check for placeholder text
            if "Klicke auf" in de_content or "Click" in en_content:
                if "Aktualisieren" in de_content or "Refresh" in en_content:
                    return True
                    
        except Exception:
            return True
        
        return False

    async def generate_initial_documentation(self) -> dict[str, Any]:
        """Generate complete documentation for all framework components."""
        start_time = datetime.now(timezone.utc)
        
        # Log start of generation
        await self.log_service.log_generation(
            category="initial",
            action="start",
            status="in_progress",
            details={"message": "Starting initial documentation generation"}
        )
        
        try:
            # Run the documentation agent to scan and generate all docs
            result = await self.agent.scan_and_generate_all(force=True)
            
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Log successful completion
            await self.log_service.log_generation(
                category="initial",
                action="complete",
                status="success",
                components_affected=result.get("generated", 0),
                duration_ms=duration_ms,
                details={
                    "scanned": result.get("scanned", 0),
                    "generated": result.get("generated", 0),
                    "components": result.get("components", []),
                }
            )
            
            return {
                "status": "success",
                "scanned": result.get("scanned", 0),
                "generated": result.get("generated", 0),
                "duration_ms": duration_ms,
            }
            
        except Exception as e:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Log failure
            await self.log_service.log_generation(
                category="initial",
                action="complete",
                status="failed",
                duration_ms=duration_ms,
                error_message=str(e),
                details={"error": str(e)}
            )
            
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": duration_ms,
            }


async def run_initial_documentation_if_needed(
    repo_path: str | None = None,
    wiki_path: str | None = None,
    log_service: DocumentationLogService | None = None,
) -> dict[str, Any] | None:
    """Run initial documentation generation if needed."""
    if repo_path is None:
        repo_path = os.getenv("REPO_PATH", os.getcwd())
    if wiki_path is None:
        wiki_path = os.getenv("WIKI_PATH", os.path.join(os.getcwd(), "wiki"))
    
    # Create log service if not provided
    if log_service is None:
        from app.auth.db import async_session_maker
        log_service = DocumentationLogService(async_session_maker)
    
    generator = InitialDocumentationGenerator(
        repo_path=repo_path,
        wiki_path=wiki_path,
        log_service=log_service,
        llm_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    if await generator.should_generate():
        print("No documentation found or documentation is incomplete, generating initial documentation...")
        result = await generator.generate_initial_documentation()
        print(f"Initial documentation generation completed: {result}")
        return result
    else:
        print("Documentation already exists, skipping initial generation")
        return None
