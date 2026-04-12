"""
This is the main backend server for the Hatul Basak puzzle game. It serves API endpoints for fetching puzzles, submitting results, and also serves the frontend static files.
To run locally, set-up a .env file, and run:
python -m uvicorn main:app --reload
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from supabase import create_client, Client
from typing import List, Optional
from dotenv import load_dotenv
import statistics

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

# --- API Endpoints ---

@app.get("/api/puzzles/daily")
async def get_daily_puzzle():
    """Returns the most recently created daily puzzle."""
    response = supabase.table("puzzles").select("*").eq("is_daily", True).order("created_at", desc=True).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="No daily puzzle found")
    return response.data[0]

@app.get("/api/puzzles/archive")
async def get_archive():
    """Returns all puzzles with their stats for the archive page."""
    # Fetch all puzzles
    puzzles_res = supabase.table("puzzles").select("id, created_at, is_daily, title").order("created_at", desc=True).execute()
    puzzles = puzzles_res.data
    
    # Fetch all submissions to calculate stats
    subs_res = supabase.table("submissions").select("puzzle_id, total_score").execute()
    subs = subs_res.data
    
    # Process submissions
    puzzle_stats = {}
    for sub in subs:
        pid = sub["puzzle_id"]
        if pid not in puzzle_stats:
            puzzle_stats[pid] = {"scores": [], "solves": 0}
        puzzle_stats[pid]["scores"].append(sub["total_score"])
        puzzle_stats[pid]["solves"] += 1
        
    archive_data = []
    for p in puzzles:
        pid = p["id"]
        stats = puzzle_stats.get(pid, {"scores": [], "solves": 0})
        
        median_score = None
        if stats["scores"]:
            median_score = statistics.median(stats["scores"])
            
        title = p.get("title")
        if not title:
            created = p.get("created_at", "")[:10] if p.get("created_at") else ""
            if p.get("is_daily"):
                title = f"חידה יומית - {created}" if created else "חידה יומית"
            else:
                title = f"חידת קהילה - {created}" if created else "חידת קהילה"
                
        archive_data.append({
            "id": pid,
            "title": title,
            "created_at": p.get("created_at"),
            "is_daily": p.get("is_daily", False),
            "solves": stats["solves"],
            "median_score": median_score
        })
        
    return archive_data

@app.get("/api/puzzles/{puzzle_id}")
async def get_puzzle(puzzle_id: str):
    """Returns a specific puzzle by ID (for archives or manual games)."""
    response = supabase.table("puzzles").select("*").eq("id", puzzle_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return response.data[0]

# Define the shape of the incoming article from the frontend
class ArticleItem(BaseModel):
    url: str
    image: Optional[str] = None
    title: str
    aliases: List[str] = []
    extract: str
    categories: List[str] = []

# The payload wrapping the list of articles
class ManualPuzzleRequestPayload(BaseModel):
    title: Optional[str] = None
    data: List[ArticleItem]

@app.post("/api/puzzles/manual")
async def create_manual_puzzle(req: ManualPuzzleRequestPayload):
    """Saves a fully assembled puzzle directly from the frontend."""
    
    if not req.data or len(req.data) > 20:
        raise HTTPException(status_code=400, detail="Puzzle must contain between 1 and 20 articles.")
    
    # Convert Pydantic models to dicts for Supabase insertion
    new_puzzle = {
        "is_daily": False,
        "data": [item.model_dump() for item in req.data]
    }
    if req.title:
        new_puzzle["title"] = req.title
    
    try:
        result = supabase.table("puzzles").insert(new_puzzle).execute()
        return {"id": result.data[0]["id"]}
    except Exception as e:
        # Logging the error on your server side
        print(f"Database insertion failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save puzzle to database.")

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