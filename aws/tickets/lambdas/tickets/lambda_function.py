import os
import json
import uuid
import boto3
import datetime

dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table(os.environ["TICKETS_TABLE"])


#
# This lambda is responsible for:
#
# POST    /tickets      → create a ticket
# GET     /tickets/{id} → fetch a ticket
# PUT     /tickets/{id} → update a ticket
# DELETE  /tickets/{id} → delete a ticket
#
def handler(event, context):

    method    = event["requestContext"]["http"]["method"]
    path      = event["requestContext"]["http"]["path"]
    protocol  = event["requestContext"]["http"]["protocol"]
    source_ip = event["requestContext"]["http"]["sourceIp"]

    #
    # POST /tickets
    #
    if method == "POST" and path == "/tickets":

        body        = json.loads(event["body"])
        title       = body.get("title")
        description = body.get("description")

        #
        # Validate request
        #
        if not title:
            return {
                "statusCode": 400,
                "body"      : json.dumps({
                    "message": "Bad request: there is no title"
                })
            }

        if not description:
            return {
                "statusCode": 400,
                "body"      : json.dumps({
                    "message": "Bad request: there is no description"
                })
            }

        ticket_id = str(uuid.uuid4())

        #
        # Create ticket
        #
        ticket = {
            "ticket_id"  : ticket_id,
            "title"      : title,
            "description": description,
            "status"     : "OPEN",
            "created_at" : datetime.datetime.utcnow().isoformat()
        }

        table.put_item(
            Item=ticket
        )

        return {
            "statusCode": 201,
            "body"      : json.dumps(ticket)
        }

    #
    # GET /tickets/{id}
    #
    if method == "GET":

        tid = event.get("pathParameters", {}).get("id")

        if not tid:
            return {
                "statusCode": 400,
                "body"      : json.dumps({
                    "message": "Missing ticket id"
                })
            }

        res = table.get_item(
            Key={
                "ticket_id": tid
            }
        )

        ticket = res.get("Item")

        return {
            "statusCode": 404,
            "body"      : json.dumps({
                "message": "Ticket not found"
            })
        } if ticket is None else {
            "statusCode": 200,
            "body"      : json.dumps(ticket)
        }

    #
    # PUT /tickets/{id}
    #
    if method == "PUT":

        tid = event.get("pathParameters", {}).get("id")

        if not tid:
            return {
                "statusCode": 400,
                "body"      : json.dumps({
                    "message": "Missing ticket id"
                })
            }

        body = json.loads(event["body"])

        title       = body.get("title")
        description = body.get("description")
        status      = body.get("status")

        #
        # Verify ticket exists
        #
        res = table.get_item(
            Key={
                "ticket_id": tid
            }
        )

        ticket = res.get("Item")

        if ticket is None:
            return {
                "statusCode": 404,
                "body"      : json.dumps({
                    "message": "Ticket not found"
                })
            }

        update_expr = []
        attr_values = {}

        if title is not None:
            update_expr.append("title = :title")
            attr_values[":title"] = title

        if description is not None:
            update_expr.append("description = :description")
            attr_values[":description"] = description

        if status is not None:
            update_expr.append("#status = :status")
            attr_values[":status"] = status

        if not update_expr:
            return {
                "statusCode": 400,
                "body"      : json.dumps({
                    "message": "Nothing to update"
                })
            }

        res = table.update_item(
            Key={
                "ticket_id": tid
            },
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues=attr_values,
            ReturnValues="ALL_NEW"
        )

        return {
            "statusCode": 200,
            "body"      : json.dumps(res["Attributes"])
        }

    #
    # DELETE /tickets/{id}
    #
    if method == "DELETE":

        tid = event.get("pathParameters", {}).get("id")

        if not tid:
            return {
                "statusCode": 400,
                "body"      : json.dumps({
                    "message": "Missing ticket id"
                })
            }

        res = table.get_item(
            Key={
                "ticket_id": tid
            }
        )

        ticket = res.get("Item")

        if ticket is None:
            return {
                "statusCode": 404,
                "body"      : json.dumps({
                    "message": "Ticket not found"
                })
            }

        table.delete_item(
            Key={
                "ticket_id": tid
            }
        )

        return {
            "statusCode": 204,
            "body"      : ""
        }

    #
    # Unsupported route
    #
    return {
        "statusCode": 405,
        "body"      : json.dumps({
            "message": "Method not allowed"
        })
    }