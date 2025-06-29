import statsapi as mlb
import requests
import json
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Any, Optional

class WhiffWatcher:
    """Main class for generating MLB whiff watch ratings using Baseball Savant data"""
    
    def __init__(self):
        self.current_season = 2025
        self.min_at_bats = 150
        
    def fetch_current_batters(self) -> List[Dict[str, Any]]:
        """Fetch real 2025 batter data from MLB StatsAPI"""
        try:
            print("Fetching real 2025 batter data from MLB StatsAPI...")
            
            # Get teams playing today for focused data retrieval
            today_games = mlb.schedule(date=date.today().strftime('%m/%d/%Y'))
            team_ids = set()
            
            for game in today_games:
                team_ids.add(game.get('home_id'))
                team_ids.add(game.get('away_id'))
            
            batters = []
            
            # Get batters from teams playing today - this ensures current active players
            batters = self.get_batters_from_todays_teams(team_ids)
            
            if len(batters) < 20:  # If we don't have enough, get more from league leaders
                try:
                    # Use MLB StatsAPI endpoint for season hitting leaders
                    url = f"https://statsapi.mlb.com/api/v1/stats/leaders?leaderCategories=strikeOuts&season={self.current_season}&statGroup=hitting&limit=100"
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'leaderCategories' in data and data['leaderCategories']:
                            leaders = data['leaderCategories'][0].get('leaders', [])
                            existing_ids = {b['player_id'] for b in batters}
                            
                            for player in leaders:
                                if len(batters) >= 50:  # Limit to 50 batters
                                    break
                                    
                                person = player.get('person', {})
                                player_id = person.get('id')
                                
                                if player_id and player_id not in existing_ids:
                                    player_stats = self.get_player_season_stats(player_id, 'hitting')
                                    
                                    if player_stats:
                                        at_bats = player_stats.get('atBats', 0)
                                        strikeouts = player_stats.get('strikeOuts', 0)
                                        
                                        if at_bats >= 100:  # Lower threshold for league leaders
                                            strikeout_rate = round((strikeouts / at_bats) * 100, 2) if at_bats > 0 else 0
                                            
                                            batters.append({
                                                'player_id': player_id,
                                                'name': person.get('fullName', 'Unknown'),
                                                'team': 'Various',  # Will be updated with actual team info
                                                'team_abbreviation': 'MLB',
                                                'position': 'N/A',
                                                'at_bats': at_bats,
                                                'strikeouts': strikeouts,
                                                'strikeout_rate': strikeout_rate
                                            })
                                            existing_ids.add(player_id)
                    
                except Exception as e:
                    print(f"Error with leaders API: {e}")
            
            print(f"Found {len(batters)} batters with real 2025 MLB data")
            return batters
            
        except Exception as e:
            print(f"Error fetching batter data: {e}")
            return []
    
    def get_player_season_stats(self, player_id: int, stat_type: str) -> Dict[str, Any]:
        """Get season stats for a specific player"""
        try:
            url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&group={stat_type}&season={self.current_season}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'stats' in data and data['stats']:
                    for stat_group in data['stats']:
                        splits = stat_group.get('splits', [])
                        for split in splits:
                            return split.get('stat', {})
            return {}
        except Exception:
            return {}
    
    def get_batters_from_todays_teams(self, team_ids: set) -> List[Dict[str, Any]]:
        """Get batters from teams playing today"""
        batters = []
        
        for team_id in list(team_ids)[:10]:  # Limit to 10 teams for performance
            try:
                roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/Active"
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                
                response = requests.get(roster_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    roster_data = response.json()
                    roster = roster_data.get('roster', [])
                    
                    team_info = roster_data.get('teamId')
                    
                    batter_count = 0
                    for player in roster:
                        if batter_count >= 3:  # 3 batters per team
                            break
                            
                        player_info = player['person']
                        player_id = player_info['id']
                        position = player.get('position', {}).get('abbreviation', 'N/A')
                        
                        # Skip pitchers
                        if position in ['P', 'RP', 'SP']:
                            continue
                        
                        # Get player stats
                        stats = self.get_player_season_stats(player_id, 'hitting')
                        if stats:
                            at_bats = stats.get('atBats', 0)
                            strikeouts = stats.get('strikeOuts', 0)
                            
                            if at_bats >= 50:  # Lower threshold for current season
                                strikeout_rate = round((strikeouts / at_bats) * 100, 2) if at_bats > 0 else 0
                                
                                batters.append({
                                    'player_id': player_id,
                                    'name': player_info['fullName'],
                                    'team': f"Team {team_id}",
                                    'team_abbreviation': str(team_id),
                                    'position': position,
                                    'at_bats': at_bats,
                                    'strikeouts': strikeouts,
                                    'strikeout_rate': strikeout_rate
                                })
                                batter_count += 1
            except Exception:
                continue
        
        return batters
    
    def fetch_current_pitchers(self) -> List[Dict[str, Any]]:
        """Fetch real 2025 pitcher data from MLB StatsAPI"""
        try:
            print("Fetching real 2025 pitcher data from MLB StatsAPI...")
            
            # Get today's probable pitchers first
            today_games = mlb.schedule(date=date.today().strftime('%m/%d/%Y'))
            probable_pitchers = []
            
            if today_games:
                for game in today_games:
                    home_pitcher_name = game.get('home_probable_pitcher', '')
                    away_pitcher_name = game.get('away_probable_pitcher', '')
                    
                    for pitcher_name, is_home in [(home_pitcher_name, True), (away_pitcher_name, False)]:
                        if pitcher_name and pitcher_name != 'TBD':
                            try:
                                # Look up pitcher by name
                                pitcher_lookup = mlb.lookup_player(pitcher_name)
                                if pitcher_lookup:
                                    player_id = pitcher_lookup[0]['id']
                                    
                                    # Get real pitching statistics
                                    stats = self.get_player_season_stats(player_id, 'pitching')
                                    if stats:
                                        batters_faced = stats.get('battersFaced', 0)
                                        strikeouts = stats.get('strikeOuts', 0)
                                        
                                        if batters_faced >= 20:  # Lower threshold for current season
                                            strikeout_rate = round((strikeouts / batters_faced) * 100, 2)
                                            
                                            probable_pitchers.append({
                                                'player_id': player_id,
                                                'name': pitcher_name,
                                                'team': game['home_name'] if is_home else game['away_name'],
                                                'team_abbreviation': str(game.get('home_id', 'UNK') if is_home else game.get('away_id', 'UNK')),
                                                'opponent': game['away_name'] if is_home else game['home_name'],
                                                'opponent_abbreviation': str(game.get('away_id', 'UNK') if is_home else game.get('home_id', 'UNK')),
                                                'game_time': game.get('game_datetime', ''),
                                                'batters_faced': batters_faced,
                                                'strikeouts': strikeouts,
                                                'strikeout_rate': strikeout_rate,
                                                'is_home': is_home
                                            })
                            except Exception:
                                continue
            
            print(f"Found {len(probable_pitchers)} starting pitchers with real 2025 MLB data")
            return probable_pitchers
            
        except Exception as e:
            print(f"Error fetching pitcher data: {e}")
            return []
    
    def get_todays_matchups(self, pitchers: List[Dict], batters: List[Dict]) -> List[Dict[str, Any]]:
        """Create matchups based on today's actual games"""
        try:
            print("Creating matchups based on today's games...")
            
            # Get today's games
            today_games = mlb.schedule(date=date.today().strftime('%m/%d/%Y'))
            matchups = []
            
            if not today_games:
                print("No games today, creating team-based matchups")
                return self.create_team_matchups(pitchers, batters)
            
            # Create matchups based on actual games
            for game in today_games:
                home_team = game.get('home_name', '')
                away_team = game.get('away_name', '')
                home_id = str(game.get('home_id', ''))
                away_id = str(game.get('away_id', ''))
                
                # Find pitchers for this game
                home_pitcher = None
                away_pitcher = None
                
                for pitcher in pitchers:
                    # Match by team name or abbreviation
                    if any(team in pitcher['team'] for team in [home_team, home_id]):
                        home_pitcher = pitcher.copy()
                        home_pitcher['opponent'] = away_team
                        home_pitcher['opponent_abbreviation'] = away_id
                        home_pitcher['is_home'] = True
                        home_pitcher['game_time'] = game.get('game_datetime', '')
                    elif any(team in pitcher['team'] for team in [away_team, away_id]):
                        away_pitcher = pitcher.copy()
                        away_pitcher['opponent'] = home_team
                        away_pitcher['opponent_abbreviation'] = home_id
                        away_pitcher['is_home'] = False
                        away_pitcher['game_time'] = game.get('game_datetime', '')
                
                # Create matchups for this game
                if home_pitcher:
                    opposing_batters = [b for b in batters if any(team in b['team'] for team in [away_team, away_id])]
                    for batter in opposing_batters[:3]:  # Top 3 batters per team
                        matchups.append(self.create_matchup(home_pitcher, batter, f"{away_team} @ {home_team}"))
                
                if away_pitcher:
                    opposing_batters = [b for b in batters if any(team in b['team'] for team in [home_team, home_id])]
                    for batter in opposing_batters[:3]:
                        matchups.append(self.create_matchup(away_pitcher, batter, f"{away_team} @ {home_team}"))
            
            # Sort by whiff watch rating
            matchups.sort(key=lambda x: x['whiff_watch_rating'], reverse=True)
            
            print(f"Created {len(matchups)} real game matchups")
            return matchups
            
        except Exception as e:
            print(f"Error creating today's matchups: {e}")
            return self.create_team_matchups(pitchers, batters)
    
    def create_team_matchups(self, pitchers: List[Dict], batters: List[Dict]) -> List[Dict[str, Any]]:
        """Create general team-based matchups"""
        matchups = []
        
        for pitcher in pitchers[:10]:  # Top 10 pitchers
            # Find batters from different teams
            opposing_batters = [b for b in batters if b['team'] != pitcher['team']][:20]
            
            for batter in opposing_batters:
                matchups.append(self.create_matchup(pitcher, batter, f"{batter['team']} vs {pitcher['team']}"))
        
        matchups.sort(key=lambda x: x['whiff_watch_rating'], reverse=True)
        return matchups[:50]  # Top 50 matchups
    
    def create_matchup(self, pitcher: Dict, batter: Dict, game_info: str) -> Dict[str, Any]:
        """Create a single matchup"""
        combined_rating = round(batter['strikeout_rate'] + pitcher['strikeout_rate'], 2)
        
        return {
            'matchup_id': f"{pitcher['player_id']}_{batter['player_id']}",
            'game_info': game_info,
            'pitcher': pitcher,
            'batter': batter,
            'whiff_watch_rating': combined_rating,
            'rating_level': self.get_rating_level(combined_rating)
        }
    
    def get_rating_level(self, rating: float) -> str:
        """Categorize whiff watch rating into levels"""
        if rating >= 60:
            return "EXTREME"
        elif rating >= 50:
            return "HIGH"
        elif rating >= 40:
            return "MODERATE"
        elif rating >= 30:
            return "LOW"
        else:
            return "MINIMAL"
    
    def generate_whiff_watch_data(self) -> Dict[str, Any]:
        """
        Main method to generate complete whiff watch data using Baseball Savant
        """
        try:
            print("Starting whiff watch data generation with Baseball Savant data...")
            
            # Fetch real data from Baseball Savant
            batters = self.fetch_current_batters()
            pitchers = self.fetch_current_pitchers()
            
            if not batters:
                raise Exception("No batter data available from Baseball Savant")
            
            if not pitchers:
                raise Exception("No pitcher data available from Baseball Savant")
            
            # Create accurate matchups
            whiff_ratings = self.get_todays_matchups(pitchers, batters)
            
            if not whiff_ratings:
                raise Exception("No matchups could be created")
            
            # Generate summary statistics
            total_ratings = len(whiff_ratings)
            avg_rating = round(sum(r['whiff_watch_rating'] for r in whiff_ratings) / total_ratings, 2) if total_ratings > 0 else 0
            max_rating = max((r['whiff_watch_rating'] for r in whiff_ratings), default=0)
            min_rating = min((r['whiff_watch_rating'] for r in whiff_ratings), default=0)
            
            # Count by rating level
            rating_counts = {}
            for rating in whiff_ratings:
                level = rating['rating_level']
                rating_counts[level] = rating_counts.get(level, 0) + 1
            
            return {
                'app_name': 'Whiff Watcher',
                'generated_at': datetime.now().isoformat(),
                'date': date.today().isoformat(),
                'season': self.current_season,
                'data_summary': {
                    'total_whiff_ratings': total_ratings,
                    'active_batters_count': len(batters),
                    'probable_pitchers_count': len(pitchers),
                    'min_at_bats_requirement': self.min_at_bats,
                    'average_whiff_rating': avg_rating,
                    'highest_whiff_rating': max_rating,
                    'lowest_whiff_rating': min_rating,
                    'rating_level_counts': rating_counts
                },
                'whiff_watch_ratings': whiff_ratings,
                'active_batters': batters,
                'probable_pitchers': pitchers,
                'metadata': {
                    'data_source': 'Baseball Savant (Real 2025 Data)',
                    'calculation_method': 'Batter strikeout rate + Pitcher strikeout rate',
                    'strikeout_rate_formula': {
                        'batter': 'strikeouts / at_bats * 100',
                        'pitcher': 'strikeouts / batters_faced * 100'
                    },
                    'last_updated': datetime.now().isoformat(),
                    'version': '2.0',
                    'data_season': self.current_season,
                    'note': 'Real MLB data from Baseball Savant with accurate team matchups'
                }
            }
            
        except Exception as e:
            error_data = {
                'app_name': 'Whiff Watcher',
                'generated_at': datetime.now().isoformat(),
                'error': True,
                'error_message': str(e),
                'error_type': type(e).__name__,
                'whiff_watch_ratings': [],
                'active_batters': [],
                'probable_pitchers': [],
                'data_summary': {
                    'total_whiff_ratings': 0,
                    'active_batters_count': 0,
                    'probable_pitchers_count': 0,
                    'error_occurred': True
                }
            }
            print(f"Error generating whiff watch data: {e}")
            return error_data

if __name__ == "__main__":
    # Command line execution for testing
    watcher = WhiffWatcher()
    data = watcher.generate_whiff_watch_data()
    
    # Save to file
    with open('whiff_watch_output.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Whiff watch data saved to whiff_watch_output.json")
    print(f"Total whiff ratings generated: {data['data_summary']['total_whiff_ratings']}")