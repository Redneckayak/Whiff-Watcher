from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import datetime
import pandas as pd

app = FastAPI()

# Allow CORS for frontend use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output model
class PlayerRanking(BaseModel):
    name: str
    team: str
    pitcher: str
    batter_k_pct: float
    pitcher_k_pct: float
    whiff_score: float

class WhiffRankings(BaseModel):
    rankings: list[PlayerRanking]

# Opening Day to Today
def get_date_range():
    start = datetime.date(2025, 3, 20)
    end = datetime.date.today()
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

# Fetch batter strikeout stats from Statcast
def fetch_batter_k_data():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfSea=2025&hfFlag=player_type=batter&hfGames=on&hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    print("Fetching batter CSV...")
    df = pd.read_csv(url)
    df = df[df['ab'] >= 200]
    df = df.head(100)
    batters = df[['player_name', 'team', 'k_percent']].rename(columns={'player_name': 'name', 'k_percent': 'b_k_pct'})
    return batters.to_dict(orient="records")

# Fetch pitcher strikeout stats from Statcast
def fetch_pitcher_k_data():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfSea=2025&hfFlag=player_type=pitcher&hfGames=on&hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    print("Fetching pitcher CSV...")
    df = pd.read_csv(url)
    df = df[df['batters_faced'] >= 50]
    df = df.head(30)
    pitchers = df[['player_name', 'k_percent']].rename(columns={'player_name': 'name', 'k_percent': 'p_k_pct'})
    return pitchers.to_dict(orient="records")

# Dummy probable matchups
def fetch_probable_pitchers():
    return [
        {"team": "NYY", "name": "Gerrit Cole"},
        {"team": "LAD", "name": "Tyler Glasnow"},
        {"team": "ATL", "name": "Max Fried"},
    ]

# Main logic
def calculate_whiff_scores():
    batters = fetch_batter_k_data()
    pitchers = fetch_pitcher_k_data()
    matchups = fetch_probable_pitchers()

    rankings = []
    for bf in batters:
        for m in matchups:
            if bf["team"] == m["team"]:
                match = next((p for p in pitchers if p["name"] == m["name"]), None)
                if match:
                    score = bf["b_k_pct"] + match["p_k_pct"]
                    rankings.append({
                        "name": bf["name"],
                        "team": bf["team"],
                        "pitcher": match["name"],
                        "batter_k_pct": round(bf["b_k_pct"], 2),
                        "pitcher_k_pct": round(match["p_k_pct"], 2),
                        "whiff_score": round(score, 2)
                    })
    return sorted(rankings, key=lambda x: x["whiff_score"], reverse=True)

# Root check
@app.get("/")
def root():
    return {"message": "Whiff Watcher API is live"}

# Rankings endpoint
@app.get("/whiff-rankings", response_model=WhiffRankings)
def get_whiff_rankings():
    try:
        rankings = calculate_whiff_scores()
        return {"rankings": rankings}
    except Exception as e:
        print("ERROR in /whiff-rankings:", e)
        return {"rankings": []}
