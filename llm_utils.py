import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

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

def get_llm_picks(input_list) -> list[tuple[str, list[str]]]:
    """
    AI-driven method to pick a subset from a list of random pages that would work.
    Returns list, each item is an article title and the categories that should be shown for it.
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

    ARTICLE_NAME should be the exact title of the article as given in the input list.
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
