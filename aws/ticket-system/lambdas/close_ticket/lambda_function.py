import boto3
import json

from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb", region_name="eu-central-1")
table    = dynamodb.Table("tickets")


def lambda_handler(event, context):

    response = table.scan(FilterExpression=Attr("status").eq("OPEN"))
    items    = response["Items"]

    print(f"found {len(items)} OPEN tickets")

    for item in items:

        print(f"closing ticket {item['id']}")

        table.update_item(
            Key={
                "id": item["id"]
            },
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":status": "CLOSED"
            }
        )

    return {
        "statusCode": 200,
        "body"      : json.dumps({
            "message": "Tickets closed...",
            "closed" : len(items)
        })
    }