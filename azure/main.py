from   azure.identity      import DefaultAzureCredential
from   azure.mgmt.resource import ResourceManagementClient
import json
import uuid

subscription_id = "db053b9a-dd8a-4b7a-8eb7-cfbe46960c55"
credential      = DefaultAzureCredential()
client          = ResourceManagementClient(credential, subscription_id)
location        = "norwayeast"

def delete_resource_groups():
    rgs = client.resource_groups.list()
    for rg in rgs:
        print(f"Deleting rg {rg.name} ...")
        client.resource_groups.begin_delete(rg.name)
        print(f"Deleting rg {rg.name} ... completed!")

def create_resource_groups():
    for i in range(0, 4):
        name = f"rg-{uuid.uuid4().hex[:8]}"
        print(f"Creating rg {name} ...")
        client.resource_groups.create_or_update(
            name,
            {
                "location"          : "norwayeast",
                "tags": {
                    "environment"   : "demo",
                    "owner"         : "g.luppina@reply.it",
                    "application"   : "test",
                    "business_unit" : "BLUTIT_CA"
                }
            }
        )
        print(f"Creating rg {name} ... completed!")

if __name__ == "__main__":
    delete_resource_groups()
    create_resource_groups()