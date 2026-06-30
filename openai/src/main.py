from collections import defaultdict
import time
import dotenv
import os
import csv
import pandas

from datetime           import datetime, timedelta
from openai             import OpenAI
from focus              import *
from concurrent.futures import ThreadPoolExecutor

dotenv.load_dotenv()

OPENAI_ORGANIZATION_NAME = os.getenv("OPENAI_ORGANIZATION_NAME")
OPENAI_ORGANIZATION_ID   = os.getenv("OPENAI_ORGANIZATION_ID")
OPENAI_SECRET_KEY        = os.getenv("OPENAI_SECRET_KEY")


def span():

    today = datetime.now()

    # First day of current month
    fdthm = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Last day and first day of last month
    ldlm = fdthm - timedelta(seconds=1)
    fdlm = ldlm.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return int(fdlm.timestamp()), int(ldlm.timestamp())

ts, te  = span()



def get_projs():
    client  = OpenAI(admin_api_key=OPENAI_SECRET_KEY, organization=OPENAI_ORGANIZATION_ID)
    records = list(client.admin.organization.projects.list())
    rows    = []

    for project in records:
        rows.append(project.model_dump())

    if rows:
        fieldnames = sorted({k for row in rows for k in row})
        with open("out/projects.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Exports {len(records)} records about projects")

    return records

def get_costs():
    client  = OpenAI(admin_api_key=OPENAI_SECRET_KEY, organization=OPENAI_ORGANIZATION_ID)
    page    = None
    buckets = []
    records = []

    while True:
        res = client.admin.organization.usage.costs(start_time=ts, end_time=te, bucket_width="1d", group_by=["line_item", "project_id", "api_key_id"], limit=31, page=page)
        buckets.extend(res.data)
        if not res.has_more:
            break
        page = res.next_page

    for bucket in buckets:
        for item in bucket.results:
            records.append([
                bucket.start_time,      # UNIX timestamp representing when invoices starts
                bucket.end_time,        # UNIX timestamp representing when invoices finishes
                item.amount.currency,
                item.amount.value,
                item.api_key_id,
                item.line_item,
                item.object,
                item.organization_id,
                item.project_id,
                item.quantity,
            ])

    print(f"Exports {len(records)} records about costs")

    return records

def get_users():
    client  = OpenAI(admin_api_key=OPENAI_SECRET_KEY, organization=OPENAI_ORGANIZATION_ID)
    records = list(client.admin.organization.users.list())
    rows    = [user.model_dump() for user in records]

    if rows:
        fieldnames = sorted({k for row in rows for k in row})
        with open("out/users.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Exports {len(records)} records about users")

    return records

def get_keys():
    client  = OpenAI(admin_api_key=OPENAI_SECRET_KEY, organization=OPENAI_ORGANIZATION_ID)
    records = list(client.admin.organization.admin_api_keys.list())
    rows    = []

    for key in records:
        rows.append({
            "id"                : key.id,
            "name"              : key.name,
            "created_at"        : key.created_at,
            "expires_at"        : key.expires_at,
            "last_used_at"      : key.last_used_at,
            "owner_id"          : key.owner.id,
            "owner_created_at"  : key.owner.created_at,
            "owner_name"        : key.owner.name,
            "owner_role"        : key.owner.role,
            "owner_type"        : key.owner.type,
        })

    if rows:
        fieldnames = rows[0].keys()

        with open("out/api_keys.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Exports {len(records)} records about API keys")

    return records






if __name__ == "__main__":
    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(get_projs),
            executor.submit(get_costs),
            executor.submit(get_users),
            executor.submit(get_keys),
        ]

        for future in futures:
            future.result()

    print(f"Completed in {time.perf_counter() - started:.2f} seconds")
