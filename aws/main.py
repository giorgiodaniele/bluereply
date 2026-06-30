accounts = [
    {'name': 'Infra'                  , 'email': 'blue.aws.subscription+infra@reply.it'},
    {'name': 'Agent'                  , 'email': 'blue.aws.subscription+agent@reply.it'},
    {'name': 'Data'                   , 'email': 'blue.aws.subscription+data@reply.it'},
    {'name': 'Application'            , 'email': 'blue.aws.subscription+app@reply.it'},
    {'name': 'Integration'            , 'email': 'blue.aws.subscription+integrazione@reply.it'},
]

import boto3
org_client = boto3.client('organizations')

for account in accounts:
    res = org_client.create_account(Email=account['email'], AccountName=account['name'])
    print(f"Creating    {account['name']}: {account['email']}")
    print(f"Request ID: {res['CreateAccountStatus']['Id']}\n")