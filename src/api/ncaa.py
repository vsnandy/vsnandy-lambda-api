import os
import json
import logging
import urllib3
import time
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta
from itertools import groupby

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()

dynamodb_table_name = "wapit_draft"
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(dynamodb_table_name)

cognito = boto3.client("cognito-idp")

NCAA_SCHOOLS_URL = "https://www.ncaa.com/json/schools"
NCAA_API_URL = "https://data.ncaa.com/casablanca"
NCAA_MM_LIVE_URL = "https://sdataprod.ncaa.com/"

# Get NCAA schools
def get_schools():
    try:
        response = http.request("GET", NCAA_SCHOOLS_URL)
        print("Response Code:", response.status)
        data = json.loads(response.data)

        body = {
            "schools": data
        }

        return body
    except Exception as e:
        logger.exception("Exception in Get Schools method !!")
        logger.exception(e)
        return json.dumps("Server error")
        
# Get NCAA Game Schedule for a Sport/Division/Year/Month
def get_schedule(sport, division, year, month):
    try:
        response = http.request("GET", f"{NCAA_API_URL}/schedule/{sport}/{division}/{year}/{month}/schedule-all-conf.json")
        print("Response Code:", response.status)
        data = json.loads(response.data)

        body = {
            "schedule": data
        }

        return body
    except Exception as e:
        logger.exception("Exception in Get Schedule method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get NCAA Scoreboard for a Sport/Division/Date
def get_scoreboard(sport, division, date):
    try:
        response = http.request("GET", f"{NCAA_API_URL}/scoreboard/{sport}/{division}/{date}/scoreboard.json")
        print("Response Code:", response.status)
        data = json.loads(response.data)

        body = {
            "scoreboard": data
        }

        return body
    except Exception as e:
        logger.exception("Exception in Get Scoreboard method !!")
        logger.exception(e)
        return json.dumps("Server Error")
    
# Get NCAA Game Details for a Game/Page
def get_game_details(game_id, page):
    try:
        response = http.request("GET", f"{NCAA_API_URL}/game/{game_id}/{page}.json")
        print("Response Code:", response.status)
        data = json.loads(response.data)

        body = {
            page: data
        }

        return body
    except Exception as e:
        logger.exception("Exception in Get Scoreboard method !!")
        logger.exception(e)
        return json.dumps("Server Error")
    

# Get NCAA March Madness WAPIT stats for a player
def get_wapit_stats(id, player_name, number, school, year):
    LOGGER_CONTEXT = f"[ncaa.py / get_wapit_stats({player_name}, {number}, {school}, {year})]"
    logger.info(f"{LOGGER_CONTEXT} - In Get WAPIT Stats!!!")
    try:
        start_time = time.time()

        logger.info(f"{LOGGER_CONTEXT} - Getting all boxscores for ")

        response = http.request(
            "GET", 
            f"{NCAA_MM_LIVE_URL}?operationName=gamecenter_game_stats_web&variables=%7B%22seasonYear%22:{int(year)-1}%7D&extensions=%7B%22persistedQuery%22:%7B%22version%22:1,%22sha256Hash%22:%220677d7ecf3cf630d58ed4f221c74908fb4494c12e0dacb70c45190d55accdc74%22%7D%7D"
        )

        logger.info(f"{LOGGER_CONTEXT} - Response Status:")
        logger.info(response.status)

        # Get all March Madness games
        game_stats = json.loads(response.data)["data"]["mmlContests"]
        #logger.info(f"{LOGGER_CONTEXT} - Game Stats:")
        #logger.info(game_stats)

        #logger.info(f"{LOGGER_CONTEXT} - Response Data:")
        #logger.info(game_stats)

        # Filter only completed games
        # Filter games for school of given player
        filtered_games = [game for game in game_stats if (game["gameState"] != "P" and game["round"]["roundNumber"] > 1)]
        player_games = [game for game in filtered_games if game["teams"][0]["nameFull"] == school or game["teams"][1]["nameFull"] == school]
        
        # Loop through games and compile stats for given player
        player_stats = []
        for game in player_games:
            # Only keep the below fields from games list
            keys_to_keep = {"bracketId", "contestId", "startDate", "broadcaster", 
                            "condensedVideo", "location", "region", "round"}
            filtered_game = {k: v for k, v in game.items() if k in keys_to_keep}

            # Only keep the player stats for the given player
            for team in game["boxscore"]["teamBoxscore"]:
                if (team["nameFull"] == school):
                    for player in team["playerStats"]:
                        if (player["num"] == int(number) and f"{player['fname']} {player['lname']}" == player_name):
                            filtered_game["playerStats"] = player

            # Assign "team" and "opponent"
            for team in game["teams"]:
                filtered_team = {k: v for k, v in team.items() if k != "roster"}
                if (filtered_team["nameFull"] == school):
                    filtered_game["team"] = filtered_team
                else:
                    filtered_game["opponent"] = filtered_team

            player_stats.append(filtered_game)

        logger.info(f"{LOGGER_CONTEXT} - {player_name} appeared in {len(player_stats)} games...")

        end_time = time.time()
        elapsed_time = end_time - start_time

        logger.info(f"{LOGGER_CONTEXT} - Elapsed time: {elapsed_time:.4f} seconds")

        body = {
            "timeElapsed": elapsed_time,
            "playerId": id,
            "playerName": player_name,
            "number": number,
            "school": school,
            "year": year,
            "stats": player_stats
        }

        return body
    except Exception as e:
        logger.exception("Exception in Get Scoreboard method !!")
        logger.exception(e)
        return json.dumps("Server Error")
    

# Get NCAA March Madness WAPIT stats for an entire league
def get_all_wapit_stats(year):
    LOGGER_CONTEXT = f"[ncaa.py / get_all_wapit_stats({year})]"
    logger.info(f"{LOGGER_CONTEXT} - In Get All WAPIT Stats!!!")
    try:
        start_time = time.time()

        logger.info(f"{LOGGER_CONTEXT} - Getting all boxscores for ")

        game_response = http.request(
            "GET", 
            f"{NCAA_MM_LIVE_URL}?operationName=gamecenter_game_stats_web&variables=%7B%22seasonYear%22:{int(year)-1}%7D&extensions=%7B%22persistedQuery%22:%7B%22version%22:1,%22sha256Hash%22:%220677d7ecf3cf630d58ed4f221c74908fb4494c12e0dacb70c45190d55accdc74%22%7D%7D"
        )

        logger.info(f"{LOGGER_CONTEXT} - Response Status:")
        logger.info(game_response.status)

        # Get all March Madness games
        game_stats = json.loads(game_response.data)["data"]["mmlContests"]

        # Filter out any pending games and first four games
        filtered_games = [game for game in game_stats if (game["gameState"] != "P" and game["round"]["roundNumber"] > 1)]

        # Loop through games and compile stats for all wapit players
        player_stats = {}
        for game in filtered_games:
            # Only keep the below fields from games list
            keys_to_keep = {"bracketId", "contestId", "startDate", "broadcaster", 
                            "condensedVideo", "location", "region", "round", "teams"}
            filtered_game = {k: v for k, v in game.items() if k in keys_to_keep}

            # Only keep the player stats for the given player
            print("GAME:", game["bracketId"], game["teams"][0]["nameShort"], game["teams"][1]["nameShort"])
            for team in game["teams"]:
                for player in team["roster"]:
                    # If ID doesn't exist in player_stats, create it and assign the game to an empty list
                    # stats will be list of dicts
                    #print("PLAYER: ", player["id"], player["firstName"] + " " + player["lastName"])
                    #print("Team:", team)
                    #print("Team Boxscore:", game["boxscore"]["teamBoxscore"])

                    player_team_boxscore = next((t for t in game["boxscore"]["teamBoxscore"] if t["ncaaOrgId"] == team["ncaaOrgId"]), None)
                    player_boxscore = next((p for p in player_team_boxscore["playerStats"] if (p["fname"] + " " + p["lname"]) == (player["firstName"] + " " + player["lastName"])), None)    
                    
                    if (not player_boxscore):
                        #print("SKIPPING ", player["id"], player["firstName"] + " " + player["lastName"])
                        continue

                    if player["id"] not in player_stats:
                        # Initialize player in player_stats
                        player_stats[player["id"]] = {
                            **player,
                            "schoolColor": team["color"],
                            "seed": team["seed"],
                            "schoolNameFull": team["nameFull"],
                            "schoolNameShort": team["nameShort"],
                            "schoolName6Char": team["name6Char"],
                            "schoolSeoName": team["seoname"],
                            "schoolNickname": team["nickname"],
                            "boxscores": [{
                                "bracketId": game["bracketId"],
                                "contestId": game["contestId"],
                                "roundName": game["round"]["title"],
                                "startDate": game["startDate"],
                                "gameState": game["gameState"],
                                "isWinner": team["isWinner"],
                                "score": team["score"],
                                **player_boxscore
                            }]
                        }
                    # Player already exists in the stats dictionary, so append to it
                    else:
                        player_stats[player["id"]]["boxscores"].append({
                            "bracketId": game["bracketId"],
                            "contestId": game["contestId"],
                            "roundName": game["round"]["title"],
                            "startDate": game["startDate"],
                            "gameState": game["gameState"],
                            "isWinner": team["isWinner"],
                            "score": team["score"],
                            **player_boxscore
                        })

        logger.info(f"{LOGGER_CONTEXT} - Collected MML stats for {len(list(player_stats.keys()))} players !!!")

        end_time = time.time()
        elapsed_time = end_time - start_time

        logger.info(f"{LOGGER_CONTEXT} - Elapsed time: {elapsed_time:.4f} seconds")

        body = {
            "timeElapsed": elapsed_time,
            "year": year,
            "stats": player_stats
        }

        return body
    except Exception as e:
        logger.exception("Exception in Get Scoreboard method !!")
        logger.exception(e)
        return json.dumps("Server Error")
    

# Get NCAA March Madness Tournament Players
# 1. Get schedule and determine Day 1 & 2 of tournament (3rd Thursday of March = Day 1)
# 2. Get all games on Day 1 & Day 2, then filter those on Tournament games
# 3. For each game, extract the players
def get_wapit_players(year):
    LOGGER_CONTEXT = "[ncaa.py / get_wapit_players()]"
    try:
        start_time = time.time()
        
        #URL --- https://sdataprod.ncaa.com/?operationName=gamecenter_game_stats_web&variables={"seasonYear":2024}&extensions={"persistedQuery":{"version":1,"sha256Hash":"0677d7ecf3cf630d58ed4f221c74908fb4494c12e0dacb70c45190d55accdc74"}}
        response = http.request(
            "GET", 
            f"{NCAA_MM_LIVE_URL}?operationName=gamecenter_game_stats_web&variables=%7B%22seasonYear%22:{int(year)-1}%7D&extensions=%7B%22persistedQuery%22:%7B%22version%22:1,%22sha256Hash%22:%220677d7ecf3cf630d58ed4f221c74908fb4494c12e0dacb70c45190d55accdc74%22%7D%7D"
        )

        logger.info(f"{LOGGER_CONTEXT} - Response Status:")
        logger.info(response.status)

        # Get all March Madness games
        game_stats = json.loads(response.data)["data"]["mmlContests"]
        players = []
        counter = 0
        for game in game_stats:
            if game["round"]["roundNumber"] == 2: # roundNumber = 2 --> First Round
                for team in game["teams"]:
                    #logger.info(f"{LOGGER_CONTEXT} - Adding players from {team['nameFull']}")

                    # Add the school to each player in the roster (for future lookups)
                    enhanced_roster = team["roster"]
                    for player in enhanced_roster:
                        player["school"] = team["nameFull"]

                    players.extend(team["roster"])
                    counter += 1
            
        logger.info(f"{LOGGER_CONTEXT} - {len(players)} players added from {counter} teams!!!")

        end_time = time.time()
        elapsed_time = end_time - start_time

        logger.info(f"{LOGGER_CONTEXT} - Elapsed time: {elapsed_time:.4f} seconds")

        body = {
            "timeElapsed": elapsed_time,
            "year": year,
            "players": players
        }

        return body
    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception in Get Scoreboard method !!")
        logger.exception(e)
        return json.dumps("Server Error")
    

# GET /ncaa/wapit/league/{league_id}/year/{year}
# Grab the WAPIT league from the DB
def get_wapit_league(league_id, year, cognito_user_pool_id):
    LOGGER_CONTEXT = f"[ncaa.py / get_wapit_league({league_id}, {year})]"
    try:
        start_time = time.time()

        draft = []
        # Query DB
        response = table.query(
            KeyConditionExpression=Key('LeagueID').eq(league_id + year)
        )

        if "Items" in response:
            draft = response["Items"]
        else:
            return { "Message": f"League {league_id + year} not found" }, 404
        
        # Get the list of users in the Cognito wapit_ group
        users = get_users_in_group(cognito_user_pool_id, f"wapit_{league_id}{year}")

        # Order the draft picks into teams format
        teams = {} if len(draft) == 0 else populate_teams_in_league(draft)

        end_time = time.time()
        elapsed_time = end_time - start_time

        logger.info(f"{LOGGER_CONTEXT} - Elapsed time: {elapsed_time:.4f} seconds")

        body = {
            "timeElapsed": elapsed_time,
            "leagueName": league_id,
            "year": year,
            "users": users,
            "teams": teams,
            "draft": draft
        }

        return body
    
    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception in Get WAPIT League method !!")
        logger.exception(e)
        return json.dumps("Server Error")
    

# POST /ncaa/wapit/league/{league_id}/year/{year}/draft
def post_wapit_draft(league_id, year, draft_picks):
    LOGGER_CONTEXT = f"[ncaa.py] / post_wapit_draft({league_id}, {year})"
    try:
        start_time = time.time()

        '''
        Example draft_picks structure
        draft_picks = [
            {"LeagueID": "NBA2024", "PickNumber": 1, "TeamID": "TeamA", "PlayerID": "123", "PlayerName": "LeBron James", "Position": "SF"},
            {"LeagueID": "NBA2024", "PickNumber": 2, "TeamID": "TeamB", "PlayerID": "456", "PlayerName": "Giannis Antetokounmpo", "Position": "PF"},
            {"LeagueID": "NBA2024", "PickNumber": 3, "TeamID": "TeamC", "PlayerID": "789", "PlayerName": "Luka Dončić", "Position": "PG"},
            {"LeagueID": "NBA2024", "PickNumber": 4, "TeamID": "TeamD", "PlayerID": "101", "PlayerName": "Nikola Jokić", "Position": "C"},
            {"LeagueID": "NBA2024", "PickNumber": 5, "TeamID": "TeamE", "PlayerID": "112", "PlayerName": "Kevin Durant", "Position": "SF"},
        ]
        '''

        # split upload into chunks of 25
        counter = 0
        for i in range(0, len(draft_picks), 25):  # Process in chunks of 25
            with table.batch_writer() as batch:
                for pick in draft_picks[i:i+25]:  
                    pick["Timestamp"] = datetime.now().isoformat()
                    batch.put_item(Item=pick)
                    counter += 1

        end_time = time.time()
        elapsed_time = end_time - start_time

        body = {
            "timeElapsed": elapsed_time,
            "leagueName": league_id,
            "year": year,
            "picksSubmitted": counter,
            "draft_picks": draft_picks,
        }

        return body
    
    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception in POST WAPIT Draft !!")
        logger.exception(e)
        return json.dumps("Server Error")


####################
# HELPER FUNCTIONS #
####################

# Build the response to send
def build_response(status_code, response_body=None):
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,DELETE,PATCH",
            "Access-Control-Allow-Headers": "Content-Type,Authorization"
        }
    }

    if response_body is not None:
        response["body"] = json.dumps(response_body, default=str)
    return response


# Calculate the nth day of week of the month/year
def get_nth_day(year, month, day, n):
    # Get first day of month
    date = datetime(year, month, 1)
    dow = date.isoweekday()
    # ISO Weekday is 1 = Monday, 7 = Sunday

    while(dow != day):
        date = date + timedelta(days=1)
        dow = date.isoweekday()

    # Found the 1st day in the given month/year
    # Add (n-1)*7 more days to get the nth day in the given month/year
    date = date + timedelta(days=(n-1)*7)

    return date

# Get users in a cognito user group
# Will be used to get all the league members/teams
def get_users_in_group(user_pool_id, group_name):
    logger.info("Getting cognito users for User Pool ID - " + user_pool_id)
    users = []
    
    response = cognito.list_users_in_group(
        UserPoolId=user_pool_id,
        GroupName=group_name,
        Limit=60
    )

    logger.info("get_users_in_group response: ")
    logger.info(response)

    users.extend(response["Users"])

    return users


# Given a draft, populate the list of teams
def populate_teams_in_league(draft):
    logger.info("Populating teams for League --- " + draft[0]["LeagueID"])

    '''
    Example draft_picks structure
        draft_picks = [
            {"LeagueID": "NBA2024", "PickNumber": 1, "TeamID": "TeamA", "PlayerID": "123", "PlayerName": "LeBron James", "Position": "SF"},
            {"LeagueID": "NBA2024", "PickNumber": 2, "TeamID": "TeamB", "PlayerID": "456", "PlayerName": "Giannis Antetokounmpo", "Position": "PF"},
            {"LeagueID": "NBA2024", "PickNumber": 3, "TeamID": "TeamC", "PlayerID": "789", "PlayerName": "Luka Dončić", "Position": "PG"},
            {"LeagueID": "NBA2024", "PickNumber": 4, "TeamID": "TeamD", "PlayerID": "101", "PlayerName": "Nikola Jokić", "Position": "C"},
            {"LeagueID": "NBA2024", "PickNumber": 5, "TeamID": "TeamE", "PlayerID": "112", "PlayerName": "Kevin Durant", "Position": "SF"},
        ]
    '''
    
    # Sort first
    picks_sorted = sorted(draft, key=lambda x: x["TeamID"])

    # Group by team
    teams = { key: list(group) for key, group in groupby(picks_sorted, key=lambda x: x["TeamID"]) }

    return teams