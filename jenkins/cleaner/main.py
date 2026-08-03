import logging
import sys
import jenkins
import os
import csv
import time
import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s - %(message)s")

LOGGER            = logging.getLogger(__name__)
JENKINS_SERVER    = os.getenv("JENKINS_SERVER")
JENKINS_USERNAME  = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD  = os.getenv("JENKINS_PASSWORD")
JENKINS_PIPELINES = os.getenv("JENKINS_PIPELINES")

os.environ["REQUESTS_CA_BUNDLE"] = "../res/bperROOTCA.crt"

def connect_server():
    try:
        LOGGER.info("Connecting to Jenkins server %s...", JENKINS_SERVER)
        server = jenkins.Jenkins(JENKINS_SERVER, username=JENKINS_USERNAME, password=JENKINS_PASSWORD, timeout=120)
        whoami = server.get_whoami()
        LOGGER.info("Successfully authenticated as %s", whoami["fullName"])
        return server
    except Exception as e:
        LOGGER.exception(f"Something unexpected happened: {e}")
        sys.exit(1)


def main():

    # Connect Jenkins and get all pipelines by fullname and name
    server        = connect_server()
    all_pipelines = [job.get("fullname", job["name"]) for job in server.get_all_jobs()]

    # Read all components, by skipping the header
    with open(JENKINS_PIPELINES, encoding="utf-8") as file:
        components = [record for record in csv.reader(file)][1:]

    matches = {}
    for namespace, component in components:
        component_matches = []
        for pipeline in all_pipelines:
            job_name = pipeline.rsplit("/", 1)[-1]
            if job_name == component or job_name.startswith(component + "-"):
                component_matches.append(pipeline)
        matches[(namespace, component)] = component_matches

    for (namespace, component), pipelines in matches.items():
        if not pipelines:
            LOGGER.warning("No pipelines found for %s/%s", namespace, component)
            continue

        for pipeline in pipelines:
            try:
                LOGGER.info("Deleting pipeline %s...", pipeline)
                server.delete_job(pipeline)
                LOGGER.info("Deleted pipeline %s", pipeline)
            except Exception:
                LOGGER.exception("Failed to delete pipeline %s", pipeline)
                continue

if __name__ == "__main__":
    main()