import requests

def get_matchups(league_id, week):
    url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError if the response status is 4xx or 5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    league_id = "1132420390292287488"
    week = 15

    matchups = get_matchups(league_id, week)

    if matchups:
        print("Matchups:")
        print(matchups)
    else:
        print("Failed to fetch matchups.")