import discord
import aiohttp
import os
import logging
import datetime
import pytz
import asyncio
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    filename='sleeper_playoff_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

# Environment variables
try:
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    LEAGUE_1_ID = os.getenv('LEAGUE_1_ID')
    LEAGUE_2_ID = os.getenv('LEAGUE_2_ID')
    CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
    
    if not all([DISCORD_BOT_TOKEN, LEAGUE_1_ID, LEAGUE_2_ID, CHANNEL_ID]):
        raise ValueError("Missing required environment variables")
except Exception as e:
    logging.error(f"Error loading environment variables: {str(e)}")
    raise

LEAGUE_1_NAME = "C and O league 1"
LEAGUE_2_NAME = "C&O Best League"

nicknames_league_1 = {
    'calummurray14': 'Calum',
    'Kroftszn': 'Scot Adam',
    'GjermundH': 'Gjermund',
    'AshG82': 'Ash',
    'Lottiebirch92': 'Lottie',
    'sackmasterkatie': 'Katie',
    'aligunn': 'Ally',
    'Adamski11': 'Irish Adam',
    'Fergus75': 'Fergus',
    'CamTitans95': 'Cal'
}

nicknames_league_2 = {
    'shelbyxmas': 'Shelby',
    'RagingTurtle28': 'Ben',
    'lulltula': 'Dan',
    'vorkem': 'Mike',
    'ThomasCullen': 'Thomas C',
    'Doppler221': 'Doppler',
    'MartyG93': 'Marty',
    'Doonhamer': 'Doonhamer',
    'Tygre': 'Tygre',
    'brianp671': 'Brian'
}

def get_nfl_week():
    week_mapping = {
        3: datetime.date(2024, 9, 26),
        4: datetime.date(2024, 10, 1),
        5: datetime.date(2024, 10, 8),
        6: datetime.date(2024, 10, 15),
        7: datetime.date(2024, 10, 22),
        8: datetime.date(2024, 10, 29),
        9: datetime.date(2024, 11, 5),
        10: datetime.date(2024, 11, 12),
        11: datetime.date(2024, 11, 19),
        12: datetime.date(2024, 11, 26),
        13: datetime.date(2024, 12, 3),
        14: datetime.date(2024, 12, 10),
        15: datetime.date(2024, 12, 17),
        16: datetime.date(2024, 12, 24),
        17: datetime.date(2024, 12, 31)
    }

    today = datetime.date.today()
    current_week = None
    for week, start_date in sorted(week_mapping.items()):
        if today >= start_date:
            current_week = week
    return current_week

class SleeperAPI:
    @staticmethod
    async def fetch_data(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """Fetch data from Sleeper API asynchronously"""
        try:
            logging.info(f"Fetching data from: {url}")
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Error fetching {url}: Status {response.status}")
                    return None
        except Exception as e:
            logging.error(f"Error fetching {url}: {str(e)}")
            return None

    @staticmethod
    async def get_league_data(session: aiohttp.ClientSession, league_id: str, week: int) -> Dict[str, Any]:
        """Fetch all league data concurrently including weekly matchups"""
        logging.info(f"Fetching data for league {league_id}")
        
        urls = {
            'rosters': f'https://api.sleeper.app/v1/league/{league_id}/rosters',
            'users': f'https://api.sleeper.app/v1/league/{league_id}/users',
            'winners_bracket': f'https://api.sleeper.app/v1/league/{league_id}/winners_bracket',
            'losers_bracket': f'https://api.sleeper.app/v1/league/{league_id}/losers_bracket',
            'matchups': f'https://api.sleeper.app/v1/league/{league_id}/matchups/{week}'
        }
        
        tasks = {
            name: asyncio.create_task(SleeperAPI.fetch_data(session, url))
            for name, url in urls.items()
        }
        
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                logging.error(f"Error fetching {name}: {str(e)}")
                results[name] = None
        
        return results if all(results.values()) else None
        
def get_matchup_points(matchups, roster_id):
    """Get points for a specific roster from the weekly matchups"""
    if not matchups:
        return None
        
    matchup = next((m for m in matchups if m['roster_id'] == roster_id), None)
    if matchup:
        points = matchup.get('points', 0)
        points_decimal = matchup.get('points_decimal', 0)
        # Combine points and decimal points
        return points + (points_decimal / 100) if points is not None else None
    return None

def format_visual_bracket(matches, rosters, users, nicknames, matchups):
    """Create a minimal visual representation of the playoff bracket"""
    if not matches:
        return "No matches available"
    
    matches = sorted(matches, key=lambda x: (x.get('r', 0), x.get('m', 0)))
    
    def get_team_info(roster_id, from_ref=None, matches=None):
        if from_ref:
            if 'w' in from_ref:
                ref_match = next((m for m in matches if m['m'] == from_ref['w']), None)
                if ref_match and ref_match.get('w'):
                    return get_team_info(ref_match['w'], None, matches)[0], "TBD"
            return "TBD", "TBD"
            
        if not roster_id:
            return "TBD", "TBD"
        
        try:
            roster = next((r for r in rosters if r['roster_id'] == roster_id), None)
            if roster:
                user = next((u for u in users if u['user_id'] == roster['owner_id']), None)
                if user:
                    username = user.get('display_name', 'Unknown')
                    name = nicknames.get(username, username)
                    # Get points from matchups
                    points = get_matchup_points(matchups, roster_id)
                    score = f"{points:.2f}" if points is not None else "TBD"
                    return name, score
        except Exception as e:
            logging.error(f"Error getting team info: {str(e)}")
            
        return "TBD", "TBD"

def create_bracket_embed(title: str, bracket_data: str, color: int = 0x587ac7) -> discord.Embed:
    """Create an embed for a single bracket"""
    embed = discord.Embed(
        title=title,
        description=bracket_data,
        color=color
    )
    return embed

def format_single_bracket(bracket_data, rosters, users, nicknames, matchups, bracket_type="Championship"):
    """Format a single bracket into a Discord message"""
    message = []
    message.append("```")
    message.append(format_visual_bracket(bracket_data, rosters, users, nicknames, matchups))
    message.append("```")
    return "\n".join(message)

def format_single_bracket(bracket_data, rosters, users, nicknames, matchups, bracket_type="Championship"):
    """Format a single bracket into a Discord message"""
    message = []
    message.append("```")
    message.append(format_visual_bracket(bracket_data, rosters, users, nicknames, matchups))
    message.append("```")
    return "\n".join(message)

async def send_playoff_message(channel, league1_data, league2_data, current_week):
    """Send playoff brackets as separate messages with retries"""
    try:
        dublin_tz = pytz.timezone('Europe/Dublin')
        current_time = datetime.datetime.now(dublin_tz)
        
        # Function to create and send a single bracket embed
        async def send_bracket_embed(title, bracket_data, bracket_type, league_data, nicknames):
            try:
                formatted_bracket = format_single_bracket(
                    bracket_data,
                    league_data['rosters'],
                    league_data['users'],
                    nicknames,
                    league_data['matchups'],  # Pass matchups data
                    bracket_type
                )
                
                embed = create_bracket_embed(title, formatted_bracket)
                embed.set_footer(
                    text=f"Fantasy Playoff Results – Week {current_week}",
                    icon_url="https://play-lh.googleusercontent.com/L5sDy5zFKKLLMndpR7wJfD3aum4w0FVL_rRK6W1t9T5-d4BYc-4A7LTXa2nGeP62TCo"
                )
                embed.timestamp = current_time
                
                # Try to send message with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await channel.send(embed=embed)
                        return True
                    except discord.HTTPException as e:
                        if attempt == max_retries - 1:  # Last attempt
                            logging.error(f"Failed to send embed after {max_retries} attempts: {str(e)}")
                            return False
                        await asyncio.sleep(1)  # Wait before retrying
            except Exception as e:
                logging.error(f"Error creating/sending embed for {title}: {str(e)}")
                return False

        # Send initial message
        await channel.send("🏈 Playoff Update Time! Who's making it to the ship? 🏆")

        # Send League 1 brackets
        await send_bracket_embed(
            f"{LEAGUE_1_NAME} - Championship Bracket",
            league1_data['winners_bracket'],
            "Championship",
            league1_data,
            nicknames_league_1
        )
        await asyncio.sleep(1)  # Small delay between messages
        
        await send_bracket_embed(
            f"{LEAGUE_1_NAME} - Consolation Bracket",
            league1_data['losers_bracket'],
            "Consolation",
            league1_data,
            nicknames_league_1
        )
        await asyncio.sleep(1)

        # Send League 2 brackets
        await send_bracket_embed(
            f"{LEAGUE_2_NAME} - Championship Bracket",
            league2_data['winners_bracket'],
            "Championship",
            league2_data,
            nicknames_league_2
        )
        await asyncio.sleep(1)
        
        await send_bracket_embed(
            f"{LEAGUE_2_NAME} - Consolation Bracket",
            league2_data['losers_bracket'],
            "Consolation",
            league2_data,
            nicknames_league_2
        )

        logging.info("Successfully sent playoff update messages")
        
    except Exception as e:
        logging.error(f"Error sending playoff messages: {str(e)}")
        raise

# Discord bot setup
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    try:
        logging.info(f'Logged in as {client.user}')
        
        current_week = get_nfl_week()
        if current_week is None:
            logging.error("Could not determine NFL week")
            await client.close()
            return

        logging.info(f"Processing playoff data for Week {current_week}")

        # Create aiohttp session for all requests
        async with aiohttp.ClientSession() as session:
            # Fetch league data concurrently including weekly matchups
            league1_data = await SleeperAPI.get_league_data(session, LEAGUE_1_ID, current_week)
            league2_data = await SleeperAPI.get_league_data(session, LEAGUE_2_ID, current_week)

            if not league1_data or not league2_data:
                logging.error("Failed to fetch league data")
                await client.close()
                return

            # Send message
            channel = client.get_channel(CHANNEL_ID)
            if channel is None:
                logging.error(f"Channel with ID {CHANNEL_ID} not found")
                await client.close()
                return

            # Send brackets with current week's matchup data
            await send_playoff_message(channel, league1_data, league2_data, current_week)

    except Exception as e:
        logging.error(f"Error in on_ready: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    try:
        client.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        logging.error(f"Failed to start bot: {str(e)}")