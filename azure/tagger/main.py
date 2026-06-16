#!/usr/bin/env python3
__author__      = "Giorgio Daniele Luppina"
__version__     = "1.0"
__description__ = "Using a CSV as datasource, this script applies tags to Azure resources and resource groups"

from urllib.parse        import unquote
from azure.identity      import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

import csv
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("tagger.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logging.getLogger("azure").setLevel(logging.ERROR)

logger          = logging.getLogger(__name__)
sid             = "05476e17-e88b-43a4-a2de-12e26e0717f1"
credential      = DefaultAzureCredential()
client          = ResourceManagementClient(credential, sid)


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


def main():

    logger.info("Starting tagging process")

    success = 0
    failed  = 0

    rg_processed = set()

    with open(
        "azure_resources.csv",
        newline="",
        encoding="utf-8"
    ) as file:
        
        reader = csv.DictReader(file)
        for index, record in enumerate(reader, start=2):

            res_id   = None
            res_name = None
            tags     = {}

            try:

                res_id   = get_resource_id(record["RESOURCE LINK"])
                res_name = res_id.split("/")[-1]

                tags = build_tags(record)

                if not tags:
                    logger.info("Record %s skipped: no tags found", index)
                    continue

                apply_tags(res_id, tags)

                rg = record.get("RESOURCE GROUP", "").strip()
                if rg and rg not in rg_processed:
                    apply_tags(f"/subscriptions/{sid}/resourceGroups/{rg}", tags)
                    rg_processed.add(rg)
                    
                success += 1
                logger.info("Resource '%s' tagged successfully", res_name)

            except Exception as e:
                failed += 1
                logger.info("Resource=%s RID=%s Tags=%s", res_name, res_id, tags)
                logger.info("Tagging failed: %s", str(e))

    logger.info("Tagging process completed. Success=%s Failed=%s", success, failed)


if __name__ == "__main__":
    main()