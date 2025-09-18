from datetime import datetime
import os
import json
import logging
import boto3
import urllib3
from boto3.dynamodb.conditions import Key
from api.ncaa import (
    get_schools, get_schedule, get_scoreboard, get_game_details, 
    get_wapit_players, get_wapit_stats, get_wapit_league, post_wapit_draft, 
    get_all_wapit_stats
)
from api.pick_poolr import (
    create_bet_record, get_bet_record, delete_bet_record
)
from utils.helper import build_response

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
NKEY = "Name"

ESPN_API_URL = "https://sports.core.api.espn.com"
ESPN_HOST = "site.api.espn.com"

# Define routes
ROUTES = {
    "OPTIONS": {
        "default": "handle_options"
    },
    "GET": {
        "/health": "get_health",
        "/bets": "get_bets",
        "/bettor": "get_bettor",
        "/athletes": "get_all_players",
        "/teams": "get_teams",
        "/events": "get_events",
        "/athlete": "get_player_by_id",
        "/ncaa/schools": "get_schools",
        "/ncaa/schedule": "get_schedule",
        "/ncaa/scoreboard": "get_scoreboard",
        "/ncaa/game": "get_game_details",
        "/ncaa/wapit/players": "get_wapit_players",
        "/ncaa/wapit/stats/player": "get_wapit_stats",
        "/ncaa/wapit/stats/league": "get_all_wapit_stats",
        "/ncaa/wapit/league": "get_wapit_league",
        "/pick-poolr/bets": "get_bet_record"
    },
    "POST": {
        "/health": "post_health",
        "/bets": "put_bets_for_week_by_bettor",
        "/bettor": "add_bettor",
        "/bettor/add-bets": "add_bets_for_week_by_bettor",
        "/ncaa/wapit/league": "post_wapit_draft",
        "/pick-poolr/bets": "create_bet_record"
    },
    "PATCH": {
        "/bettor": "update_bets_for_week_by_bettor"
    },
    "DELETE": {
        "/bettor": "delete_week_for_bettor",
        "/pick-poolr/bets": "delete_bet_record"
    }
}

def handler(event, context):
    logger.info("*** ENVIRONMENT VARIABLES ***")
    logger.info(os.environ['AWS_LAMBDA_LOG_GROUP_NAME'])
    logger.info(os.environ['AWS_LAMBDA_LOG_STREAM_NAME'])
    logger.info('*** EVENT ***')
    logger.info(event)

    http_method = event["requestContext"]["http"]["method"]
    path = event["requestContext"]["http"]["path"]

    logger.info(f"HTTP Method: {http_method}, Path: {path}")

    status_code = 200
    response_body = {}

    try:
        # Route the request
        route_handler = ROUTES.get(http_method, {}).get(path, None)
        logger.info(f"Route Handler: {route_handler}")
        if route_handler:
            handler_function = globals()[route_handler]
            response_body = handler_function(event, logger)
        else:
            return build_response(404, "Not Found")

    except Exception as e:
        logger.exception("Exception caught in handler.py!!!")
        logger.exception(e)
        return build_response(500, "Server Error")

    return build_response(status_code, response_body)

def handle_options(event, logger):
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PATCH,DELETE",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps("Preflight Check Complete")
    }

def get_health(event, logger):
    return {
        "status": "OK",
        "message": "Service is healthy",
        "timestamp": datetime.now().isoformat()
    }

def post_health(event, logger):
    return {
        "status": "OK",
        "message": event.get("body", "No message received"),
        "timestamp": datetime.now().isoformat()
    }

# Scan table for all bets
# GET /bets
def get_bets(event, logger):
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
def get_bettor(event, logger):
    try:
        bettor = event.get("queryStringParameters", {}).get("Bettor", None)

        if bettor is None:
            return {"Message": "Bettor parameter is required"}, 400
        
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
def put_bets_for_week_by_bettor(event, logger):
    try:
        bettor = event.get("queryStringParameters", {}).get("Bettor", None)
        name = event.get("queryStringParameters", {}).get("Name", None)
        week = event.get("queryStringParameters", {}).get("Week", None)
        bets = event.get("queryStringParameters", {}).get("Bets", None)

        if bettor is None or week is None or name is None or bets is None:
            return {"Message": "Bettor, Name, Week and Bets parameters are required"}, 400
        
        table.put_item(
            Item = {
                PKEY: bettor.upper(),
                NKEY: name,
                SKEY: week,
                IKEY: bets
            }
        )

        body = {
            "Operation": "INSERT",
            "Message": "SUCCESS",
            "Item": {
                PKEY: bettor.upper(),
                NKEY: name,
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
def update_bets_for_week_by_bettor(event, logger):
    try:
        bettor = event.get("queryStringParameters", {}).get("Bettor", None)
        name = event.get("queryStringParameters", {}).get("Name", None)
        week = event.get("queryStringParameters", {}).get("Week", None)
        bets = event.get("queryStringParameters", {}).get("Bets", None)

        if bettor is None or week is None or name is None or bets is None:
            return {"Message": "Bettor, Name, Week and Bets parameters are required"}, 400
        
        response = table.update_item(
            Key = {
                PKEY: bettor.upper(),
                NKEY: name,
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
def add_bets_for_week_by_bettor(event, logger):
    try:
        bettor = event.get("queryStringParameters", {}).get("Bettor", None)
        week = event.get("queryStringParameters", {}).get("Week", None)
        bets = event.get("queryStringParameters", {}).get("Bets", None)

        if bettor is None or week is None or bets is None:
            return {"Message": "Bettor, Week and Bets parameters are required"}, 400
        
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
def add_bettor(event, logger):
    try:
        bettor = event.get("queryStringParameters", {}).get("Bettor", None)
        name = event.get("queryStringParameters", {}).get("Name", None)
        year = event.get("queryStringParameters", {}).get("Year", datetime.now().year)
                                                          
        if bettor is None or name is None:
            return {"Message": "Bettor and Name parameters are required"}, 400

        table.put_item(
            Item = {
                PKEY: bettor.upper(),
                NKEY: name,
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
def delete_week_for_bettor(event, logger):
    try:
        bettor = event.get("queryStringParameters", {}).get("Bettor", None)
        week = event.get("queryStringParameters", {}).get("Week", None)
        if bettor is None or week is None:
            return {"Message": "Bettor and Week parameters are required"}, 400
        
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
def get_all_players(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", "football")
        league = event.get("queryStringParameters", {}).get("league", "college-football")
        limit = event.get("queryStringParameters", {}).get("limit", 100)
        page = event.get("queryStringParameters", {}).get("page", 1)
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400
        
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
def get_teams(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", "football")
        league = event.get("queryStringParameters", {}).get("league", "college-football")
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400

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
def get_events(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", "football")
        league = event.get("queryStringParameters", {}).get("league", "college-football")
        week = event.get("queryStringParameters", {}).get("week", "")
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400

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
def get_player_by_id(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", "football")
        league = event.get("queryStringParameters", {}).get("league", "college-football")
        id = event.get("queryStringParameters", {}).get("id", None)
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400

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