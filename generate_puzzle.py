import argparse
import os
import logging
import random
import re
from supabase import create_client, Client
from dotenv import load_dotenv

import llm_utils
from wiki_utils import get_wikipedia_pages

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Initialize Supabase
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def create_new_puzzle(theme: str | None = None):
    """Generates list of 10 wikipedia articles, and saves as daily puzzle."""
    if theme:
        logging.info("Using pre-selected theme for today's puzzle: %s", theme)
    else:
        themes = llm_utils.pick_themes()
        theme = random.choice(themes)
        logging.info("Selected theme for today's puzzle: %s, out of these options: %s", theme, themes)

    titles = llm_utils.pick_articles(theme)
    logging.info(f"AI selected list of %d articles: %s", len(titles), titles)
    pages_with_metadata = get_wikipedia_pages(titles=titles)
    ai_picks = llm_utils.filter_list(pages_with_metadata)
    logging.info(f"AI filtered the list down to {len(ai_picks)} articles: {[(item['title']) for item in ai_picks]}")

    # Add aliases automatically
    ai_picks = [add_aliases(item) for item in ai_picks]
    # Clean categories
    ai_picks = [clean_categories(item) for item in ai_picks]
    
    # Save to Supabase
    new_puzzle = {
        "is_daily": True,
        "title": f"חידה יומית: {theme}",
        "data": ai_picks
    }
    result = supabase.table("puzzles").insert(new_puzzle).execute()
    logging.info(f"New daily puzzle created with ID: {result.data[0]['id']}")
    return {"message": "Daily puzzle generated successfully", "puzzle": result.data[0]}

def add_aliases(item: dict) -> dict:
    """Adds an 'aliases' field to the item dict, which is a list of alternative names for the article."""
    title = item['title']
    aliases = []

    # If title contains parentheses, add the part before parentheses as an alias.
    if '(' in title:
        alias = title.split('(')[0].strip()
        aliases.append(alias)

    item["aliases"] = aliases
    return item

def normalize_str(s: str) -> str:
    # Remove all characters except:
    # - word chars (\w)
    # - whitespace (\s)
    # - Hebrew Unicode range (\u0590-\u05FF)
    s = re.sub(r'[^\w\s\u0590-\u05FF]', '', s, flags=re.IGNORECASE)
    
    # Remove all whitespace
    s = re.sub(r'\s+', '', s)
    
    # Trim (mostly redundant after removing whitespace, but kept for parity)
    return s.strip()

def clean_categories(item: dict) -> dict:
    """Renames / removes categories based on what we want to show users."""
    clean_titles = [normalize_str(a) for a in [item["title"]] + item.get("aliases", [])]
    for cat in item.get("categories", []):
        clean_cat = normalize_str(cat)
        if any(title in clean_cat for title in clean_titles):
            item["categories"] = [c for c in item["categories"] if c != cat]
    return item


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--theme",
        type=str,
        help="Optional pre-selected theme to use instead of generating one.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    theme = args.theme.strip() if args.theme else None
    create_new_puzzle(theme=theme)

if __name__ == "__main__":
    main()
