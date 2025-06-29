from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import pandas as pd
from io import StringIO
import datetime

app = FastAPI()

# Allow all CORS for frontend use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output models
class PlayerRanking(BaseModel):
    name: str
    team: str
    pitcher: str
    batter_k_pct: float
    pitcher_k_pct: float
    whiff_score: float

class WhiffRankings(BaseModel):
    rankings: list[PlayerRanking]

# Helper to get date range YTD
def get_date_range():
    start = datetime.date(2025, 3, 20)  # Opening Day 2025
    end = datetime.date.today()
    return start, end

# Fetch top 100 batters YTD
def fetch_top_batters():
    start, end = get_date_range()
    url = (
        "https://baseballsavant.mlb.com/statcast_search/csv?"
        f"all=true&hfSea=2025&hfFlag=player_type=batter&hfGames=on&"
        f"startDate={start}&endDate={end}&sort_col=k_percent&sort_order=desc"
    )
    response = requests.get(url)
    df = pd.read_csv(StringIO(response.text))
    df = df[df["ab"] >= 200]  # Filter for qualified batters
    df = df[["player_name", "team", "k_percent"]].rename(columns={"k_percent": "b_k_pct"})
    return df.head(100)

# Fetch probable starting pitchers YTD
def fetch_starting_pitchers():
    start, end = get_date_range()
    url = (
        "https://baseballsavant.mlb.com/statcast_search/csv?"
        f"all=true&hfSea=2025&hfFlag=player_type=pitcher&hfGames=on&"
        f"startDate={start}&endDate={end}&sort_col=k_percent&sort_order=desc"
    )
    response = requests.get(url)
    df = pd.read_csv(StringIO(response.text))
    df = df[df["batters_faced"] >= 50]  # Filter for starters
    df = df[df["role"] == "Starting"]
    return df[["player_name", "team", "k_percent"]].rename(columns={"k_percent": "p_k_pct"})

# Match batters to pitchers by team
def calculate_whiff_scores():
    batters = fetch_top_batters()
    pitchers = fetch_starting_pitchers()
    matchups = []

    for _, batter in batters.iterrows():
        team = batter["team"]
        match = pitchers[pitchers["team"] == team]
        if not match.empty:
            pitcher = match.iloc[0]
            score = batter["b_k_pct"] + pitcher["p_k_pct"]
            matchups.append({
                "name": batter["player_name"],
                "team": team,
                "pitcher": pitcher["player_name"],
                "batter_k_pct": round(batter["b_k_pct"], 2),
                "pitcher_k_pct": round(pitcher["p_k_pct"], 2),
                "whiff_score": round(score, 2),
            })

    return sorted(matchups, key=lambda x: -x["whiff_score"])

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
