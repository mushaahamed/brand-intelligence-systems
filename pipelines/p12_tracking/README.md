# P12 — Tracking & Engagement Scoring

The final pipeline. Takes the outreach sequences from P11, generates unique tracking IDs per contact-touch, embeds 1×1 pixel tracking in email HTML, wraps links with redirect tracking, and builds the engagement dashboard.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | Consumes P11 outreach sequences (no external fetch) | Orchestrator context |
| **L2 EXTRACT** | Generate MD5 tracking IDs per `company:contact:touch:uuid`; embed pixels; wrap links | Python MD5 + string builder |
| **L3 SYNTHESISE** | Build dashboard_entries with initial state + next actions | Claude Haiku |

## Tracking mechanics

### Pixel tracking (email opens)
```html
<img src="https://api.steponexp.com/track/open/{tracking_id}" width="1" height="1" />
```
Embedded invisibly at the bottom of every email body.

### Link tracking (clicks)
```
https://api.steponexp.com/track/click/{tracking_id}/{touch}?redirect={encoded_url}
```
Every link in the email body is wrapped through the redirect endpoint.

## Engagement scoring rubric

| Event | Points |
|-------|--------|
| Email opened | +1 |
| Link clicked | +5 |
| LinkedIn accepted | +4 |
| LinkedIn reply | +10 |
| Email reply | +10 |
| Meeting booked | +20 |

## Status thresholds

| Status | Min Score | Meaning |
|--------|-----------|---------|
| COLD | 0 | No engagement |
| OPENED | 1 | Email opened |
| ENGAGED | 3 | Multiple opens or one click |
| WARM | 10 | Reply or multiple clicks |
| HOT | 20 | Meeting booked or high engagement |

## API endpoints (FastAPI)
- `GET /track/open/{id}` — returns 1×1 GIF, logs open event
- `GET /track/click/{id}/{touch}?redirect=url` — logs click, redirects to target
- `POST /track/event` — manual event (reply, meeting)
- `GET /track/dashboard/{id}` — returns current score + status + history

## Cost estimate
~$0.01/run (no external APIs, 1 Haiku synthesis call)
