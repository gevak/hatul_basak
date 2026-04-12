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
import datetime

from wiki_utils import get_wikipedia_pages, select_pages_subset

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Initialize Supabase
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def create_new_puzzle():
    """Generates list of 10 wikipedia articles, and saves as daily puzzle."""
    num_random_articles = 100
    logging.info(f"Fetching {num_random_articles} random Wikipedia articles")
    random_data = get_wikipedia_pages(limit=100)
    logging.info(f"Fetched {len(random_data)} random Wikipedia articles")
    ai_picks = select_pages_subset(random_data)
    logging.info(f"AI selected {len(ai_picks)} articles for the puzzle: {[item['title'] for item in ai_picks]}")
    
    # Save to Supabase
    new_puzzle = {
        "is_daily": True,
        "title": f"חידה יומית - {datetime.date.today().strftime('%d/%m/%Y')}",
        "data": ai_picks
    }
    result = supabase.table("puzzles").insert(new_puzzle).execute()
    logging.info(f"New daily puzzle created with ID: {result.data[0]['id']}")
    return {"message": "Daily puzzle generated successfully", "puzzle": result.data[0]}


def main():
    create_new_puzzle()

if __name__ == "__main__":
    main()