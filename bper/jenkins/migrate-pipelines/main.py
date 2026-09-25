#!/usr/bin/env python3

import csv
import logging
import os
import sys
import argparse
import xml.etree.ElementTree as ET
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   datetime           import datetime
from   pathlib            import Path

import dotenv
import jenkins


dotenv.load_dotenv()

OUTPUT_FOLDER                = Path(f"output_{datetime.now().strftime('%Y%m%d%H%M%S')}")
CA_BUNDLE                    = "../../bperROOTCA.crt"
PIPELINES_TO_MIGRATE         = "jenkins_pipelines_20260918_095459_filtered.csv"
MAX_WORKERS                  = 10

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


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


def connect_to_jenkins(url: str, username: str, password: str) -> jenkins.Jenkins:
    try:
        server = jenkins.Jenkins(url=url, username=username, password=password)
        return server
    except Exception:
        logging.info(f"Can't connect to Jenkins: {url}. Exiting program with error code 1.")
        sys.exit(1)


def save_xml_config(fullname: str, xml: ET.Element, output: Path, is_folder: bool) -> None: 

    path_elements = fullname.split("/")
    output_path   = output.joinpath(*path_elements[:-1])

    output_path.mkdir(parents=True, exist_ok=True)

    if is_folder:
        file_name = f"__IS_A_FOLDER__{path_elements[-1]}.xml"
    else:
        file_name = f"{path_elements[-1].replace('/', '__')}.xml"

    file_path = output_path / file_name
    tree      = ET.ElementTree(xml)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)

def edit_xml_config(fullname: str, xml: ET.Element, output: Path, record: dict) -> None:

    parameters = xml.find(".//parameterDefinitions")

    if parameters is None:
        return

    # Remove parameters which are no longer
    for parameter in list(parameters):
        name = parameter.find("name")
        if name is not None and name.text in ["mvnBuild", "mvnUIT", "mvnArtifactDeploy", "JVMAdditionalParameters"]:
            parameters.remove(parameter)

    # Fix the value of the gitlabGroup parameter
    for parameter in parameters:
        name = parameter.find("name")
        if name is None:
            continue
        if name.text == "gitlabGroup":
            default = parameter.find("defaultValue")
            if default is not None:
                default.text = record["gitlabGroup"]

    # Fix the value of the gitlabProject parameter
    for parameter in parameters:
        name = parameter.find("name")
        if name is None:
            continue
        if name.text == "gitlabPproject":
            name.text = "gitlabProject"
            default = parameter.find("defaultValue")
            if default is not None:
                default.text = record["gitlabPproject"]

    # Fix the value of the gitlabUrl parameter
    for parameter in parameters:
        name = parameter.find("name")
        if name is None:
            continue
        if name.text == "gitlabUrl":
            default = parameter.find("defaultValue")
            if default is not None:
                default.text = "https://gitlab.gbbper.priv"

    # A pipeline requires the JVMAdditionalParameters parameter if the jenkinsfile is based on maven
    requires_jvm_parameters = any(filename in record["jenkinsfileName"] for filename in ("Jenkins_fe", "Jenkins_be", "Jenkins_public", "Jenkins_be_sb3", "Jenkins_be_quarkus"))

    # Add the JVMAdditionalParameters parameter if required
    if requires_jvm_parameters:
        parameter = ET.SubElement(parameters, "hudson.model.StringParameterDefinition")
        ET.SubElement(parameter, "name").text         = "JVMAdditionalParameters"
        ET.SubElement(parameter, "defaultValue").text = ""
        ET.SubElement(parameter, "description").text  = "Additional JVM Parameters"

    # Add always the applicationCode parameter
    parameter = ET.SubElement(parameters, "com.wangyin.parameter.WHideParameterDefinition")
    ET.SubElement(parameter, "name").text         = "applicationCode"
    ET.SubElement(parameter, "defaultValue").text = record["applicationCode"]
    ET.SubElement(parameter, "description").text  = "Application Code associated with the pipeline"

    if requires_jvm_parameters:
        for parameter in parameters:
            name = parameter.find("name")
            if name is None or name.text != "jdkVersion":
                continue
            default = parameter.find("defaultValue")
            if default is not None and default.text in JDKS_MAPPING:
                default.text = JDKS_MAPPING[default.text]
            for choice in parameter.findall(".//string"):
                if choice.text in JDKS_MAPPING:
                    choice.text = JDKS_MAPPING[choice.text]
            break

    # Fix the value of the jenkinsfileName parameter
    script = xml.find(".//scriptPath")
    if script is not None:
        script.text = record["jenkinsfileName"]

    # Fix the value of the jenkinsfileBranch parameter
    branch = xml.find(".//branches/hudson.plugins.git.BranchSpec/name")
    if branch is not None:
        branch.text = record["jenkinsfileBranch"]
        
    # Fix the value of the URL of the repository
    url = xml.find(".//scm/userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url")
    if url is not None:
        url.text = record["jenkinsfileRepository"]

    save_xml_config(fullname=fullname, xml=xml, output=output, is_folder=False)

def process_pipeline(server: jenkins.Jenkins, job: dict, pipelines: dict) -> None:  

    fullname = job["fullname"]
    xml_text = server.get_job_config(fullname)
    xml      = ET.fromstring(xml_text)

    if xml.tag == "com.cloudbees.hudson.plugins.folder.Folder":
        save_xml_config(fullname=fullname, xml=xml, output=OUTPUT_FOLDER, is_folder=True)
        logger.info(f"Found folder named {fullname}. Exported successfully at {OUTPUT_FOLDER}")
        return

    if xml.tag == "project":
        save_xml_config(fullname=fullname, xml=xml, output=OUTPUT_FOLDER, is_folder=False)
        logger.info(f"Found project named {fullname}. Exported successfully at {OUTPUT_FOLDER}")
        return

    if xml.tag == "flow-definition":
        record = pipelines.get(fullname)
        if record is not None:
            logger.info(f"Processing pipeline: {fullname} ...")
            edit_xml_config(fullname=fullname, xml=xml, output=OUTPUT_FOLDER, record=record)
            logger.info(f"Pipeline {fullname} processed successfully! Exported at {OUTPUT_FOLDER}")
        else:
            logger.info(f"Pipeline {fullname} not found in the pipelines to migrate. Skipping...")

def load_pipelines() -> dict:
    pipelines = {}
    with open(PIPELINES_TO_MIGRATE, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for record in reader:
            pipelines[record["fullname"]] = record
    return pipelines

def import_pipelines(output: Path, server: jenkins.Jenkins) -> None:

    folders   = []
    pipelines = []

    for file in output.rglob("*.xml"):

        if file.name.startswith("__IS_A_FOLDER__"):
            folders.append(file)
        else:
            pipelines.append(file)

    logger.info("Found %d folders and %d pipelines to import", len(folders), len(pipelines))

    # Get already existing jobs
    try:
        jobs = {
            job["fullname"]
            for job in server.get_jobs()
        }

    except Exception:
        logger.exception("Failed to retrieve existing Jenkins jobs")
        jobs = set()

    # Generate folder jobs
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

    # Generate pipeline jobs
    def generate_pipeline(file: Path) -> None:
        rel_path = file.relative_to(output)
        fullname = str(rel_path.with_suffix(""))
        fullname = fullname.replace("\\", "/").replace("__", "/")

        try:
            config = file.read_text(encoding="utf-8")
        except Exception:
            logger.exception("Failed to read pipeline configuration: %s", file)
            return

        try:
            if server.job_exists(fullname):
                server.reconfig_job(fullname, config)
                logger.info("Pipeline %s reconfigured", fullname)
            else:
                server.create_job(fullname, config)
                logger.info("Pipeline %s created", fullname)

        except Exception:
            logger.exception("Failed to configure pipeline: %s", fullname)

    # Create all folders
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(generate_folder, file) for file in sorted(folders)]
        for future in as_completed(futures):
            future.result()

    # Create all pipelines
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(generate_pipeline, file) for file in sorted(pipelines)]
        for future in as_completed(futures):
            future.result()

def main() -> None:

    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE

    parser = argparse.ArgumentParser(description="Save BPER Jenkins pipelines to a CSV file")
    parser.add_argument("--jenkins-src",   type=str, help="URL to Jenkins source server", default="http://172.16.63.239/jenkins")
    parser.add_argument("--username-src",  type=str, help="Username to Jenkins source server", default="admin")
    parser.add_argument("--password-src",  type=str, help="Password to Jenkins source server", default="admin")
    parser.add_argument("--jenkins-dst",   type=str, help="URL to Jenkins destination server", default="https://jenkins-build.gbbper.priv/")
    parser.add_argument("--username-dst",  type=str, help="Username to Jenkins destination server", default="admin")
    parser.add_argument("--password-dst",  type=str, help="Password to Jenkins destination server", default="admin")
    args = parser.parse_args()

    src       = connect_to_jenkins(url=args.jenkins_src, username=args.username_src, password=args.password_src)
    dst       = connect_to_jenkins(url=args.jenkins_dst, username=args.username_dst, password=args.password_dst)
    pipelines = load_pipelines()
    jobs      = src.get_all_jobs()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as e:
        futures = [e.submit(process_pipeline, src, job, pipelines) for job in jobs]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                logger.exception("Failed to process Jenkins job")
    import_pipelines(output=OUTPUT_FOLDER, server=dst)

#
# MAIN
#
if __name__ == "__main__":
    main()