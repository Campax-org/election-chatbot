# 🔧 Troubleshooting Guide - Scraper-Framework Auto-Dokumentation

## Problem 1: Daily Job startet nicht um 0700 GMT

**Symptome:**
- Kein Log-Eintrag um 0700 UTC
- GET /scheduler/status zeigt: "next_run_time": null

**Ursachen & Lösungen:**

### 1. Scheduler läuft nicht
```bash
curl http://api:8000/docs/scheduler/status
# Falls "running": false → Scheduler starten
curl -X POST http://api:8000/docs/scheduler/daily-start
```

### 2. Falsche Zeitzone
```bash
# Prüfe APScheduler Config in scheduler_service.py
# Sollte sein: timezone='UTC'
grep -n "timezone" app/documentation/scheduler_service.py
```

### 3. Container-Zeit falsch
```bash
# In Docker Container
docker exec scheduler-container date -u
# Sollte UTC Zeit zeigen, nicht lokale Zeit
```

---

## Problem 2: LLM-Batch-Validator crasht

**Symptome:**
- Log: "❌ Daily Documentation Job fehlgeschlagen"
- Error: "LLM Provider error" oder "Connection timeout"

**Ursachen:**
1. GPT-OSS (Ollama) nicht erreichbar
2. OpenAI API down (Fallback)
3. Rate-Limiting (zu viele Requests)

**Lösungen:**

```bash
# 1. Prüfe Ollama-Status
curl http://ollama:11434/api/generate -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","prompt":"test"}'

# 2. Falls Ollama down: Fallback zu OpenAI prüfen
grep -n "fallback" app/documentation/llm_provider.py

# 3. Rate-Limit: Reduziere batch_size in LLMBatchValidator
# validator = LLMBatchValidator(wiki_path, batch_size=3)  # statt 5-10
```

---

## Problem 3: Git-Change-Detection nicht funktioniert

**Symptome:**
- Log: "ℹ️ Keine neuen Komponenten seit letztem Sync" (obwohl neue .py Dateien)
- GET /scheduler/logs/latest zeigt keine component_changes

**Ursachen:**
1. .last_sync Datei korrumpiert
2. Git-Repo nicht initialisiert im Container
3. Geänderte Dateien nicht in component_dirs

**Lösungen:**

```bash
# 1. .last_sync zurücksetzen
rm /workspace/project/1_generic/.last_sync

# 2. Git-Config im Container prüfen
docker exec worker-container git config --list

# 3. component_dirs erweitern (falls neue Komponenten-Ordner)
# In git_service.py: component_dirs Liste updaten
```

---

## Problem 4: Wiki-Dateien wachsen unkontrolliert

**Symptome:**
- Disk-Space läuft voll
- Wiki-Ordner: mehrere GB statt erwartet ~500 MB

**Ursachen:**
1. Duplikate werden nicht gelöscht
2. Log-Dateien nicht rotiert (nicht 7 Tage)
3. Alte Backups nicht gelöscht

**Lösungen:**

```bash
# 1. Doppelte .md Dateien finden
find wiki/en/etl-types -name "*.md" | sort | uniq -d

# 2. Log-Rotation Status prüfen
ls -lh logs/ | tail -20
# Sollte nur 7 Tage von logs sein

# 3. Alte Backups löschen
rm -rf wiki/backups/*_old.tar.gz
```

---

## Problem 5: LLM Quality-Score zu niedrig

**Symptome:**
- Log: "⚠️ component_name.md: 0.72 (unter 0.90)"
- Nur 80% der Komponenten bestehen Quality-Gate

**Ursachen:**
1. LLM-Prompt zu streng
2. Generierte .md Dateien mangelhaft
3. LLM-Model hat Probleme

**Lösungen:**

```bash
# 1. Validierungs-Report prüfen (welche Komponenten failed?)
curl http://api:8000/docs/scheduler/validation-report | jq '.report.results[] | select(.score < 0.90)'

# 2. Beispiel-Datei checken
cat wiki/en/etl-types/low_score_component.md
# Prüfe: Fehlen Headings? Code-Beispiele?

# 3. Quality-Gate Threshold senken (Notfall)
# In batch_validator.py: "passed": score >= 0.85  # statt 0.90
```

---

## Emergency Procedures

### Fallback: Scheduler ausschalten + Manual Trigger
```bash
# Stoppe Auto-Scheduler
curl -X POST http://api:8000/docs/scheduler/daily-stop

# Triggere manuell (z.B. täglich per Cron)
curl -X POST http://api:8000/docs/scheduler/force-sync

# Oder manuell in Python
python -c "
from app.documentation.agent import DocumentationAgent
agent = DocumentationAgent()
agent.run_full_sync(force=True)
"
```

### Recovery: Wiki aus Git Backup
```bash
# Falls Wiki-Dateien beschädigt
git checkout wiki/

# Oder aus S3 Backup (falls konfiguriert)
aws s3 sync s3://my-backup/wiki/ ./wiki/
```

---

## Performance Troubleshooting

### Job läuft zu lang (>30 Minuten)
**Ursachen:**
1. Zu viele Komponenten (139+)
2. LLM-Validierung langsam
3. Netzwerk-Latenz zu LLM-API

**Lösungen:**
```bash
# 1. Batch-Größe reduzieren
# In batch_validator.py: batch_size=3 (statt 10)

# 2. Parallelisierung aktivieren
# In batch_validator.py: ThreadPoolExecutor verwenden

# 3. LLM-Cache aktivieren (falls implementiert)
# Wiederholte Validierungen cachen
```

### Memory Usage zu hoch
**Ursachen:**
1. Zu viele .md Dateien im Memory
2. LLM-Responses nicht gecleared
3. Log-Buffer zu groß

**Lösungen:**
```bash
# 1. Memory-Limit setzen
export PYTHONMALLOC=debug
# Oder in Docker: --memory=2g

# 2. Log-Rotation aktivieren
# In json_logger.py: maxBytes=50*1024*1024 (50 MB)

# 3. Batch-Processing optimieren
# Dateien in Batches laden, nicht alle auf einmal
```

---

## Monitoring & Alerting Setup

### Essential Metrics to Monitor:
1. **Job Duration**: Sollte < 30 Minuten sein
2. **Success Rate**: Sollte > 95% sein
3. **LLM Score Average**: Sollte > 0.90 sein
4. **Components Processed**: Sollte stabil sein (~139)
5. **Error Rate**: Sollte < 5% sein

### Alert Thresholds:
- Job Duration > 45 Minuten → WARNING
- Success Rate < 90% → CRITICAL
- LLM Score Average < 0.85 → WARNING
- Disk Usage > 80% → WARNING
- Memory Usage > 90% → CRITICAL

### Health Check Endpoints:
```bash
# Basic Health
curl http://api:8000/health

# Scheduler Status
curl http://api:8000/docs/scheduler/status

# Latest Logs
curl http://api:8000/docs/scheduler/logs/latest?lines=10

# Validation Report
curl http://api:8000/docs/scheduler/validation-report
```