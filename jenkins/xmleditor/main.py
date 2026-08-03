# Author:       Giorgio Daniele Luppina
# Date:         2026-07-23
# Description:  Considering BPER's Jenkins build, this script will update JDK choices for all jobs
#               listed in resources.csv

import csv
import logging
import os
import xml.etree.ElementTree as ET
import dotenv
import jenkins
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   lib                import *

dotenv.load_dotenv()

JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def read_resources(filename: str) -> set[str]:
    resources = set()
    with open(filename, "r", encoding="utf-8") as fd:
        reader = csv.DictReader(fd)
        for record in reader:
            resources.add(f"{record['folder']}/{record['component']}")
    return resources

def process_pipeline(server: jenkins.Jenkins, pipeline_path: str):

    # Get TXT job configuration from pipeline path out of XML
    xml = server.get_job_config(pipeline_path)
    txt = ET.fromstring(xml)

    # EDIT IN HERE
    add_jdk_option(node=txt, jdk="JDK_17.0.5")

    # Get XML job configuration from pipeline path out of TXT
    # and then request Jenkins to update the job
    xml = ET.tostring(txt, encoding="utf-8").decode("utf-8")
    server.reconfig_job(pipeline_path, xml)
    
    LOGGER.info(f"Aggiornato con successo il job: {pipeline_path}")

def main():

    resources = read_resources("resources.csv")
    server    = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD, timeout=120)

    # Run in parallel the execution
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(process_pipeline, server, path): path for path in resources}
        for future in as_completed(futures):
            path = futures[future]
            try:
                future.result()
            except Exception as e:
                LOGGER.error(f"Error fetching {path}: {e}")


if __name__ == "__main__":
    main()