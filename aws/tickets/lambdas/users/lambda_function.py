import os
import boto3

dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table(os.environ["USERS_TABLE"])

#
# This lambda is responsible for
#
#
# POST    /tickets      → create a ticket
# GET     /tickets/{id} → fetch  a ticket
# PUT     /tickets/{id} → update a ticket
# DELETE  /tickets/{id} → delete a ticket