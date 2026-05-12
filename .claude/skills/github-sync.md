# Skill: github-sync

## Trigger
Activate immediately when the user pastes ANY of these:
- A URL containing `github.com/mushaahamed/brand-intelligence-systems`
- A URL containing `raw.githubusercontent.com/mushaahamed/brand-intelligence-systems`
- A file path like `pipelines/p09.../pipeline.py` with no other context

## CRITICAL RULE — NO QUESTIONS
**Do NOT ask any questions. Do NOT show a menu. Do NOT ask about JSON fields, output format, or anything else.**
Just execute steps 1-6 immediately and silently.

---

## Execute These Steps Immediately

### Step 1 — Convert to raw URL
If URL contains `/blob/`:
```
https://github.com/mushaahamed/brand-intelligence-systems/blob/main/PATH
→ https://raw.githubusercontent.com/mushaahamed/brand-intelligence-systems/main/PATH
```
If already a `raw.githubusercontent.com` URL — use as-is.

### Step 2 — Fetch the file
Use WebFetch on the raw URL. No confirmation needed.

### Step 3 — Map to local path
```
Repo path  →  Local path
ANY/PATH/FILE  →  C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system\ANY\PATH\FILE
```

### Step 4 — Read existing local file
Use Read tool on the local path (required before Write). If file doesn't exist yet, skip Read.

### Step 5 — Write the file
Use Write tool to save fetched content to local path. Done.

### Step 6 — Report + syntax check
Print one line: `✅ Written: pipelines/p09.../pipeline.py (1234 bytes)`

If it's a `pipeline.py` file, run:
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -m py_compile pipelines/FOLDER/pipeline.py && echo "syntax ok"
```

Then ask ONE thing only: "Commit this? (yes/no)"

---

## Examples

**User pastes:**
```
https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p09_decision_makers/pipeline.py
```
**Claude does:** Fetch raw → Read local → Write local → syntax check → report done. No questions before this.

**User pastes:**
```
https://github.com/mushaahamed/brand-intelligence-systems/blob/main/frontend/app.js
```
**Claude does:** Fetch raw → Write to `frontend/app.js` → report done.

**User pastes:**
```
https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p11_outreach/pipeline.py
```
**Claude does:** Fetch raw → Write to `pipelines/p11_outreach/pipeline.py` → syntax check → report done.

---

## What NOT to do
- ❌ Do NOT ask "What fields should the JSON output include?"
- ❌ Do NOT ask "What do you want to build?"
- ❌ Do NOT show numbered options or menus
- ❌ Do NOT ask about purpose, description, or intent
- ❌ Do NOT trigger the skill-creator workflow
- ✅ Just fetch → write → report
