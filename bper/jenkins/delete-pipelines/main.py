#
# Use this script to delete all pipelines that are listed in resources.csv
#

import csv
import os
import sys
import logging
import dotenv
import jenkins

dotenv.load_dotenv()

JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")
INPUT_FILE       = "pipelines_to_delete.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s - %(message)s")

def connect_server(url: str, username: str, password: str) -> jenkins.Jenkins | str:
    try:
        return jenkins.Jenkins(url=url, username=username, password=password)
    except Exception as e:
        return f"Failed to connect to Jenkins: {e}"

def read_resources(filename: str) -> list[str]:
    with open(filename, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [f"{record['namespace'].strip()}/{record['component'].strip()}" for record in reader]

def main():
    server = connect_server(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
    if type(server) == str:
        logging.error(server)
        sys.exit(1)

    resources = read_resources(INPUT_FILE)
    for resource in resources:
        resource_branched = [f"{resource}-{branch}" for branch in ("master", "develop", "release", "it", "lab", "main")]
        for resource_branched in resource_branched:
            try:
                server.get_job_info(resource_branched)
                server.delete_job(resource_branched)
                logging.info(f"Deleted pipeline job {resource_branched}")
            except Exception as e:
                logging.error(f"Failed to delete pipeline job {resource_branched}: {e}")


if __name__ == "__main__":
    main()