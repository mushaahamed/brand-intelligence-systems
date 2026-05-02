#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# push_to_github.sh — Create repo + push brand-intelligence-system to GitHub
#
# Usage:
#   chmod +x push_to_github.sh
#   ./push_to_github.sh
#
# Requirements:
#   - git installed
#   - GitHub CLI (gh) installed  →  https://cli.github.com/
#     OR set GITHUB_PAT in your environment
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_NAME="brand-intelligence-system"
GITHUB_USER="mushaahamed"
DESCRIPTION="12-pipeline brand intelligence and outreach automation system for StepOneXP"
BRANCH="main"

# ── colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "  ◈  BrandScope → GitHub Push Script"
echo "  ─────────────────────────────────────"
echo ""

# ── check git ────────────────────────────────────────────────────────────────
command -v git >/dev/null 2>&1 || error "git not found. Install git first."
info "git found: $(git --version)"

# ── check we're in the right folder ──────────────────────────────────────────
if [[ ! -f "orchestrator.py" ]]; then
  error "Run this script from inside the brand-intelligence-system/ folder."
fi

# ── init git if not already done ─────────────────────────────────────────────
if [[ ! -d ".git" ]]; then
  git init -b "$BRANCH"
  info "Git repository initialised (branch: $BRANCH)"
else
  info "Existing git repository detected"
  # ensure we're on main
  git checkout -B "$BRANCH" 2>/dev/null || true
fi

# ── create .gitignore ────────────────────────────────────────────────────────
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
venv/
.venv/
env/

# Environment
.env

# Outputs (large JSON reports — don't commit)
outputs/*.json

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Logs
*.log
logs/
EOF
info ".gitignore created"

# ── stage everything ─────────────────────────────────────────────────────────
git add .
info "All files staged"

# ── commit ───────────────────────────────────────────────────────────────────
git commit -m "feat: initial BrandScope system — 12-pipeline brand intelligence

- 3-layer friction architecture (Fetch → Extract → Synthesise)
- P01–P12 pipelines: company overview → brand identity → market position
  → competitor mapping → brand activity → experiential footprint
  → reputation research → strategic watchouts → decision makers
  → contact intelligence → outreach sequences → tracking
- FastAPI backend with pixel tracking + engagement scoring
- Frontend SPA (index.html + style.css + app.js)
- Apify token rotation across 5 accounts (5 pipeline groups)
- Claude Haiku for synthesis, Sonnet for outreach writing
- Hunter.io email lookup with pattern inference fallback
- Full test suite (tests/test_apis.py)

Built for StepOneXP Hackathon 2024" 2>/dev/null || {
  warning "Nothing new to commit (repo may already be up to date)"
}

# ── create GitHub repo ───────────────────────────────────────────────────────
echo ""
echo "  Attempting to create GitHub repo..."
echo ""

# Method 1: GitHub CLI (preferred)
if command -v gh >/dev/null 2>&1; then
  info "GitHub CLI found — using gh"
  gh auth status >/dev/null 2>&1 || {
    warning "Not logged into GitHub CLI. Running gh auth login..."
    gh auth login
  }
  gh repo create "$REPO_NAME" \
    --public \
    --description "$DESCRIPTION" \
    --source=. \
    --remote=origin \
    --push 2>/dev/null && {
    info "Repo created and pushed via GitHub CLI!"
    PUSHED=1
  } || {
    warning "Repo may already exist. Will try push only."
    PUSHED=0
  }

# Method 2: PAT via curl
elif [[ -n "${GITHUB_PAT:-}" ]]; then
  info "Using GITHUB_PAT environment variable"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "https://api.github.com/user/repos" \
    -H "Authorization: token $GITHUB_PAT" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$REPO_NAME\",\"description\":\"$DESCRIPTION\",\"private\":false}")

  if [[ "$HTTP_CODE" == "201" ]]; then
    info "Repo created successfully on GitHub"
  elif [[ "$HTTP_CODE" == "422" ]]; then
    warning "Repo '$REPO_NAME' may already exist on GitHub — will push to existing"
  else
    error "GitHub API returned HTTP $HTTP_CODE — check your PAT and permissions"
  fi
  PUSHED=0

else
  warning "Neither GitHub CLI (gh) nor GITHUB_PAT found."
  echo ""
  echo "  Please do ONE of the following:"
  echo ""
  echo "  Option A — Install GitHub CLI:"
  echo "    https://cli.github.com/   then run:  gh auth login"
  echo ""
  echo "  Option B — Set your PAT:"
  echo "    export GITHUB_PAT=your_token_here"
  echo "    ./push_to_github.sh"
  echo ""
  echo "  Then re-run this script."
  exit 1
fi

# ── set remote and push (if not already pushed by gh) ────────────────────────
if [[ "${PUSHED:-0}" != "1" ]]; then
  REMOTE_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$REMOTE_URL"
  else
    git remote add origin "$REMOTE_URL"
  fi

  info "Remote set to: $REMOTE_URL"

  # use PAT in URL if available
  if [[ -n "${GITHUB_PAT:-}" ]]; then
    git remote set-url origin "https://${GITHUB_PAT}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
  fi

  git push -u origin "$BRANCH"
  info "Pushed to GitHub!"
fi

# ── done ─────────────────────────────────────────────────────────────────────
echo ""
echo "  ─────────────────────────────────────"
echo "  ✓ Done! Your repo is live at:"
echo ""
echo "    https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo ""
echo "  Next steps:"
echo "    1. Add your API keys to .env (copy from .env.example)"
echo "    2. Run:  python -m pytest tests/ -v"
echo "    3. Run:  uvicorn api.main:app --reload --port 8000"
echo "    4. Open: http://localhost:8000"
echo "  ─────────────────────────────────────"
echo ""
