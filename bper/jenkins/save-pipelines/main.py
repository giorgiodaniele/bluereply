import csv
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET

import dotenv
import jenkins

from   pathlib            import Path
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   datetime           import datetime

dotenv.load_dotenv()

JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")
OUTPUT_FOLDER    = Path("output")
PATTERNS_FILE    = Path("patterns.txt")
MAX_WORKERS      = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


def connect_to_jenkins() -> jenkins.Jenkins:
    try:
        server = jenkins.Jenkins(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD) 
        server.get_whoami()
        return server
    except Exception as e:
        logger.error("Can't connect to Jenkins (%s): %s", JENKINS_URL, e)
        sys.exit(1)

def get_xml_text(e: ET.Element | None) -> str | None:
    if e is not None and e.text:
        text = e.text.strip()
        return text if text else None
    return None

def inspect_pipeline(xml_str: str, fullname: str) -> dict:
    root = ET.fromstring(xml_str)

    record = {}

    record["fullname"]                = fullname
    record["gitlabGroup"]             = ""
    record["gitlabPproject"]          = ""
    record["gitlabBranch"]            = ""
    record["jdkVersion"]              = ""
    record["JVMAdditionalParameters"] = ""
    record["jenkinsfileName"]         = get_xml_text(root.find(".//scriptPath"))
    record["jenkinsfileBranch"]       = get_xml_text(root.find(".//branches/hudson.plugins.git.BranchSpec/name"))
    record["jenkinsfileRepository"]   = get_xml_text(root.find(".//hudson.plugins.git.UserRemoteConfig/url"))

    for param in root.findall(".//parameterDefinitions/*"):
        parameter_name = get_xml_text(param.find("name"))
        if not parameter_name:
            continue
        if parameter_name == "gitlabGroup":
            record["gitlabGroup"] = get_xml_text(param.find("defaultValue"))
        elif parameter_name == "gitlabPproject":
            record["gitlabPproject"] = get_xml_text(param.find("defaultValue"))
        elif parameter_name == "gitlabBranch":
            record["gitlabBranch"] = get_xml_text(param.find("defaultValue"))
        elif parameter_name == "JVMAdditionalParameters":
            record["JVMAdditionalParameters"] = get_xml_text(param.find("defaultValue"))
        elif parameter_name == "jdkVersion":
            record["jdkVersion"] = [ get_xml_text(choice) for choice in param.findall(".//string") if get_xml_text(choice) ]
            record["jdkVersion"] = ";".join(record["jdkVersion"])

    return record

def process_pipeline(server: jenkins.Jenkins, pipeline: dict) -> dict | None:
    name = pipeline["fullname"]
    try:
        str = server.get_job_config(name)
        res = inspect_pipeline(str, name)
        logger.info("Successfully processed: %s", name)
        return res
    except Exception:
        logger.exception("Failed to process pipeline: %s", name)
        return None


def load_regex():
    patterns = []
    with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    if patterns:
        return re.compile("|".join(patterns))
    return None

def save_csv(results: list[dict]) -> None:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_FOLDER / f"jenkins_pipelines_{timestamp}.csv"

    fieldnames = [ 
        "fullname", 
        "gitlabGroup", 
        "gitlabPproject", 
        "gitlabBranch", 
        "jdkVersion", 
        "JVMAdditionalParameters", 
        "jenkinsfileName", 
        "jenkinsfileBranch", 
        "jenkinsfileRepository" 
    ]

    with output_file.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for result in results:
            writer.writerow(result)

def main() -> None:
    server = connect_to_jenkins()
    jobs   = server.get_all_jobs()

    pipelines = [ job for job in jobs if job.get("_class") == "org.jenkinsci.plugins.workflow.job.WorkflowJob" ]
    logger.info("Found %d pipelines", len(pipelines))

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [ executor.submit(process_pipeline, server, p) for p in pipelines ]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
    save_csv(results)


if __name__ == "__main__":
    main()