"""
Apify actor IDs and per-pipeline configuration.
Each actor is validated against the Apify marketplace.
"""

# ─── ACTOR IDs ─────────────────────────────────────────────────────────────────
ACTORS = {
    # Web content crawling
    "website_crawler":      "apify/website-content-crawler",
    "google_search":        "apify/google-search-scraper",
    "instagram_scraper":    "apify/instagram-scraper",
    "linkedin_search":      "harvestapi/linkedin-profile-search",
    "linkedin_company":     "harvestapi/linkedin-company-scraper",
    "reddit_scraper":       "trudax/reddit-scraper",
    "google_news":          "apify/google-news-scraper",
    "google_reviews":       "apify/google-maps-reviews-scraper",
    "trustpilot":           "apify/trustpilot-scraper",
    "twitter_scraper":      "quacker/twitter-scraper",
    "domain_info":          "apify/whois",
}

# ─── PER-PIPELINE ACTOR ASSIGNMENT ─────────────────────────────────────────────
PIPELINE_ACTORS = {
    "p01_company_overview":     ["website_crawler", "linkedin_company", "google_search"],
    "p02_brand_identity":       ["website_crawler"],
    "p03_market_position":      ["google_search", "google_news"],
    "p04_competitor_mapping":   ["google_search", "website_crawler"],
    "p05_brand_activity":       ["google_news", "instagram_scraper", "google_search"],
    "p06_experiential_footprint": ["google_news", "instagram_scraper", "google_search"],
    "p07_reputation_research":  ["reddit_scraper", "google_reviews", "trustpilot", "twitter_scraper"],
    "p08_strategic_watchouts":  ["google_news", "google_search"],
    "p09_decision_makers":      ["linkedin_search", "linkedin_company"],
    "p10_contact_intelligence": ["linkedin_search"],
    "p11_outreach":             [],   # LLM only — no scraping
    "p12_tracking":             [],   # Internal logic only
}

# ─── APIFY TOKEN → PIPELINE GROUP MAPPING ─────────────────────────────────────
TOKEN_GROUP_MAP = {
    "group_1": ["p01_company_overview", "p02_brand_identity"],
    "group_2": ["p03_market_position",  "p04_competitor_mapping"],
    "group_3": ["p05_brand_activity",   "p06_experiential_footprint"],
    "group_4": ["p07_reputation_research", "p08_strategic_watchouts"],
    "group_5": ["p09_decision_makers",  "p10_contact_intelligence"],
}

# ─── DEFAULT RUN INPUT CONFIGS ─────────────────────────────────────────────────
ACTOR_DEFAULTS = {
    "website_crawler": {
        "maxCrawlDepth": 2,
        "maxCrawlPages": 8,
        "useSitemaps": False,
        "saveHtml": False,
        "saveMarkdown": True,
    },
    "google_search": {
        "maxPagesPerQuery": 1,
        "resultsPerPage": 10,
        "languageCode": "en",
        "countryCode": "in",   # India-first for StepOneXP context
    },
    "linkedin_search": {
        "maxResults": 5,
        "searchType": "people",
    },
    "reddit_scraper": {
        "maxItems": 30,
        "sort": "relevance",
        "time": "year",
    },
    "instagram_scraper": {
        "resultsLimit": 20,
        "searchType": "hashtag",
    },
}
