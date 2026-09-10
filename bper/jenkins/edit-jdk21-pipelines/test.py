
import logging
import os
import sys
import xml.etree.ElementTree as ET
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   pathlib            import Path

import dotenv
import jenkins


dotenv.load_dotenv()


JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")

JOBS_FILE   = Path("pipelines.txt")
CA_BUNDLE   = "../../bperROOTCA.crt"
MAX_WORKERS = 10


# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)


# Jenkins configuration
def connect_to_jenkins() -> jenkins.Jenkins:

    if not all([JENKINS_URL, JENKINS_USERNAME, JENKINS_PASSWORD]):
        raise RuntimeError("JENKINS_URL, JENKINS_USERNAME and " "JENKINS_PASSWORD must be configured")

    try:
        logger.info("Connecting to Jenkins: %s ...", JENKINS_URL)
        server = jenkins.Jenkins(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
        server.get_whoami()
        logger.info("Connected successfully to %s", JENKINS_URL)
        return server
    except Exception:
        logger.exception("Failed to connect to Jenkins: %s", JENKINS_URL)
        sys.exit(1)

# Read Jenkins to process from TXT file
def load_pipelines() -> list[str]:
    with JOBS_FILE.open("r", encoding="utf-8") as file:
       return [ line.strip() for line in file if line.strip() and not line.strip().startswith("#") ]


def process_job(server: jenkins.Jenkins, fullname: str) -> None:

    try:
        xml_text = server.get_job_config(fullname)
        xml      = ET.fromstring(xml_text)

        parameters = xml.find(".//parameterDefinitions")
        if parameters is None:
            logger.warning("No parameter definitions found for: %s", fullname)
            return None

        #
        # Edit JDKs
        #
        for parameter in parameters:
            name = parameter.find("name")

            if name is None or name.text != "jdkVersion":
                continue

            choices = parameter.find(".//choices/a")
            if choices is None:
                logger.warning("No choices found for jdkVersion in: %s", fullname)
                break

            # Remove it first if it already exists, to avoid duplicates
            for choice in choices.findall("string"):
                if choice.text == "JDK_21.0.3":
                    choices.remove(choice)

            # Add as the first choice => default
            new_choice      = ET.Element("string")
            new_choice.text = "JDK_21.0.3"
            choices.insert(0, new_choice)
            break

        #
        # Edit the job
        #
        config_xml = ET.tostring(xml, encoding="unicode")
        server.reconfig_job(fullname, config_xml)

    except Exception:
        logger.exception("Failed at processing: %s", fullname)
        return None


# Load all pipeline jobs
def load_all_pipelines(server: jenkins.Jenkins) -> list[str]:
    jobs = server.get_all_jobs()

    return [
        job
        for job in jobs
        if job.get("_class")
        == "org.jenkinsci.plugins.workflow.job.WorkflowJob"
    ]


# Main
def main() -> None:

    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE

    server               = connect_to_jenkins()
    pipelines_to_process = load_pipelines()
    pipelines            = load_all_pipelines(server)

    for pipeline in pipelines:
        for pipeline_to_process in pipelines_to_process:
            if pipeline["fullname"].startswith(pipeline_to_process):
                logging.info(f"Found matching pipeline: {pipeline["fullname"]}")
                process_job(server, pipeline["fullname"])

if __name__ == "__main__":
    main()
