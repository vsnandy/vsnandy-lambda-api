import os
import json
import logging
import boto3

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodbTableName = "vsnandy_bets"
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(dynamodbTableName)

PKEY = "Bettor"
SKEY = "Week"
IKEY = "Bets"

def handler(event, context):
    # TODO: vsnandy-lambda-api
    logger.info("*** ENVIRONMENT VARIABLES ***")
    logger.info(os.environ['AWS_LAMBDA_LOG_GROUP_NAME'])
    logger.info(os.environ['AWS_LAMBDA_LOG_STREAM_NAME'])
    logger.info('*** EVENT ***')

    logger.info(event)

    httpMethod = event["httpMethod"]
    path = event["path"]

    HEALTH_PATH = "/health"
    BETTOR_PATH = "/bettor"
    BETS_PATH = "/bets"

    if httpMethod == "GET" and path == HEALTH_PATH:
        response = build_response(200)

    elif httpMethod == "GET" and path == BETS_PATH:
        response = getBets()

    elif httpMethod == "POST" and path == BETS_PATH:
        requestBody = event["body"]
        response = putBetsForWeekByBettor(requestBody[PKEY], requestBody[SKEY], requestBody[IKEY])

    elif httpMethod == "GET" and path == BETTOR_PATH:
        response = getBettor(event["queryStringParameters"][PKEY])

    elif httpMethod == "PATCH" and path == BETTOR_PATH:
        requestBody = event["body"]
        response = updateBetsForWeekByBettor(requestBody[PKEY], requestBody[SKEY], requestBody[IKEY])

    elif httpMethod == "POST" and path == BETTOR_PATH + "/add-bets":
        requestBody = event["body"]
        response = addBetsForWeekByBettor(requestBody[PKEY], requestBody[SKEY], requestBody[IKEY])

    elif httpMethod == "POST" and path == BETTOR_PATH:
        requestBody = event["body"]
        response = addBettor(requestBody[PKEY])

    elif httpMethod == "DELETE" and path == BETTOR_PATH:
        requestBody = event["body"]
        response = deleteWeekForBettor(requestBody[PKEY], requestBody[SKEY])

    else:
        response = build_response(404, "Not Found")

    return response

# Scan table for all bets
def getBets():
    try:
        response = table.scan()
        result = response["Items"]

        while "LastEvaluateKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            result.extend(response["Items"])

        body = {
            "bets": response
        }

        return build_response(200, body)
    except Exception as e:
        logger.exception("Exception in GetBets!!")
        logger.exception(e)
        build_response(400, json.dumps("Server error"))

# Get all bets for a given Bettor
def getBettor(bettor, week=None):
    try:
        response = table.get_item(
            Key = {
                PKEY: bettor.upper(),
                SKEY: week
            }
        )

        if "Item" in response:
            return build_response(200, response["Item"])
        else:
            return build_response(404, {"Message": "Bettor: {0}s not found".format(bettor.upper())})
    except Exception as e:
        logger.exception("Exception in GetBettor!!")
        logger.exception(e)
        build_response(400, json.dumps("Server error"))

# Put bets for a Bettor for the Week
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
        build_response(400, json.dumps("Server error"))

# Updates bets for a Bettor for the Week
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
        build_response(400, json.dumps("Server error"))

# Add a bet for a week
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
        build_response(400, json.dumps("Server Error"))

# Add a new Bettor to the DB
def addBettor(bettor):
    try:
        table.put_item(
            Item = {
                PKEY: bettor.upper(),
                SKEY: "TOTAL",
                IKEY: []
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
        build_response(400, json.dumps("Server error"))

# Delete a week for a bettor from the DB
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
        build_response(400, json.dumps("Server error"))


def build_response(statusCode, body=None):
    response = {
        "statusCode": statusCode,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "https://vsnandy.github.io"
        }
    }

    if body is not None:
        response["body"] = body
    return response
