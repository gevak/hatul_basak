import logging
import requests

import llm_utils

logging.basicConfig(level=logging.INFO)

HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36" 
    }

def fetch_wiki_metadata(titles, lang="he"):
    """
    Core logic to fetch metadata for a specific list of titles.
    """
    base_url = f"https://{lang}.wikipedia.org/w/api.php"
    results = []
    
    # Wikipedia limits queries to 50 titles at a time for most properties
    chunk_size = 20 
    for i in range(0, len(titles), chunk_size):
        chunk = titles[i : i + chunk_size]
        
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts|categories|pageimages",
            "titles": "|".join(chunk),
            "exintro": True,      # Just the intro
            "explaintext": True,  # Plain text, no HTML
            "cllimit": "max",
            "clshow": "!hidden",
            "exlimit": "max",
            "pithumbsize": 500    # Image size
        }

        response = requests.get(base_url, params=params, headers=HEADERS).json()
        pages = response.get("query", {}).get("pages", {})

        for page_id, p in pages.items():
            # Clean up categories
            raw_cats = p.get("categories", [])
            clean_cats = [c["title"] for c in raw_cats]

            # Build the dictionary as per your requirements
            item = {
                "title": p.get("title", ""),
                "url": f"https://{lang}.wikipedia.org/wiki/{p.get('title', '').replace(' ', '_')}",
                "extract": p.get("extract", "").split('\n')[0] if p.get("extract") else "",
                "categories": clean_cats,
                "image": p.get("thumbnail", {}).get("source", None)
            }
            results.append(item)
            
    return results

def get_wikipedia_pages(limit=10, titles=None, lang="he"):
    """
    Main method: 
    - If 'titles' is provided (list), it fetches those.
    - If 'titles' is None, it fetches 'limit' random pages.
    """
    if titles:
        return fetch_wiki_metadata(titles, lang=lang)
    
    # Step: Get random titles first
    random_params = {
        "action": "query",
        "list": "random",
        "rnnamespace": 0,
        "rnlimit": limit,
        "format": "json"
    }
    base_url = f"https://{lang}.wikipedia.org/w/api.php"
    res = requests.get(base_url, params=random_params, headers=HEADERS).json()
    random_titles = [page['title'] for page in res['query']['random']]
    
    return fetch_wiki_metadata(random_titles, lang=lang)

def wiki_item_to_string(item) -> str:
    return item['title'] + "\n" + ', '.join(item['categories'])

def select_pages_subset(json_items) -> list:
    json_dict = {item["title"]: item for item in json_items}
    input_list = [wiki_item_to_string(item) for item in json_items]
    ai_picks = llm_utils.get_llm_picks(input_list)
    result = []
    for title, ai_categories in ai_picks:
        assert title in json_dict, "Title %s selected by AI was not on the input list: %s" % (title, input_list)
        new_item = json_dict[title]
        new_item['categories'] = ai_categories
        result.append(new_item)
    return result
    

if __name__ == "__main__":
    # --- Examples ---
    # 1. Get 5 Random Pages
    print("--- RANDOM PAGES ---")
    random_data = get_wikipedia_pages(limit=100)
    import json
    print(json.dumps(random_data, indent=4, ensure_ascii=False))

    ai_picks = select_pages_subset(random_data)
    print("\n--- AI-SELECTED SUBSET ---")
    print(json.dumps(ai_picks, indent=4, ensure_ascii=False))

    # 2. Get Hardcoded Pages
    print("\n--- HARDCODED PAGES ---")
    specific_titles = ["ישראל", "אלברט איינשטיין", "פיצה"]
    hardcoded_data = get_wikipedia_pages(titles=specific_titles)
    print(json.dumps(hardcoded_data, indent=4, ensure_ascii=False))