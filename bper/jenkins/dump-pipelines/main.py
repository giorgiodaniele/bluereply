#
# Use this script to generate a summary of all pipelines configured
#

import csv
import os
import sys
import logging
import dotenv
import jenkins
import xml.etree.ElementTree as ET
import datetime

from   concurrent.futures import ThreadPoolExecutor, as_completed

dotenv.load_dotenv()

JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")
OUTPUT_FOLDER    = "output"

# Import custom certificate
os.environ["REQUESTS_CA_BUNDLE"] = "../../bperROOTCA.crt"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s - %(message)s")

def connect_server(url: str, username: str, password: str):
    try:
        return jenkins.Jenkins(url=url, username=username, password=password)
    except Exception as e:
        return f"Failed to connect to Jenkins: {e}"

def save_resources(resources: dict, output_folder: str):
    os.makedirs(output_folder, exist_ok=True)
    
    if resources:
        fieldnames = [
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
            "is_standard"
        ]
        
        csv_file = os.path.join(output_folder, f"pipelines_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv")
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for config in resources.values():
                if config:
                    writer.writerow(config)
        logging.info(f"Saved CSV results to: {csv_file}")

def inspect_pipeline(xml: str, pipeline_name: str) -> dict:
    root   = ET.fromstring(xml)
    result = {"fullname": pipeline_name}
    
    # Extract parameters definition
    parameters = root.findall('.//parameterDefinitions/*')
    
    for parameter in parameters:
        name_elem = parameter.find('name')
        if name_elem is None or name_elem.text is None:
            continue
            
        param_name    = name_elem.text
        default_value = parameter.find('defaultValue')
        
        # Inspect JDK options
        if parameter.tag.endswith('ChoiceParameterDefinition'):
            choices = parameter.find('.//string-array')
            if choices is not None:
                jdk_options    = [s.text for s in choices.findall('string') if s.text]
                result["jdks"] = jdk_options
        
        elif parameter.tag.endswith('StringParameterDefinition'):
            def set_parameter(key: str, value):
                result[key] = value.text if value is not None else None
            
            # GitLab related parameters
            if param_name == "gitlabGroup":
                set_parameter("gitlab_group",   default_value)
            elif param_name == "gitlabPproject":
                set_parameter("gitlab_project", default_value)
            elif param_name == "gitlabBranch":
                set_parameter("gitlab_branch", default_value)
            
            # Maven related parameters
            elif param_name == "mvnBuild":
                set_parameter("mvn_build", default_value)
            elif param_name == "mvnUIT":
                set_parameter("mvn_uit", default_value)
            elif param_name == "mvnArtifactDeploy":
                set_parameter("mvn_artifactdeploy", default_value)
            
            # JVM related parameters
            elif param_name == "JVMAdditionalParameters":
                set_parameter("jvm_additional_parameters", default_value)

    # Extract script spec - the Jenkinsfile adopted from Gitlab
    script_path = root.find('.//scriptPath')
    if script_path is not None:
        result["jenkinsfile_name"] = script_path.text
    
    # Extract branch spec - the branch the Jenkinsfile is based on
    branch_elem = root.find('.//branches/hudson.plugins.git.BranchSpec/name')
    if branch_elem is not None and branch_elem.text:
        result["jenkinsfile_branch"] = branch_elem.text

    # Extract remote spec - the repository the Jenkinsfile is coming from
    remote_configs = root.findall('.//hudson.plugins.git.UserRemoteConfig')
    if remote_configs:
        url_elem = remote_configs[0].find('url')
        if url_elem is not None and url_elem.text:
            result["jenkinsfile_repository"] = url_elem.text

    #
    # Clasify the pipeline if standard or not. A pipeline is considered to be standard
    # if the jenkinsfile is coming from the standard repository managed by Reply team
    # DevOps
    #

    if result["jenkinsfile_repository"] is None:
        result["is_standard"] = False
    elif result["jenkinsfile_repository"] == "http://172.16.63.237/Devops/pipeline-build.git":
        result["is_standard"] = True
    elif result["jenkinsfile_repository"] == "http://172.16.63.237/Devops/PipelineBatchToolchain.git":
        result["is_standard"] = True
    else:
        result["is_standard"] = False
    
    return result

def process_pipeline(server: jenkins.Jenkins, pipeline: dict) -> tuple:
    pipeline_name = pipeline["fullname"]
    try:
        xml = server.get_job_config(pipeline_name)
        cfg = inspect_pipeline(xml, pipeline_name)
        logging.info(f"Successfully processed: {pipeline_name}")
        return (pipeline_name, cfg)
    except Exception as e:
        logging.error(f"Failed to process pipeline {pipeline_name}: {e}")
        return (pipeline_name, None)

def main():
    server = connect_server(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
    if isinstance(server, str):
        logging.error(server)
        sys.exit(1)
    
    logging.info("Connected to Jenkins successfully")
    
    # Get all pipeline jobs considering just workflow jobs (pipelines)
    all_jobs  = server.get_all_jobs()
    pipelines = [job for job in all_jobs if job["_class"] == "org.jenkinsci.plugins.workflow.job.WorkflowJob"]
    logging.info(f"Found {len(pipelines)} pipeline jobs")
    
    # Split pipelines to be processed in batches
    batch_size = 100
    batches    = [pipelines[i:i + batch_size] for i in range(0, len(pipelines), batch_size)]
    
    results          = {}
    failed_pipelines = []
    
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = []
        for batch in batches:
            for pipeline in batch:
                futures.append(pool.submit(process_pipeline, server=server, pipeline=pipeline))
        for future in as_completed(futures):
            try:
                name, config = future.result()
                if config is not None:
                    results[name] = config
                else:
                    failed_pipelines.append(name)
            except Exception as e:
                logging.error(f"Unexpected error while processing future: {e}")

    # Save results on disk
    save_resources(results, OUTPUT_FOLDER)

if __name__ == "__main__":
    main()