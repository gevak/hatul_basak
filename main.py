import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from supabase import create_client, Client
from typing import List
from dotenv import load_dotenv


load_dotenv()

app = FastAPI()

# Allow CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Models
class Submission(BaseModel):
    puzzle_id: str
    article_scores: List[float]
    total_score: float

class ManualPuzzleRequest(BaseModel):
    titles: List[str]

# --- Helper Functions ---

async def fetch_wikipedia_data(titles: List[str]) -> list:
    """Fetches categories, extracts, and images from Hebrew Wikipedia."""
    titles_param = "|".join(titles)
    url = "https://he.wikipedia.org/w/api.php"
    
    # Wikipedia requires a descriptive User-Agent header
    headers = {
        "User-Agent": "CatfishingHebrew/1.0 (your-email@example.com)" 
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

# --- API Endpoints ---

@app.get("/api/puzzles/daily")
async def get_daily_puzzle():
    """Returns the most recently created daily puzzle."""
    response = supabase.table("puzzles").select("*").eq("is_daily", True).order("created_at", desc=True).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="No daily puzzle found")
    return response.data[0]

@app.get("/api/puzzles/{puzzle_id}")
async def get_puzzle(puzzle_id: str):
    """Returns a specific puzzle by ID (for archives or manual games)."""
    response = supabase.table("puzzles").select("*").eq("id", puzzle_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return response.data[0]

@app.post("/api/puzzles/manual")
async def create_manual_puzzle(req: ManualPuzzleRequest):
    """Creates a manually curated puzzle and saves it to DB to enable stats."""
    wiki_data = await fetch_wikipedia_data(req.titles)
    if not wiki_data:
        raise HTTPException(status_code=400, detail="Could not fetch data for provided titles.")
    
    new_puzzle = {
        "is_daily": False,
        "data": wiki_data
    }
    result = supabase.table("puzzles").insert(new_puzzle).execute()
    return {"id": result.data[0]["id"]}

@app.post("/api/submissions")
async def submit_results(sub: Submission):
    """Saves user stats and returns distribution/percentile."""
    # Save submission
    supabase.table("submissions").insert({
        "puzzle_id": sub.puzzle_id,
        "total_score": sub.total_score,
        "article_scores": sub.article_scores
    }).execute()

    # Fetch all submissions for this puzzle to calculate stats
    all_subs = supabase.table("submissions").select("*").eq("puzzle_id", sub.puzzle_id).execute()
    
    total_players = len(all_subs.data)
    if total_players == 0:
        return {"error": "Stats unavailable"}

    # Calculate percent correct per article
    # Assuming article_scores is length 10
    num_articles = len(sub.article_scores)
    article_percentages = [0] * num_articles
    
    scores_distribution = {i: 0 for i in range(11)} # Buckets 0 to 10
    
    for row in all_subs.data:
        # Tally article percentages (treating 1 and 0.5 as correct for the sake of 'did they get it')
        for idx, score in enumerate(row["article_scores"]):
            if idx < num_articles and score > 0:
                article_percentages[idx] += 1
                
        # Tally distribution (rounding to nearest int for buckets)
        rounded_score = round(row["total_score"])
        if rounded_score in scores_distribution:
            scores_distribution[rounded_score] += 1

    article_percentages = [round((count / total_players) * 100) for count in article_percentages]

    # Calculate Percentile
    # Count how many people scored LESS than the user
    lower_scores = sum(1 for row in all_subs.data if row["total_score"] < sub.total_score)
    percentile = round((lower_scores / total_players) * 100)

    return {
        "total_players": total_players,
        "article_percentages": article_percentages,
        "distribution": scores_distribution,
        "percentile": percentile
    }


# Serve the index.html at the root URL
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")