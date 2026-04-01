import asyncio
import os
import json
import logging
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from typing import List
from dotenv import load_dotenv
import requests

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Initialize Supabase
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

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

async def fetch_wikipedia_data(titles: List[str]) -> list:
    """Fetches categories, extracts, and images from Hebrew Wikipedia."""
    titles_param = "|".join(titles)
    url = "https://he.wikipedia.org/w/api.php"
    
    # Wikipedia requires a descriptive User-Agent header
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36" 
    }
    
    params = {
        "origin": "*",
        "action": "query",
        "format": "json",
        "prop": "categories|extracts|info|pageimages",
        "pithumbsize": 400,
        "clshow": "!hidden",
        "cllimit": "max",
        "exintro": 1,
        "explaintext": 1,
        "titles": titles_param
    }
    
    async with httpx.AsyncClient() as client:
        # Pass headers and params separately for cleaner code
        response = await client.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Wiki API Error: {response.status_code}")
            return []
            
        data = response.json()
        
    pages = []
    if "query" in data and "pages" in data["query"]:
        for p in data["query"]["pages"].values():
            if "missing" in p:
                continue
            
            # Clean categories
            raw_cats = p.get("categories", [])
            clean_cats = [
                c["title"].replace("קטגוריה:", "") for c in raw_cats
                if not any(x in c["title"] for x in ["ויקיפדיה", "תחזוקה", "קצרמר", "שגיאות", "ערכים", "דפים"])
            ]
            
            pages.append({
                "title": p.get("title", ""),
                "url": f"https://he.wikipedia.org/wiki/{p.get('title', '').replace(' ', '_')}",
                "extract": p.get("extract", "").split('\n')[0] if p.get("extract") else "",
                "categories": clean_cats,
                "image": p.get("thumbnail", {}).get("source", None)
            })
    return pages

async def create_new_puzzle():
    """Calls OpenRouter AI to generate 10 articles, fetches Wiki data, and saves as daily puzzle."""
    prompt = """
    You are generating a trivia game for Hebrew Wikipedia. 
    Provide exactly 10 interesting, distinct Hebrew Wikipedia article titles.
    Choose entities, historical events, famous people, or concepts that have multiple categories.
    Return ONLY a valid JSON array of strings. Example: ["ישראל", "אלברט איינשטיין", "פיצה"]
    """
    
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    body = {
        "model": "google/gemini-3.1-flash-lite-preview",
        # "model": "google/gemini-3.1-pro-preview",
        # "model": "google/gemini-3-flash-preview",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    async with httpx.AsyncClient() as client:
        ai_resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
        ai_data = ai_resp.json()
    
    try:
        content = ai_data["choices"][0]["message"]["content"]
        # Strip markdown code blocks if AI added them
        content = content.replace("```json", "").replace("```", "").strip()
        titles = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {e} {ai_data}")

    # Fetch rich data from Wikipedia
    wiki_data = await fetch_wikipedia_data(titles)
    
    # Save to Supabase
    new_puzzle = {
        "is_daily": True,
        "data": wiki_data
    }
    result = supabase.table("puzzles").insert(new_puzzle).execute()
    logging.info(f"New daily puzzle created with ID: {result.data[0]['id']}")
    return {"message": "Daily puzzle generated successfully", "puzzle": result.data[0]}


def main():
    asyncio.get_event_loop().run_until_complete(create_new_puzzle())

if __name__ == "__main__":
    main()