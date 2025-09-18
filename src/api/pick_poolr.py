import json
import os
import logging
import datetime
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from utils.helper import build_response

dynamodb = boto3.resource("dynamodb")
pick_poolr_table_name = "pick_poolr_bets"
pick_poolr_table = dynamodb.Table(pick_poolr_table_name)

# CREATE (Put new record)
def create_bet_record(event, logger):
    body = json.loads(event.get("body", "{}"))
    bettor = body.get("bettor", None)
    week = body.get("week", None)
    name = body.get("name", None)
    props = body.get("props", [])
    total_odds = body.get("total_odds", 0)
    if bettor is None or week is None or name is None:
        return build_response(400, "Missing 'bettor', 'week' or 'name' in request body")
    
    logger.info(f"Creating new bet record for {bettor} - {week}...")

    try:
        response = pick_poolr_table.put_item(
            Item={
                "PK": f"BETTOR#{bettor}",
                "SK": f"WEEK#{week}",
                "bettor": bettor,
                "week": week,
                "name": name,
                "props": props,
                "total_odds": total_odds,
                "status": "PENDING",
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            },
            ConditionExpression="attribute_not_exists(bettor) AND attribute_not_exists(week)" # avoid overwrite
        )
        return response
    except Exception as e:
        logger.exception("Error creating bet record - ")
        logger.exception(e)
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.exception("Record already exists !!")
            logger.exception(e)
            return build_response(400, "Record already exists")
        else:
            raise

# READ (Get record by bettor + week)
def get_bet_record(event, logger):
    bettor = event.get("queryStringParameters", {}).get("bettor", None)
    week = event.get("queryStringParameters", {}).get("week", None)
    if bettor is None or week is None:
        return build_response(400, "Missing 'bettor' or 'week' in query string")
    
    logger.info(f"Getting bet record for {bettor} - {week}...")

    try:
        response = pick_poolr_table.get_item(
            Key={
                "PK": f"BETTOR#{bettor}",
                "SK": f"WEEK#{week}"
            }
        ).get("Item", None)

        if response is None:
            return build_response(404, "Record not found")
        
        return response
    except Exception as e:
        raise

# DELETE (Remove record completely)
def delete_bet_record(event, logger):
    body = json.loads(event.get("body", "{}"))
    bettor = body.get("bettor", None)
    week = body.get("week", None)

    if bettor is None or week is None:
        return build_response(400, "Missing 'bettor' or 'week' in request body")
    
    logger.info(f"Deleting bet record for {bettor} - {week}...")

    try:
        response = pick_poolr_table.delete_item(
            Key={
                "PK": f"BETTOR#{bettor}",
                "SK": f"WEEK#{week}"
            }
        )
        return response
    except Exception as e:
        raise
