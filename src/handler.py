import os
import json
import logging
import boto3
import urllib3
from boto3.dynamodb.conditions import Key

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()

dynamodbTableName = "vsnandy_bets"
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(dynamodbTableName)

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

    logger.info(event)

    httpMethod = event["requestContext"]["http"]["method"]
    path = event["requestContext"]["http"]["path"]

    HEALTH_PATH = "/health"
    BETTOR_PATH = "/bettor"
    BETS_PATH = "/bets"
    ATHLETE_PATH = "/athlete"
    ATHLETES_PATH = "/athletes"
    TEAMS_PATH = "/teams"
    EVENTS_PATH = "/events"

    # OPTIONS preflight check
    if httpMethod == "OPTIONS":
        logger.info("IN OPTIONS CHECK!!!")
        response = {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PATCH,DELETE",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps("Preflight Check Complete")
        }

        return response

    # GET /health
    elif httpMethod == "GET" and path == HEALTH_PATH:
        response = build_response(200, "HEALTHY")

    # POST /health
    elif httpMethod == "POST" and path == HEALTH_PATH:
        requestBody = json.loads(event["body"])
        response = build_response(200, requestBody["key"])

    # GET /bets
    elif httpMethod == "GET" and path == BETS_PATH:
        response = getBets()

    # POST /bets?Bettor={}&Week={}&Bets={}
    elif httpMethod == "POST" and path == BETS_PATH:
        requestBody = json.loads(event["body"])
        response = putBetsForWeekByBettor(requestBody[PKEY], requestBody[SKEY], requestBody[IKEY])

    # GET /bettor?Bettor={}
    elif httpMethod == "GET" and path == BETTOR_PATH:
        response = getBettor(event["queryStringParameters"][PKEY])

    # PATCH /bettor?Bettor={}&Week={}&Bets={}
    elif httpMethod == "PATCH" and path == BETTOR_PATH:
        requestBody = json.loads(event["body"])
        response = updateBetsForWeekByBettor(requestBody[PKEY], requestBody[SKEY], requestBody[IKEY])

    # POST /bettor/add-bets?Bettor={}&Week={}&Bets={}
    elif httpMethod == "POST" and path == BETTOR_PATH + "/add-bets":
        requestBody = json.loads(event["body"])
        response = addBetsForWeekByBettor(requestBody[PKEY], requestBody[SKEY], requestBody[IKEY])

    # POST /bettor?Bettor={}
    elif httpMethod == "POST" and path == BETTOR_PATH:
        requestBody = json.loads(event["body"])
        response = addBettor(requestBody[PKEY])

    # DELETE /bettor?Bettor={}&Week={}
    elif httpMethod == "DELETE" and path == BETTOR_PATH:
        requestBody = json.loads(event["body"])
        response = deleteWeekForBettor(requestBody[PKEY], requestBody[SKEY])

    # GET /athletes
    elif httpMethod == "GET" and path == ATHLETES_PATH:
        params = event["queryStringParameters"]
        response = getAllPlayers(params["sport"], params["league"], params["limit"], params["page"])

    # GET /teams
    elif httpMethod == "GET" and path == TEAMS_PATH:
        params = event["queryStringParameters"]
        response = getTeams(params["sport"], params["league"])

    # GET /events
    elif httpMethod == "GET" and path == EVENTS_PATH:
        params = event["queryStringParameters"]
        response = getEvents(params["sport"], params["league"], params["week"])

    # GET /athlete?id={}
    elif httpMethod == "GET" and path == ATHLETE_PATH:
        params = event["queryStringParameters"]
        response = getPlayerById(params["sport"], params["league"], params["id"])

    else:
        response = build_response(404, "Not Found")

    return response


# Scan table for all bets
# GET /bets
def getBets():
    try:
        response = table.scan()
        result = response["Items"]

        while "LastEvaluateKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            result.extend(response["Items"])

        body = {
            "bets": result
        }

        return build_response(200, body)
    except Exception as e:
        logger.exception("Exception in GetBets!!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))


# Get all bets for a given Bettor
# GET /bettor?Bettor={}
def getBettor(bettor):
    try:
        response = table.query(
            KeyConditionExpression=Key("Bettor").eq(bettor)
        )

        if "Item" in response:
            return build_response(200, response["Item"])
        else:
            return build_response(404, {"Message": "Bettor: {0}s not found".format(bettor.upper())})
    except Exception as e:
        logger.exception("Exception in GetBettor!!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))


# Put bets for a Bettor for the Week
# POST /bets?Bettor={}&Week={}&Bets={}
def putBetsForWeekByBettor(bettor, week, bets):
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
        return build_response(200, body)
    except Exception as e:
        logger.exception("Exception in PutBetsForWeekByBettor!!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))


# Updates bets for a Bettor for the Week
# PATCH /bettor?Bettor={}&Week={}&Bets={}
def updateBetsForWeekByBettor(bettor, week, bets):
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
        return build_response(200, body)
    except Exception as e:
        logger.exception("Exception in PutBetsForWeekByBettor!!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))


# Add a bet for a week
# POST /bettor/add-bets?Bettor={}&Week={}&Bets={}
def addBetsForWeekByBettor(bettor, week, bets):
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

        return build_response(200, body)
    except Exception as e:
        logger.exception("Exception in AddBetsForWeekByBettor!!")
        logger.exception(e)
        return build_response(400, json.dumps("Server Error"))


# Add a new Bettor to the DB
# POST /bettor?Bettor={}
def addBettor(bettor):
    try:
        table.put_item(
            Item = {
                PKEY: bettor.upper()
            }
        )

        body = {
            "Operation": "CREATE",
            "Message": "SUCCESS",
            "Item": bettor.upper()
        }

        return build_response(200, body)
    except Exception as e:
        logger.exception("Exception in AddBettor Method!!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))


# Delete a week for a bettor from the DB
# DELETE /bettor?Bettor={}&Week={}
def deleteWeekForBettor(bettor, week):
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

        return build_response(200, body)
    except Exception as e:
        logger.exception("Exception in DeleteBettor Method!!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))


# Get All Players for Sport
# GET /athletes
def getAllPlayers(sport, league, limit, page=1):
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

        return build_response(200, body)
    except Exception as e:
        logger.exception("Exception in Get All Players Method !!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))
    
# Get all teams for sport
# GET /teams
def getTeams(sport, league):
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
        return build_response(200, body)

    except Exception as e:
        logger.exception("Exception in Get Teams method !!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))
    
# Get events for sport
# GET /events
def getEvents(sport, league, week = ""):
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
        return build_response(200, body)
    
    except Exception as e:
        logger.exception("Exception in Get Events method !!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))

# Get player info
# GET /player/:id
def getPlayerById(sport, league, id):
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
        return build_response(200, body)
    
    except Exception as e:
        logger.exception("Exception in Get Player by ID method !!")
        logger.exception(e)
        return build_response(400, json.dumps("Server error"))

# Build the response to send
def build_response(statusCode, body=None):
    response = {
        "statusCode": statusCode,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,DELETE,PATCH"
        }
    }

    if body is not None:
        response["body"] = json.dumps(body)
    return response
