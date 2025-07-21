import discord
from discord import app_commands
from discord.ext import commands
import nfl_data_py as nfl
from nba_api.stats.static import players as nba_players
from nba_api.stats.endpoints import playerdashboardbyyearoveryear
from datetime import datetime
import pytz
from difflib import get_close_matches
from cachetools import TTLCache
import statsapi as mlbstats
import json
import os


DUMP_PATH = os.path.join(os.path.dirname(__file__), 'data', 'mlb_players_dump.json')

def save_player_cache(players: list):
    with open(DUMP_PATH, 'w', encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

import os
import json

def load_player_cache(path: str = "data/mlb_players_dump.json"):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Loaded {len(data)} players from cache.")
            return data
    except Exception as e:
        print(f"Error loading player cache: {e}")
        return []

    
def generate_player_dump(path: str = "data/mlb_players_dump.json"):
    players = mlbstats.lookup_player("")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)

mlb_players = load_player_cache()

nba_cache = TTLCache(maxsize=100, ttl=3600)
nfl_cache = TTLCache(maxsize=100, ttl=3600)
mlb_cache = TTLCache(maxsize=100, ttl=360)

OWNER_ID = 825106419333857312

class PlayerSelect(discord.ui.View):
    def __init__(self, matches: list, sport: str):
        super().__init__(timeout=30)
        self.matches = matches
        self.sport = sport
        
        for i, player_name in enumerate(matches[:3]):
            button = discord.ui.Button(label=player_name, custom_id=f"player_{i}", style=discord.ButtonStyle.primary, row=0)
            button.callback = self.create_callback(player_name)
            self.add_item(button)
    
    def create_callback(self, player_name: str):
        async def callback(interaction: discord.Interaction):
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            
            try:
                if self.sport == "NBA":
                    stats = await get_nba_stats(player_name, fuzzy_match=False)
                elif self.sport == "NFL":
                    stats = await get_nfl_stats(player_name, fuzzy_match=False)
                elif self.sport == "MLB":
                    stats = await get_mlb_stats(player_name, fuzzy_match=False)
                else:
                    pass
                if not stats:
                    await interaction.followup.send(f"Could not find stats for {player_name}.", ephemeral=True)
                    return
                
                em = create_stats_embed(stats, self.sport)
                await interaction.followup.send(embed=em)
                
            except Exception as e:
                await interaction.followup.send(f"An error occurred while fetching stats: {str(e)}", ephemeral=True)
        
        return callback

def create_stats_embed(stats: dict, sport: str) -> discord.Embed:
    polarpickscolor = 0xd6e1ff
    em = discord.Embed(title=f"{stats['name']} - {sport} Stats", color=polarpickscolor)
    
    if sport == "NBA":
        em.add_field(name="Points", value=str(stats['pts']), inline=True)
        em.add_field(name="Rebounds", value=str(stats['reb']), inline=True)
        em.add_field(name="Assists", value=str(stats['ast']), inline=True)
        em.add_field(name="Steals", value=str(stats['stl']), inline=True)
        em.add_field(name="Blocks", value=str(stats['blk']), inline=True)
        em.add_field(name="Turnovers", value=str(stats['tov']), inline=True)
        em.add_field(name="Minutes", value=str(stats['min']), inline=True)
    elif sport == "MLB":
        position = stats.get("position", "")
        player_stats = stats.get("stats", {})

        em.title = f"{stats['name']} - MLB Stats"
        em.set_footer(text=f"{player_stats.get('season', datetime.now().year)} Season")
        if position == 'P':
            em.add_field(name="ERA", value=player_stats.get("era", "N/A"), inline=True)
            em.add_field(name="WHIP", value=player_stats.get("whip", "N/A"), inline=True)
            em.add_field(name="Ks", value=player_stats.get("strikeOuts", "N/A"), inline=True)
            em.add_field(name="BB", value=player_stats.get("baseOnBalls", "N/A"), inline=True)
            pwins = player_stats.get("wins", "N/A")
            plosses = player_stats.get("losses", "N/A")
            em.add_field(name="W/L", value=f"{pwins}-{plosses}", inline=True)
            em.add_field(name="Saves", value=player_stats.get("saves", "N/A"), inline=True)
            em.add_field(name="Holds", value=player_stats.get("holds", "N/A"), inline=True)
            em.add_field(name="Blown Saves", value=player_stats.get("blownSaves", "N/A"), inline=True)
            em.add_field(name="IP", value=player_stats.get("inningsPitched", "N/A"), inline=True)
        else:
            em.add_field(name="AVG", value=player_stats.get("avg", "N/A"), inline=True)
            em.add_field(name="H", value=player_stats.get("hits", "N/A"), inline=True)
            em.add_field(name="AB", value=player_stats.get("atBats", "N/A"), inline=True)
            em.add_field(name="HR", value=player_stats.get("homeRuns", "N/A"), inline=True)
            em.add_field(name="RBI", value=player_stats.get("rbi", "N/A"), inline=True)
            em.add_field(name="TB", value=player_stats.get("totalBases", "N/A"), inline=True)
            em.add_field(name="SB", value=player_stats.get("stolenBases", "N/A"), inline=True)
            em.add_field(name="OBP", value=player_stats.get("obp", "N/A"), inline=True)
            em.add_field(name="SLG", value=player_stats.get("slg", "N/A"), inline=True)
            em.add_field(name="OPS", value=player_stats.get("ops", "N/A"), inline=True)

    elif sport == "NFL":
        if stats.get('position') in ['RG', 'LG', 'RT', 'LT', 'C']:
            return None
            
        em.title = f"{stats['name']} - NFL Stats"
        
        if stats['position'] == 'QB':
            em.add_field(name="Completions/Attempts", value=f"{stats['completions']}/{stats['attempts']} ({stats['completion_pct']}%)", inline=True)
            em.add_field(name="Pass Yards", value=str(stats['pass_yards']), inline=True)
            em.add_field(name="Rush Yards", value=str(stats['rush_yards']), inline=True)
            em.add_field(name="Touchdowns", value=str(stats['touchdowns']), inline=True)
            em.add_field(name="Interceptions", value=str(stats['interceptions']), inline=True)
            em.add_field(name="Fumbles", value=str(stats['fumbles']), inline=True)
        
        elif stats['position'] in ['WR', 'TE']:
            em.add_field(name="Receptions", value=str(stats['receptions']), inline=True)
            em.add_field(name="Receiving Yards", value=str(stats['rec_yards']), inline=True)
            em.add_field(name="Touchdowns", value=str(stats['touchdowns']), inline=True)
            em.add_field(name="Targets", value=str(stats['targets']), inline=True)
            em.add_field(name="Drops", value=str(stats['drops']), inline=True)
            em.add_field(name="Fumbles", value=str(stats['fumbles']), inline=True)
        
        elif stats['position'] in ['RB', 'FB']:
            em.add_field(name="Rush Yards", value=str(stats['rush_yards']), inline=True)
            em.add_field(name="Carries", value=str(stats['carries']), inline=True)
            em.add_field(name="Rush TDs", value=str(stats['rush_tds']), inline=True)
            em.add_field(name="Receiving Yards", value=str(stats['rec_yards']), inline=True)
            em.add_field(name="Receiving TDs", value=str(stats['rec_tds']), inline=True)
            em.add_field(name="Targets", value=str(stats['targets']), inline=True)
            em.add_field(name="Drops", value=str(stats['drops']), inline=True)
            em.add_field(name="Fumbles", value=str(stats['fumbles']), inline=True)
        
        elif stats['position'] in ['DT', 'DE']:
            em.add_field(name="Tackles", value=str(stats['tackles']), inline=True)
            em.add_field(name="Sacks", value=str(stats['sacks']), inline=True)
            em.add_field(name="Forced Fumbles", value=str(stats['forced_fumbles']), inline=True)
            em.add_field(name="Fumbles Recovered", value=str(stats['fumbles_recovered']), inline=True)
            em.add_field(name="Interceptions", value=str(stats['interceptions']), inline=True)
        
        elif stats['position'] in ['LB', 'CB', 'S']:
            em.add_field(name="Tackles", value=str(stats['tackles']), inline=True)
            em.add_field(name="Sacks", value=str(stats['sacks']), inline=True)
            em.add_field(name="Interceptions", value=str(stats['interceptions']), inline=True)
            em.add_field(name="Deflections", value=str(stats['deflections']), inline=True)
            em.add_field(name="Passes Defended", value=str(stats['passes_defended']), inline=True)
            em.add_field(name="Forced Fumbles", value=str(stats['forced_fumbles']), inline=True)
            em.add_field(name="Fumbles Recovered", value=str(stats['fumbles_recovered']), inline=True)
        
        elif stats['position'] == 'K':
            em.add_field(name="Field Goals", value=f"{stats['fg_made']}/{stats['fg_attempts']}", inline=True)
            em.add_field(name="Extra Points", value=f"{stats['xp_made']}/{stats['xp_attempts']}", inline=True)
    
    em.set_footer(text=f"Last Updated: {datetime.now(pytz.timezone('EST')).strftime('%Y-%m-%d %H:%M:%S EST')}")
    return em

async def get_nba_stats(player_name: str, fuzzy_match: bool = True) -> dict:
    cache_key = player_name.lower()
    
    if cache_key in nba_cache:
        return nba_cache[cache_key]
        
    try:
        all_players = nba_players.get_players()
        player_names = [p['full_name'].lower() for p in all_players]
        
        close_matches = get_close_matches(player_name.lower(), player_names, n=3, cutoff=0.6)
        
        if not close_matches:
            return None
            
        best_match = close_matches[0]
        player = next(p for p in all_players if p['full_name'].lower() == best_match)
        
        player_id = player['id']
        
        current_year = datetime.now().year
        if datetime.now().month < 8:
            current_year -= 1
        season = f"{current_year}-{str(current_year + 1)[2:]}"
        
        stats_data = playerdashboardbyyearoveryear.PlayerDashboardByYearOverYear(
            player_id=player_id,
            per_mode_detailed="PerGame",
            season=season
        )
        
        current_stats = stats_data.get_data_frames()[0]
        
        if current_stats.empty:
            return None
            
        stats = {
            'name': player['full_name'],
            'pts': round(float(current_stats['PTS'].iloc[0]), 1),
            'reb': round(float(current_stats['REB'].iloc[0]), 1),
            'ast': round(float(current_stats['AST'].iloc[0]), 1),
            'stl': round(float(current_stats['STL'].iloc[0]), 1),
            'blk': round(float(current_stats['BLK'].iloc[0]), 1),
            'tov': round(float(current_stats['TOV'].iloc[0]), 1),
            'min': round(float(current_stats['MIN'].iloc[0]), 1),
            'close_matches': close_matches[1:] if len(close_matches) > 1 else []
        }
        
        nba_cache[cache_key] = stats
        return stats
    except Exception as e:
        try:
            owner = await bot.fetch_user(OWNER_ID)
            await owner.send(f"Error fetching NBA stats for {player_name}: {str(e)}")
        except:
            pass
        print(f"Error fetching NBA stats: {str(e)}")
        return None

async def get_mlb_stats(player_name: str, fuzzy_match: bool = True) -> dict:
    cache_key = player_name.lower()

    if cache_key in mlb_cache:
        return mlb_cache[cache_key]
    
    try:
        all_players = load_player_cache()
        player_names = [p['fullName'].lower() for p in all_players]

        close_matches = get_close_matches(player_name.lower(), player_names, n=3, cutoff=0.6)
        
        if not close_matches:
            return None
        
        best_match = close_matches[0]
        player = next(p for p in all_players if p['fullName'].lower() == best_match)
        playerid = player['id']
        pos = player.get("primaryPosition", {}).get("abbreviation", "")
        group = "pitching" if pos == "P" else "hitting"
        raw = mlbstats.player_stat_data(playerid, group=group, type="season")

        if raw.get("stats") and raw["stats"][0].get("stats"):
            stat_obj = raw["stats"][0]["stats"]
            result = {
            "name": player["fullName"],
            "team": player["currentTeam"]["id"],
            "position": pos,
            "stats": stat_obj,
            "close_matches": close_matches[1:] if len(close_matches) > 1 else []
            }
            mlb_cache[cache_key] = result
            return result
        else:
            return None
    except Exception as e:
        print(f"Error fetching MLB stats: {str(e)}")
        return None

async def get_nfl_stats(player_name: str, fuzzy_match: bool = True) -> dict:
    cache_key = player_name.lower()
    
    if cache_key in nfl_cache:
        return nfl_cache[cache_key]
        
    try:
        current_year = datetime.now().year
        if datetime.now().month < 8:
            current_year -= 1
            
        player_stats = nfl.import_seasonal_rosters([current_year])
        weekly_stats = nfl.import_weekly_data([current_year])
        
        player_names = player_stats['player_name'].str.lower().tolist()
        
        close_matches = get_close_matches(player_name.lower(), player_names, n=3, cutoff=0.6)
        
        if not close_matches:
            return None
            
        best_match = close_matches[0]
        player = player_stats[player_stats['player_name'].str.lower() == best_match].iloc[0]
        position = player['position'].upper()
        
        if position in ['RG', 'LG', 'RT', 'LT', 'C']:
            result = {
                'name': player['player_name'], 
                'position': position,
                'close_matches': close_matches[1:] if len(close_matches) > 1 else []
            }
            nfl_cache[cache_key] = result
            return result
            
        player_weekly = weekly_stats[weekly_stats['player_id'] == player['player_id']]
        if player_weekly.empty:
            return None
            
        def safe_sum(df, column):
            if column in df.columns:
                return df[column].sum()
            return 0
            
        stats = {
            'name': player['player_name'],
            'position': position,
            'close_matches': close_matches[1:] if len(close_matches) > 1 else []
        }
        
        if position == 'QB':
            completions = safe_sum(player_weekly, 'completions')
            attempts = safe_sum(player_weekly, 'attempts')
            stats.update({
                'completions': int(completions),
                'attempts': int(attempts),
                'completion_pct': round(completions / attempts * 100, 1) if attempts > 0 else 0,
                'pass_yards': int(safe_sum(player_weekly, 'passing_yards')),
                'rush_yards': int(safe_sum(player_weekly, 'rushing_yards')),
                'touchdowns': int(safe_sum(player_weekly, 'passing_tds') + safe_sum(player_weekly, 'rushing_tds')),
                'interceptions': int(safe_sum(player_weekly, 'interceptions')),
                'fumbles': int(safe_sum(player_weekly, 'fumbles'))
            })
            
        elif position in ['WR', 'TE']:
            stats.update({
                'receptions': int(safe_sum(player_weekly, 'receptions')),
                'rec_yards': int(safe_sum(player_weekly, 'receiving_yards')),
                'touchdowns': int(safe_sum(player_weekly, 'receiving_tds')),
                'targets': int(safe_sum(player_weekly, 'targets')),
                'drops': int(safe_sum(player_weekly, 'drops')),
                'fumbles': int(safe_sum(player_weekly, 'fumbles'))
            })
            
        elif position in ['RB', 'FB']:
            stats.update({
                'rush_yards': int(safe_sum(player_weekly, 'rushing_yards')),
                'carries': int(safe_sum(player_weekly, 'carries')),
                'rush_tds': int(safe_sum(player_weekly, 'rushing_tds')),
                'rec_yards': int(safe_sum(player_weekly, 'receiving_yards')),
                'rec_tds': int(safe_sum(player_weekly, 'receiving_tds')),
                'targets': int(safe_sum(player_weekly, 'targets')),
                'drops': int(safe_sum(player_weekly, 'drops')),
                'fumbles': int(safe_sum(player_weekly, 'fumbles'))
            })
            
        elif position in ['DT', 'DE', 'LB', 'CB', 'S']:
            stats.update({
                'tackles': int(safe_sum(player_weekly, 'tackles')),
                'sacks': float(safe_sum(player_weekly, 'sacks')),
                'interceptions': int(safe_sum(player_weekly, 'interceptions')),
                'passes_defended': int(safe_sum(player_weekly, 'passes_defended')),
                'forced_fumbles': int(safe_sum(player_weekly, 'forced_fumbles')),
                'fumbles_recovered': int(safe_sum(player_weekly, 'fumbles_recovered'))
            })
            
        elif position == 'K':
            stats.update({
                'fg_made': int(safe_sum(player_weekly, 'field_goals_made')),
                'fg_attempts': int(safe_sum(player_weekly, 'field_goals_attempted')),
                'xp_made': int(safe_sum(player_weekly, 'extra_points_made')),
                'xp_attempts': int(safe_sum(player_weekly, 'extra_points_attempted'))
            })
            
        nfl_cache[cache_key] = stats
        return stats
        
    except Exception as e:
        try:
            owner = await bot.fetch_user(OWNER_ID)
            await owner.send(f"Error fetching NFL stats for {player_name}: {str(e)}")
        except:
            pass
        print(f"Error fetching NFL stats: {str(e)}")
        return None

async def fetch_odds(sport: str, fuzzy_match: bool = True) -> dict:
    if sport == "NBA":
        pass
    if sport == "MLB":
        pass
    if sport == "NFL":
        pass

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
            name="buildjson",
            description="buildjson"
    )
    async def _buildjson(self, interaction: discord.Interaction):
        await interaction.response.defer()
        generate_player_dump()
        players = mlbstats.lookup_player("")
        print(f"Fetched {len(players)} total players.")
        await interaction.followup.send("Done.", emphemeral=True)
    
    @app_commands.command(name="stats", description="Get season stats for a specific player")
    @app_commands.choices(sport=[
        app_commands.Choice(name="NBA", value="NBA"),
        app_commands.Choice(name="NFL", value="NFL"),
        app_commands.Choice(name="MLB", value="MLB")
    ])
    async def stats(self, interaction: discord.Interaction, sport: app_commands.Choice[str], player_name: str):
        await interaction.response.defer()
        
        try:
            if sport.value == "NBA":
                all_players = nba_players.get_players()
                player_names = [p['full_name'].lower() for p in all_players]
            elif sport.value == "NFL":
                current_year = datetime.now().year
                if datetime.now().month < 8:
                    current_year -= 1
                player_stats = nfl.import_seasonal_rosters([current_year])
                player_names = player_stats['player_name'].str.lower().tolist()
            elif sport.value == "MLB":
                player_names = [p['fullName'].lower() for p in mlb_players]
            else:
                pass
            matches = get_close_matches(player_name.lower(), player_names, n=5, cutoff=0.6)
            
            if not matches:
                await interaction.followup.send(f"Could not find any {sport.value} player matching: {player_name}. Please check the spelling.", ephemeral=True)
                return
                
            exact_match = None
            for match in matches:
                if player_name.lower() in match.lower():
                    if exact_match is None:
                        exact_match = match
                    else:
                        exact_match = None
                        break
            
            if exact_match or len(matches) == 1:
                player_to_use = exact_match or matches[0]
                if sport.value == "NBA":
                    stats = await get_nba_stats(player_to_use, fuzzy_match=False)
                elif sport.value == "NFL":
                    stats = await get_nfl_stats(player_to_use, fuzzy_match=False)
                elif sport.value == "MLB":
                    stats = await get_mlb_stats(player_to_use, fuzzy_match=False)
                else:
                    pass
                if not stats:
                    await interaction.followup.send("Could not retrieve stats at this time. Please try again later.", ephemeral=True)
                    return
                    
                em = create_stats_embed(stats, sport.value)
                if em:
                    await interaction.followup.send(embed=em)
                else:
                    await interaction.followup.send("Stats not available for this player.", ephemeral=True)
            else:
                em = discord.Embed(
                    title="Multiple Players Found",
                    description="Please select the player you meant:",
                    color=0xd6e1ff
                )
                view = PlayerSelect(matches, sport.value)
                await interaction.followup.send(embed=em, view=view)
            
        except Exception as e:
            try:
                owner = await self.bot.fetch_user(OWNER_ID)
                await owner.send(f"Error in stats command for {player_name} ({sport.value}): {str(e)}")
            except:
                pass
            print(f"Error in stats command: {str(e)}")
            await interaction.followup.send("Could not retrieve stats at this time. Please try again later.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Stats(bot)) 