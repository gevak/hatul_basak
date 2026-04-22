import asyncio
import logging
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

from prompts import Prompt
import wiki_utils

load_dotenv()
logging.basicConfig(level=logging.INFO)

DEFAULT_MODEL = "google/gemini-3.1-flash-lite-preview"

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

def filter_list_and_categories(input_list) -> list[tuple[str, list[str]]]:
    """
    AI-driven method to pick a subset from a list of random pages that would work.
    Returns list, each item is an article title.
    """
    input_list_str = "\n\n".join(input_list)
    prompt = Prompt.FILTER_LIST.format(input_list=input_list_str)
    result = []
    response = generate_model_response(prompt, model=DEFAULT_MODEL)
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

def parse_response_list(response: str) -> list[str]:
    result = []
    for line in response.splitlines():
        if line.strip() == "":
            continue
        if not line.split('.')[0].isdigit():
            continue
        try:
            item = line.split(".", 1)[1].strip()
            result.append(item)
        except Exception as e:
            print(f"Error parsing line: {line}. Error: {e}")

    return result

def filter_list(wiki_pages: list[dict]) -> list[dict]:
    """
    AI-driven method to pick a subset from a list of random pages that would work.
    Returns list, each item is an article title.
    """
    articles_dict = {item["title"]: item for item in wiki_pages}
    input_list = [wiki_utils.wiki_item_to_string(item) for item in wiki_pages]
    input_list_str = "\n\n".join(input_list)
    prompt = Prompt.FILTER_LIST.format(input_list=input_list_str)
    response = generate_model_response(prompt, model=DEFAULT_MODEL)
    chosen = parse_response_list(response)
    assert len(chosen) == 10, "Expected AI to pick exactly 10 articles, but got %d. Response was:\n%s" % (len(chosen), response)
    for title in chosen:
        assert title in articles_dict, "Title %s selected by AI was not on the input list: %s" % (title, input_list)
    result = [articles_dict[title] for title in chosen]
    return result

def pick_themes() -> list[str]:
    """
    AI-driven method to generate a list of theme proposals for the daily game.
    Based on the date.
    # TODO: Add theme generation based on popular news items?
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    prompt = Prompt.PICK_THEMES.format(date=date_str)
    response = generate_model_response(prompt, model=DEFAULT_MODEL)
    return parse_response_list(response)

def pick_articles(theme) -> list[str]:
    """
    AI-driven method to generate a list of article proposals for a game, inspired by the given theme.
    # TODO: Add hard-coded list of areas of life, to help pick diverse articles.
    """
    prompt = Prompt.PICK_ARTICLES.format(theme=theme)
    response = generate_model_response(prompt, model=DEFAULT_MODEL)
    proposed_articles = parse_response_list(response)
    wiki_pages = asyncio.run(wiki_utils.search_articles(proposed_articles))
    return [page['title'] for page in wiki_pages.values() if page is not None]


if __name__ == "__main__":
    themes = pick_themes()
    print("Proposed themes:")
    for t in themes:
        print(t)

    theme = 'פסח'
    articles = pick_articles(theme)
    print(f"Proposed articles for theme {theme}:")
    for a in articles:
        print(a)