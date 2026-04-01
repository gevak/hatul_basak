import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()
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

def generate_model_response(prompt, model):
  api_key = os.getenv('OPENROUTER_API_KEY')
  if not api_key:
      return "OPENROUTER_API_KEY was not set, you wanted to add that I would bet."
  try:
      response = requests.post(
          url="https://openrouter.ai/api/v1/chat/completions",
          headers={"Authorization": f"Bearer {api_key}"},
          json={
              "model": model,
              "messages": [{"role": "user", "content": prompt}],
          },
          timeout=30,
      )
      response.raise_for_status()
      data = response.json()
      return data['choices'][0]['message']['content'].strip()

  except Exception as e:
      return f"Don't feel no terror, but I've got an error: {e}"

def get_ai_picks(input_list) -> list[tuple[str, list[str]]]:
    """
    AI-driven method to pick a subset from a list of random pages that would work.
    """
    PROMPT = """Catfishing is a game where players get the categories containing a secret wikipedia article, and need to guess which article is it.
    You are given the following list of Wikipedia article titles, and the list of categories each article is contained in. Pick 10 that would work well as secret articles for this game.
    Focus points:

    1. Some of the categories are too revealing. For example, the category “Tbilisi” for the article about the city of Tbilisi, or the category “Shirley Temple” for the article about the article “Shirley Temple (Cocktail)”. Remove those categories when considering articles.
    2. Don't pick articles that are impossible to guess from their categories (after filtering out the revealing categories mentioned above), For instance, if the only categories are “Geography” and “Japan”, this is too broad to guess any specific Japanese-geography-related article.
    3. Don't pick articles that are too general/categorical. The article “Tetris” is good, the article “Video game” is not.
    4. The articles should be relatively well known for the average Israeli. At least 1% of Israeli people should have heard of each of the topics before, according to your estimate.

    Pick ten diverse articles, no two should belong to a similar area of life. Don't pick two music-related articles, two food-related articles etc.

    Write the output in this specific format, without any header or intro:

    <NUMBER>. Article: <ARTICLE_NAME>. Categories: <FILTERED_CATEGORY_LIST>


    FILTERED_CATEGORY_LIST should contain the list of categories, comma separated, after removing the revealing categories mentioned above.

    The list of articles to select from:
    {input_list}
    """

    input_list_str = "\n\n".join(input_list)
    prompt = PROMPT.format(input_list=input_list_str)
    result = []
    response = generate_model_response(prompt, model="google/gemini-3.1-flash-lite-preview")
    logging.info(f"AI response:\n{response}")
    for line in response.splitlines():
        if line.strip() == "":
            continue
        if not line[0].isdigit():
            continue
        try:
            article_part, categories_part = line.split("Categories:")
            article_name = article_part.split("Article:")[1].strip().rstrip(".")
            categories = [c.strip() for c in categories_part.split(",")]
            result.append((article_name, categories))
        except Exception as e:
            print(f"Error parsing line: {line}. Error: {e}")

    return result


def select_pages_subset(json_items) -> list:
    json_dict = {item["title"]: item for item in json_items}
    input_list = [wiki_item_to_string(item) for item in json_items]
    ai_picks = get_ai_picks(input_list)
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