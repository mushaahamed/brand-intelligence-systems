# Skill: github-sync

## Trigger
When the user pastes a GitHub URL from the brand-intelligence-systems repo.

## What to do — no questions, just do it
1. Convert the GitHub URL to a raw URL (replace `/blob/` with `/raw/` or use raw.githubusercontent.com)
2. Fetch the file content using WebFetch
3. Find the matching local file in this project (same relative path as in the URL)
4. Write the fetched content to that local file
5. Tell the user: "✅ Updated: [filename]"
6. Ask once: "Want me to commit this?"
