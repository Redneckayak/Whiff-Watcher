from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import datetime
import csv
import io

app = FastAPI()

# Allow CORS for frontend use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class PlayerRanking(BaseModel):
    name: str
    team: str
    pitcher: str
    batter_k_pct: float
    pitcher_k_pct: float
    whiff_score: float

class WhiffRankings(BaseModel):
    rankings: list[PlayerRanking]

# Root check
@app.get("/")
def root():
    return {"message": "Whiff Watcher API is live"}

# Get YTD date range
def get_date_range():
    today = datetime.date.today()
    return "2025-03-20", today.strftime("%Y-%m-%d")  # Opening Day to today

# Fetch and parse batter strikeout data from Statcast
def fetch_batter_k_data():
    start, end = get_date_range()
    url = (
        f"https://baseballsavant.mlb.com/statcast_search/csv?"
        f"all=true&hfSea=2025&hfFlag=&player_type=batter&hfGames=on&"
        f"hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    )
    print("Fetching batter CSV from:", url)
    res = requests.get(url)
    decoded = res.content.decode("utf-8")
    f = io.StringIO(decoded)
    reader = csv.DictReader(f)

    batters = []
    for row in reader:
        try:
            ab = int(row.get("AB", 0))
            k_pct = float(row.get("K%", 0.0))
            if ab >= 30:
                batters.append({
                    "name": row["Player"],
                    "team": row.get("Team", ""),
                    "k_pct": k_pct,
                })
        except Exception as e:
            print("Error parsing batter row:", row)
            continue

        if len(batters) >= 200:
            break

    print("Loaded batters:", len(batters))
    return batters

# Fetch and parse pitcher strikeout data from Statcast
def fetch_pitcher_k_data():
    start, end = get_date_range()
    url = (
        f"https://baseballsavant.mlb.com/statcast_search/csv?"
        f"all=true&hfSea=2025&hfFlag=&player_type=pitcher&hfGames=on&"
        f"hfStartDate={start}&hfEndDate={end}&sort_col=k_percent&sort_order=desc"
    )
    print("Fetching pitcher CSV from:", url)
    res = requests.get(url)
    decoded = res.content.decode("utf-8")
    f = io.StringIO(decoded)
    reader = csv.DictReader(f)

    pitchers = []
    for row in reader:
        try:
            bf = int(row.get("BF", 0))
            k_pct = float(row.get("K%", 0.0))
            if bf >= 30:
                pitchers.append({
                    "name": row["Player"],
                    "team": row.get("Team", ""),
                    "k_pct": k_pct,
                })
        except Exception as e:
            print("Error parsing pitcher row:", row)
            continue

        if len(pitchers) >= 200:
            break

    print("Loaded pitchers:", len(pitchers))
    return pitchers

# Probable pitcher matchups from MLB API
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

    print("Loaded matchups:", len(matchups))
    return matchups

# Core logic
def calculate_whiff_scores():
    batters = fetch_batter_k_data()
    pitchers = fetch_pitcher_k_data()
    matchups = fetch_probable_pitchers()

    rankings = []

    for b in batters:
        for team, pitcher_name in matchups:
            if b["team"] == team:
                match = next((p for p in pitchers if p["name"] == pitcher_name), None)
                if match:
                    score = b["k_pct"] + match["k_pct"]
                    rankings.append({
                        "name": b["name"],
                        "team": b["team"],
                        "pitcher": pitcher_name,
                        "batter_k_pct": b["k_pct"],
                        "pitcher_k_pct": match["k_pct"],
                        "whiff_score": round(score, 2)
                    })

    print("Total rankings:", len(rankings))
    return sorted(rankings, key=lambda x: x["whiff_score"], reverse=True)

# Endpoint
@app.get("/whiff-rankings", response_model=WhiffRankings)
def get_whiff_rankings():
    try:
        rankings = calculate_whiff_scores()
        return {"rankings": rankings}
    except Exception as e:
        print("ERROR in /whiff-rankings:", e)
        return {"rankings": []}
