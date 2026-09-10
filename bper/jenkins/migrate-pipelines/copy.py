#!/usr/bin/env python3

import csv
import logging
import os
import sys
import xml.etree.ElementTree as ET
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   datetime           import datetime
from   pathlib            import Path

import dotenv
import jenkins


dotenv.load_dotenv()


JENKINS_SOURCE_URL           = os.getenv("JENKINS_SOURCE_URL")
JENKINS_SOURCE_USERNAME      = os.getenv("JENKINS_SOURCE_USERNAME")
JENKINS_SOURCE_PASSWORD      = os.getenv("JENKINS_SOURCE_PASSWORD")
JENKINS_DESTINATION_URL      = os.getenv("JENKINS_DESTINATION_URL")
JENKINS_DESTINATION_USERNAME = os.getenv("JENKINS_DESTINATION_USERNAME")
JENKINS_DESTINATION_PASSWORD = os.getenv("JENKINS_DESTINATION_PASSWORD")

OUTPUT_FOLDER = Path(f"output_{datetime.now().strftime('%Y%m%d%H%M%S')}")
CA_BUNDLE     = "../../bperROOTCA.crt"
MAX_WORKERS   = 10

JDKS_MAPPING = {
    "JDK_1.8.0_172_cifratura2048": "openjdk-1.8.0",
    "JDK_11_0_2"                 : "openjdk-11",
    "JDK_11+28"                  : "openjdk-11",
    "JDK_17.0.5"                 : "openjdk-17",
    "JDK_21.0.3"                 : "openjdk-21",
}

DEPRECATED_PARAMETERS = {
    "mvnBuild",
    "mvnUIT",
    "mvnArtifactDeploy",
    "JVMAdditionalParameters",
}

GITLAB_URL = "https://gitlab.gbbper.priv"


#
# Logging
#
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


#
# Jenkins configuration
#

def connect_to_jenkins(
    url     : str | None,
    username: str | None,
    password: str | None,
) -> jenkins.Jenkins:

    if not all([url, username, password]):
        raise RuntimeError("Jenkins URL, username and password must be configured")

    logger.info("Connecting to Jenkins: %s ...", url)
    server = jenkins.Jenkins(url=url, username=username, password=password)
    server.get_whoami()
    logger.info("Connected successfully to %s", url)

    return server


#
# XML configuration
#

def save_xml_config(
    fullname : str,
    xml      : ET.Element,
    output   : Path,
    is_folder: bool,
) -> None:

    path_elements = fullname.split("/")
    output_path   = output.joinpath(*path_elements[:-1])

    output_path.mkdir(parents=True, exist_ok=True)

    if is_folder:
        file_name = f"__IS_A_FOLDER__{path_elements[-1]}.xml"
    else:
        file_name = f"{path_elements[-1].replace('/', '__')}.xml"

    file_path = output_path / file_name

    tree = ET.ElementTree(xml)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)


def edit_xml_config(
    fullname: str,
    xml     : ET.Element,
    output  : Path,
    record  : dict,
) -> None:

    parameters = xml.find(".//parameterDefinitions")

    if parameters is None:
        logger.warning("No parameter definitions found for: %s", fullname)
        return

    #
    # Remove deprecated parameters
    #
    for parameter in list(parameters):
        name = parameter.find("name")
        if name is not None and name.text in DEPRECATED_PARAMETERS:
            parameters.remove(parameter)

    #
    # Edit gitlabGroup
    #
    for parameter in parameters:
        name = parameter.find("name")

        if name is None:
            continue
        if name.text == "gitlabGroup":
            default = parameter.find("defaultValue")
            if default is not None:
                default.text = record["gitlab_group"]

    #
    # Edit gitlabProject
    #
    for parameter in parameters:
        name = parameter.find("name")

        if name is None:
            continue
        if name.text == "gitlabPproject":
            name.text = "gitlabProject"
            default = parameter.find("defaultValue")
            if default is not None:
                default.text = record["gitlab_project"]

    #
    # Edit gitlabUrl
    #
    for parameter in parameters:
        name = parameter.find("name")

        if name is None:
            continue

        if name.text == "gitlabUrl":
            default = parameter.find("defaultValue")
            if default is not None:
                default.text = GITLAB_URL

    #
    # Add JVMAdditionalParameters
    #
    jenkinsfile             = record.get("jenkinsfile_name", "")
    requires_jvm_parameters = any(token in jenkinsfile for token in ("Jenkins_fe", "Jenkins_be", "Jenkins_public"))

    if requires_jvm_parameters:
        parameter = ET.SubElement(parameters, "hudson.model.StringParameterDefinition")
        ET.SubElement(parameter, "name").text         = "JVMAdditionalParameters"
        ET.SubElement(parameter, "defaultValue").text = ""
        ET.SubElement(parameter, "description").text  = "Additional JVM Parameters"

    #
    # Add applicationCode as hidden parameter
    #
    parameter = ET.SubElement(parameters, "com.wangyin.parameter.WHideParameterDefinition")

    ET.SubElement(parameter, "name").text         = "applicationCode"
    ET.SubElement(parameter, "defaultValue").text = record["application_code"]
    ET.SubElement(parameter, "description").text  = "Application Code associated with the pipeline"

    #
    # Edit JDKs
    #
    for parameter in parameters:
        name = parameter.find("name")

        if name is None or name.text != "jdkVersion":
            continue

        #
        # Single value
        #
        default = parameter.find("defaultValue")

        if default is not None and default.text in JDKS_MAPPING:
            default.text = JDKS_MAPPING[default.text]

        #
        # Multiple values
        #
        for choice in parameter.findall(".//string"):

            if choice.text in JDKS_MAPPING:
                choice.text = JDKS_MAPPING[choice.text]

        break

    #
    # Edit Jenkinsfile name
    #
    script = xml.find(".//scriptPath")

    if script is not None:
        script.text = record["jenkinsfile_name"]

    #
    # Edit Jenkinsfile branch
    #
    branch = xml.find(".//branches/hudson.plugins.git.BranchSpec/name")

    if branch is not None:
        branch.text = "*/new-master"

    save_xml_config(fullname=fullname, xml=xml, output=output, is_folder=False)
    logger.info("Pipeline named %s has been saved successfully", fullname)


#
# Export jobs from source Jenkins
#

def process_job(
    server   : jenkins.Jenkins,
    job      : dict,
    pipelines: dict,
) -> None:

    fullname = job["fullname"]

    xml_text = server.get_job_config(fullname)
    xml      = ET.fromstring(xml_text)

    #
    # Folder
    #
    if xml.tag == "com.cloudbees.hudson.plugins.folder.Folder":
        save_xml_config(fullname=fullname, xml=xml, output=OUTPUT_FOLDER, is_folder=True)
        logger.info("Folder named %s has been saved successfully", fullname)
        return

    #
    # Freestyle/project job
    #
    if xml.tag == "project":
        save_xml_config(fullname=fullname, xml=xml, output=OUTPUT_FOLDER, is_folder=False)
        logger.info("Project named %s has been saved successfully", fullname)
        return

    #
    # Pipeline
    #
    if xml.tag == "flow-definition":
        record = pipelines.get(fullname)
        if record is not None:
            edit_xml_config(fullname=fullname, xml=xml, output=OUTPUT_FOLDER, record=record)


#
# Import jobs into destination Jenkins
#

def import_to_destination(
    output: Path,
    server: jenkins.Jenkins,
) -> None:

    folders   = []
    pipelines = []

    #
    # Find exported configuration files
    #
    for file in output.rglob("*.xml"):

        if file.name.startswith("__IS_A_FOLDER__"):
            folders.append(file)
        else:
            pipelines.append(file)

    logger.info("Found %d folders and %d pipelines to import", len(folders), len(pipelines))

    #
    # Get existing jobs
    #
    try:
        jobs = {
            job["fullname"]
            for job in server.get_jobs()
        }

    except Exception:
        logger.exception("Failed to retrieve existing Jenkins jobs")
        jobs = set()

    #
    # Create folder jobs
    #
    def generate_folder(file: Path) -> None:

        relative_path = file.relative_to(output)
        fullname      = str(relative_path.with_suffix(""))
        fullname      = fullname.replace("\\", "/")
        fullname      = fullname.replace("__IS_A_FOLDER__", "")

        if fullname in jobs:
            logger.info("Folder %s already exists", fullname)
            return

        try:
            config = file.read_text(encoding="utf-8")

        except Exception:
            logger.exception("Failed to read folder configuration: %s", file)
            return

        try:
            server.create_job(fullname, config)
            logger.info("Folder %s created", fullname)

        except Exception:
            logger.exception("Failed to create folder: %s", fullname)

    #
    # Create pipeline jobs
    #
    def generate_pipeline(file: Path) -> None:

        relative_path = file.relative_to(output)
        fullname      = str(relative_path.with_suffix(""))
        fullname      = fullname.replace("\\", "/")
        fullname      = fullname.replace("__", "/")

        if fullname in jobs:
            logger.info("Pipeline %s already exists", fullname)
            return

        try:
            config = file.read_text(encoding="utf-8")

        except Exception:
            logger.exception("Failed to read pipeline configuration: %s", file)
            return

        try:
            server.create_job(fullname, config)
            logger.info("Pipeline %s created", fullname)

        except Exception:
            logger.exception("Failed to create pipeline: %s", fullname)

    #
    # Create folders in parallel
    #
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(generate_folder, file) for file in sorted(folders)]
        for future in as_completed(futures):
            future.result()

    #
    # Create pipelines in parallel
    #
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(generate_pipeline, file) for file in sorted(pipelines)]
        for future in as_completed(futures):
            future.result()


#
# CSV
#

def load_validated_pipelines() -> dict:

    pipelines = {}

    with open("jenkins_pipelines.csv", "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for record in reader:
            pipelines[record["fullname"]] = record
    return pipelines


#
# Main
#

def main() -> None:

    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE

    #
    # Connect to source Jenkins
    #
    source_server = connect_to_jenkins(url=JENKINS_SOURCE_URL, username=JENKINS_SOURCE_USERNAME, password=JENKINS_SOURCE_PASSWORD)

    #
    # Read validated pipelines
    #
    pipelines = load_validated_pipelines()

    #
    # Get all jobs
    #
    jobs = source_server.get_all_jobs()

    logger.info("Found %d Jenkins jobs", len(jobs))

    #
    # Export jobs
    #
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        futures = [executor.submit(process_job, source_server, job, pipelines) for job in jobs]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                logger.exception("Failed to process Jenkins job")

    logger.info("Export completed successfully")

    #
    # Connect to destination Jenkins
    #
    # logger.info("#################################################################")
    # logger.info("Importing Jenkins jobs ...")
    # logger.info("#################################################################")

    # destination_server = connect_to_jenkins(url=JENKINS_DESTINATION_URL, username=JENKINS_DESTINATION_USERNAME, password=JENKINS_DESTINATION_PASSWORD)

    #
    # Import jobs
    #
    # import_to_destination(output=OUTPUT_FOLDER, server=destination_server)

    # logger.info("Jenkins migration completed successfully")


if __name__ == "__main__":
    main()