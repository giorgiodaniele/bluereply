#
# Use this script to migrate standalone jobs
#

import csv
import os
import sys
import logging
import dotenv
import jenkins
import xml.etree.ElementTree as ET

dotenv.load_dotenv()

JENKINS_URL              = os.getenv("JENKINS_URL")
JENKINS_USERNAME         = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD         = os.getenv("JENKINS_PASSWORD")
INPUT_FILE               = "resources.csv"

# Load certificate
os.environ["REQUESTS_CA_BUNDLE"] = "../../bperROOTCA.crt"


def connect_jenkins(url, username, password):
    try:
        return jenkins.Jenkins(url=url, username=username, password=password)
    except Exception as e:
        return f"Failed to connect to Jenkins: {e}"

def process_component(server, fullname, tech, new_env=False):

    # Read XML config
    xml_text = server.get_job_config(fullname)
    xml      = ET.fromstring(xml_text)

    if tech == "python":

        """
        THIS IS USUALLY REQUIRED BY ANY TEAM OPERATING PYTHON. THEY USUALLY
        REQUIRE TO MIGRATE JENKINSFILE, REPLACING CI FOR APP INTO CI FOR LIB
        AS A CONSEQUENCE, IT IS REQUESTED TO EDIT SCRIPT PATH
        """

        tag = xml.find(".//scriptPath")
        if tag is not None:
            if not new_env:
                tag.text = "Jenkins_docker_python_lib"
            else:
                tag.text = "Jenkins_python_lib"


    elif tech == "java":

        """
        THIS IS USUALLY REQUIRED BY ANY TEAM OPERATING JAVA. THEY USUALLY
        REQUIRE TO MIGRATE JDKS, ADDING JDKs IN MULTIPLE CHOICES. AS A
        CONSEQUENCE, IT IS REQUESTED TO ADD JDKs TO PARAMETERS SECTION
        """
        pass


    else:
        pass

    # Write XML config
    xml_text = ET.tostring(xml, "utf-8").decode("utf-8")
    server.reconfig_job(fullname, xml_text)


if __name__ == "__main__":

    #
    # Connect Jenkins server
    #
    server = connect_jenkins(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
    if type(server) == str:
        logging.error(server)
        sys.exit(1)

    # Get all pipeline jobs considering just workflow jobs (pipelines)
    all_jobs  = server.get_all_jobs()
    pipelines = [job for job in all_jobs if job["_class"] == "org.jenkinsci.plugins.workflow.job.WorkflowJob"]

    #
    # Read components from file
    #
    names = {}
    with open(INPUT_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for record in reader:
            names[record["name"]] = record["tech"]

    #
    # For each pipeline in Jenkins, select
    # all jobs whose name matches the name
    # of the component listed in the document
    #
    for pipeline in pipelines:
        pipeline_name = pipeline["fullname"].rsplit("-", 1)[0]
        for name in names:
            if pipeline_name == name:
                process_component(server, pipeline["fullname"], names[name], new_env=False)
                print(f"Pipeline {pipeline['fullname']} processed!")
