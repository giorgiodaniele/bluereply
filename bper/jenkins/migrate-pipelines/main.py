#!/usr/bin/env python3

import csv
import os
import sys
import logging
import dotenv
import jenkins
import datetime
import xml.etree.ElementTree as ET
from   concurrent.futures import ThreadPoolExecutor, as_completed

dotenv.load_dotenv()

JENKINS_SOURCE_URL           = os.getenv("JENKINS_SOURCE_URL")
JENKINS_SOURCE_USERNAME      = os.getenv("JENKINS_SOURCE_USERNAME")
JENKINS_SOURCE_PASSWORD      = os.getenv("JENKINS_SOURCE_PASSWORD")
JENKINS_DESTINATION_URL      = os.getenv("JENKINS_DESTINATION_URL")
JENKINS_DESTINATION_USERNAME = os.getenv("JENKINS_DESTINATION_USERNAME")
JENKINS_DESTINATION_PASSWORD = os.getenv("JENKINS_DESTINATION_PASSWORD")
OUTPUT_FOLDER                = f"output_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

# Configure certificate
os.environ["REQUESTS_CA_BUNDLE"] = "../../bperROOTCA.crt"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s - %(message)s")

JDKS_MAPPING = {
    "JDK_1.8.0_172_cifratura2048": "openjdk-1.8.0",
    "JDK_11_0_2"                 : "openjdk-11",
    "JDK_11+28"                  : "openjdk-11",
    "JDK_17.0.5"                 : "openjdk-17",
    "JDK_21.0.3"                 : "openjdk-21",
}

def save_xml_config(fullname: str, xml: ET.Element, out: str, is_folder: bool):

    pces = fullname.split("/")
    path = os.path.join(out, *pces[:-1])

    os.makedirs(path, exist_ok=True)

    file_name = f"__IS_A_FOLDER__{pces[-1]}.xml" if is_folder else f"{pces[-1].replace('/', '__')}.xml"
    file_path = os.path.join(path, file_name)

    tree = ET.ElementTree(xml)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)

def edit_xml_config(fullname: str, xml: ET.Element, out: str, record: dict):

    # Remove deprecated parameters
    deprecated = ["mvnBuild", "mvnUIT", "mvnArtifactDeploy", "JVMAdditionalParameters"]
    parameters = xml.find(".//parameterDefinitions")

    if parameters is not None:
        for parameter in list(parameters):
            name = parameter.find("name")
            if name is not None and name.text in deprecated:
                parameters.remove(parameter)

    # Edit gitlabGroup and edit the value
    for parameter in list(parameters):
        name = parameter.find("name")
        if name is None:
            continue
        if name.text == "gitlabGroup":
            default = parameter.find("defaultValue")
            if default is not None:
                default.text = record["gitlab_group"]

    # Edit gitlabPproject and edit the value
    for parameter in list(parameters):
        name = parameter.find("name")
        if name is None:
            continue
        if name.text == "gitlabPproject":
            name.text = "gitlabProject"
            default   = parameter.find("defaultValue")
            if default is not None:
                default.text = record["gitlab_project"]

    # Edit gitlabUrl and edit the value
    for parameter in list(parameters):
        name = parameter.find("name")
        if name is None:
            continue
        if name.text == "gitlabUrl":
            default = parameter.find("defaultValue")
            if default is not None:
                default.text = "https://gitlab.gbbper.priv"

    # Add JVMAdditionalParameters
    jenkinsfile = record.get("jenkinsfile_name", "")
    found       = any(token in jenkinsfile for token in ("Jenkins_fe", "Jenkins_be", "Jenkins_public"))
    if found:
        parameter = ET.SubElement(parameters, "hudson.model.StringParameterDefinition")
        ET.SubElement(parameter, "name").text         = "JVMAdditionalParameters"
        ET.SubElement(parameter, "defaultValue").text = ""
        ET.SubElement(parameter, "description").text  = "Additional JVM Parameters"

    # Add applicationCode as hidden parameter
    parameter = ET.SubElement(parameters, "com.wangyin.parameter.WHideParameterDefinition")
    ET.SubElement(parameter, "name").text         = "applicationCode"
    ET.SubElement(parameter, "defaultValue").text = record["application_code"]
    ET.SubElement(parameter, "description").text  = "Application Code associated with the pipeline"

    # Edit JDKs - it can be either a single value or a list of choices
    for parameter in parameters:
        name = parameter.find("name")
        if name is None or name.text != "jdkVersion":
            continue

        # Single value
        default = parameter.find("defaultValue")
        if default is not None and default.text in JDKS_MAPPING:
            default.text = JDKS_MAPPING[default.text]
        # Multiple values
        for choice in parameter.findall(".//string"):
            if choice.text in JDKS_MAPPING:
                choice.text = JDKS_MAPPING[choice.text]
        break

    # Edit the name of the script file
    script = xml.find(".//scriptPath")
    if script is not None:
        script.text = record["jenkinsfile_name"]

    # Edit the name of the branch
    branch = xml.find(".//branches/hudson.plugins.git.BranchSpec/name")
    if branch is not None:
        branch.text = "*/new-master"

    save_xml_config(fullname=fullname, xml=xml, out=out, is_folder=False)
    logging.info(f"Pipeline named {fullname} has been saved successfully")

def process_job(server: jenkins.Jenkins, job: dict, pipelines: dict):

    fullname = job["fullname"]
    xml_text = server.get_job_config(fullname)
    xml      = ET.fromstring(xml_text)

    if xml.tag == "com.cloudbees.hudson.plugins.folder.Folder":
        save_xml_config(fullname, xml, OUTPUT_FOLDER, True)
        logging.info(f"Folder named {fullname} has been saved successfully")
        return
    if xml.tag == "project":
        save_xml_config(fullname, xml, OUTPUT_FOLDER, False)
        logging.info(f"Project named {fullname} has been saved successfully")
        return
    if xml.tag == "flow-definition":
        record = pipelines.get(fullname)
        if record is not None:
            edit_xml_config(fullname, xml, OUTPUT_FOLDER, record)

def import_to_destination(files: list, server: jenkins.Jenkins, folder: str):

    folders   = []
    pipelines = []

    for file in files:
        filename: str = os.path.basename(file)
        if filename.startswith("__IS_A_FOLDER__") and not os.path.isdir(file):
            folders.append(file)
        elif os.path.isdir(file):
            for item in os.listdir(file):
                path = os.path.join(file, item)
                if os.path.isfile(path) and path.endswith(".xml"):
                    pipelines.append(path)
    try:
        jobs = {job['fullname'] for job in server.get_jobs()}
    except Exception:
        jobs = set()

    #
    # Helper function to create folder jobs
    #
    def __generate_folder(file):
        fullname = os.path.relpath(file, folder)
        fullname = os.path.splitext(fullname)[0].replace("__IS_A_FOLDER__", "").replace("\\", "/")
        try:
            with open(file, 'r') as file:
                config = file.read()
        except Exception:
            return

        if fullname in jobs:
            logging.info(f"Cartella {fullname} esiste già...")
            return

        try:
            server.create_job(fullname, config)
            logging.info(f"Cartella {fullname} creata!")
        except Exception:
            pass

    #
    # Helper function to create pipeline jobs
    #
    def __generate_pipeline(file):
        rel_path = os.path.relpath(file, folder)
        fullname = rel_path[:-4].replace("__", "/").replace("\\", "/")
        try:
            with open(file, 'r') as file:
                config = file.read()
        except Exception:
            return

        if fullname in jobs:
            logging.info(f"Pipeline {fullname} esiste già...")
            return

        try:
            server.create_job(fullname, config)
            logging.info(f"Pipeline {fullname} creata!")
        except Exception:
            pass

    #
    # Create folders in parallel
    #
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(__generate_folder, f) for f in sorted(folders)]
        for _ in as_completed(futures):
            continue

    #
    # Create pipelines in parallel
    #
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(__generate_pipeline, f) for f in sorted(pipelines)]
        for _ in as_completed(futures):
            continue

def connect_server(url: str, username: str, password: str):
    try:
        return jenkins.Jenkins(url=url, username=username, password=password)
    except Exception as e:
        return f"Failed to connect to Jenkins: {e}"

def main():

    # Connect to source Jenkins server
    server = None
    server = connect_server(url=JENKINS_SOURCE_URL, username=JENKINS_SOURCE_USERNAME, password=JENKINS_SOURCE_PASSWORD)

    if isinstance(server, str):
        logging.error(server)
        sys.exit(1)

    logging.info("Connected to Jenkins successfully")

    # Read from disk all pipelines
    pipelines = {}
    with open("validated.csv", "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for record in reader:
            pipelines[record["fullname"]] = record

    # Get all jobs
    jobs = server.get_all_jobs()
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(process_job, server, job, pipelines) for job in jobs]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                logging.exception("Failed to process Jenkins job")

    logging.info("#################################################################")
    logging.info(f"Importing jenkins jobs  ...")
    logging.info("#################################################################")

    # Connect destination Jenkins server
    server = None
    server = connect_server(url=JENKINS_DESTINATION_URL, username=JENKINS_DESTINATION_USERNAME, password=JENKINS_DESTINATION_PASSWORD)

    # Migrate to destination Jenkins server
    files  = [os.path.join(OUTPUT_FOLDER, f) for f in os.listdir(OUTPUT_FOLDER)]
    import_to_destination(files=files, server=server, folder=OUTPUT_FOLDER)

if __name__ == "__main__":
    main()