from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from datetime import datetime
import requests
from io import StringIO

app = FastAPI()

class WhiffRankings(BaseModel):
    rankings: list

def get_date_range():
    return "2025-03-20", datetime.today().strftime("%Y-%m-%d")

def fetch_top_batters():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfSea=2025&hfFlag=player_type=batter%7Cgamelog%7C&player_type=batter&hfGames=on&hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    res = requests.get(url)
    df = pd.read_csv(StringIO(res.text))
    df = df[df['ab'] >= 200]
    return df[["player_name", "team", "k_percent"]].rename(columns={"k_percent": "b_k_pct"})

def fetch_starting_pitchers():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfSea=2025&hfFlag=player_type=pitcher%7Cgamelog%7C&player_type=pitcher&hfGames=on&hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    res = requests.get(url)
    df = pd.read_csv(StringIO(res.text))
    df = df[df['role'] == "Starting"]
    df = df[df['batters_faced'] >= 50]
    return df[["player_name", "team", "k_percent"]].rename(columns={"k_percent": "p_k_pct"})

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

@app.get("/")
def root():
    return {"message": "Whiff Watcher API is live"}

@app.get("/whiff-rankings", response_model=WhiffRankings)
def get_whiff_rankings():
    try:
        rankings = calculate_whiff_scores()
        return {"rankings": rankings}
    except Exception as e:
        print("ERROR in /whiff-rankings:", e)
        return {"rankings": []}
