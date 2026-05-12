# Skill: p02-brand-identity

## Trigger
User pastes the GitHub link for p02, or says "run p02", "brand identity", "brand colours", "brand fonts", "tone of voice"

## Step 1 — Ask this one question
"What's the brand name and website URL?"

## Step 2 — Do the analysis using these exact steps

**Crawl the website:**
- Fetch the homepage using WebFetch — look for colour hex codes, font-family names, CSS variables
- Fetch /about or /about-us — look for brand story, mission, values
- Look at image descriptions, button styles, design language

**Search Google for:**
- "[brand] brand guidelines colours fonts"
- "[brand] brand identity visual style India"

**From all the data, produce this exact output:**

```
BRAND IDENTITY — [Brand Name]
==============================
Primary Colors: [hex codes found e.g. #FF6B35, #FFFFFF]
Secondary Colors: [hex codes]
Primary Fonts: [font names e.g. Helvetica Neue, Playfair Display]

Brand Tone: Warm / Bold / Minimal / Playful / Premium / Trustworthy
Brand Personality: [50-word description of how the brand sounds and feels]
Visual Style: Photography-led / Illustration-heavy / Icon-driven / Text-focused

Brand Voice Keywords:
• [word/phrase the brand uses repeatedly]
• [word/phrase]
• [word/phrase]

Key Messaging Themes:
• [theme 1 — what the brand stands for]
• [theme 2]

Activation Recommendations for StepOneXP:
• [experiential idea that fits this brand's visual identity]
• [experiential idea]
```
