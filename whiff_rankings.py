from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import datetime

app = FastAPI()

# Enable CORS
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

# Root endpoint (optional)
@app.get("/")
def root():
    return {"message": "Whiff Watcher API is live"}

# Get last 30-day date range for Statcast
def get_date_range():
    end = datetime.date.today()
    start = end - datetime.timedelta(days=30)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

# Fetch batter K% from Statcast (using AB and SO)
def fetch_batter_k_data():
    start_date, end_date = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfPT=&hfAB=&hfBBT=&hfPR=&hfZ=&stadium=&hfBBL=&hfNewZones=&hfGT=R%7C&hfC=&hfSea=2025&hfSit=&player_type=batter&hfOuts=&opponent=&pitcher_throws=&batter_stands=&hfSA=&game_date_gt={start_date}&game_date_lt={end_date}&team=&position=&hfRO=&home_road=&hfFlag=&hfPull=&metric_1=&hfInn=&min_pitches=1&min_results=0&group_by=name&sort_col=pitches&player_event_sort=api_p_release_speed&sort_order=desc&min_pas=1&type=batter"

    response = requests.get(url)
    lines = response.text.splitlines()
    header = lines[0].split(",")
    data = lines[1:]

    name_idx = header.index("player_name")
    team_idx = header.index("team")
    ab_idx = header.index("ab")
    so_idx = header.index("so")

    batters = []
    for row in data:
        cols = row.split(",")
        try:
            ab = int(cols[ab_idx])
            so = int(cols[so_idx])
            if ab >= 15:
                k_pct = round(100 * so / ab, 2)
                batters.append({
                    "name": cols[name_idx],
                    "team": cols[team_idx],
                    "k_pct": k_pct
                })
        except:
            continue
    return batters

# Fetch pitcher K% from Statcast (using BF and SO)
def fetch_pitcher_k_data():
    start_date, end_date = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&hfPT=&hfAB=&hfBBT=&hfPR=&hfZ=&stadium=&hfBBL=&hfNewZones=&hfGT=R%7C&hfC=&hfSea=2025&hfSit=&player_type=pitcher&hfOuts=&opponent=&pitcher_throws=&batter_stands=&hfSA=&game_date_gt={start_date}&game_date_lt={end_date}&team=&position=&hfRO=&home_road=&hfFlag=&hfPull=&metric_1=&hfInn=&min_pitches=1&min_results=0&group_by=name&sort_col=pitches&player_event_sort=api_p_release_speed&sort_order=desc&min_pas=1&type=pitcher"

    response = requests.get(url)
    lines = response.text.splitlines()
    header = lines[0].split(",")
    data = lines[1:]

    name_idx = header.index("player_name")
    team_idx = header.index("team")
    bf_idx = header.index("batters_faced")
    so_idx = header.index("so")

    pitchers = []
    for row in data:
        cols = row.split(",")
        try:
            bf = int(cols[bf_idx])
            so = int(cols[so_idx])
            if bf >= 20:
                k_pct = round(100 * so / bf, 2)
                pitchers.append({
                    "name": cols[name_idx],
                    "team": cols[team_idx],
                    "k_pct": k_pct
                })
        except:
            continue
    return pitchers

# Fetch matchups from MLB API
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

# Compute Whiff Scores
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

# API endpoint
@app.get("/whiff-rankings", response_model=WhiffRankings)
def get_whiff_rankings():
    try:
        rankings = calculate_whiff_scores()
        return {"rankings": rankings}
    except Exception as e:
        print("ERROR in /whiff-rankings:", e)
        return {"rankings": []}
