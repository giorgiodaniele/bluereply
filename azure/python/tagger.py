#!/usr/bin/env python3
from urllib.parse        import unquote
from azure.identity      import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.core.exceptions import HttpResponseError
import csv
import os
import dotenv

dotenv.load_dotenv()
SUBSCRIPTION_ID = os.getenv("SUBSCRIPTION_ID")
credential      = DefaultAzureCredential()
client          = ResourceManagementClient(credential=credential, subscription_id=SUBSCRIPTION_ID)

def get_resource_id(url: str) -> str:
    marker = "#resource"
    if marker not in url:
        raise ValueError(f"Invalid Azure Portal URL: {url}")
    return unquote(url.split(marker, 1)[1])


def build_tags(record: dict) -> dict:

    tags = {
        "business_unit": record.get("business_unit"),
        "owner":         record.get("owner"),
        "application":   record.get("application"),
        "environment":   record.get("environment")
    }

    return {
        key: str(value).strip()
        for key, value in tags.items()
        if value and str(value).strip()
    }


def apply_tags(scope: str, tags: dict) -> None:

    client.tags.begin_create_or_update_at_scope(
        scope=scope,
        parameters={
            "operation" : "Replace",
            "properties": {
                "tags"  : tags
            }
        }
    ).result()

import csv

AZURE_EXPORT = "resources.csv"

def main():

    #
    # Statistics
    #
    success = 0
    failing = 0
    rgroups = set()

    with open(AZURE_EXPORT, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for index, record in enumerate(reader, start=1):
            
            try:
                # Get the resource and apply 
                id   = get_resource_id(record["RESOURCE LINK"])
                name = id.split("/")[-1]
                tags = build_tags(record)
                apply_tags(id, tags)

                # Attach tags to resource group the resource belongs to
                rg = record.get("RESOURCE GROUP", "").strip()
                if rg and rg not in rgroups:
                    apply_tags(f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{rg}", tags)
                    rgroups.add(rg)
                print(f"Tags applied to resource_id={id}")
            except Exception:
                print(f"Can't apply tags to resource_id={id}")
                continue

if __name__ == "__main__":
    main()



