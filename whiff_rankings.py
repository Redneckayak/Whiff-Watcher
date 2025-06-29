from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import datetime

app = FastAPI()

# Allow all CORS (safe for dev or public API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class PlayerRanking(BaseModel):
    name: str
    team: str
    pitcher: str
    batter_k_pct: float
    pitcher_k_pct: float
    whiff_score: float

class WhiffRankings(BaseModel):
    rankings: list[PlayerRanking]

# Root route for health check
@app.get("/")
def root():
    return {"message": "Whiff Watcher API is live"}

# Fetch probable pitchers from MLB API
def fetch_probable_pitchers():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=team,probablePitcher(note),linescore"
    res = requests.get(url)
    data = res.json()

    matchups = []
    for date in data.get("dates", []):
        for game in date.get("games", []):
            away_team = game["teams"]["away"]["team"]["abbreviation"]
            home_team = game["teams"]["home"]["team"]["abbreviation"]
            away_pitcher = game["teams"]["away"].get("probablePitcher", {}).get("fullName")
            home_pitcher = game["teams"]["home"].get("probablePitcher", {}).get("fullName")

            if away_pitcher:
                matchups.append((home_team, away_pitcher))
            if home_pitcher:
                matchups.append((away_team, home_pitcher))

    return matchups

# Fetch batter strikeout data
def fetch_batter_k_data(min_pa=200):
    url = "https://www.fangraphs.com/api/leaders/board?pos=all&stats=bat&lg=all&qual=0&type=8&season=2025&month=1000&season1=2025&startdate=2025-03-01&enddate=2025-12-01&ind=0&team=0&rost=0&age=0&filter=&players=0&pageitems=5000"
    res = requests.get(url)
    batters = res.json()["data"]

    filtered = []
    for b in batters:
        try:
            pa = int(b["PA"])
            if pa >= min_pa:
                filtered.append({
                    "name": b["PlayerName"],
                    "team": b["Team"],
                    "k_pct": float(b["K%"].replace('%', ''))
                })
        except:
            continue

    return filtered

# Fetch pitcher strikeout data
def fetch_pitcher_k_data():
    url = "https://www.fangraphs.com/api/leaders/board?pos=all&stats=pit&lg=all&qual=0&type=2&season=2025&month=1000&season1=2025&startdate=2025-03-01&enddate=2025-12-01&ind=0&team=0&rost=0&age=0&filter=&players=0&pageitems=5000"
    res = requests.get(url)
    pitchers = res.json()["data"]

    filtered = []
    for p in pitchers:
        try:
            filtered.append({
                "name": p["PlayerName"],
                "team": p["Team"],
                "k_pct": float(p["K%"].replace('%', ''))
            })
        except:
            continue

    return filtered

# Calculate Whiff Scores
def calculate_whiff_scores():
    batters = fetch_batter_k_data()
    pitchers = fetch_pitcher_k_data()
    matchups = fetch_probable_pitchers()

    rankings = []

    for b in batters:
        for team, pitcher_name in matchups:
            if b["team"] == team:
                matching_pitchers = [p for p in pitchers if p["name"] == pitcher_name]
                if matching_pitchers:
                    p = matching_pitchers[0]
                    score = b["k_pct"] + p["k_pct"]
                    rankings.append({
                        "name": b["name"],
                        "team": b["team"],
                        "pitcher": pitcher_name,
                        "batter_k_pct": b["k_pct"],
                        "pitcher_k_pct": p["k_pct"],
                        "whiff_score": round(score, 2)
                    })

    return sorted(rankings, key=lambda x: x["whiff_score"], reverse=True)

# API endpoint with error logging
@app.get("/whiff-rankings", response_model=WhiffRankings)
def get_whiff_rankings():
    try:
        rankings = calculate_whiff_scores()
        return {"rankings": rankings}
    except Exception as e:
        print("ERROR in /whiff-rankings:", e)
        return {"rankings": []}
