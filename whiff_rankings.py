import requests

class WhiffRankings:
    def __init__(self, date):
        self.date = date
        self.pitchers = self.get_probable_pitchers()
        self.batters = self.get_batters_over_200_pa()
        self.pitcher_stats = self.get_pitcher_k_stats()

    def get_probable_pitchers(self):
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={self.date}&hydrate=probablePitcher"
        res = requests.get(url).json()
        pitcher_by_team = {}

        for date in res.get("dates", []):
            for game in date.get("games", []):
                for side in ['home', 'away']:
                    team = game["teams"][side]
                    pitcher = team.get("probablePitcher")
                    if pitcher:
                        team_key = team["team"].get("abbreviation", "").upper()
                        if team_key:
                            pitcher_by_team[team_key] = {
                                "id": pitcher["id"],
                                "name": pitcher["fullName"],
                                "team": team_key
                            }

        return pitcher_by_team

    def get_batters_over_200_pa(self):
        url = "https://statsapi.mlb.com/api/v1/stats?stats=season&group=hitting&limit=3000"
        res = requests.get(url).json()
        players = []

        for row in res.get("stats", [])[0].get("splits", []):
            stat = row.get("stat", {})
            pa = stat.get("plateAppearances", 0)
            so = stat.get("strikeOuts", 0)

            if pa >= 200 and pa > 0:
                k_percent = round(so / pa * 100, 1)
                team = row["team"].get("abbreviation", "").upper()
                if team:
                    players.append({
                        "id": row["player"]["id"],
                        "name": row["player"]["fullName"],
                        "team": team,
                        "pa": pa,
                        "k_percent": k_percent,
                        "handedness": row.get("player", {}).get("batSide", {}).get("code", "R")
                    })

        return players

    def get_pitcher_k_stats(self):
        pitcher_ids = [str(p["id"]) for p in self.pitchers.values()]
        if not pitcher_ids:
            return {}

        ids_str = ",".join(pitcher_ids)
        url = f"https://statsapi.mlb.com/api/v1/stats?stats=season&group=pitching&playerIds={ids_str}"
        res = requests.get(url).json()
        k_stats = {}

        for row in res.get("stats", [])[0].get("splits", []):
            stat = row.get("stat", {})
            strikeouts = stat.get("strikeOuts", 0)
            batters_faced = stat.get("battersFaced", 0)

            if batters_faced > 0:
                k_percent = round(strikeouts / batters_faced * 100, 1)
                k_stats[row["player"]["id"]] = {
                    "k_percent": k_percent,
                    "handedness": row.get("player", {}).get("pitchHand", {}).get("code", "R")
                }

        return k_stats

    def get_rankings(self):
        results = []

        # Debug info
        print("✅ DEBUG — Total Batters:", len(self.batters))
        print("✅ DEBUG — Total Pitcher Teams:", len(self.pitchers))
        print("✅ DEBUG — Pitcher Teams:", list(self.pitchers.keys())[:5])
        print("✅ DEBUG — Sample Batters:", [b['name'] for b in self.batters[:5]])

        for batter in self.batters:
            opp_pitcher = self.pitchers.get(batter["team"])
            if not opp_pitcher:
                print(f"🔸 Skipping {batter['name']} (no SP for {batter['team']})")
                continue

            pitcher_stats = self.pitcher_stats.get(opp_pitcher["id"])
            if not pitcher_stats:
                print(f"⚠️ Skipping {batter['name']} — no pitcher stats for {opp_pitcher['name']}")
                continue

            whiff_score = round(batter["k_percent"] + pitcher_stats["k_percent"], 1)

            results.append({
                "player_name": batter["name"],
                "team": batter["team"],
                "batter_k_percent": batter["k_percent"],
                "plate_appearances": batter["pa"],
                "handedness": batter["handedness"],
                "pitcher_name": opp_pitcher["name"],
                "pitcher_team": opp_pitcher["team"],
                "pitcher_k_percent": pitcher_stats["k_percent"],
                "pitcher_handedness": pitcher_stats["handedness"],
                "whiff_score": whiff_score
            })

        print("✅ DEBUG — Final Matchups:", len(results))
        return sorted(results, key=lambda x: x["whiff_score"], reverse=True)
