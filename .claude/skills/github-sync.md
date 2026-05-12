# Skill: github-sync

## Trigger
Use this skill whenever the user pastes a GitHub URL that points to a file in this repository (github.com/mushaahamed/brand-intelligence-systems).

Trigger patterns:
- Any URL matching `github.com/mushaahamed/brand-intelligence-systems/blob/*`
- User says "update this file", "sync this", "use this version", "replace with this"
- User pastes a raw.githubusercontent.com URL for this repo

## What This Skill Does
Fetches the file content from GitHub and writes it to the correct local path — no manual copy-paste needed.

## Steps

1. **Parse the URL** — extract the file path from the GitHub URL.
   - GitHub blob URL format: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/PATH/TO/FILE.py`
   - Convert to raw URL: `https://raw.githubusercontent.com/mushaahamed/brand-intelligence-systems/main/PATH/TO/FILE.py`

2. **Fetch the raw file** using WebFetch on the raw URL.

3. **Determine local path** — map the repo path to the local filesystem:
   - Repo root = `C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system\`
   - e.g. `pipelines/p09_decision_makers/pipeline.py` → `C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system\pipelines\p09_decision_makers\pipeline.py`

4. **Read the existing local file** first (required before Write).

5. **Write the fetched content** to the local path using the Write tool.

6. **Confirm** — tell the user which file was updated and its size.

7. **If it's a pipeline file** (`pipeline.py`), also run:
   ```
   cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "import pipelines.PIPELINE_ID.pipeline" 2>&1
   ```
   to verify it imports without syntax errors.

8. **Offer to commit** — ask if they want to `git add` and `git commit` the change.

## Example Usage

User pastes:
```
https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p09_decision_makers/pipeline.py
```

Claude should:
- Fetch `https://raw.githubusercontent.com/mushaahamed/brand-intelligence-systems/main/pipelines/p09_decision_makers/pipeline.py`
- Write to `C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system\pipelines\p09_decision_makers\pipeline.py`
- Run syntax check
- Report success

## Pipeline ID Mapping

| Folder | Pipeline ID |
|--------|------------|
| p01_company_overview | p01_company_overview |
| p02_brand_identity | p02_brand_identity |
| p03_market_position | p03_market_position |
| p04_competitor_mapping | p04_competitor_mapping |
| p05_brand_activity | p05_brand_activity |
| p06_experiential_footprint | p06_experiential_footprint |
| p07_reputation_research | p07_reputation_research |
| p08_strategic_watchouts | p08_strategic_watchouts |
| p09_decision_makers | p09_decision_makers |
| p10_contact_intelligence | p10_contact_intelligence |
| p11_outreach | p11_outreach |
| p12_tracking | p12_tracking |
