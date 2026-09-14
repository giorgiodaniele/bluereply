
import os
import csv
import sys
import logging
import dotenv
import shutil
from   redminelib import Redmine

REDMINE_PROJECT = "Richieste ALM"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

def connect_remdmine(url: str, username: str, password: str) -> Redmine:
    try:
        redmine = Redmine(url, username=username, password=password)
        return redmine
    except Exception as e:
        logging.error(f"Failed at Redmine connection: {url}. Exiting program with error code 1")
        sys.exit(1)

def process_tracker(server: Redmine, project: object, tracker: object):

    records = []
    offset  = 0
    limit   = 100


    while True:
        issues = server.issue.filter(project_id=project.id, tracker_id=tracker.id, status_id="*", offset=offset, limit=limit)
        if not issues:
            break

        for issue in issues:
            record = {
                "id"      : issue.id,
                "subject" : issue.subject,
                "project" : issue.project.name,
                "tracker" : issue.tracker.name,
                "status"  : issue.status.name,
                "priority": issue.priority.name,
                "author"  : issue.author.name,
            }

            for cf in issue.custom_fields:
                fn         = f"custom_{cf.name}".replace(" ", "_")
                record[fn] = cf.value
            records.append(record)

        offset += limit

    fieldnames = []
    for record in records:
        for field in record:
            if field not in fieldnames:
                fieldnames.append(field)

    filename = f"output/{tracker.name}.csv".replace(" ", "_")
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    logger.info("Saved %d issues to %s", len(records), filename)

def process_results(input_dir="output", output_file="redmine_issues.csv"):

    csv_files = [os.path.join(input_dir, filename)
        for filename in os.listdir(input_dir)
        if  filename.endswith(".csv")
        and filename != os.path.basename(output_file)
    ]

    if not csv_files:
        return

    records = []
    columns = []

    for filename in csv_files:
        with open(filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for field in reader.fieldnames or []:
                if field not in columns:
                    columns.append(field)

            for row in reader:
                records.append(row)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

def main() -> None:

    os.makedirs("output", exist_ok=True)
    dotenv.load_dotenv()

    project  = None
    trackers = None
    server   = connect_remdmine(url=os.getenv("REDMINE_SERVER_URL"), username=os.getenv("REDMINE_USERNAME"), password=os.getenv("REDMINE_PASSWORD"))

    for p in server.project.all():
        if p.name == REDMINE_PROJECT:
            project = p

    if project is None:
        logging.error(f"Project ${REDMINE_PROJECT} not found")
        sys.exit(1)

    trackers = project.trackers
    for t in trackers:
        logging.info(f"Processing Redmine tracker {t.name} ...")
        process_tracker(server, project, t)

    process_results()

    # remove temp output
    shutil.rmtree("output")


if __name__ == "__main__":
    main()