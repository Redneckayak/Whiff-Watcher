from fastapi import FastAPI
from whiff_rankings import WhiffRankings
from datetime import date

app = FastAPI()

@app.get("/whiff-rankings")
def whiff_rankings():
    today = str(date.today())
    rankings = WhiffRankings(today).get_rankings()
    return {"rankings": rankings}
