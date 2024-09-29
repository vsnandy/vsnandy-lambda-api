import os
import json
import logging
import boto3

logging.basicConfig()
logger = logging.getLogger(__name__)

dynamodbTableName = "vsnandy_bets"
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(dynamodbTableName)

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
        requestBody = json.loads(event["body"])

        response = putBetsForWeekByBettor(requestBody["bettor"], requestBody["week"], requestBody["bets"])

    elif httpMethod == "GET" and path == BETTOR_PATH:
        response = getBettor(event["queryStringParameters"]["bettor"])

    elif httpMethod == "PATCH" and path == BETTOR_PATH:
        requestBody = json.loads(event["body"])
        response = updateBetsForWeekByBettor(requestBody["better"], requestBody["week"], requestBody["bets"])

    elif httpMethod == "POST" and path == BETTOR_PATH:
        requestBody = json.loads(event["body"])
        response = addBettor(requestBody["bettor"])

    elif httpMethod == "DELETE" and path == BETTOR_PATH:
        requestBody = json.loads(event["body"])
        response = deleteBettor(requestBody["bettor"])

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
                "Bettor": bettor.upper(),
                "Week": week
            }
        )

        if "Item" in response:
            return build_response(200, response["Item"])
        else:
            return build_response(404, {"Message": "ProductId: {0}s not found".format(bettor.upper())})
    except Exception as e:
        logger.exception("Exception in GetBettor!!")
        logger.exception(e)
        build_response(400, json.dumps("Server error"))

# Put bets for a Bettor for the Week
def putBetsForWeekByBettor(bettor, week, bets):
    try:
        table.put_item(
            Item = {
                "Bettor": bettor.upper(),
                "Week": week,
                "Bets": bets
            }
        )

        body = {
            "Operation": "INSERT",
            "Message": "SUCCESS",
            "Item": {
                "Bettor": bettor.upper(),
                "Week": week,
                "Bets": bets
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
                "Bettor": bettor.upper()
            },

            UpdateExpression = "set {0}s = :value".format(week),
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

# Add a new Bettor to the DB
def addBettor(bettor):
    try:
        table.put_item(
            Item = {
                "Bettor": bettor.upper(),
                "Week": "TOTAL",
                "Bets": []
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

# Delete a Bettor from the DB
def deleteBettor(bettor):
    try:
        response = table.delete_item(
            Key = {
                "Bettor": bettor.upper()
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
        response["body"] = json.dumps(body, cls=CustomEncoder)
    return response
