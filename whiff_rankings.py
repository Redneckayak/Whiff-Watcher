from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import datetime
import csv
import io

app = FastAPI()

# Enable CORS for all origins (Bubble friendly)
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

# Get today's YTD range
def get_date_range():
    start = datetime.datetime(2025, 3, 20).strftime('%Y-%m-%d')  # MLB 2025 Opening Day
    end = datetime.datetime.today().strftime('%Y-%m-%d')
    return start, end

# Statcast: Fetch batter K% (min 200 AB)
def fetch_batter_k_data():
    start, end = get_date_range()
    url = (
        "https://baseballsavant.mlb.com/statcast_search/csv?"
        f"all=true&hfSea=2025&hfFlag=player_type=batter&hfGames=on&"
        f"hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    )
    res = requests.get(url)
    batters = []
    reader = csv.DictReader(io.StringIO(res.text))
    for row in reader:
        try:
            ab = int(row.get("ab", 0))
            if ab >= 200:
                batters.append({
                    "name": row["player_name"],
                    "team": row["team_name"],
                    "k_pct": float(row["k_percent"])
                })
        except:
            continue
    print(f"Loaded {len(batters)} batters")
    return batters

# Statcast: Fetch pitcher K% (min 50 BF)
def fetch_pitcher_k_data():
    start, end = get_date_range()
    url = (
        "https://baseballsavant.mlb.com/statcast_search/csv?"
        f"all=true&hfSea=2025&hfFlag=player_type=pitcher&hfGames=on&"
        f"hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    )
    res = requests.get(url)
    pitchers = []
    reader = csv.DictReader(io.StringIO(res.text))
    for row in reader:
        try:
            bf = int(row.get("batters_faced", 0))
            if bf >= 50:
                pitchers.append({
                    "name": row["player_name"],
                    "team": row["team_name"],
                    "k_pct": float(row["k_percent"])
                })
        except:
            continue
    print(f"Loaded {len(pitchers)} pitchers")
    return pitchers

# Probable pitcher matchups
def fetch_probable_pitchers():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=team,probablePitcher"
    res = requests.get(url)
    data = res.json()
    matchups = []
    for date in data.get("dates", []):
        for game in date.get("games", []):
            away_team = game["teams"]["away"]["team"]["name"]
            home_team = game["teams"]["home"]["team"]["name"]
            away_pitcher = game["teams"]["away"].get("probablePitcher", {}).get("fullName")
            home_pitcher = game["teams"]["home"].get("probablePitcher", {}).get("fullName")

            if away_pitcher:
                matchups.append((home_team, away_pitcher))
            if home_pitcher:
                matchups.append((away_team, home_pitcher))
    return matchups

# Combine logic
def calculate_whiff_scores():
    batters = fetch_batter_k_data()
    pitchers = fetch_pitcher_k_data()
    matchups = fetch_probable_pitchers()

    rankings = []
    for bf in batters:
        for team, pitcher_name in matchups:
            if bf["team"] == team:
                match = next((p for p in pitchers if p["name"] == pitcher_name), None)
                if match:
                    score = bf["k_pct"] + match["k_pct"]
                    rankings.append({
                        "name": bf["name"],
                        "team": bf["team"],
                        "pitcher": pitcher_name,
                        "batter_k_pct": bf["k_pct"],
                        "pitcher_k_pct": match["k_pct"],
                        "whiff_score": round(score, 2)
                    })

    return sorted(rankings, key=lambda x: x["whiff_score"], reverse=True)

# Root check (optional)
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
