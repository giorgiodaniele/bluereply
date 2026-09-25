import csv
import logging
import sys
import argparse
import xml.etree.ElementTree as ET
import dotenv
import jenkins

from   pathlib            import Path
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   datetime           import datetime

dotenv.load_dotenv()

PATTERNS_FILE    = Path("patterns.txt")
MAX_WORKERS      = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

def connect_to_jenkins(url: str, username: str, password: str) -> jenkins.Jenkins:
    try:
        server = jenkins.Jenkins(url=url, username=username, password=password)
        return server
    except Exception as e:
        logger.error("Can't connect to Jenkins (%s): %s", url, e)
        sys.exit(1)

def get_xml_text(e: ET.Element | None) -> str | None:
    if e is not None and e.text:
        text = e.text.strip()
        return text if text else None
    return None

def inspect_pipeline(text: str, fullname: str) -> dict:
    root   = ET.fromstring(text)
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
        logger.info("Successfully processed pipeline [%s]", name)
        return res
    except Exception:
        logger.exception("Failed at processing pipeline [%s]", name)
        return None

def save_csv(results: list[dict], output_folder: Path) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_folder / f"jenkins_pipelines_{timestamp}.csv"

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
#
# MAIN
#
def main() -> None:

    parser = argparse.ArgumentParser(description="Save BPER Jenkins pipelines to a CSV file")
    parser.add_argument("--jenkins-server", type=str, help="URL to Jenkins server",    default="http://172.16.63.239/jenkins")
    parser.add_argument("--username", type=str, help="Username to Jenkins server",     default="admin")
    parser.add_argument("--password", type=str, help="Password to Jenkins server",     default="admin")
    parser.add_argument("--output",   type=str, help="Output folder for the CSV file", default="output")
    args = parser.parse_args()

    server    = connect_to_jenkins(url=args.jenkins_server, username=args.username, password=args.password)
    jobs      = server.get_all_jobs()
    pipelines = [ job for job in jobs if job.get("_class") == "org.jenkinsci.plugins.workflow.job.WorkflowJob" ]
    results   = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [ executor.submit(process_pipeline, server, p) for p in pipelines ]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
    save_csv(results, output_folder=Path(args.output))

if __name__ == "__main__":
    main()