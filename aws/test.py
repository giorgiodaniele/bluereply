import boto3

dynamodb = boto3.resource(
    "dynamodb",
    region_name="eu-central-1"
)

table = dynamodb.Table("tickets")

response = table.scan()

print(response["Items"])