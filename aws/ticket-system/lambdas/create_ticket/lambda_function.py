import json
import uuid
import boto3

from  datetime import datetime

dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table("tickets")


def lambda_handler(event, context):

    body = json.loads(event["body"])

    #
    # Generate the ticket
    #
    ticket = {
        "id"          : str(uuid.uuid4()),
        "title"       : body["title"],
        "status"      : "OPEN",
        "created_at"  : datetime.utcnow().isoformat()
    }

    #
    # Put the ticket within the database
    #
    table.put_item(Item=ticket)

    # Return that a new ticket has been inserted into
    # the database
    return {
        "statusCode": 201,
        "body"      : json.dumps(ticket)
    }