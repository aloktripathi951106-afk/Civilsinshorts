#!/usr/bin/env python3
"""
scripts/auto_fetch.py
Fully Automated News Aggregation and AI Summarizer Pipeline for CivilsInshorts.
Fetches latest UPSC-relevant news articles from RSS feeds (The Hindu, Indian Express, PIB),
summarizes them to under 60 words with GS Paper mapping using Gemini API,
resolves contextual topic imagery, and updates canonical news.json.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Target file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_JSON_PATHS = [
    os.path.join(BASE_DIR, "public", "news.json"),
    os.path.join(BASE_DIR, "news.json"),
    os.path.join(BASE_DIR, "app", "src", "main", "assets", "news.json")
]

# RSS feeds from premier civil services news sources
RSS_FEEDS = [
    {
        "source": "The Hindu",
        "sourceBadge": "THE HINDU EDITORIAL",
        "category": "The Hindu",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss"
    },
    {
        "source": "Indian Express",
        "sourceBadge": "EXPRESS EXPLAINED",
        "category": "Indian Express",
        "url": "https://indianexpress.com/section/india/feed/"
    },
    {
        "source": "PIB Delhi",
        "sourceBadge": "PIB PRESS RELEASE",
        "category": "PIB Delhi",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1"
    }
]

# Curated Topic Photo Vault (High-Resolution Contextual Imagery)
TOPIC_PHOTO_VAULT = {
    "space_isro": [
        "https://images.unsplash.com/photo-1517976487502-5e42a98f82f8?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=800&auto=format&fit=crop&q=80"
    ],
    "defence_drdo": [
        "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1519074069444-1ba4ea16e6f4?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=800&auto=format&fit=crop&q=80"
    ],
    "judiciary": [
        "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1436450412740-6b988f486c6b?w=800&auto=format&fit=crop&q=80"
    ],
    "economy_rbi": [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=800&auto=format&fit=crop&q=80"
    ],
    "green_energy": [
        "https://images.unsplash.com/photo-1509391365360-2e959784a276?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1466611653911-95081537e5b7?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1548337138-e87d889cc369?w=800&auto=format&fit=crop&q=80"
    ],
    "ecology_environment": [
        "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1500534623283-312aade485b7?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1511497584788-87676104235f?w=800&auto=format&fit=crop&q=80"
    ],
    "agriculture_farming": [
        "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1592982537447-7440770cbfc9?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800&auto=format&fit=crop&q=80"
    ],
    "health_medical": [
        "https://images.unsplash.com/photo-1516549655169-df83a0774514?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=800&auto=format&fit=crop&q=80"
    ],
    "heritage_culture": [
        "https://images.unsplash.com/photo-1599661046289-e31897846e41?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=800&auto=format&fit=crop&q=80"
    ],
    "science_tech": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&auto=format&fit=crop&q=80"
    ],
    "infrastructure_transport": [
        "https://images.unsplash.com/photo-1474487548417-781cb71495f3?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1513828583688-c52646db42da?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1541888946425-d0fbb186c5f7?w=800&auto=format&fit=crop&q=80"
    ],
    "education_youth": [
        "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1532012164546-f432f2e3777a?w=800&auto=format&fit=crop&q=80"
    ],
    "international_relations": [
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1577495508048-b635879837f1?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=800&auto=format&fit=crop&q=80"
    ],
    "parliament_polity": [
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1540910419892-4a36d2c3266c?w=800&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=800&auto=format&fit=crop&q=80"
    ]
}

TOPIC_RULES = [
    ("space_isro", ["space", "isro", "satellite", "spadex", "orbit", "chandrayaan", "gaganyaan", "aditya-l1", "pslv", "gslv", "sslv", "rocket", "astronomy", "propulsion", "nasa"]),
    ("defence_drdo", ["defence", "defense", "drdo", "missile", "submarine", "navy", "naval", "warship", "destroyer", "frigate", "fighter", "rafale", "tejas", "armed forces", "border", "agni", "brahmos"]),
    ("judiciary", ["court", "judiciary", "article 142", "article 32", "article 21", "article 22", "supreme court", "high court", "chief justice", "cji", "justice", "verdict", "collegium", "bench", "detention"]),
    ("economy_rbi", ["rbi", "inflation", "monetary", "economy", "repo", "cbdc", "gdp", "fiscal", "deficit", "budget", "rupee", "forex", "banking", "sebi", "stock market", "uli", "lending", "credit"]),
    ("green_energy", ["green hydrogen", "solar", "renewable", "clean energy", "wind", "solar park", "ev", "electric vehicle", "battery", "grid", "biofuel", "decarbonization", "electrolyser", "sight"]),
    ("ecology_environment", ["peatland", "wetland", "ecology", "biodiversity", "forest", "unep", "tiger", "cheetah", "sanctuary", "national park", "wildlife", "ramsar", "climate change", "pollution", "aqi", "air quality", "ncap", "cpcb"]),
    ("agriculture_farming", ["agriculture", "farming", "farmer", "farmers", "msp", "kharif", "rabi", "crop", "crops", "irrigation", "fertilizer", "soil", "pulses", "wheat", "paddy", "monsoon", "kisan"]),
    ("health_medical", ["health", "medical", "dghs", "surgical", "hospital", "doctor", "medicine", "pharma", "amr", "vaccine", "drug", "disease", "patient", "ayushman", "clinical", "healthcare"]),
    ("heritage_culture", ["heritage", "unesco", "ahom", "temple", "culture", "archeolog", "archaeology", "monument", "excavation", "sculpture", "ancient", "mughal", "gupta", "artifact", "asi"]),
    ("science_tech", ["quantum", "semiconductor", "chip", "artificial intelligence", "ai", "supercomputer", "biotechnology", "robotics", "nanotechnology", "cyber", "5g", "telecom"]),
    ("infrastructure_transport", ["highway", "expressway", "railway", "vande bharat", "train", "port", "shipping", "airport", "aviation", "logistics", "corridor", "metro"]),
    ("education_youth", ["education", "university", "ugc", "nep", "students", "school", "literacy", "skilling", "higher education", "upsc", "iit"]),
    ("international_relations", ["imec", "asean", "bilateral", "international", "summit", "g20", "brics", "quad", "un", "united nations", "diplomacy", "treaty", "foreign affairs", "ambassador"]),
    ("parliament_polity", ["parliament", "lok sabha", "rajya sabha", "election", "bill", "prs", "ordinance", "speaker", "president", "governance", "delimitation", "constitution", "statutory"])
]

def resolve_topic_photo(syllabus, text):
    combined = (str(text) + " " + str(syllabus)).lower()
    best_key = "parliament_polity"
    highest_score = 0
    for key, keywords in TOPIC_RULES:
        score = 0
        for kw in keywords:
            if kw in combined:
                score += 2 if len(kw) > 5 else 1
        if score > highest_score:
            highest_score = score
            best_key = key
    images = TOPIC_PHOTO_VAULT.get(best_key, TOPIC_PHOTO_VAULT["parliament_polity"])
    idx = abs(len(combined)) % len(images)
    return images[idx]

def detect_syllabus(text):
    t = text.lower()
    if any(k in t for k in ["space", "isro", "drdo", "defence", "ai", "quantum", "technology", "semiconductor"]):
        return "GS-III: Science, Tech & Defence"
    if any(k in t for k in ["rbi", "economy", "inflation", "gdp", "banking", "budget", "fiscal", "uli", "lending"]):
        return "GS-III: Indian Economy & Finance"
    if any(k in t for k in ["environment", "ecology", "climate", "biodiversity", "forest", "solar", "energy", "ncap", "pollution"]):
        return "GS-III: Ecology & Clean Transition"
    if any(k in t for k in ["court", "judiciary", "constitution", "detention", "parliament", "election", "governance", "bill", "act"]):
        return "GS-II: Constitution & Governance"
    if any(k in t for k in ["bilateral", "international", "summit", "diplomacy", "treaty", "asean", "brics", "un"]):
        return "GS-II: International Relations"
    if any(k in t for k in ["health", "education", "social", "welfare", "dghs", "medical", "disease", "pharma"]):
        return "GS-II: Social Justice & Health Policy"
    if any(k in t for k in ["heritage", "culture", "temple", "monument", "history", "unesco", "archaeology"]):
        return "GS-I: Art, Culture & Heritage"
    if any(k in t for k in ["agriculture", "farmer", "crop", "msp", "irrigation", "soil", "kisan"]):
        return "GS-III: Agriculture & Food Systems"
    return "GS-II: Governance & Public Policy"

def fetch_rss_feed(feed_info):
    url = feed_info["url"]
    print(f"Fetching RSS feed from: {feed_info['source']} ({url})")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (CivilsInshorts Aggregator 1.0; +https://github.com)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            items = []
            # Find item elements in channel
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                desc_elem = item.find("description")
                link_elem = item.find("link")
                pub_elem = item.find("pubDate")

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else "#"
                pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else datetime.now(timezone.utc).isoformat()

                # Clean CDATA and HTML
                title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title).strip()
                desc = re.sub(r"<[^>]*>", " ", desc)
                desc = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", desc).strip()
                desc = re.sub(r"\s+", " ", desc)

                if title and len(title) > 10:
                    items.append({
                        "source": feed_info["source"],
                        "sourceBadge": feed_info["sourceBadge"],
                        "category": feed_info["category"],
                        "title": title,
                        "desc": desc,
                        "link": link,
                        "pubDate": pub_date
                    })
            print(f"  -> Extracted {len(items)} items from {feed_info['source']}")
            return items
    except Exception as e:
        print(f"  [WARN] Failed to fetch feed {url}: {e}")
        return []

def summarize_with_gemini(article, api_key):
    """
    Summarize article using Gemini API (gemini-3.5-flash) into an under-60-word UPSC brief.
    Returns parsed dictionary or None on failure.
    """
    if not api_key:
        return None

    prompt = f"""You are a Principal UPSC Civil Services Exam (CSE) Editor and Analyst.
Summarize this news article into an Inshorts-style 60-word exam brief suitable for Civil Services aspirants.

Title: {article['title']}
Source: {article['source']}
Content: {article['desc'][:1000]}

Strict constraints:
1. "headline": 8-14 words, informative, punchy, ending with a colon ':'
2. "body": Under 60 words (strictly 50 to 60 words). State core facts, constitutional/statutory provisions, data, and relevance for Prelims/Mains.
3. "syllabus": Map to exact GS Paper (e.g. 'GS-II: Indian Constitution & Statutory Bodies', 'GS-III: Renewable Energy', 'GS-III: Indian Economy & Banking', 'GS-II: International Relations', 'GS-I: Heritage & Culture', etc.)
4. "hindi": Accurate, professional Hindi translation (संक्षेप) in Noto Sans Devanagari script (strictly 50 to 65 words).
5. "tags": 3 to 5 high-yield exam tags like ["#GS2", "#Polity", "#PrelimsFacts"].

Respond strictly with a valid JSON object only. No markdown fences, no explanatory text.
JSON format:
{{
  "headline": "...",
  "body": "...",
  "syllabus": "...",
  "hindi": "...",
  "tags": ["..."]
}}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 600,
            "responseMimeType": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            if candidates:
                raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                # Remove markdown fences if present
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
                raw_text = re.sub(r"\s*```$", "", raw_text, flags=re.MULTILINE).strip()
                # Find JSON block
                json_match = re.search(r"\{[\s\S]*\}", raw_text)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if "headline" in parsed and "body" in parsed:
                        return parsed
    except Exception as e:
        print(f"  [WARN] Gemini summarization failed for '{article['title'][:30]}': {e}")
        return None

def fallback_summarize(article):
    """
    Deterministic rule-based summarizer fallback when Gemini API key is unavailable.
    """
    title = article["title"]
    desc = article["desc"] if article["desc"] else title
    sentences = re.split(r"(?<=[.!?])\s+", desc)
    words = []
    for s in sentences:
        sw = s.split()
        if len(words) + len(sw) <= 60:
            words.extend(sw)
        else:
            rem = 58 - len(words)
            if rem > 5:
                words.extend(sw[:rem])
                words[-1] = re.sub(r"[^\w]$", "", words[-1]) + "."
            break
    body = " ".join(words).strip()
    if not body.endswith("."):
        body += "."

    syllabus = detect_syllabus(title + " " + desc)
    headline = title if title.endswith(":") else title + ":"
    hindi = f"संक्षेप: {title}। यह राष्ट्रीय महत्व का समसामयिक विषय सिविल सेवा मुख्य परीक्षा के {syllabus} तथा प्रारंभिक परीक्षा दोनों के लिए अत्यंत प्रासंगिक है।"

    tags = ["#UPSC", "#CivilServices", "#CurrentAffairs"]
    if "GS-I" in syllabus: tags.append("#GS1")
    elif "GS-II" in syllabus: tags.append("#GS2")
    elif "GS-III" in syllabus: tags.append("#GS3")

    return {
        "headline": headline,
        "body": body,
        "syllabus": syllabus,
        "hindi": hindi,
        "tags": tags[:4]
    }

def main():
    print("=" * 60)
    print("Starting CivilsInshorts Automated News Aggregation Pipeline")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 1. Load existing articles
    primary_path = NEWS_JSON_PATHS[0]
    existing_articles = []
    if os.path.exists(primary_path):
        try:
            with open(primary_path, "r", encoding="utf-8") as f:
                existing_articles = json.load(f)
            print(f"Loaded {len(existing_articles)} existing articles from {primary_path}")
        except Exception as e:
            print(f"Error loading {primary_path}: {e}")

    # Build deduplication lookup sets
    seen_titles = set()
    seen_urls = set()
    seen_ids = set()
    for a in existing_articles:
        seen_ids.add(a.get("id"))
        seen_urls.add(a.get("sourceUrl"))
        title_snippet = re.sub(r"[^\w]", "", a.get("headline", "").lower())[:40]
        if title_snippet:
            seen_titles.add(title_snippet)

    # 2. Fetch from RSS feeds
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        print("✓ GEMINI_API_KEY detected. Using Gemini 3.5 Flash for high-yield civil services summaries.")
    else:
        print("ℹ No GEMINI_API_KEY found in environment. Using algorithmic UPSC editorial summarizer.")

    raw_candidates = []
    for feed in RSS_FEEDS:
        items = fetch_rss_feed(feed)
        for item in items[:5]: # Take top 5 latest from each feed
            title_snippet = re.sub(r"[^\w]", "", item["title"].lower())[:40]
            if title_snippet not in seen_titles and item["link"] not in seen_urls:
                raw_candidates.append(item)
                seen_titles.add(title_snippet)
                seen_urls.add(item["link"])

    print(f"Total new unique candidate articles to process: {len(raw_candidates)}")

    new_cards = []
    for item in raw_candidates:
        print(f"Processing: {item['title'][:60]}...")
        summary_data = None
        if gemini_key:
            summary_data = summarize_with_gemini(item, gemini_key)

        if not summary_data:
            summary_data = fallback_summarize(item)

        # Enforce strict 60 words boundary on body
        body_words = summary_data["body"].split()
        if len(body_words) > 65:
            summary_data["body"] = " ".join(body_words[:60]).rstrip(".,;") + "."

        card_id = "ai-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + str(abs(hash(item['title'])) % 10000)
        syllabus = summary_data.get("syllabus") or detect_syllabus(item['title'] + " " + summary_data['body'])
        topic_image = resolve_topic_photo(syllabus, summary_data['headline'] + " " + summary_data['body'])

        card = {
            "id": card_id,
            "source": item["source"],
            "sourceBadge": item["sourceBadge"],
            "syllabus": syllabus,
            "headline": summary_data["headline"],
            "body": summary_data["body"],
            "hindi": summary_data["hindi"],
            "tags": summary_data.get("tags") or ["#UPSC", "#CivilServices"],
            "image": topic_image,
            "sourceUrl": item["link"],
            "pubDate": datetime.now(timezone.utc).isoformat(),
            "category": item["category"],
            "isLiveFetched": True
        }
        new_cards.append(card)

    print(f"Successfully generated {len(new_cards)} new UPSC briefs.")

    if new_cards:
        # Prepend new cards to existing list
        updated_articles = new_cards + existing_articles
        # Keep maximum 100 articles
        updated_articles = updated_articles[:100]

        # Write to all target locations
        for path in NEWS_JSON_PATHS:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(updated_articles, f, indent=2, ensure_ascii=False)
            print(f"✓ Successfully wrote {len(updated_articles)} articles to {path}")

        print(f"Pipeline finished: Added {len(new_cards)} new articles. Total: {len(updated_articles)}.")
    else:
        print("No new articles to add. All feeds are up-to-date.")

if __name__ == "__main__":
    main()
