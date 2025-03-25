import os
import json
import logging
import boto3
import urllib3
from boto3.dynamodb.conditions import Key
from api.ncaa import get_schools, get_schedule, get_scoreboard, get_game_details, get_wapit_players, get_wapit_stats

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()

dynamodb_table_name = "vsnandy_bets"
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(dynamodb_table_name)

PKEY = "Bettor"
SKEY = "Week"
IKEY = "Bets"

ESPN_API_URL = "https://sports.core.api.espn.com"
ESPN_HOST = "site.api.espn.com"

def handler(event, context):
    # TODO: vsnandy-lambda-api
    logger.info("*** ENVIRONMENT VARIABLES ***")
    logger.info(os.environ['AWS_LAMBDA_LOG_GROUP_NAME'])
    logger.info(os.environ['AWS_LAMBDA_LOG_STREAM_NAME'])
    logger.info('*** EVENT ***')

    #logger.info(event)

    http_method = event["requestContext"]["http"]["method"]
    path = event["requestContext"]["http"]["path"]

    HEALTH_PATH = "/health"
    BETTOR_PATH = "/bettor"
    BETS_PATH = "/bets"
    ATHLETE_PATH = "/athlete"
    ATHLETES_PATH = "/athletes"
    TEAMS_PATH = "/teams"
    EVENTS_PATH = "/events"
    NCAA_PATH = "/ncaa"

    status_code = 200

    try:        
        # OPTIONS preflight check
        if http_method == "OPTIONS":
            logger.info("IN OPTIONS CHECK!!!")
            preflight_response = {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
                    "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PATCH,DELETE",
                    "Access-Control-Allow-Headers": "Content-Type"
                },
                "body": json.dumps("Preflight Check Complete")
            }

            return preflight_response

        # GET /health
        elif http_method == "GET" and path == HEALTH_PATH:
            response_body = "HEALTHY"

        # POST /health
        elif http_method == "POST" and path == HEALTH_PATH:
            request_body = json.loads(event["body"])
            response_body = request_body["key"]

        # GET /bets
        elif http_method == "GET" and path == BETS_PATH:
            response_body = get_bets()

        # POST /bets?Bettor={}&Week={}&Bets={}
        elif http_method == "POST" and path == BETS_PATH:
            request_body = json.loads(event["body"])
            response_body = put_bets_for_week_by_bettor(request_body[PKEY], request_body[SKEY], request_body[IKEY])

        # GET /bettor?Bettor={}
        elif http_method == "GET" and path == BETTOR_PATH:
            response_body, status_code = get_bettor(event["queryStringParameters"][PKEY])

        # PATCH /bettor
        elif http_method == "PATCH" and path == BETTOR_PATH:
            request_body = json.loads(event["body"])
            response_body = update_bets_for_week_by_bettor(request_body[PKEY], request_body[SKEY], request_body[IKEY])

        # POST /bettor/add-bets
        elif http_method == "POST" and path == BETTOR_PATH + "/add-bets":
            request_body = json.loads(event["body"])
            response_body = add_bets_for_week_by_bettor(request_body[PKEY], request_body[SKEY], request_body[IKEY])

        # POST /bettor
        elif http_method == "POST" and path == BETTOR_PATH:
            request_body = json.loads(event["body"])
            response_body = add_bettor(request_body[PKEY], request_body["year"])

        # DELETE /bettor
        elif http_method == "DELETE" and path == BETTOR_PATH:
            request_body = json.loads(event["body"])
            response_body = delete_week_for_bettor(request_body[PKEY], request_body[SKEY])

        # GET /athletes
        elif http_method == "GET" and path == ATHLETES_PATH:
            params = event["queryStringParameters"]
            response_body = get_all_players(params["sport"], params["league"], params["limit"], params["page"])

        # GET /teams
        elif http_method == "GET" and path == TEAMS_PATH:
            params = event["queryStringParameters"]
            response_body = get_teams(params["sport"], params["league"])

        # GET /events
        elif http_method == "GET" and path == EVENTS_PATH:
            params = event["queryStringParameters"]
            response_body = get_events(params["sport"], params["league"], params["week"])

        # GET /athlete?id={}
        elif http_method == "GET" and path == ATHLETE_PATH:
            params = event["queryStringParameters"]
            response_body = get_player_by_id(params["sport"], params["league"], params["id"])

        # GET /ncaa/schools
        elif http_method == "GET" and path == NCAA_PATH + "/schools":
            response_body = get_schools()

        # GET /ncaa/schedule?sport&division&year&month
        elif http_method == "GET" and path == NCAA_PATH + "/schedule":
            params = event["queryStringParameters"]
            response_body = get_schedule(params["sport"], params["division"], params["year"], params["month"])

        # GET /ncaa/scoreboard?sport&division&date
        elif http_method == "GET" and path == NCAA_PATH + "/scoreboard":
            params = event["queryStringParameters"]
            response_body = get_scoreboard(params["sport"], params["division"], params["date"])

        # GET /ncaa/game?gameId&page
        elif http_method == "GET" and path == NCAA_PATH + "/game":
            params = event["queryStringParameters"]
            response_body = get_game_details(params["gameId"], params["page"])
        
        # GET /ncaa/wapit/players
        elif http_method == "GET" and path == NCAA_PATH + "/wapit/players":
            params = event["queryStringParameters"]
            response_body = get_wapit_players(params["year"])

        # GET /ncaa/wapit/stats
        elif http_method == "GET" and path == NCAA_PATH + "/wapit/stats":
            params = event["queryStringParameters"]
            response_body = get_wapit_stats(params["playerId"], params["playerName"], params["number"], params["school"])

        else:
            build_response(404, "Not Found")
    except Exception as e:
        logger.exception("Exception caught in handler.py!!!")
        return build_response(500, "Server Error")

    return build_response(status_code, response_body)


# Scan table for all bets
# GET /bets
def get_bets():
    try:
        response = table.scan()
        result = response["Items"]

        while "LastEvaluateKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            result.extend(response["Items"])

        body = {
            "bets": result
        }

        return body
    except Exception as e:
        logger.exception("Exception in GetBets!!")
        logger.exception(e)
        raise Exception("Server Error")


# Get all bets for a given Bettor
# GET /bettor?Bettor={}
def get_bettor(bettor):
    try:
        response = table.query(
            KeyConditionExpression=Key("Bettor").eq(bettor.upper())
        )

        if "Items" in response:
            return response["Items"]
        else:
            return {"Message": "Bettor: {0} not found".format(bettor.upper())}, 404
    except Exception as e:
        logger.exception("Exception in GetBettor!!")
        logger.exception(e)
        raise Exception("Server Error")


# Put bets for a Bettor for the Week
# POST /bets?Bettor={}&Week={}&Bets={}
def put_bets_for_week_by_bettor(bettor, week, bets):
    try:
        table.put_item(
            Item = {
                PKEY: bettor.upper(),
                SKEY: week,
                IKEY: bets
            }
        )

        body = {
            "Operation": "INSERT",
            "Message": "SUCCESS",
            "Item": {
                PKEY: bettor.upper(),
                SKEY: week,
                IKEY: bets
            }
        }
        return body
    except Exception as e:
        logger.exception("Exception in PutBetsForWeekByBettor!!")
        logger.exception(e)
        return json.dumps("Server error")


# Updates bets for a Bettor for the Week
# PATCH /bettor?Bettor={}&Week={}&Bets={}
def update_bets_for_week_by_bettor(bettor, week, bets):
    try:
        response = table.update_item(
            Key = {
                PKEY: bettor.upper(),
                SKEY: week
            },
            UpdateExpression = f"set {IKEY} = :value",
            ExpressionAttributeValues = {
                ":value": bets
            },
            ReturnValues="UPDATED_NEW"
        )

        body = {
            "Operation": "UPDATE",
            "Message": "SUCCESS",
            "UpdatedAttributes": response
        }
        return body
    except Exception as e:
        logger.exception("Exception in PutBetsForWeekByBettor!!")
        logger.exception(e)
        return json.dumps("Server error")


# Add a bet for a week
# POST /bettor/add-bets?Bettor={}&Week={}&Bets={}
def add_bets_for_week_by_bettor(bettor, week, bets):
    try:
        response = table.update_item(
            Key = {
                PKEY: bettor.upper(),
                SKEY: week
            },
            UpdateExpression = f"set {IKEY} = list_append({IKEY}, :vals)",
            ExpressionAttributeValues = {
                ":vals": bets
            },
            ReturnValues="ALL_NEW"
        )

        body = {
            "Operation": "APPEND",
            "Message": "SUCCESS",
            "AppendedAttributes": response
        }

        return body
    except Exception as e:
        logger.exception("Exception in AddBetsForWeekByBettor!!")
        logger.exception(e)
        return json.dumps("Server Error")


# Add a new Bettor to the DB
# POST /bettor?Bettor={}
def add_bettor(bettor, year):
    try:
        table.put_item(
            Item = {
                PKEY: bettor.upper(),
                SKEY: f"{year}#TOTAL",
                IKEY: []
            }
        )

        body = {
            "Operation": "CREATE",
            "Message": "SUCCESS",
            "Item": bettor.upper()
        }

        return body
    except Exception as e:
        logger.exception("Exception in AddBettor Method!!")
        logger.exception(e)
        return json.dumps("Server error")


# Delete a week for a bettor from the DB
# DELETE /bettor?Bettor={}&Week={}
def delete_week_for_bettor(bettor, week):
    try:
        response = table.delete_item(
            Key = {
                PKEY: bettor.upper(),
                SKEY: week
            }
        )

        body = {
            "Operation": "DELETE",
            "Message": "SUCCESS",
            "deletedItem": response
        }

        return body
    except Exception as e:
        logger.exception("Exception in DeleteBettor Method!!")
        logger.exception(e)
        return json.dumps("Server error")


# Get All Players for Sport
# GET /athletes
def get_all_players(sport, league, limit, page=1):
    try:
        response = http.request("GET", f"{ESPN_API_URL}/v3/sports/{sport}/{league}/athletes?limit={limit}&page={page}")
        print("Response Code:", response.status)

        data = json.loads(response.data)

        print("Response Keys:", data.keys())
        print("Response Pages:", data["pageCount"])

        body = {
            "players": data["items"],
            "pageCount": data["pageCount"],
            "count": data["count"],
            "pageIndex": data["pageIndex"],
            "pageSize": data["pageSize"]
        }

        return body
    except Exception as e:
        logger.exception("Exception in Get All Players Method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get all teams for sport
# GET /teams
def get_teams(sport, league):
    try:
        response = http.request(
            "GET", 
            f"{ESPN_API_URL}/apis/site/v2/sports/{sport}/{league}/teams",
            headers={
                "Host": ESPN_HOST
            }
        )

        print("Response Code:", response.status)
        data = json.loads(response.data)
        body = {
            "teams": data["sports"][0]["leagues"][0]["teams"]
        }
        return body

    except Exception as e:
        logger.exception("Exception in Get Teams method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get events for sport
# GET /events
def get_events(sport, league, week = ""):
    try:
        response = http.request(
            "GET", 
            f"{ESPN_API_URL}/apis/site/v2/sports/{sport}/{league}/scoreboard?week={week}",
            headers={
                "Host": ESPN_HOST
            }
        )
        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Events method !!")
        logger.exception(e)
        return json.dumps("Server error")

# Get player info
# GET /player/:id
def get_player_by_id(sport, league, id):
    try:
        response = http.request(
            "GET", 
            f"{ESPN_API_URL}/apis/common/v3/sports/{sport}/{league}/athletes/{id}",
            headers={
                "Host": ESPN_HOST
            }
        )

        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Player by ID method !!")
        logger.exception(e)
        return json.dumps("Server error")

# Build the response to send
def build_response(status_code, response_body=None):
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,DELETE,PATCH"
        }
    }

    if response_body is not None:
        response["body"] = json.dumps(response_body)
    return response
