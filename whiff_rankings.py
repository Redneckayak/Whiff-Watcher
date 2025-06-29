from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import datetime

app = FastAPI()

# Enable CORS for all origins
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

# Helper to get date range for season
def get_date_range():
    return "2025-03-28", datetime.datetime.now().strftime("%Y-%m-%d")

# Fetch batter data from Statcast
def fetch_batter_k_data():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfPT=&hfAB=&hfBB=&hfSO=&hfPull=&hfCenter=&hfOpp=&hfZ=&hfStadium=&hfBBL=&hfNewZones=&hfGT=R%7C&hfC=&hfSea=2025&hfSit=&player_type=batter&hfOuts=&opponent=&pitcher_throws=&batter_stands=&hfSA=&game_date_gt={start}&game_date_lt={end}&hfInfield=&team=&position=&home_road=&metric_1=K%25&sort_col=K%25&sort_order=desc"

    res = requests.get(url)
    lines = res.text.splitlines()
    headers = lines[0].split(',')
    rows = [line.split(',') for line in lines[1:]]

    rankings = []
    for row in rows:
        data = dict(zip(headers, row))
        try:
            ab = int(data.get("ab", 0))
            so = int(data.get("so", 0))
            if ab >= 30:
                k_pct = round((so / ab) * 100, 1)
                rankings.append({
                    "name": data.get("player_name", "Unknown"),
                    "team": data.get("team", "UNK"),
                    "k_pct": k_pct
                })
        except:
            continue

    return rankings

# Fetch pitcher data from Statcast
def fetch_pitcher_k_data():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfPT=&hfAB=&hfBB=&hfSO=&hfPull=&hfCenter=&hfOpp=&hfZ=&hfStadium=&hfBBL=&hfNewZones=&hfGT=R%7C&hfC=&hfSea=2025&hfSit=&player_type=pitcher&hfOuts=&opponent=&pitcher_throws=&batter_stands=&hfSA=&game_date_gt={start}&game_date_lt={end}&hfInfield=&team=&position=&home_road=&metric_1=K%25&sort_col=K%25&sort_order=desc"

    res = requests.get(url)
    lines = res.text.splitlines()
    headers = lines[0].split(',')
    rows = [line.split(',') for line in lines[1:]]

    rankings = []
    for row in rows:
        data = dict(zip(headers, row))
        try:
            bf = int(data.get("batters_faced", 0))
            so = int(data.get("so", 0))
            if bf >= 30:
                k_pct = round((so / bf) * 100, 1)
                rankings.append({
                    "name": data.get("player_name", "Unknown"),
                    "team": data.get("team", "UNK"),
                    "k_pct": k_pct
                })
        except:
            continue

    return rankings

# Probable pitcher matchups
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

# Combine to calculate Whiff Score
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
