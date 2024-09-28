import os
import json
import logging

logger = logging.getLogger()
logger.setLevel("INFO")

def handler(event, context):
    # TODO: vsnandy-lambda-api
    logger.info()
    logger.info("*** ENVIRONMENT VARIABLES ***")
    logger.info(os.environ['AWS_LAMBDA_LOG_GROUP_NAME'])
    logger.info(os.environ['AWS_LAMBDA_LOG_STREAM_NAME'])
    logger.info('*** EVENT ***')
    logger.info(event)

    message = f"Hello, {event['name']}!"


    return {
        'statusCode': 200,
        'body': json.dumps(message)
    }