# 🚀 Production Deployment Checklist - Scraper-Framework Auto-Documentation

## Pre-Deployment (Vor dem Go-Live)

### Code Quality
- [x] Alle Tests bestanden (Unit + Integration)
- [x] Code-Coverage >= 80% für kritische Komponenten
- [ ] Linting: `black`, `flake8`, `mypy` ohne Fehler
- [x] No hardcoded credentials (alle Secrets in .env)
- [x] API-Dokumentation via Swagger/OpenAPI vollständig

### Konfiguration
- [x] Environment-Variablen dokumentiert (.env.example erstellt)
- [x] Log-Level auf INFO (Produktion: nicht DEBUG)
- [x] APScheduler auf UTC konfiguriert (nicht lokale Zeit!)
- [x] Backup-Strategie für Wiki-Dateien definiert
- [x] 7-Tage Log-Rotation getestet und aktiviert

### Infrastruktur
- [ ] Docker-Images gebaut und getestet
- [ ] docker-compose.yml für Produktion vorbereitet
- [ ] MongoDB-Backup-Strategie (täglich?)
- [x] Disk-Space für Logs/Wiki prüfen (min. 10 GB)
- [ ] Git-Zugang für daily-worker-container konfiguriert

### Monitoring & Alerting
- [x] Log-Aggregation aufgesetzt (JSON-Logs zu Elasticsearch/CloudWatch)
- [ ] Alerts für fehlerhafte Jobs (Email/Slack)
- [x] Metrics: Job-Duration, Komponenten/Sek, Fehlerrate
- [ ] Dashboard für Real-Time Monitoring (Grafana/Datadog?)

### Security
- [x] GitHub Token in Secrets Manager (nicht in Code!)
- [x] OpenAI/GPT-OSS API-Keys in Secrets
- [ ] Database Credentials verschlüsselt
- [ ] RBAC für Wiki-Zugang definiert
- [ ] Rate-Limiting für API-Endpoints

### Documentation
- [x] README.md: Scheduler aktivieren/deaktivieren
- [x] Runbook: Manueller Trigger falls 0700 GMT Job fehlschlägt
- [x] Troubleshooting Guide: Häufige Fehler + Lösungen
- [x] Rollback-Prozedur dokumentiert

---

## Deployment (Go-Live)

### Phase 1: Staging (24h Testlauf)
```bash
# 1. Deploy zu Staging
docker-compose -f docker-compose.staging.yml up -d

# 2. Logs monitoren
curl http://staging-api:8000/docs/scheduler/logs/latest?lines=100

# 3. Validiere 24h ohne Fehler
# (Beobachte ob Daily-Job um 0700 GMT korrekt läuft)

# 4. Prüfe Disk-Space, Memory, CPU
docker stats

# 5. Backup testen
./scripts/backup-wiki.sh
```

### Phase 2: Production (Schrittweise Aktivierung)
```bash
# 1. Deploy Infrastruktur (ohne Scheduler-Start)
docker-compose -f docker-compose.prod.yml up -d

# 2. Validiere Konnektivität
curl http://prod-api:8000/health
curl http://prod-api:8000/docs/scheduler/status

# 3. Starte Scheduler manuell (via API)
curl -X POST http://prod-api:8000/docs/scheduler/daily-start

# 4. Warte auf ersten 0700 GMT Job
# (Überwache Logs live)

# 5. Nach erfolgreichem ersten Lauf: Auto-Start aktivieren
# (In kubernetes/docker-compose: scheduler.start() bei App-Startup)
```

### Phase 3: Monitoring (Erste Woche)
- [ ] Täglich 0700 GMT Job prüfen
- [ ] Log-Fehler-Rate monitoren
- [ ] Git-Change-Detection: Funktioniert neue Komponenten-Erkennung?
- [ ] LLM-Batch-Validator: Quality-Scores stabil?
- [ ] Wiki-Dateien: Wachsen sie erwartungsgemäß?
- [ ] Disk-Space: Noch OK?

---

## Post-Deployment (Laufender Betrieb)

### Tägliche Aufgaben
- [ ] Logs prüfen: Fehler oder Warnungen?
- [ ] API-Health-Check: /health Status OK?

### Wöchentliche Aufgaben
- [ ] Wiki-Backup verifizieren (Größe, Integrität)
- [ ] LLM-Quality-Report prüfen (Durchschnitt-Score)
- [ ] Git-Changes Statistik: Wie viele Komponenten/Woche?

### Monatliche Aufgaben
- [ ] Logs-Archiv: Alte Logs korrekt gelöscht (7-Tage-Rotation)?
- [ ] Performance-Trends: Job-Duration steigt? (Indiz für Probleme?)
- [ ] Dokumentations-Coverage: Noch 100% aller 139 Komponenten?
- [ ] Team-Training: Alle Runbooks und Troubleshooting verstanden?

---

## Rollback-Strategie

### Falls Scheduler fehlgeschlagen:
```bash
# 1. Sofort stoppen
curl -X POST http://prod-api:8000/docs/scheduler/daily-stop

# 2. Letzte Logs prüfen
curl http://prod-api:8000/docs/scheduler/logs/latest?lines=50

# 3. Git-Commit reverten (falls Komponenten-Code fehlerhaft)
git revert HEAD

# 4. Wiki aus Backup wiederherstellen (falls Dateien beschädigt)
./scripts/restore-wiki-backup.sh

# 5. Nach Fix: Scheduler neu starten
curl -X POST http://prod-api:8000/docs/scheduler/daily-start
```

### Falls LLM-API down (z.B. OpenAI):
- Batch-Validator läuft weiter (mit schlechterem Score)
- Nur Quality-Gate senkt Threshold (z.B. von 0.90 auf 0.70)
- Job läuft zu Ende, aber mit partial Status
- Log zeigt: "⚠️ LLM-Batch-Validierung übersprungen"
- Nächster Job am nächsten Tag: Retry (LLM hoffentlich wieder up)

---

## Success Metrics

### ✅ Erfolg nach 2 Wochen:
- [ ] 14 tägliche Jobs erfolgreich durchgelaufen (tägl 0700 GMT)
- [ ] 0 kritische Fehler in Logs
- [ ] Wiki-Größe stabil (keine unerwartete Größenänderung)
- [ ] Git-Changes korrekt erkannt
- [ ] LLM-Validator durchschnittlicher Score >= 0.90

### ✅ Erfolg nach 1 Monat:
- [ ] 30 erfolgreiche Jobs (100% Uptime)
- [ ] Auto-Dokumentation reduziert Manual-Work um 90%
- [ ] Team kennt Runbooks und Troubleshooting
- [ ] Keine Rollbacks nötig
- [ ] Logs-Archiv korrekt organisiert (nach 7 Tagen)