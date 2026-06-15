import argparse
import logging
import dotenv
import csv
import os
import datetime

from   typing     import Dict, List
from   redminelib import Redmine


MAX_WORKERS = 20
FINAL_FILE  = "issues.csv"
LOG_FORMAT  = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOGGER      = logging.getLogger("redmines")

dotenv.load_dotenv()

#
# Logging
#
def configure_logging(level=logging.INFO):
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT)


PROJECT_NAME            = "Richieste ALM"
JENKINS_JOB_TO_CREATE   = "Genera job jenkins"
URL_JENKINS_JOB_DEVELOP = "URL Job Jenkins Develop"
URL_JENKINS_JOB_MASTER  = "URL Job Jenkins Master"
URL_JENKINS_JOB_RELEASE = "URL Job Jenkins Release"
URL_JENKINS_JOB_IT      = "URL Job Jenkins It"
URL_JENKINS_JOB_LAB     = "URL Job Jenkins Lab"
URL_JENKINS_JOB_MAIN    = "URL Job Jenkins Main"
APPLICATION_GROUP       = "Gruppo/Applicazione"
APPLICATION_NAME        = "Componente"
APPLICATION_CODE        = "Codice Applicativo"
APPLICATION_LAYER       = "Layer"


def get_issues(server: Redmine, project_id: int, tracker_id: int, status_id=None) -> List[Dict]:

    issues = []
    offset = 0
    limit  = 100

    try:
        while True:

            params = {
                "project_id" : project_id,
                "tracker_id" : tracker_id,
                "offset"     : offset,
                "limit"      : limit,
            }

            if status_id is not None:
                params["status_id"] = status_id
            batch = list(server.issue.filter(**params))
            if not batch:
                break
            issues.extend(batch)
            offset += limit
    except Exception as e:
        LOGGER.error(f"Errore durante il recupero delle issue nel tracker {tracker_id}: {e}")
    return issues

def fetch_project(redmine: Redmine, project_name: str) -> Dict:

    for project in redmine.project.all():
        if project.name == project_name:
            return {
                "id"        : project.id,
                "name"      : project.name,
                "identifier": project.identifier
            }
    raise ValueError(f"Il progetto {project_name}' non è stato trovato!")

def fetch_project_trackers(redmine: Redmine, project_id: int) -> List[Dict]:

    try:
        project  = redmine.project.get(project_id, include=["trackers"])
        trackers = []

        for tracker in getattr(project, "trackers", []):
            trackers.append({
                "id"  : tracker.id,
                "name": tracker.name
            })
        return trackers

    except Exception:
        LOGGER.error(f"Impossibile recuperare trackers associati al progetto {project_id}")
        return []

def fetch_statuses(redmine: Redmine) -> List[Dict]:
    try:
        result = []
        for status in redmine.issue_status.all():
            result.append({
                "id"       : status.id,
                "name"     : status.name,
                "is_closed": getattr(status, "is_closed", False)
            })

        return result

    except Exception:
        LOGGER.error(f"Impossibile recuperare gli stati Redmine!")
        return []

def get_status_id_by_name(statuses: List[Dict], name: str) -> int:

    for status in statuses:
        if status["name"] == name:
            return status["id"]

    raise ValueError(f"Status '{name}' not found")

def extract_custom_fields(issue) -> Dict:

    result = {}

    for field in issue.custom_fields:
        result[field.name] = field.value

    return result

def process_issue(issue):

    fields = extract_custom_fields(issue)
    return {
        "ISSUE_ID"                : issue.id,
        "CREATED_ON"              : issue.created_on,
        "JENKINS_PIPELINE"        : fields.get(JENKINS_JOB_TO_CREATE),
        "TEAM"                    : fields.get(APPLICATION_GROUP),
        "LAYER"                   : fields.get(APPLICATION_LAYER),
        "COMPONENT"               : fields.get(APPLICATION_NAME),
        "APPLICATION_CODE"        : fields.get(APPLICATION_CODE),
        "JENKINS_PIPELINE_DEVELOP": fields.get(URL_JENKINS_JOB_DEVELOP),
        "JENKINS_PIPELINE_MASTER" : fields.get(URL_JENKINS_JOB_MASTER),
        "JENKINS_PIPELINE_RELEASE": fields.get(URL_JENKINS_JOB_RELEASE),
        "JENKINS_PIPELINE_IT"     : fields.get(URL_JENKINS_JOB_IT),
        "JENKINS_PIPELINE_LAB"    : fields.get(URL_JENKINS_JOB_LAB),
        "JENKINS_PIPELINE_MAIN"   : fields.get(URL_JENKINS_JOB_MAIN),
    }

#
# CSV writer
#
def write_csv(file_path, data, fieldnames):

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(data)


#
# Main
#
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()

    try:
        server = Redmine(args.url, key=args.key, requests={"timeout": 30})
        LOGGER.info(f"Connesso al server Redmine {args.url}!")

        project = fetch_project(server, PROJECT_NAME)
        LOGGER.info(f"Recuperato progetto {project['name']} (ID={project['id']})!")

        trackers = fetch_project_trackers(server, project["id"])
        LOGGER.info(f"Recuperati {len(trackers)} trackers dal progetto {project['name']}!")

        statuses  = fetch_statuses(server)
        status_id = get_status_id_by_name(statuses, "Creato")


        records = []
        for tracker in trackers:
            issues = get_issues(server=server, project_id=project["id"], tracker_id=tracker["id"], status_id=status_id)
            LOGGER.info(f"Recuperate {len(issues)} issues per il tracker {tracker['name']} (ID={tracker['id']})")
            for issue in issues:
                record = process_issue(issue)
                records.append(record)

        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(output_dir, f"output_{timestamp}.csv")

        # #
        # # Remove all records which do not contain any pipeline
        # # 
        # url_fields = [
        #     "url_jenkins_develop",
        #     "url_jenkins_master",
        #     "url_jenkins_release",
        #     "url_jenkins_it",
        #     "url_jenkins_lab",
        #     "url_jenkins_main"
        # ]

        # filtered = [
        #     record for record in records
        #         if any(record.get(field) for field in url_fields)]

        write_csv(
            file_path=file_path,
            data=records,
            fieldnames=[
                "ISSUE_ID",
                "CREATED_ON",
                "JENKINS_PIPELINE",
                "TEAM",
                "LAYER",
                "COMPONENT",
                "APPLICATION_CODE",
                "JENKINS_PIPELINE_DEVELOP",
                "JENKINS_PIPELINE_MASTER",
                "JENKINS_PIPELINE_RELEASE",
                "JENKINS_PIPELINE_IT",
                "JENKINS_PIPELINE_LAB",
                "JENKINS_PIPELINE_MAIN"
            ]
        )

    except Exception as e:
        raise 

if __name__ == "__main__":
    configure_logging()
    main()