import argparse
import logging
import sys
import redminelib

LOGGER       = logging.getLogger(__name__)
PROJECT_NAME = "Richieste ALM"
OUTPUT_DIR   = "out"

import csv

def main():

    #
    # Create a new argument parse
    #
    parser = argparse.ArgumentParser(description="Fetch and process Redmine issues by tracker.")
    parser.add_argument("--url", required=True, help="Redmine server URL")
    parser.add_argument("--key", required=True, help="API Key")
    args = parser.parse_args()

    #
    # Connect Redmine
    #
    try:
        server = redminelib.Redmine(args.url, key=args.key, requests={"timeout": 30})
        LOGGER.info("Connected to %s", args.url)
    except Exception as e:
        LOGGER.error("Failed to connect to Redmine: %s", e)
        sys.exit(1)

    #
    # Find new project
    #
    project = next((p for p in server.project.all() if p.name.strip() == PROJECT_NAME), None)
    if not project:
        raise ValueError(f"Project '{PROJECT_NAME}' not found!")

    #
    # Find all issues
    #
    records = {}
    limit   = 100
    for tracker in project.trackers:
        issues = []
        offset = 0
        while True:
            batch = list(server.issue.filter(project_id=project.id, tracker_id=tracker.id, status_id="*", offset=offset, limit=limit))
            if not batch:
                break
            LOGGER.info("Found %d issues for %s", len(batch), tracker.name)
            issues.extend(batch)
            offset += limit
        records[tracker.name] = issues


    # 1. Flatten the issues into single-level dictionaries
    rows          = []
    custom_fields = set()

    for tracker, issues in records.items():
        for issue in issues:
            row = {
                "Tracker"   : tracker,
                "Id"        : issue.id,
                "Author"    : getattr(issue.author, "name", ""),
                "Subject"   : issue.subject,
                "Created_on": issue.created_on,
                "Updated_on": issue.updated_on,
                "Url"       : issue.url,
            }

            # Extract custom fields and add them directly as top-level keys
            for cf in getattr(issue, "custom_fields", []):
                cf_name      = cf.name
                row[cf_name] = cf.value
                custom_fields.add(cf_name)
            rows.append(row)

    # Define the fieldnames
    fieldnames = [
        "Tracker",
        "Id",
        "Author",
        "Subject",
        "Created_on",
        "Cpdated_on",
        "Url",
    ] + sorted(custom_fields)

    # Create if not exists
    import os
    import datetime
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Write CSV with datetime
    with open(os.path.join(OUTPUT_DIR, f"issues_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"), "w", newline="", encoding="utf-8") as fd:
        writer = csv.DictWriter(fd, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()