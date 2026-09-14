import logging
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import dotenv
import jenkins

dotenv.load_dotenv()


JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")

PIPELINE_FILE = Path("Application_Codes_From_Redmine.txt")
CA_BUNDLE     = "../../bperROOTCA.crt"

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S", stream=sys.stdout, force=True)
logger = logging.getLogger(__name__)

def connect_to_jenkins() -> jenkins.Jenkins:
    try:
        server = jenkins.Jenkins(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
        server.get_whoami()
        logger.info("Connected successfully to %s", JENKINS_URL)
        return server
    except Exception:
        logger.error("Failed to connect to Jenkins: %s", JENKINS_URL)
        sys.exit(1)


def edit_application_code(fullname: str, xml: ET.Element, application_code: str) -> bool:

    updated = False

    for param in xml.findall(".//parameterDefinitions/*"):
        name_elem = param.find("name")
        if name_elem is not None and name_elem.text == "applicationCode":
            default_val_elem = param.find("defaultValue")

            if default_val_elem is not None:
                old_val               = default_val_elem.text if default_val_elem.text else ""
                default_val_elem.text = application_code
            else:
                default_val_elem      = ET.SubElement(param, "defaultValue")
                default_val_elem.text = application_code
            updated = True
            break

    if old_val == "":
        logger.info(f"Job {fullname} missing application code. It will use now value={application_code}")
    else:
        logger.info(f"Job {fullname} already existings application code (old value={old_val}). It will use now value={application_code}")
    return updated


def process_job(server: jenkins.Jenkins, fullname: str, application_code: str) -> None:
    try:
        xml_text = server.get_job_config(fullname)
        xml      = ET.fromstring(xml_text)

        # Run edit
        edit_application_code(fullname=fullname, xml=xml, application_code=application_code)

        updated_xml_text = ET.tostring(xml, encoding="unicode")
        server.reconfig_job(fullname, updated_xml_text)
        logger.info(f"Job {fullname} reconfigured successfully with new application code: {application_code}")

    except Exception as e:
        logger.error(f"Failed to process job {fullname}: {e}")


# Load all pipeline jobs
def load_all_pipelines(server: jenkins.Jenkins) -> list[dict]:
    jobs = server.get_all_jobs()

    return [
        job
        for job in jobs
        if job.get("_class") == "org.jenkinsci.plugins.workflow.job.WorkflowJob"
    ]


def load_pipelines() -> list[tuple[str, str]]:

    pipelines = []
    with PIPELINE_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            cleaned = line.strip()
            # Skip empty lines and comments
            if not cleaned or cleaned.startswith("#"):
                continue
            # Split each line into two parts
            parts = [part.strip() for part in cleaned.split(",", 1)]
            if len(parts) == 2:
                pipelines.append((parts[0], parts[1]))

    return pipelines


# Main
def main() -> None:

    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE

    server               = connect_to_jenkins()
    pipelines_to_process = load_pipelines()
    pipelines            = load_all_pipelines(server)

    for pipeline in pipelines:
        for (pipeline_name, application_code) in pipelines_to_process:
            if pipeline["fullname"].startswith(pipeline_name):
                process_job(server=server, fullname=pipeline["fullname"], application_code=application_code if application_code else "")
                break


if __name__ == "__main__":
    main()