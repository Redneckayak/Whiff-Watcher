from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import datetime
import csv
import io

app = FastAPI()

# Allow all CORS
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

# Date range
def get_date_range():
    return "2025-03-20", datetime.date.today().strftime("%Y-%m-%d")

# Fetch & parse Statcast CSVs
def fetch_csv(url):
    response = requests.get(url)
    content = response.content.decode("utf-8")
    return list(csv.DictReader(io.StringIO(content)))

# Fetch and filter top 10 batters
def fetch_batter_k_data():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&player_type=batter&hfSea=2025&hfGames=on&hfStartDate={start}&hfEndDate={end}&hfAB=200"
    rows = fetch_csv(url)
    batters = []
    for row in rows[:10]:  # Top 10 only
        try:
            k_pct = float(row.get("K%", "0").replace("%", ""))
            ab = int(row.get("AB", "0"))
            if ab >= 200:
                batters.append({"name": row["Player"], "team": row["Team"], "k_pct": k_pct})
        except:
            continue
    return batters

# Fetch and filter top 10 pitchers
def fetch_pitcher_k_data():
    start, end = get_date_range()
    url = f"https://baseballsavant.mlb.com/statcast_search/csv?all=true&player_type=pitcher&hfSea=2025&hfGames=on&hfStartDate={start}&hfEndDate={end}&hfBF=50"
    rows = fetch_csv(url)
    pitchers = []
    for row in rows[:10]:  # Top 10 only
        try:
            k_pct = float(row.get("K%", "0").replace("%", ""))
            bf = int(row.get("BF", "0"))
            if bf >= 50:
                pitchers.append({"name": row["Player"], "team": row["Team"], "k_pct": k_pct})
        except:
            continue
    return pitchers

# Match batters vs pitchers by team (test logic)
def calculate_whiff_scores():
    batters = fetch_batter_k_data()
    pitchers = fetch_pitcher_k_data()

    rankings = []
    for b in batters:
        for p in pitchers:
            if b["team"] == p["team"]:  # crude match logic
                score = b["k_pct"] + p["k_pct"]
                rankings.append({
                    "name": b["name"],
                    "team": b["team"],
                    "pitcher": p["name"],
                    "batter_k_pct": b["k_pct"],
                    "pitcher_k_pct": p["k_pct"],
                    "whiff_score": round(score, 2)
                })
    return sorted(rankings, key=lambda x: x["whiff_score"], reverse=True)

@app.get("/")
def root():
    return {"message": "Whiff Watcher API is live"}

@app.get("/whiff-rankings", response_model=WhiffRankings)
def get_whiff_rankings():
    try:
        rankings = calculate_whiff_scores()
        return {"rankings": rankings}
    except Exception as e:
        print("ERROR:", e)
        return {"rankings": []}
