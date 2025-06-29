from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import requests
import pandas as pd
from io import StringIO
from datetime import datetime

app = FastAPI()

class WhiffRankings(BaseModel):
    rankings: List[dict]

# Opening Day 2025
OPENING_DAY = datetime(2025, 3, 20)

def get_date_range():
    start = OPENING_DAY.strftime("%Y-%m-%d")
    end = datetime.today().strftime("%Y-%m-%d")
    return start, end

def fetch_top_batters():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfSea=2025&hfFlag=player_type=batter&hfGames=on&hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    response = requests.get(url)
    df = pd.read_csv(StringIO(response.text), sep=",", engine="python", on_bad_lines="skip")
    df = df[df["ab"] >= 200]
    df = df[["player_name", "team", "k_percent"]]
    df = df.rename(columns={"k_percent": "b_k_pct"})
    return df.head(100)

def fetch_starting_pitchers():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfSea=2025&hfFlag=player_type=pitcher&hfGames=on&hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    response = requests.get(url)
    df = pd.read_csv(StringIO(response.text), sep=",", engine="python", on_bad_lines="skip")
    df = df[df["batters_faced"] >= 50]
    df = df[df["role"] == "Starting"]
    df = df[["player_name", "team", "k_percent"]]
    df = df.rename(columns={"k_percent": "p_k_pct"})
    return df

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
