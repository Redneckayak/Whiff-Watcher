from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import requests
from io import StringIO
from datetime import datetime

app = FastAPI()

class WhiffRanking(BaseModel):
    name: str
    team: str
    pitcher: str
    batter_k_pct: float
    pitcher_k_pct: float
    whiff_score: float

class WhiffRankings(BaseModel):
    rankings: list[WhiffRanking]

# Constants
START_DATE = "2025-03-20"
END_DATE = datetime.today().strftime("%Y-%m-%d")

def fetch_top_batters():
    url = (
        f"https://baseballsavant.mlb.com/statcast_search/csv?"
        f"all=true&hfSea=2025&hfFlag=player_type=batter"
        f"&hfGames=on&hfStartDate={START_DATE}&hfEndDate={END_DATE}"
        f"&sort_col=k_percent&sort_order=desc"
    )
    res = requests.get(url)
    df = pd.read_csv(StringIO(res.text), engine="python")
    df = df[df["ab"] > 200]  # Minimum 200 AB
    return df[["player_name", "team", "k_percent"]].rename(columns={"k_percent": "b_k_pct"})

def fetch_starting_pitchers():
    url = (
        f"https://baseballsavant.mlb.com/statcast_search/csv?"
        f"all=true&hfSea=2025&hfFlag=player_type=pitcher"
        f"&hfGames=on&hfStartDate={START_DATE}&hfEndDate={END_DATE}"
        f"&sort_col=k_percent&sort_order=desc"
    )
    res = requests.get(url)
    df = pd.read_csv(StringIO(res.text), engine="python")
    df = df[(df["batters_faced"] > 50) & (df["role"] == "Starting")]
    return df[["player_name", "team", "k_percent"]].rename(columns={"k_percent": "p_k_pct"})

def calculate_whiff_scores():
    batters = fetch_top_batters().head(100)  # Top 100 K% batters
    pitchers = fetch_starting_pitchers()     # Up to 30 SPs

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
