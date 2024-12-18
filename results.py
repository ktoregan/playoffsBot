import discord
import requests
import os
from discord.ext import commands
import datetime
import pytz

# Import environment variables
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
LEAGUE_1_ID = os.getenv('LEAGUE_1_ID')
LEAGUE_2_ID = os.getenv('LEAGUE_2_ID')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

LEAGUE_1_NAME = "C and O league 1"
LEAGUE_2_NAME = "C&O Best League"

# Nicknames for teams in League 1 and League 2
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
    # Define the starting week dates for each NFL week
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

    # Initialize current_week to None in case no week matches
    current_week = None

    # Compare today's date with the week start dates
    for week, start_date in sorted(week_mapping.items()):
        if today >= start_date:
            current_week = week

    return current_week

# Function to get league information
def get_league_info(league_id):
    url = f'https://api.sleeper.app/v1/league/{league_id}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# Function to get rosters and their owner IDs
def get_rosters(league_id):
    url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

# Function to get users (team names)
def get_users(league_id):
    url = f'https://api.sleeper.app/v1/league/{league_id}/users'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

# Function to get matchups for the week
def get_matchups(league_id, week):
    url = f'https://api.sleeper.app/v1/league/{league_id}/matchups/{week}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

# Function to get league standings and include division info (if applicable)
def get_league_standings(league_id, users, rosters, nicknames, has_divisions=False):
    standings = []
    for roster in rosters:
        user_id = roster['owner_id']
        user_info = next((u for u in users if u['user_id'] == user_id), {})

        # Get the user's Sleeper username (display_name)
        username = user_info.get('display_name', 'Unknown User')

        # Fallback to username if no team name is found
        team_name = user_info.get('metadata', {}).get('team_name', username)

        # Get wins, losses, points for, points against
        wins = roster['settings']['wins']
        losses = roster['settings']['losses']
        points_for = float(f"{roster['settings']['fpts']}.{roster['settings']['fpts_decimal']:02d}")
        points_against = float(f"{roster['settings']['fpts_against']}.{roster['settings']['fpts_against_decimal']:02d}")

        # Get the nickname (if exists) or fallback to username
        nickname = nicknames.get(username, username)

        # Get division if it's a league with divisions
        division = roster['settings'].get('division') if has_divisions else None

        standings.append({
            'team_name': team_name,
            'nickname': nickname,
            'wins': wins,
            'losses': losses,
            'points_for': points_for,
            'points_against': points_against,
            'owner_id': user_id,
            'division': division  # Division will be None if it's a league without divisions
        })

    # Sort standings by wins (descending), points_for (descending), and points_against (ascending)
    standings.sort(key=lambda x: (-x['wins'], -x['points_for'], x['points_against']))
    
    return standings

# Function to split standings by division for League 1
def split_standings_by_division(standings):
    division_1 = []
    division_2 = []
    
    for team in standings:
        if team['division'] == 1:  # Division 1 teams
            division_1.append(team)
        elif team['division'] == 2:  # Division 2 teams
            division_2.append(team)

    # Since we are sorting in get_league_standings(), there's no need to sort here again
    return division_1, division_2

# Utility function to get team name or username if no team name is available
def get_team_name_or_username(team, users):
    owner_id = team.get('owner_id')
    team_name = team.get('team_name', 'Unknown Team')
    
    # Special case to replace "Forgot my funny team name" with the username
    if team_name == "blahblah":
        username = next((u['display_name'] for u in users if u.get('user_id') == owner_id), "Unknown User")
        return username  # Use username instead of the long team name
    
    # If team name is unknown, use the username
    return team_name if team_name != "Unknown Team" else next((u['display_name'] for u in users if u.get('user_id') == owner_id), "Unknown User")

def get_lowest_scorers(matchups, users, rosters, nicknames):
    lowest_scorers = []

    # Iterate through each matchup and find the lowest scorer
    for matchup in matchups:
        # Get the roster ID
        roster_id = matchup.get('roster_id', None)
        if not roster_id:
            continue
        
        # Get the roster information
        roster_info = next((r for r in rosters if r['roster_id'] == roster_id), {})
        
        # Get user details using owner_id (username)
        user_info = next((u for u in users if u['user_id'] == roster_info.get('owner_id')), {})
        username = user_info.get('display_name', 'Unknown User')

        # Use nickname or fallback to username
        nickname = nicknames.get(username, username)
        
        # Get team name or use nickname if team name is not available
        team_name = roster_info.get('metadata', {}).get('team_name', nickname).strip()

        # Get the points scored by the team
        points = matchup.get('points', 0.0)

        # Append the player to the lowest scorers list
        lowest_scorers.append((team_name, points))

    # Sort by points to find the lowest scorer
    lowest_scorers.sort(key=lambda x: x[1])

    # Return the team with the lowest points
    return lowest_scorers[:1]  # You can adjust this to get more than 1 player if needed

def format_league_one_with_divisions(league_name, standings_div1, standings_div2, users, nicknames):
    description = f"      🏅 **{LEAGUE_1_NAME} Standings:**\n\n"

    # Division 1
    description += "`Division 1` \n```"
    for idx, team in enumerate(standings_div1, start=1):
        emoji = "🏆" if idx == 1 else "🏈"
        
        # Combine team name and owner nickname into one string
        team_name = get_team_name_or_username(team, users)
        owner_nickname = nicknames.get(team['nickname'], team['nickname'])
        combined_name = f" {team_name} ({owner_nickname})"
        
        # Combine W-L and Pts For/Against into one string
        combined_info = f" {team['wins']}-{team['losses']} | PF {team['points_for']:.2f} | PA {team['points_against']:.2f}"

        # Add the formatted team rank, combined name, and combined info
        description += f"{emoji:<1}{idx:<3} {combined_name:<30}\n"
        description += f"      {combined_info:<32}\n"
        description += "                                       \n"
    description += "```\n"

    # Division 2
    description += "`Division 2` \n```"
    for idx, team in enumerate(standings_div2, start=1):
        emoji = "🏆" if idx == 1 else "🏈"
        
        # Combine team name and owner nickname into one string
        team_name = get_team_name_or_username(team, users)
        owner_nickname = nicknames.get(team['nickname'], team['nickname'])
        combined_name = f" {team_name} ({owner_nickname})"

        # Combine W-L and Pts For/Against into one string
        combined_info = f" {team['wins']}-{team['losses']} | PF {team['points_for']:.2f} | PA {team['points_against']:.2f}"

        # Add the formatted team rank, combined name, and combined info
        description += f"{emoji:<1}{idx:<3} {combined_name:<30}\n"
        description += f"      {combined_info:<32}\n"
        description += "                                       \n"
    description += "```\n"

    return description

def format_donkeys_of_the_week(lowest_scorers):
    description = "```"
    
    # Add the lowest scorer to the description
    for team_name, points in lowest_scorers:
        description += f"{team_name:<10} {points:<8.2f}\n"
    
    description += "```"
    
    return description

def format_league_two(league_name, standings_league_2, users, nicknames):
    description = f"      🏅 **{LEAGUE_2_NAME} Standings:**\n"

    # League 2 Standings
    description += "```"
    for idx, team in enumerate(standings_league_2, start=1):
        emoji = "🏆" if idx == 1 else "🏈"
        
        # Combine team name and owner nickname into one string
        team_name = get_team_name_or_username(team, users)
        owner_nickname = nicknames.get(team['nickname'], team['nickname'])
        combined_name = f" {team_name} ({owner_nickname})"
        
        # Combine W-L and Pts For/Against into one string
        combined_info = f" {team['wins']}-{team['losses']} | PF {team['points_for']:.2f} | PA {team['points_against']:.2f}"

        # Add the formatted team rank, combined name, and combined info
        description += f"{emoji:<1}{idx:<3} {combined_name:<30}\n"
        description += f"      {combined_info:<32}\n"
        description += "                                       \n"
    description += "```\n"

    return description

def get_team_name_or_username_in_matchups(team, users):
    owner_id = team.get('owner_id')
    team_name = team.get('metadata', {}).get('team_name', None)

    # If the team has no name, fall back to the username
    if not team_name or team_name == "Unknown Team":
        username = next((u['display_name'] for u in users if u.get('user_id') == owner_id), "Unknown User")
        return username
    return team_name

def format_matchups_table(matchups, users, rosters, nicknames):
    description = "```"
    description += "Team 1       T1 Pts  ⚔️   T2 Pts   Team 2  \n"
    description += "---------------------------------------------\n"

 # Organize matchups by matchup ID
    matchups_by_id = {}
    for matchup in matchups:
        matchup_id = matchup.get('matchup_id', None)
        if matchup_id:
            if matchup_id not in matchups_by_id:
                matchups_by_id[matchup_id] = []
            matchups_by_id[matchup_id].append(matchup)

    # Iterate over each matchup (where there are two teams)
    for matchup_id, matchup_pair in matchups_by_id.items():
        if len(matchup_pair) == 2:
            team1 = matchup_pair[0]
            team2 = matchup_pair[1]

            # Get roster IDs (team 1 and team 2)
            team1_id = team1.get('roster_id', None)
            team2_id = team2.get('roster_id', None)

            if not team1_id or not team2_id:
                continue  # Skip if roster IDs are missing

            # Get points for both teams (float values)
            team1_points = team1.get('points', 0.0)
            team2_points = team2.get('points', 0.0)

            # Get roster information for both teams
            team1_info = next((r for r in rosters if r['roster_id'] == team1_id), {})
            team2_info = next((r for r in rosters if r['roster_id'] == team2_id), {})

            # Get user details using owner_id (username)
            team1_user = next((u for u in users if u['user_id'] == team1_info.get('owner_id')), {})
            team2_user = next((u for u in users if u['user_id'] == team2_info.get('owner_id')), {})

            # Get usernames
            team1_username = team1_user.get('display_name', 'Unknown User')
            team2_username = team2_user.get('display_name', 'Unknown User')

            # Use nickname or fallback to username
            team1_nickname = nicknames.get(team1_username, team1_username)
            team2_nickname = nicknames.get(team2_username, team2_username)

            # Get team names, fallback to usernames if team names are not available
            team1_name = team1_info.get('metadata', {}).get('team_name', team1_nickname)
            team2_name = team2_info.get('metadata', {}).get('team_name', team2_nickname)

            # Strip any leading/trailing spaces in team names
            team1_name = team1_name.strip()
            team2_name = team2_name.strip()

            # Determine the winner emoji
            winner_emoji_team1 = "🏆" if team1_points > team2_points else "❌"
            winner_emoji_team2 = "🏆" if team2_points > team1_points else "❌"
            versusstring = "vs"

            # Add formatted matchup to the table with improved alignment
            description += (
                f"{winner_emoji_team1:<1}{team1_name:<11}{team1_points:<8.2f}{versusstring:<5}{team2_points:<8.2f}{winner_emoji_team2:<1}{team2_name:<10}\n"
            )

    # Close the table
    description += "```"

    return description

# Get the current timestamp (UTC)
dublin_tz = pytz.timezone('Europe/Dublin')
current_time = datetime.datetime.now(dublin_tz)

# Discord bot setup
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    # Get the current NFL week dynamically
    current_week = get_nfl_week()

    if current_week is None:
        print("Error: Could not determine the NFL week.")
        await client.close()
        return

    print(f"Fetching data for Week {current_week}")

    # Fetch data for League 1
    rosters_league_1 = get_rosters(LEAGUE_1_ID)
    users_league_1 = get_users(LEAGUE_1_ID)
    standings_league_1 = get_league_standings(LEAGUE_1_ID, users_league_1, rosters_league_1, nicknames_league_1, has_divisions=True)
    matchups_league_1 = get_matchups(LEAGUE_1_ID, week=current_week)

    # Fetch data for League 2
    rosters_league_2 = get_rosters(LEAGUE_2_ID)
    users_league_2 = get_users(LEAGUE_2_ID)
    standings_league_2 = get_league_standings(LEAGUE_2_ID, users_league_2, rosters_league_2, nicknames_league_2, has_divisions=False)
    matchups_league_2 = get_matchups(LEAGUE_2_ID, week=current_week)

#    Split League 1 standings into two divisions using the actual division info
    standings_div1, standings_div2 = split_standings_by_division(standings_league_1)

    # Format the standings using the new functions
    formatted_standings_league_1 = format_league_one_with_divisions("League 1", standings_div1, standings_div2, users_league_1, nicknames_league_1)
    formatted_standings_league_2 = format_league_two("League 2", standings_league_2, users_league_2, nicknames_league_2)


    # Format the matchups using the new table format for both leagues
    formatted_matchups_league_1 = format_matchups_table(matchups_league_1, users_league_1, rosters_league_1, nicknames_league_1)
    formatted_matchups_league_2 = format_matchups_table(matchups_league_2, users_league_2, rosters_league_2, nicknames_league_2)

    # Get the lowest scoring players for both leagues
    lowest_scorers_league_1 = get_lowest_scorers(matchups_league_1, users_league_1, rosters_league_1, nicknames_league_1)
    lowest_scorers_league_2 = get_lowest_scorers(matchups_league_2, users_league_2, rosters_league_2, nicknames_league_2)

    # Get the lowest scoring players for both leagues
    lowest_scorers_league_1 = get_lowest_scorers(matchups_league_1, users_league_1, rosters_league_1, nicknames_league_1)
    lowest_scorers_league_2 = get_lowest_scorers(matchups_league_2, users_league_2, rosters_league_2, nicknames_league_2)

    # Combine both leagues' donkeys into a single formatted string
    combined_donkeys = format_donkeys_of_the_week(lowest_scorers_league_1 + lowest_scorers_league_2)
    
    # Create the embed
    embed = discord.Embed(
        description=f"{formatted_standings_league_1}\n{formatted_standings_league_2}",
        color=0x587ac7
    )
    embed.set_author(
        name=f"Fantasy Results – Week {current_week}:",
        icon_url="https://play-lh.googleusercontent.com/L5sDy5zFKKLLMndpR7wJfD3aum4w0FVL_rRK6W1t9T5-d4BYc-4A7LTXa2nGeP62TCo"
    )

    # Add fields for both leagues' matchups
    embed.add_field(name=f"{LEAGUE_1_NAME} - Matchup Results:", value=formatted_matchups_league_1, inline=False)
    embed.add_field(name=f"{LEAGUE_2_NAME} - Matchup Results:", value=formatted_matchups_league_2, inline=False)
        # Add combined Donkeys of the Week as a single field
    embed.add_field(name=f"🫏🫏🫏 Donkeys of the Week HEE-HAW! 🫏🫏🫏", value=combined_donkeys, inline=False)

    # Add the provided thumbnail and icon URLs
    embed.set_footer(text="Sleeper Bot", icon_url="https://play-lh.googleusercontent.com/L5sDy5zFKKLLMndpR7wJfD3aum4w0FVL_rRK6W1t9T5-d4BYc-4A7LTXa2nGeP62TCo")
    embed.timestamp = current_time

    # Get the channel by ID
    channel = client.get_channel(CHANNEL_ID)

    # Check if the channel exists and the bot has access to it
    if channel is None:
        print(f"Error: Channel with ID {CHANNEL_ID} not found.")
        await client.close()  # Close the bot if the channel isn't found
        return
    
    await channel.send(content="Hey cunts! It's fantasy league results time!", embed=embed)

    await client.close()

# Start the bot
client.run(DISCORD_BOT_TOKEN)