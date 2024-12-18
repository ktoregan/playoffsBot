import requests
import discord
import os
import asyncio
import datetime

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

def get_bracket(league_id, bracket_type):
    url = f"https://api.sleeper.app/v1/league/{league_id}/{bracket_type}_bracket"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching the {bracket_type} bracket: {e}")
        return None

def format_three_column_winners_bracket(matches, nicknames):
    rounds = {1: [], 2: [], 3: []}
    for match in matches:
        round_num = match.get('r', 1)
        rounds[round_num].append(match)

    def format_matchup(match):
        t1 = nicknames.get(match.get('t1_display_name', 'TBD'), 'TBD')
        t2 = nicknames.get(match.get('t2_display_name', 'TBD'), 'TBD')
        s1 = match.get('t1_score', 'TBD')
        s2 = match.get('t2_score', 'TBD')

        t1_emoji = "🏆" if s1 != 'TBD' and (s2 == 'TBD' or s1 > s2) else "❌" if s2 != 'TBD' else "❓"
        t2_emoji = "🏆" if s2 != 'TBD' and (s1 == 'TBD' or s2 > s1) else "❌" if s1 != 'TBD' else "❓"
        t1_emoji = "🙌" if t1 == 'BYE' else t1_emoji
        t2_emoji = "🙌" if t2 == 'BYE' else t2_emoji

        return f"{t1_emoji} {t1:<10} {s1:>6}\n{t2_emoji} {t2:<10} {s2:>6}\n"

    column1 = "\n".join(format_matchup(m) for m in rounds[1])
    column2 = "\n".join(format_matchup(m) for m in rounds[2])
    column3 = "\n".join(format_matchup(m) for m in rounds[3])
    return f"```\n{column1:<35}{column2:<35}{column3}\n```"

def format_two_column_losers_bracket(matches, nicknames):
    rounds = {1: [], 2: []}
    for match in matches:
        round_num = match.get('r', 1)
        rounds[round_num].append(match)

    def format_matchup(match):
        t1 = nicknames.get(match.get('t1_display_name', 'TBD'), 'TBD')
        t2 = nicknames.get(match.get('t2_display_name', 'TBD'), 'TBD')
        s1 = match.get('t1_score', 'TBD')
        s2 = match.get('t2_score', 'TBD')

        t1_emoji = "🏆" if s1 != 'TBD' and (s2 == 'TBD' or s1 > s2) else "❌" if s2 != 'TBD' else "❓"
        t2_emoji = "🏆" if s2 != 'TBD' and (s1 == 'TBD' or s2 > s1) else "❌" if s1 != 'TBD' else "❓"
        t1_emoji = "🙌" if t1 == 'BYE' else t1_emoji
        t2_emoji = "🙌" if t2 == 'BYE' else t2_emoji

        return f"{t1_emoji} {t1:<10} {s1:>6}\n{t2_emoji} {t2:<10} {s2:>6}\n"

    column1 = "\n".join(format_matchup(m) for m in rounds[1])
    column2 = "\n".join(format_matchup(m) for m in rounds[2])
    return f"```\n{column1:<35}{column2}\n```"

async def send_brackets_to_discord(bot_token, channel_id, league_1_id, league_2_id, week):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        channel = client.get_channel(channel_id)
        if channel is None:
            print("Invalid channel ID")
            await client.close()
            return

        await channel.send(f"🏈 **Playoff Update - Week {week}** 🏈")

        # League 1
        await channel.send(f"\n**{LEAGUE_1_NAME} Brackets**")
        winners_1 = get_bracket(league_1_id, "winners")
        losers_1 = get_bracket(league_1_id, "losers")
        if winners_1:
            await channel.send(f"**Winners Bracket**\n{format_three_column_winners_bracket(winners_1, nicknames_league_1)}")
        if losers_1:
            await channel.send(f"**Losers Bracket**\n{format_two_column_losers_bracket(losers_1, nicknames_league_1)}")

        # League 2
        await channel.send(f"\n**{LEAGUE_2_NAME} Brackets**")
        winners_2 = get_bracket(league_2_id, "winners")
        losers_2 = get_bracket(league_2_id, "losers")
        if winners_2:
            await channel.send(f"**Winners Bracket**\n{format_three_column_winners_bracket(winners_2, nicknames_league_2)}")
        if losers_2:
            await channel.send(f"**Losers Bracket**\n{format_two_column_losers_bracket(losers_2, nicknames_league_2)}")

        await client.close()

    client.run(bot_token)

if __name__ == "__main__":
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
    LEAGUE_1_ID = os.getenv("LEAGUE_1_ID")
    LEAGUE_2_ID = os.getenv("LEAGUE_2_ID")
    WEEK = get_nfl_week()

    asyncio.run(send_brackets_to_discord(BOT_TOKEN, CHANNEL_ID, LEAGUE_1_ID, LEAGUE_2_ID, WEEK))
