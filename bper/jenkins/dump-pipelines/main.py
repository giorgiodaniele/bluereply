import csv
import logging
import os
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   datetime           import datetime
from   pathlib            import Path
import xml.etree.ElementTree as ET

import dotenv
import jenkins


dotenv.load_dotenv()

JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")

OUTPUT_FOLDER = Path("output")
CA_BUNDLE     = "../../bperROOTCA.crt"
MAX_WORKERS   = 10

STANDARD_REPOSITORIES = {
    "http://172.16.63.237/Devops/pipeline-build.git",
    "http://172.16.63.237/Devops/PipelineBatchToolchain.git",
}

CSV_FIELDS = [
    "fullname",
    "gitlab_group",
    "gitlab_project",
    "gitlab_branch",
    "mvn_build",
    "mvn_uit",
    "mvn_artifactdeploy",
    "jdks",
    "jvm_additional_parameters",
    "jenkinsfile_name",
    "jenkinsfile_branch",
    "jenkinsfile_repository",
    "is_standard",
]


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
        raise RuntimeError("JENKINS_URL, JENKINS_USERNAME and JENKINS_PASSWORD must be configured")

    logger.info("Connecting to Jenkins: %s ...", JENKINS_URL)
    server = jenkins.Jenkins(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
    server.get_whoami()
    logger.info("Connected successfully to %s", JENKINS_URL)

    return server


#
# Process the pipeline
#

def inspect_pipeline(xml: str, name: str) -> dict:

    root = ET.fromstring(xml)

    result = {
        "fullname"                 : name,
        "gitlab_group"             : None,
        "gitlab_project"           : None,
        "gitlab_branch"            : None,
        "mvn_build"                : None,
        "mvn_uit"                  : None,
        "mvn_artifactdeploy"       : None,
        "jdks"                     : None,
        "jvm_additional_parameters": None,
        "jenkinsfile_name"         : None,
        "jenkinsfile_branch"       : None,
        "jenkinsfile_repository"   : None,
        "is_standard"              : False,
    }

    #
    # Common Jenkins parameters
    #
    parameter_mapping = {
        "gitlabGroup"            : "gitlab_group",
        "gitlabPproject"         : "gitlab_project",
        "gitlabProject"          : "gitlab_project",
        "gitlabBranch"           : "gitlab_branch",
        "mvnBuild"               : "mvn_build",
        "mvnUIT"                 : "mvn_uit",
        "mvnArtifactDeploy"      : "mvn_artifactdeploy",
        "JVMAdditionalParameters": "jvm_additional_parameters",
    }

    for parameter in root.findall(".//parameterDefinitions/*"):

        name_element = parameter.find("name")

        if name_element is None or not name_element.text:
            continue

        parameter_name = name_element.text.strip()

        #
        # JDK choices
        #
        if "jdk" in parameter_name.lower():
            choices = parameter.find("choices")
            if choices is not None:
                result["jdks"] = [item.text.strip() for item in choices.findall(".//string") if item.text and item.text.strip()]

        #
        # String parameters
        #
        elif parameter.tag.endswith("StringParameterDefinition"):
            key = parameter_mapping.get(parameter_name)
            if key:
                default     = parameter.find("defaultValue")
                result[key] = default.text.strip() if default is not None and default.text else None

    #
    # Jenkinsfile name
    #
    element = root.find(".//scriptPath")

    if element is not None:
        result["jenkinsfile_name"] = element.text

    #
    # Jenkinsfile branch
    #
    element = root.find(".//branches/hudson.plugins.git.BranchSpec/name")

    if element is not None:
        result["jenkinsfile_branch"] = element.text

    #
    # Jenkinsfile repository
    #
    element = root.find(".//hudson.plugins.git.UserRemoteConfig/url")

    if element is not None:
        result["jenkinsfile_repository"] = element.text

    #
    # Standard pipeline?
    #
    result["is_standard"] = result["jenkinsfile_repository"] in STANDARD_REPOSITORIES

    return result


def process_pipeline(
    server  : jenkins.Jenkins,
    pipeline: dict,
) -> dict | None:

    name = pipeline["fullname"]

    try:
        xml = server.get_job_config(name)
        res = inspect_pipeline(xml, name)

        logger.info("Successfully processed: %s", name)

        return res

    except Exception:
        logger.exception("Failed at processing: %s", name)
        return None


def main() -> None:
    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE

    server = connect_to_jenkins()
    jobs   = server.get_all_jobs()

    #
    # Select just pipelines
    #
    pipelines = [
        job
        for job in jobs
        if job.get("_class")
        == "org.jenkinsci.plugins.workflow.job.WorkflowJob"
    ]

    logger.info("Found %d pipelines", len(pipelines))

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        futures = [executor.submit(process_pipeline, server, pipeline) for pipeline in pipelines]
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    logger.info("Done: processed %d", len(results))
    save_csv(results)


def save_csv(results: list[dict]) -> None:

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_FOLDER / f"jenkins_pipelines_{timestamp}.csv"

    with output_file.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for result in results:
            if isinstance(result.get("jdks"), list):
                result["jdks"] = ";".join(result["jdks"])
            writer.writerow(result)


if __name__ == "__main__":
    main()