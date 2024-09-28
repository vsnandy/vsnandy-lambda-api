import json

def handler(event, context):
    # TODO: Implement
    return {
        'statusCode': 200,
        'body': json.dumps("Hello, World!")
    }