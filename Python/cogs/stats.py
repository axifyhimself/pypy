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

def load_player_cache() -> list:
    if not os.path.exists(DUMP_PATH):
        return []
    with open(DUMP_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)
    
mlb_players = load_player_cache()

# Cache configurations
nba_cache = TTLCache(maxsize=100, ttl=3600)
nfl_cache = TTLCache(maxsize=100, ttl=3600)
mlb_cache = TTLCache(maxsize=100, ttl=360)

# Owner ID for error reporting
OWNER_ID = 825106419333857312

class PlayerSelect(discord.ui.View):
    def __init__(self, matches: list, sport: str):
        super().__init__(timeout=30)  # 30 second timeout
        self.matches = matches
        self.sport = sport
        
        # Add a button for each match
        for i, player_name in enumerate(matches[:3]):  # Limit to top 3 matches
            button = discord.ui.Button(label=player_name, custom_id=f"player_{i}", style=discord.ButtonStyle.primary, row=0)
            button.callback = self.create_callback(player_name)
            self.add_item(button)
    
    def create_callback(self, player_name: str):
        async def callback(interaction: discord.Interaction):
            # Disable all buttons after selection
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            
            # Get stats for selected player
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
                
                # Create embed with stats
                em = create_stats_embed(stats, self.sport)
                await interaction.followup.send(embed=em)
                
            except Exception as e:
                await interaction.followup.send(f"An error occurred while fetching stats: {str(e)}", ephemeral=True)
        
        return callback

def create_stats_embed(stats: dict, sport: str) -> discord.Embed:
    """Helper function to create stats embed"""
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
        pass
    elif sport == "NFL":
        if stats.get('position') in ['RG', 'LG', 'RT', 'LT', 'C']:
            return None  # Don't show stats for offensive linemen
            
        em.title = f"{stats['name']} - NFL Stats ({stats['position']})"
        
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
    """Get NBA player season stats with caching (1 hour TTL)"""
    cache_key = player_name.lower()
    
    # Check cache first
    if cache_key in nba_cache:
        return nba_cache[cache_key]
        
    try:
        # Get all players for fuzzy matching
        all_players = nba_players.get_players()
        player_names = [p['full_name'].lower() for p in all_players]
        
        # Try to find close matches
        close_matches = get_close_matches(player_name.lower(), player_names, n=3, cutoff=0.6)
        
        if not close_matches:
            return None
            
        # Get the best match
        best_match = close_matches[0]
        player = next(p for p in all_players if p['full_name'].lower() == best_match)
        
        player_id = player['id']
        
        # Get current season
        current_year = datetime.now().year
        if datetime.now().month < 8:  # If before August, use previous season
            current_year -= 1
        season = f"{current_year}-{str(current_year + 1)[2:]}"
        
        # Get player's season averages
        stats_data = playerdashboardbyyearoveryear.PlayerDashboardByYearOverYear(
            player_id=player_id,
            per_mode_detailed="PerGame",
            season=season
        )
        
        # Get current season's stats
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
            'close_matches': close_matches[1:] if len(close_matches) > 1 else []  # Store other close matches
        }
        
        # Cache the result
        nba_cache[cache_key] = stats
        return stats
    except Exception as e:
        # Send error to owner
        try:
            owner = await bot.fetch_user(OWNER_ID)
            await owner.send(f"Error fetching NBA stats for {player_name}: {str(e)}")
        except:
            pass  # If we can't send to owner, just log it
        print(f"Error fetching NBA stats: {str(e)}")
        return None

async def get_mlb_stats(player_name: str, fuzzy_match: bool = True) -> dict:
    """Get MLB player season stats with caching (1 hour TTL)"""
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
        raw = mlbstats.player_stat_data(playerid, group='hitting', type='season')
        print(raw)

    except:
        pass
        
        


async def get_nfl_stats(player_name: str, fuzzy_match: bool = True) -> dict:
    """Get NFL player season stats with caching (1 hour TTL)"""
    cache_key = player_name.lower()
    
    # Check cache first
    if cache_key in nfl_cache:
        return nfl_cache[cache_key]
        
    try:
        # Get current season year
        current_year = datetime.now().year
        if datetime.now().month < 8:  # If before August, use previous season
            current_year -= 1
            
        # Get player stats for current season
        player_stats = nfl.import_seasonal_rosters([current_year])
        weekly_stats = nfl.import_weekly_data([current_year])
        
        # Get all player names for fuzzy matching
        player_names = player_stats['player_name'].str.lower().tolist()
        
        # Try to find close matches
        close_matches = get_close_matches(player_name.lower(), player_names, n=3, cutoff=0.6)
        
        if not close_matches:
            return None
            
        # Get the best match
        best_match = close_matches[0]
        player = player_stats[player_stats['player_name'].str.lower() == best_match].iloc[0]
        position = player['position'].upper()
        
        # Check for offensive linemen
        if position in ['RG', 'LG', 'RT', 'LT', 'C']:
            result = {
                'name': player['player_name'], 
                'position': position,
                'close_matches': close_matches[1:] if len(close_matches) > 1 else []
            }
            nfl_cache[cache_key] = result
            return result
            
        # Get player's weekly stats
        player_weekly = weekly_stats[weekly_stats['player_id'] == player['player_id']]
        if player_weekly.empty:
            return None
            
        # Helper function to safely get stats
        def safe_sum(df, column):
            if column in df.columns:
                return df[column].sum()
            return 0
            
        # Calculate season averages
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
            
        # Cache the result
        nfl_cache[cache_key] = stats
        return stats
        
    except Exception as e:
        # Send error to owner
        try:
            owner = await bot.fetch_user(OWNER_ID)
            await owner.send(f"Error fetching NFL stats for {player_name}: {str(e)}")
        except:
            pass  # If we can't send to owner, just log it
        print(f"Error fetching NFL stats: {str(e)}")
        return None

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

     
    @app_commands.command(
            name="mlbtest", description="mlbtest"
    )
    async def _mlbtest(self, interaction: discord.Interaction, player:str):
        stats = await get_mlb_stats(player)
        await interaction.followup.send(stats)
    
    @app_commands.command(name="stats", description="Get season stats for a specific player")
    @app_commands.choices(sport=[
        app_commands.Choice(name="NBA", value="NBA"),
        app_commands.Choice(name="NFL", value="NFL"),
        app_commands.Choice(name="MLB", value="MLB")
    ])
    async def stats(self, interaction: discord.Interaction, sport: app_commands.Choice[str], player_name: str):
        await interaction.response.defer()  # Defer response since API calls might take time
        
        try:
            # Get all players and find matches
            if sport.value == "NBA":
                all_players = nba_players.get_players()
                player_names = [p['full_name'].lower() for p in all_players]
            else:  # NFL
                current_year = datetime.now().year
                if datetime.now().month < 8:
                    current_year -= 1
                player_stats = nfl.import_seasonal_rosters([current_year])
                player_names = player_stats['player_name'].str.lower().tolist()
            
            # Find close matches
            matches = get_close_matches(player_name.lower(), player_names, n=5, cutoff=0.6)
            
            if not matches:
                await interaction.followup.send(f"Could not find any {sport.value} player matching: {player_name}. Please check the spelling.", ephemeral=True)
                return
                
            # Check if there's an exact match or if the search term is uniquely contained in one name
            exact_match = None
            for match in matches:
                if player_name.lower() in match.lower():
                    if exact_match is None:
                        exact_match = match
                    else:
                        exact_match = None  # More than one match contains the search term
                        break
            
            if exact_match or len(matches) == 1:
                # If there's a unique match or only one close match, show stats directly
                player_to_use = exact_match or matches[0]
                if sport.value == "NBA":
                    stats = await get_nba_stats(player_to_use, fuzzy_match=False)
                else:
                    stats = await get_nfl_stats(player_to_use, fuzzy_match=False)
                    
                if not stats:
                    await interaction.followup.send("Could not retrieve stats at this time. Please try again later.", ephemeral=True)
                    return
                    
                em = create_stats_embed(stats, sport.value)
                if em:
                    await interaction.followup.send(embed=em)
                else:
                    await interaction.followup.send("Stats not available for this player.", ephemeral=True)
            else:
                # If multiple potential matches, show button interface
                em = discord.Embed(
                    title="Multiple Players Found",
                    description="Please select the player you meant:",
                    color=0xd6e1ff
                )
                view = PlayerSelect(matches, sport.value)
                await interaction.followup.send(embed=em, view=view)
            
        except Exception as e:
            # Send error to owner instead of user
            try:
                owner = await self.bot.fetch_user(OWNER_ID)
                await owner.send(f"Error in stats command for {player_name} ({sport.value}): {str(e)}")
            except:
                pass  # If we can't send to owner, just log it
            print(f"Error in stats command: {str(e)}")
            await interaction.followup.send("Could not retrieve stats at this time. Please try again later.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Stats(bot)) 