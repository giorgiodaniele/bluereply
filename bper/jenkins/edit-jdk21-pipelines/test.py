
import logging
import os
import sys
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   pathlib            import Path

import dotenv
import jenkins


dotenv.load_dotenv()


JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")

JOBS_FILE   = Path("jobs.txt")
CA_BUNDLE   = "../../bperROOTCA.crt"
MAX_WORKERS = 10


#
# Logging
#
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)


#
# Jenkins configuration
#

def connect_to_jenkins() -> jenkins.Jenkins:

    if not all([JENKINS_URL, JENKINS_USERNAME, JENKINS_PASSWORD]):
        raise RuntimeError("JENKINS_URL, JENKINS_USERNAME and " "JENKINS_PASSWORD must be configured")

    try:
        logger.info("Connecting to Jenkins: %s ...", JENKINS_URL)
        server = jenkins.Jenkins(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
        server.get_whoami()
        logger.info("Connected successfully to %s", JENKINS_URL)
    except Exception:
        logger.exception("Failed to connect to Jenkins: %s", JENKINS_URL)
        sys.exit(1)

#
# Read Jenkins to process from TXT file
#

def load_pipelines() -> list[str]:
    with JOBS_FILE.open("r", encoding="utf-8") as file:
       return [ line.strip() for line in file if line.strip() and not line.strip().startswith("#") ]


#
# Check one job
#

def process_job(server: jenkins.Jenkins, fullname: str) -> None:

    try:
        server.get_job_config(fullname)
        print(fullname)
    except Exception:
        logger.exception("Failed at processing: %s", fullname)
        return None

#
# Load all pipeline jobs
#
def load_all_jobs(server: jenkins.Jenkins) -> list[str]:
    jobs = server.get_all_jobs()

    return [
        job
        for job in jobs
        if job.get("_class")
        == "org.jenkinsci.plugins.workflow.job.WorkflowJob"
    ]

#
# Main
#

def main() -> None:

    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE

    server               = connect_to_jenkins()
    pipelines_to_migrate = load_pipelines()



if __name__ == "__main__":
    main()
