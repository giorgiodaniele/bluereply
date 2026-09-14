
import logging
import os
import sys
import xml.etree.ElementTree as ET
from   concurrent.futures import ThreadPoolExecutor, as_completed
from   pathlib            import Path

import dotenv
import jenkins


dotenv.load_dotenv()


JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")

JOBS_FILE   = Path("pipelines.txt")
CA_BUNDLE   = "../../bperROOTCA.crt"
MAX_WORKERS = 10


# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)


# Jenkins configuration
def connect_to_jenkins() -> jenkins.Jenkins:

    if not all([JENKINS_URL, JENKINS_USERNAME, JENKINS_PASSWORD]):
        raise RuntimeError("JENKINS_URL, JENKINS_USERNAME and " "JENKINS_PASSWORD must be configured")

    try:
        logger.info("Connecting to Jenkins: %s ...", JENKINS_URL)
        server = jenkins.Jenkins(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
        server.get_whoami()
        logger.info("Connected successfully to %s", JENKINS_URL)
        return server
    except Exception:
        logger.exception("Failed to connect to Jenkins: %s", JENKINS_URL)
        sys.exit(1)

# Read Jenkins to process from TXT file
def load_pipelines() -> list[str]:
    with JOBS_FILE.open("r", encoding="utf-8") as file:
       return [ line.strip() for line in file if line.strip() and not line.strip().startswith("#") ]



def process_job(server: jenkins.Jenkins, fullname: str) -> None:
    try:
        logger.info("Processing job: %s", fullname)

        # Get current job configuration
        xml_text = server.get_job_config(fullname)
        xml      = ET.fromstring(xml_text)

        #
        # Find/create parameterDefinitions
        #
        parameters = xml.find(
            "./properties/"
            "hudson.model.ParametersDefinitionProperty/"
            "parameterDefinitions"
        )

        if parameters is None:
            properties = xml.find("./properties")

            if properties is None:
                properties = ET.SubElement(xml, "properties")

            parameters_property = properties.find(
                "hudson.model.ParametersDefinitionProperty"
            )

            if parameters_property is None:
                parameters_property = ET.SubElement(
                    properties,
                    "hudson.model.ParametersDefinitionProperty"
                )

            parameters = parameters_property.find("parameterDefinitions")

            if parameters is None:
                parameters = ET.SubElement(parameters_property, "parameterDefinitions")

        #
        # Add/replace jdkVersion
        #
        jdk_version_xml = """
        <hudson.model.ChoiceParameterDefinition>
            <name>jdkVersion</name>
            <description>JDK Version (auto-migrated)</description>
            <choices class="java.util.Arrays$ArrayList">
                <a class="string-array">
                    <string>JDK_21.0.3</string>
                    <string>JDK_17.0.5</string>
                </a>
            </choices>
        </hudson.model.ChoiceParameterDefinition>
        """

        jdk_parameter = ET.fromstring(jdk_version_xml)

        existing_jdk_parameter = parameters.find(
            "hudson.model.ChoiceParameterDefinition"
            "[name='jdkVersion']"
        )

        if existing_jdk_parameter is not None:
            parameters.remove(existing_jdk_parameter)

        # jdkVersion must be the first parameter
        parameters.insert(0, jdk_parameter)

        #
        # Add JVMAdditionalParameters if missing
        #
        existing_jvm_parameter = parameters.find(
            "hudson.model.StringParameterDefinition"
            "[name='JVMAdditionalParameters']"
        )

        if existing_jvm_parameter is None:
            jvm_parameter_xml = """
            <hudson.model.StringParameterDefinition>
                <name>JVMAdditionalParameters</name>
                <description>Additional JVM parameters (auto-migrated)</description>
                <defaultValue></defaultValue>
            </hudson.model.StringParameterDefinition>
            """

            jvm_parameter = ET.fromstring(jvm_parameter_xml)
            parameters.append(jvm_parameter)

        #
        # Update pipeline scriptPath
        #
        script_path = xml.find("./definition/scriptPath")
        if script_path is None:
            logger.error("Pipeline scriptPath not found for: %s", fullname)
            return

        script_path.text = "Jenkins_docker_slave_jdk17_sb3"  
              
        config_xml      = ET.tostring(xml, encoding="unicode")
        server.reconfig_job(fullname, config_xml)

        logger.info(f"Job {fullname} reconfigured successfully")
        
    except Exception:
        logger.error(f"Failed to process job {fullname}")
        return None


# Load all pipeline jobs
def load_all_pipelines(server: jenkins.Jenkins) -> list[str]:
    jobs = server.get_all_jobs()

    return [
        job
        for job in jobs
        if job.get("_class")
        == "org.jenkinsci.plugins.workflow.job.WorkflowJob"
    ]


# Main
def main() -> None:

    os.environ["REQUESTS_CA_BUNDLE"] = CA_BUNDLE

    server               = connect_to_jenkins()
    pipelines_to_process = load_pipelines()
    pipelines            = load_all_pipelines(server)

    for pipeline in pipelines:
        for pipeline_to_process in pipelines_to_process:
            if pipeline["fullname"].startswith(pipeline_to_process):
                logging.info(f"Found matching pipeline: {pipeline["fullname"]}")
                process_job(server, pipeline["fullname"])

if __name__ == "__main__":
    main()
