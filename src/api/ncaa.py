import os
import json
import logging
import urllib3
import time
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime

from utils.helper import get_users_in_group, populate_teams_in_league

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()

dynamodb_table_name      = "wapit_draft"
dynamodb_meta_table_name = "wapit_meta"
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(dynamodb_table_name)
meta_table = dynamodb.Table(dynamodb_meta_table_name)

cognito = boto3.client("cognito-idp")

NCAA_SCHOOLS_URL = "https://www.ncaa.com/json/schools"
NCAA_API_URL = "https://data.ncaa.com/casablanca"
NCAA_MM_LIVE_URL = "https://sdataprod.ncaa.com/"

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()  # e.g. "2024-01-15T10:30:00"
        return super().default(obj)

# Get NCAA schools
def get_schools(event, logger):
    try:
        response = http.request("GET", NCAA_SCHOOLS_URL)
        print("Response Code:", response.status)
        data = json.loads(response.data)

        body = {
            "schools": data
        }

        return 200, body
    except Exception as e:
        logger.exception("Exception in Get Schools method !!")
        logger.exception(e)
        return 500, {"error": "Server error"}
        
# Get NCAA Game Schedule for a Sport/Division/Year/Month
def get_schedule(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("Sport", "football")
        division = event.get("queryStringParameters", {}).get("Division", "fbs")
        year = event.get("queryStringParameters", {}).get("Year", str(datetime.now().year))
        month = event.get("queryStringParameters", {}).get("Month", str(datetime.now().month).zfill(2))

        response = http.request("GET", f"{NCAA_API_URL}/schedule/{sport}/{division}/{year}/{month}/schedule-all-conf.json")
        print("Response Code:", response.status)
        data = json.loads(response.data)

        body = {
            "schedule": data
        }

        return 200, body
    except Exception as e:
        logger.exception("Exception in Get Schedule method !!")
        logger.exception(e)
        return 500, {"error": "Server error"}
    
# Get NCAA Scoreboard for a Sport/Division/Date
def get_scoreboard(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("Sport", "football")
        division = event.get("queryStringParameters", {}).get("Division", "fbs")
        date = event.get("queryStringParameters", {}).get("Date", datetime.now().strftime("%Y%m%d"))

        response = http.request("GET", f"{NCAA_API_URL}/scoreboard/{sport}/{division}/{date}/scoreboard.json")
        print("Response Code:", response.status)
        data = json.loads(response.data)

        body = {
            "scoreboard": data
        }

        return 200, body
    except Exception as e:
        logger.exception("Exception in Get Scoreboard method !!")
        logger.exception(e)
        return 500, {"error": "Server Error"}

# Get NCAA Game Details for a Game/Page
def get_game_details(event, logger):
    try:
        game_id = event.get("queryStringParameters", {}).get("GameID", None)
        page = event.get("queryStringParameters", {}).get("Page", "summary") # summary, playbyplay, boxscore
        if game_id is None:
            return 400, {"error": "Missing GameID in query string"}

        response = http.request("GET", f"{NCAA_API_URL}/game/{game_id}/{page}.json")
        print("Response Code:", response.status)
        data = json.loads(response.data)

        body = {
            page: data
        }

        return 200, body
    except Exception as e:
        logger.exception("Exception in Get Scoreboard method !!")
        logger.exception(e)
        return 500, {"error": "Server Error"}
    

# Get NCAA March Madness WAPIT stats for a player
def get_wapit_stats(event, logger):
    logger.info("[ncaa.py / get_wapit_stats] - In Get WAPIT Stats!!!")
    try:
        id = event.get("queryStringParameters", {}).get("id", None)
        player_name = event.get("queryStringParameters", {}).get("player_name", None)
        number = event.get("queryStringParameters", {}).get("number", None)
        school = event.get("queryStringParameters", {}).get("school", None)
        year = event.get("queryStringParameters", {}).get("year", str(datetime.now().year))
        LOGGER_CONTEXT = f"[ncaa.py / get_wapit_stats({player_name}, {number}, {school}, {year})]"
        if id is None or player_name is None or number is None or school is None or year is None:
            return 400, {"error": "Missing id, player_name, number, school or year in query string"}
        
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

        return 200, body
    except Exception as e:
        logger.exception("Exception in Get Scoreboard method !!")
        logger.exception(e)
        return 500, {"error": "Server Error"}


# Get NCAA March Madness WAPIT stats for an entire league
def get_all_wapit_stats(event, logger):
    logger.info("[ncaa.py / get_all_wapit_stats] - In Get All WAPIT Stats!!!")
    try:
        year = event.get("queryStringParameters", {}).get("year", str(datetime.now().year))
        LOGGER_CONTEXT = f"[ncaa.py / get_all_wapit_stats({year})]"
        if year is None:
            return 400, {"error": "Missing year in query string"}
        
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

        return 200, body
    except Exception as e:
        logger.exception("Exception in Get Scoreboard method !!")
        logger.exception(e)
        return 500, {"error": "Server Error"}


# Get NCAA March Madness Tournament Players
# 1. Get schedule and determine Day 1 & 2 of tournament (3rd Thursday of March = Day 1)
# 2. Get all games on Day 1 & Day 2, then filter those on Tournament games
# 3. For each game, extract the players
def get_wapit_players(event, logger):
    LOGGER_CONTEXT = "[ncaa.py / get_wapit_players()]"
    try:
        year = event.get("queryStringParameters", {}).get("year", str(datetime.now().year))
        if year is None:
            return 400, {"error": "Missing year in query string"}

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

        return 200, body
    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception in Get Scoreboard method !!")
        logger.exception(e)
        return 500, {"error": "Server Error"}
    

# GET /ncaa/wapit/league/{league_id}/year/{year}
# Grab the WAPIT league from the DB
def get_wapit_league(event, logger):
    try:
        league_id = event.get("pathParameters", {}).get("league_id", None)
        year = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        cognito_user_pool_id = event.get("queryStringParameters", {}).get("user_pool_id", None)

        logger.info(f"League ID: {league_id}")
        logger.info(f"Year: {year}")
        logger.info(f"User Pool ID: {cognito_user_pool_id}")

        if league_id is None or year is None or cognito_user_pool_id is None:
            return 400, {
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Missing league_id, year or user_pool_id in request",
                    "details": [
                        {"field": "league_id", "issue": "Required field is missing"},
                        {"field": "year", "issue": "Must be a 4 digit number"},
                        {"field": "user_pool_id", "issue": "Must be a valid user pool id"}
                    ]
                }
            }
        
        LOGGER_CONTEXT = f"[ncaa.py / get_wapit_league({league_id}, {year})]"

        start_time = time.time()

        draft = []
        # Query DB
        response = table.query(
            KeyConditionExpression=Key('LeagueID').eq(league_id + year)
        )

        if "Items" in response:
            draft = response["Items"]
        else:
            return 404, { 
                "error": {
                    "code": "NOT_FOUND",
                    "message": "League not found for given year",
                }
            }
        
        # Get the list of users in the Cognito wapit_ group
        users = get_users_in_group(cognito, cognito_user_pool_id, f"wapit_{league_id}{year}", logger)

        # Order the draft picks into teams format
        teams = {} if len(draft) == 0 else populate_teams_in_league(draft, logger)

        end_time = time.time()
        elapsed_time = end_time - start_time

        logger.info(f"{LOGGER_CONTEXT} - Elapsed time: {elapsed_time:.4f} seconds")

        body = {
            "data": {
                "leagueName": league_id,
                "year": year,
                "users": users,
                "teams": teams,
                "draft": draft
            },
            "timeElapsed": elapsed_time
        }

        logger.info(f"Response Body: {body}")

        return 200, body
    
    except Exception as e:
        logger.exception("Exception in Get WAPIT League method !!")
        logger.exception(e)
        return 500, {
            "status": "Internal Server Error",
            "message": "An exception occurred",
            "timestamp": datetime.now().isoformat()
        }
    

# POST /ncaa/wapit/league/{league_id}/year/{year}/draft
def post_wapit_draft(event, logger):
    try:
        league_id = event.get("pathParameters", {}).get("league_id", None)
        year = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        LOGGER_CONTEXT = f"[ncaa.py / post_wapit_draft({league_id}, {year})]"
        body = json.loads(event.get("body", "{}"))
        draft_picks = body.get("draft_picks", [])

        if league_id is None or year is None:
            return 400, {"error": "Missing league_id or year in path parameters"}
        
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

        return 201, body

    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception in POST WAPIT Draft !!")
        logger.exception(e)
        return 500, {"error": "Server Error"}
    

# GET /ncaa/wapit/league/{league_id}/year/{year}/chat
def get_wapit_chat(event, logger):
    try:
        league_id = event.get("pathParameters", {}).get("league_id", None)
        year      = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        limit     = int(event.get("queryStringParameters", {}).get("limit", 50))

        if league_id is None:
            return 400, {"error": "Missing league_id"}

        # Chat messages live in the same table under a different key prefix
        # LeagueID = "{league_id}{year}#CHAT", sorted by Timestamp
        # get_wapit_chat
        response = table.query(
            KeyConditionExpression=(
                Key("LeagueID").eq(f"{league_id}{year}#CHAT") &
                Key("PickNumber").begins_with("MSG#")
            ),
            ScanIndexForward=False,
            Limit=limit
        )
        messages = list(reversed(response.get("Items", [])))
        return 200, {"messages": messages}
    except Exception as e:
        logger.exception("Exception in get_wapit_chat")
        return 500, {"error": "Server Error"}


# POST /ncaa/wapit/league/{league_id}/year/{year}/chat
def post_wapit_chat(event, logger):
    try:
        league_id = event.get("pathParameters", {}).get("league_id", None)
        year      = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        body      = json.loads(event.get("body", "{}"))
        username  = body.get("username")
        text      = body.get("text", "").strip()

        if not league_id or not username or not text:
            return 400, {"error": "Missing league_id, username, or text"}
        if len(text) > 300:
            return 400, {"error": "Message too long (max 300 chars)"}

        timestamp = datetime.now().isoformat()
        # post_wapit_chat
        item = {
            "LeagueID":  f"{league_id}{year}#CHAT",
            "PickNumber": f"MSG#{timestamp}",   # sort key — lexicographically sortable by time
            "Timestamp":  timestamp,
            "username":   username,
            "text":       text.strip(),
            "reactions":  {},
        }
        table.put_item(Item=item)

        return 201, {"message": item}
    except Exception as e:
        logger.exception("Exception in post_wapit_chat")
        return 500, {"error": "Server Error"}


# POST /ncaa/wapit/league/{league_id}/year/{year}/chat/react
# post_wapit_react — key uses PickNumber, not Timestamp
def post_wapit_react(event, logger):
    try:
        league_id    = event.get("pathParameters", {}).get("league_id", None)
        year         = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        body         = json.loads(event.get("body", "{}"))
        pick_number  = body.get("pick_number")   # "MSG#{timestamp}" string
        username     = body.get("username")
        emoji        = body.get("emoji")

        if not all([league_id, pick_number, username, emoji]):
            return 400, {"error": "Missing required fields"}

        chat_key = f"{league_id}{year}#CHAT"
        item_key = {"LeagueID": chat_key, "PickNumber": pick_number}

        resp = table.get_item(Key=item_key)
        item = resp.get("Item")
        if not item:
            return 404, {"error": "Message not found"}

        reactions = item.get("reactions", {})
        reactors  = set(reactions.get(emoji, []))
        reactors.discard(username) if username in reactors else reactors.add(username)
        reactions[emoji] = list(reactors)

        table.update_item(
            Key=item_key,
            UpdateExpression="SET reactions = :r",
            ExpressionAttributeValues={":r": reactions}
        )

        return 200, {"reactions": reactions}
    except Exception as e:
        logger.exception("Exception in post_wapit_react")
        return 500, {"error": "Server Error"}
    
def get_jwt_username(event):
    """Extract Cognito username from the JWT authorizer context."""
    return (
        event
        .get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
        .get("cognito:username")
    )

def validate_commissioner(league_id, year, event, logger):
    caller = get_jwt_username(event)
    if not caller:
        return None, (401, {"error": "Unauthorized"})

    resp = meta_table.get_item(          # ← meta_table
        Key={"LeagueID": league_id + year}   # ← no PickNumber
    )
    meta = resp.get("Item")
    if not meta:
        return None, (404, {"error": "League not found"})
    if meta.get("CommissionerID") != caller:
        return None, (403, {"error": "Forbidden — you are not the commissioner"})

    return meta, None

# POST /ncaa/wapit/league
# Creates a brand new league META record
def post_wapit_league(event, logger):
    LOGGER_CONTEXT = "[ncaa.py / post_wapit_league]"
    try:
        body         = json.loads(event.get("body", "{}"))
        league_id    = body.get("league_id", "").strip()
        league_name  = body.get("league_name", "").strip()
        year         = body.get("year", str(datetime.now().year))
        total_rounds = int(body.get("total_rounds", 10))
        draft_order  = body.get("draft_order", [])

        caller = get_jwt_username(event)
        if not caller:
            return 401, {"error": "Unauthorized"}
        if not league_id or not league_name:
            return 400, {"error": "Missing league_id or league_name"}

        existing = meta_table.get_item(      # ← meta_table
            Key={"LeagueID": league_id + year}   # ← no PickNumber
        ).get("Item")
        if existing:
            return 409, {"error": "League already exists for this year"}

        meta = {
            "LeagueID":       league_id + year,  # ← no PickNumber
            "LeagueName":     league_name,
            "Year":           year,
            "CommissionerID": caller,
            "Status":         "pending",
            "TotalRounds":    total_rounds,
            "DraftOrder":     draft_order,
            "retroMode":      False,
            "CreatedAt":      datetime.now().isoformat(),
        }
        meta_table.put_item(Item=meta)       # ← meta_table

        logger.info(f"{LOGGER_CONTEXT} - Created league {league_id}{year}")
        return 201, {"meta": meta}

    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception")
        return 500, {"error": "Server Error"}

# PATCH /ncaa/wapit/league/{league_id}/year/{year}
# Updates TotalRounds, DraftOrder, and/or Status — commissioner only
def patch_wapit_league(event, logger):
    LOGGER_CONTEXT = "[ncaa.py / patch_wapit_league]"
    try:
        league_id = event.get("pathParameters", {}).get("league_id")
        year      = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        body      = json.loads(event.get("body", "{}"))

        meta, err = validate_commissioner(league_id, year, event, logger)
        if err:
            return err

        updates = {}
        allowed = {"TotalRounds", "DraftOrder", "Status", "LeagueName", "retroMode"}
        for field in allowed:
            if field in body:
                updates[field] = body[field]

        if not updates:
            return 400, {"error": "No valid fields to update"}

        if "Status" in updates:
            valid_statuses = {"pending", "active", "complete"}
            if updates["Status"] not in valid_statuses:
                return 400, {"error": f"Invalid status. Must be one of: {valid_statuses}"}
            if updates["Status"] == "active":
                draft_order = updates.get("DraftOrder", meta.get("DraftOrder", []))
                if len(draft_order) < 2:
                    return 400, {"error": "Draft order must have at least 2 teams before activating"}

        expr_parts  = [f"#{k} = :{k}" for k in updates]
        expr_names  = {f"#{k}": k for k in updates}
        expr_values = {f":{k}": v for k, v in updates.items()}

        meta_table.update_item(                      # ← meta_table
            Key={"LeagueID": league_id + year},      # ← no PickNumber
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

        logger.info(f"{LOGGER_CONTEXT} - Updated {league_id}{year}: {list(updates.keys())}")
        return 200, {"updated": list(updates.keys())}

    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception")
        return 500, {"error": "Server Error"}

# DELETE /ncaa/wapit/league/{league_id}/year/{year}/team
# Removes a team from DraftOrder and deletes all their picks — commissioner only
def delete_wapit_team(event, logger):
    LOGGER_CONTEXT = "[ncaa.py / delete_wapit_team]"
    try:
        league_id = event.get("pathParameters", {}).get("league_id")
        year      = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        body      = json.loads(event.get("body", "{}"))
        team_id   = body.get("team_id")

        if not team_id:
            return 400, {"error": "Missing team_id"}

        meta, err = validate_commissioner(league_id, year, event, logger)
        if err:
            return err

        if meta.get("Status") == "active":
            return 400, {"error": "Cannot remove a team once the draft is active"}

        draft_order = [u for u in meta.get("DraftOrder", []) if u != team_id]

        meta_table.update_item(                      # ← meta_table
            Key={"LeagueID": league_id + year},      # ← no PickNumber
            UpdateExpression="SET DraftOrder = :d",
            ExpressionAttributeValues={":d": draft_order}
        )

        # Picks still live in wapit_draft — delete via TeamID GSI
        response = table.query(
            IndexName="TeamID-index",
            KeyConditionExpression=Key("TeamID").eq(team_id)
        )
        with table.batch_writer() as batch:
            for item in response.get("Items", []):
                if item["LeagueID"] == league_id + year:
                    batch.delete_item(
                        Key={
                            "LeagueID":   item["LeagueID"],
                            "PickNumber": item["PickNumber"],
                        }
                    )

        logger.info(f"{LOGGER_CONTEXT} - Removed team {team_id} from {league_id}{year}")
        return 200, {"removed": team_id, "newDraftOrder": draft_order}

    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception")
        return 500, {"error": "Server Error"}

# Updated get_wapit_league — splits META from picks in the response
def get_wapit_league(event, logger):
    try:
        league_id            = event.get("pathParameters", {}).get("league_id")
        year                 = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        cognito_user_pool_id = event.get("queryStringParameters", {}).get("user_pool_id")

        if not league_id or not year or not cognito_user_pool_id:
            return 400, {"error": "Missing league_id, year or user_pool_id"}

        start_time = time.time()

        # META from its own table — no PickNumber needed
        meta_resp = meta_table.get_item(         # ← meta_table
            Key={"LeagueID": league_id + year}   # ← no PickNumber
        )
        meta = meta_resp.get("Item")

        # Picks from wapit_draft — filter out chat messages
        draft_resp = table.query(
            KeyConditionExpression=Key("LeagueID").eq(league_id + year)
        )
        draft = [
            i for i in draft_resp.get("Items", [])
            if not str(i.get("PickNumber", "")).startswith("MSG#")
        ]

        if not meta and not draft:
            return 404, {"error": "League not found"}

        users = get_users_in_group(
            cognito, cognito_user_pool_id,
            f"wapit_{league_id}{year}", logger
        )
        teams   = {} if not draft else populate_teams_in_league(draft, logger)
        elapsed = time.time() - start_time

        return 200, {
            "data": {
                "meta":       meta,
                "leagueName": meta.get("LeagueName", league_id) if meta else league_id,
                "year":       year,
                "users":      users,
                "teams":      teams,
                "draft":      draft,
            },
            "timeElapsed": elapsed
        }

    except Exception as e:
        logger.exception("Exception in get_wapit_league")
        return 500, {
            "status": "Internal Server Error",
            "message": "An exception occurred",
            "timestamp": datetime.now().isoformat()
        }

# POST /ncaa/wapit/league/{league_id}/year/{year}/draft/bulk
def post_wapit_draft_bulk(event, logger):
    LOGGER_CONTEXT = "[ncaa.py / post_wapit_draft_bulk]"
    try:
        league_id = event.get("pathParameters", {}).get("league_id")
        year      = event.get("pathParameters", {}).get("year", str(datetime.now().year))
        body      = json.loads(event.get("body", "{}"))
        picks     = body.get("picks", [])

        if not league_id:
            return 400, {"error": "Missing league_id"}
        if not picks:
            return 400, {"error": "No picks provided"}

        meta, err = validate_commissioner(league_id, year, event, logger)
        if err:
            return err
        if meta.get("Status") == "complete":
            return 400, {"error": "Draft is already complete"}

        # Wipe existing picks from wapit_draft (chat stays untouched)
        existing = table.query(
            KeyConditionExpression=Key("LeagueID").eq(league_id + year)
        )
        existing_picks = [
            i for i in existing.get("Items", [])
            if not str(i.get("PickNumber", "")).startswith("MSG#")
        ]
        if existing_picks:
            with table.batch_writer() as batch:
                for item in existing_picks:
                    batch.delete_item(
                        Key={
                            "LeagueID":   item["LeagueID"],
                            "PickNumber": item["PickNumber"],
                        }
                    )

        # Bulk insert into wapit_draft
        timestamp = datetime.now().isoformat()
        counter   = 0
        with table.batch_writer() as batch:
            for pick in picks:
                if not all(k in pick for k in ["PickNumber", "TeamID", "PlayerName"]):
                    continue
                batch.put_item(Item={
                    **pick,
                    "LeagueID":  league_id + year,
                    "Timestamp": timestamp,
                })
                counter += 1

        # Activate league if still pending
        if meta.get("Status") == "pending":
            meta_table.update_item(                      # ← meta_table
                Key={"LeagueID": league_id + year},      # ← no PickNumber
                UpdateExpression="SET #s = :s",
                ExpressionAttributeNames={"#s": "Status"},
                ExpressionAttributeValues={":s": "active"},
            )

        logger.info(f"{LOGGER_CONTEXT} - Bulk inserted {counter} picks into {league_id}{year}")
        return 201, {"inserted": counter}

    except Exception as e:
        logger.exception(f"{LOGGER_CONTEXT} - Exception")
        return 500, {"error": "Server Error"}