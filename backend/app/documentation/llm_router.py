import logging
from enum import Enum
from typing import Dict, Optional, Literal
from datetime import datetime
import time
import json
from pathlib import Path


logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Verfügbare LLM-Provider"""
    OLLAMA = "ollama"          # Lokal, kostenlos
    GPT_OSS = "gpt_oss"        # Open-Source, kostenlos
    OPENAI = "openai"          # Cloud, kostenpflichtig
    ANTHROPIC = "anthropic"    # Claude (optional)


class LLMModelConfig:
    """Konfiguration für ein LLM-Model"""
    
    def __init__(
        self,
        provider: LLMProvider,
        model_name: str,
        cost_per_1k_tokens: float = 0.0,  # USD
        max_latency_seconds: float = 30.0,
        priority: int = 1,  # Lower = höhere Priorität
        enabled: bool = True,
        is_experimental: bool = False
    ):
        self.provider = provider
        self.model_name = model_name
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.max_latency_seconds = max_latency_seconds
        self.priority = priority
        self.enabled = enabled
        self.is_experimental = is_experimental


class LLMRouter:
    """
    Intelligentes Routing zwischen LLM-Providern.
    
    Priorität:
    1. Ollama (lokal, kostenlos, schnell)
    2. GPT-OSS (kostenlos, etwas langsamer)
    3. OpenAI (kostenpflichtig, zuverlässig)
    
    Fallback: Automatisch bei Timeout oder Fehler
    """
    
    def __init__(self, metrics_file: Optional[Path] = None):
        self.metrics_file = metrics_file or Path("llm_metrics.json")
        self.models: Dict[LLMProvider, LLMModelConfig] = {}
        self.metrics = self._load_metrics()
        self._initialize_default_models()
    
    def _initialize_default_models(self) -> None:
        """Initialisiere Standard-Models mit Prioritäten"""
        
        # 1️⃣ Ollama (Priorität 1: Höchste Priorität, lokal, kostenlos)
        self.register_model(LLMModelConfig(
            provider=LLMProvider.OLLAMA,
            model_name="llama2:7b",
            cost_per_1k_tokens=0.0,
            max_latency_seconds=5.0,
            priority=1,
            enabled=True
        ))
        
        # 2️⃣ GPT-OSS (Priorität 2)
        self.register_model(LLMModelConfig(
            provider=LLMProvider.GPT_OSS,
            model_name="gpt2-large",
            cost_per_1k_tokens=0.0,
            max_latency_seconds=15.0,
            priority=2,
            enabled=True
        ))
        
        # 3️⃣ OpenAI (Priorität 3: Fallback, kostenpflichtig)
        self.register_model(LLMModelConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o-mini",
            cost_per_1k_tokens=0.00015,  # USD pro 1k tokens
            max_latency_seconds=20.0,
            priority=3,
            enabled=True
        ))
    
    def register_model(self, config: LLMModelConfig) -> None:
        """Registriere neues Model"""
        self.models[config.provider] = config
        logger.info(f"✅ Model registriert: {config.provider.value} - {config.model_name}")
    
    def get_optimal_model(self, prefer_cost: bool = True, allow_experimental: bool = False) -> Optional[LLMModelConfig]:
        """
        Wähle optimales Model basierend auf Strategie.
        
        Strategien:
        - prefer_cost=True: Billigste + verfügbare Option
        - prefer_cost=False: Zuverlässigste (OpenAI)
        - allow_experimental=True: Teste neue Models
        
        Rückgabe: Model-Config oder None (kein Model verfügbar)
        """
        
        candidates = []
        
        for provider, config in self.models.items():
            # Skip deaktiviert Models
            if not config.enabled:
                logger.debug(f"⏭️ {provider.value} deaktiviert")
                continue
            
            # Skip experimentelle Models (falls nicht erlaubt)
            if config.is_experimental and not allow_experimental:
                logger.debug(f"⏭️ {provider.value} experimentell (übersprungen)")
                continue
            
            # Prüfe ob verfügbar (via Health-Check)
            if not self._is_model_healthy(provider):
                logger.warning(f"⚠️ {provider.value} nicht erreichbar")
                continue
            
            candidates.append(config)
        
        if not candidates:
            logger.error("❌ Keine verfügbaren LLM-Models!")
            return None
        
        # Sortiere nach Strategie
        if prefer_cost:
            # Billigste zuerst
            candidates.sort(key=lambda c: (c.cost_per_1k_tokens, c.priority))
        else:
            # Zuverlässigste zuerst (Priorität + Latenz)
            candidates.sort(key=lambda c: (c.priority, c.max_latency_seconds))
        
        selected = candidates[0]
        logger.info(f"🎯 Selected: {selected.provider.value} - {selected.model_name}")
        
        return selected
    
    def _is_model_healthy(self, provider: LLMProvider) -> bool:
        """Prüfe ob Model erreichbar via Health-Check"""
        
        try:
            if provider == LLMProvider.OLLAMA:
                # Prüfe Ollama-API
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                return response.status_code == 200
            
            elif provider == LLMProvider.GPT_OSS:
                # Prüfe GPT-OSS (z.B. HuggingFace API)
                return True  # Vereinfacht: Annahme immer verfügbar
            
            elif provider == LLMProvider.OPENAI:
                # Prüfe OpenAI API-Key
                import os
                return bool(os.getenv("OPENAI_API_KEY"))
            
            return False
        
        except Exception as e:
            logger.warning(f"Health-Check fehlgeschlagen für {provider.value}: {e}")
            return False
    
    def call_llm_with_fallback(
        self,
        prompt: str,
        prefer_cost: bool = True,
        max_retries: int = 3
    ) -> tuple[str, LLMProvider, float]:
        """
        Rufe LLM mit intelligenter Fallback-Logik auf.
        
        Rückgabe: (response, used_provider, duration_seconds)
        """
        
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            # 1️⃣ Wähle Model
            model_config = self.get_optimal_model(prefer_cost=prefer_cost)
            
            if not model_config:
                logger.error("❌ Keine Models verfügbar!")
                raise Exception("No LLM models available")
            
            # 2️⃣ Rufe LLM auf mit Timing
            start_time = time.time()
            
            try:
                logger.info(f"📞 Rufe {model_config.provider.value} auf...")
                
                # Simuliere LLM-Aufruf (in Produktion: echte Provider-Integration)
                if model_config.provider == LLMProvider.OLLAMA:
                    # Simuliere Ollama-Aufruf
                    time.sleep(0.5)  # Simulierte Latenz
                    response = "0.95"  # Simulierte Validierung
                    
                elif model_config.provider == LLMProvider.GPT_OSS:
                    # Simuliere GPT-OSS-Aufruf
                    time.sleep(1.0)
                    response = "0.92"
                    
                elif model_config.provider == LLMProvider.OPENAI:
                    # Simuliere OpenAI-Aufruf
                    time.sleep(1.5)
                    response = "0.98"
                    
                else:
                    raise ValueError(f"Unsupported provider: {model_config.provider}")
                
                duration = time.time() - start_time
                
                # 3️⃣ Logge Metrics
                self._log_metric(
                    provider=model_config.provider,
                    model=model_config.model_name,
                    duration_seconds=duration,
                    tokens_estimated=len(prompt.split()),
                    cost=self._estimate_cost(model_config, len(prompt.split())),
                    success=True
                )
                
                logger.info(f"✅ {model_config.provider.value}: {duration:.2f}s")
                
                return (response, model_config.provider, duration)
            
            except Exception as e:
                duration = time.time() - start_time
                last_error = str(e)
                
                # Logge Fehler
                self._log_metric(
                    provider=model_config.provider,
                    model=model_config.model_name,
                    duration_seconds=duration,
                    success=False,
                    error=str(e)
                )
                
                logger.warning(f"⚠️ {model_config.provider.value} fehlgeschlagen: {e}")
                
                # Markiere als unhealthy für nächsten Versuch
                model_config.enabled = False
                attempt += 1
        
        # Alle Versuche fehlgeschlagen
        logger.error(f"❌ Alle {max_retries} Versuche fehlgeschlagen: {last_error}")
        raise Exception(f"All LLM providers failed: {last_error}")
    
    def _estimate_cost(self, config: LLMModelConfig, tokens: int) -> float:
        """Schätze Kosten für Prompt"""
        return (tokens / 1000) * config.cost_per_1k_tokens
    
    def _log_metric(
        self,
        provider: LLMProvider,
        model: str,
        duration_seconds: float,
        tokens_estimated: int = 0,
        cost: float = 0.0,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Speichere Performance-Metrik"""
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider.value,
            "model": model,
            "duration_seconds": round(duration_seconds, 2),
            "tokens_estimated": tokens_estimated,
            "cost_usd": round(cost, 6),
            "success": success,
            "error": error
        }
        
        self.metrics.append(metric)
        
        # Speichere Metrics periodisch (alle 50 Requests)
        if len(self.metrics) % 50 == 0:
            self._save_metrics()
    
    def _load_metrics(self) -> list:
        """Lade Metrics aus Datei"""
        if self.metrics_file.exists():
            with open(self.metrics_file) as f:
                return json.load(f)
        return []
    
    def _save_metrics(self) -> None:
        """Speichere Metrics in Datei"""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        logger.info(f"✅ Metrics gespeichert ({len(self.metrics)} Einträge)")
    
    def get_statistics(self, provider: Optional[LLMProvider] = None) -> dict:
        """Zeige Statistiken für Provider"""
        
        relevant_metrics = self.metrics
        if provider:
            relevant_metrics = [m for m in self.metrics if m['provider'] == provider.value]
        
        if not relevant_metrics:
            return {"total": 0}
        
        successful = sum(1 for m in relevant_metrics if m['success'])
        avg_duration = sum(m['duration_seconds'] for m in relevant_metrics) / len(relevant_metrics)
        total_cost = sum(m['cost_usd'] for m in relevant_metrics)
        
        return {
            "total": len(relevant_metrics),
            "successful": successful,
            "failed": len(relevant_metrics) - successful,
            "success_rate": round(100 * successful / len(relevant_metrics), 1),
            "avg_duration_seconds": round(avg_duration, 2),
            "total_cost_usd": round(total_cost, 4)
        }