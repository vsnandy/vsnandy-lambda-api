import json
import logging
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("In lambda")
    print("IN LAMBDA")

    # Query DynamoDB table
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:4566")
    table = dynamodb.Table("bets")

    logger.info("DYNAMODB:", dynamodb)
    logger.info("TABLE:", table)

    try:
        response = table.query(KeyConditionExpression=Key("hash_key").eq("TEST") & Key("range_key").eq("test"))
    except Exception as e:
        print(e.response['Error']['Message'])
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/plain'
            },
            'body': 'Hello, World!'
        }
    
    print("total count of element: ",len(response))

    return json.dumps(response, default=str)