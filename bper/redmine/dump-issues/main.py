
import os
import logging
from   concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv     import load_dotenv
from redminelib import Redmine


#
# Logging
#
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


REDMINE_PROJECT = "Richieste ALM"


def load_configuration() -> tuple[str, str, str]:
    load_dotenv()

    url        = os.getenv("REDMINE_SERVER_URL")
    username   = os.getenv("REDMINE_USERNAME")
    password   = os.getenv("REDMINE_PASSWORD")

    if not url or not username or not password:
        raise ValueError("Missing Redmine configuration")

    return url, username, password


def connect_to_redmine(
    url     : str,
    username: str,
    password: str,
) -> Redmine:


    try:
        redmine = Redmine(url, username=username, password=password)
        logging.info("Connected successfully to %s", url)
        return redmine

    except Exception as e:
        raise RuntimeError(f"Failed to connect to Redmine: {url}") from e


def process_tracker(
    redmine : Redmine,
    project : object,
    tracker : object,
) -> None:

    logging.info("Processing tracker: %s ...", tracker.name)

    #
    # Get all issues for tracker
    #
    try:
        issues = redmine.issue.filter(project_id=project.id, tracker_id=tracker.id) 
    except Exception as e:
        raise RuntimeError(f"Failed to get issues for tracker: {tracker.name}") from e
    logging.info(f"Found {len(issues)} issues for tracker {tracker.name}")

    #
    # Prepare CSV rows
    #
    rows = []

    for issue in issues:

        row = {
            "id"      : issue.id,
            "subject" : issue.subject,
            "project" : issue.project.name,
            "tracker" : issue.tracker.name,
            "status"  : issue.status.name,
            "priority": issue.priority.name,
            "author"  : issue.author.name,
            "assigned_to": (
                issue.assigned_to.name
                if hasattr(issue, "assigned_to")
                else ""
            ),
            "category": (
                issue.category.name
                if hasattr(issue, "category")
                else ""
            ),
            "fixed_version": (
                issue.fixed_version.name
                if hasattr(issue, "fixed_version")
                else ""
            ),
            # "start_date"     : issue.start_date,
            # "due_date"       : issue.due_date,
            # "done_ratio"     : issue.done_ratio,
            # "estimated_hours": issue.estimated_hours,
            # "spent_hours"    : issue.spent_hours,
            # "created_on"     : issue.created_on,
            # "updated_on"     : issue.updated_on,
            # "closed_on"      : issue.closed_on,
            # "description"    : issue.description,
        }

        #
        # Custom fields
        #
        for custom_field in issue.custom_fields:
            row[f"custom_{custom_field.name}"] = custom_field.value
        rows.append(row)

    if not rows:
        logging.info("No issues found for tracker %s", tracker.name)
        return

    #
    # Get all columns, including custom fields
    #
    fieldnames = []

    for row in rows:
        for field in row:
            if field not in fieldnames:
                fieldnames.append(field)

    #
    # Save tracker CSV
    #
    filename = f"{tracker.id}.csv"

    try:
        import csv
        with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        raise RuntimeError(f"Failed to save CSV for tracker: {tracker.name}") from e

    logging.info("Done processing tracker: %s", tracker.name)


def main() -> None:
    url, username, password = load_configuration()

    # Connect to Redmine
    redmine = connect_to_redmine(url, username, password)

    # Find the project
    try:
        project = None

        for item in redmine.project.all():
            if item.name == REDMINE_PROJECT:
                project = item
                break

        if project is None:
            raise RuntimeError(f"Project not found: {REDMINE_PROJECT}")

    except Exception as exc:
        raise RuntimeError(f"Failed to find project: {REDMINE_PROJECT}") from exc


    try:
        logging.info("Getting trackers for project %s ...", project.name)
        trackers = project.trackers
    except Exception as exc:
        raise RuntimeError(f"Failed to get trackers for project: {REDMINE_PROJECT}") from exc


    for tracker in trackers:
        logging.info("Processing tracker: %s ...", tracker.name)
        process_tracker(redmine, project, tracker)
        logging.info("Done processing tracker: %s", tracker.name)


if __name__ == "__main__":
    main()
