import xml.etree.ElementTree as ET


class XmlClass:

    PARAMETER_STRING = "hudson.model.StringParameterDefinition"
    PARAMETER_HIDDEN = "com.wangyin.parameter.WHideParameterDefinition"


class XmlPath:

    PROPERTIES = "properties"

    #
    # Log rotation
    #
    BUILD_DISCARDER = "properties/jenkins.model.BuildDiscarderProperty"
    BUILD_DISCARDER_STRATEGY = "properties/jenkins.model.BuildDiscarderProperty/strategy"

    #
    # Cron
    #
    CRON_TRIGGER = (
        "properties/"
        "org.jenkinsci.plugins.workflow.job.properties."
        "PipelineTriggersJobProperty/"
        "triggers/hudson.triggers.TimerTrigger/spec"
    )

    #
    # SCM
    #
    SCM_URL = (
        "definition/scm/userRemoteConfigs/" "hudson.plugins.git.UserRemoteConfig/url"
    )

    SCRIPT_PATH = "definition/scriptPath"

    SCM_BRANCH = "definition/scm/branches/" "hudson.plugins.git.BranchSpec/name"

    #
    # Parameters
    #
    PARAMETER_PROPERTY = "properties/hudson.model.ParametersDefinitionProperty"

    PARAMETER_DEFINITIONS = (
        "properties/hudson.model.ParametersDefinitionProperty/" "parameterDefinitions"
    )

    PARAMETERS = (
        "properties/hudson.model.ParametersDefinitionProperty/" "parameterDefinitions/*"
    )


def set_child(parent: ET.Element, tag: str, value: str) -> ET.Element:

    child = parent.find(tag)

    if child is None:
        child = ET.SubElement(parent, tag)

    child.text = value
    return child


def get_or_create_parameter_definitions(node: ET.Element) -> ET.Element:

    params = node.find(XmlPath.PARAMETER_DEFINITIONS)

    if params is not None:
        return params

    properties = node.find("properties")
    if properties is None:
        properties = ET.SubElement(node, "properties")

    parameter_property = properties.find("hudson.model.ParametersDefinitionProperty")

    if parameter_property is None:
        parameter_property = ET.SubElement(
            properties, "hudson.model.ParametersDefinitionProperty"
        )

    params = parameter_property.find("parameterDefinitions")

    if params is None:
        params = ET.SubElement(parameter_property, "parameterDefinitions")

    return params


def find_parameter(params: ET.Element, parameter_name: str):

    for param in params:
        name = param.find("name")

        if name is not None and name.text == parameter_name:
            return param

    return None


def edit_concurrent_build(node: ET.Element):

    set_child(node, "concurrentBuild", "false")


def edit_log_params(node: ET.Element):

    strategy = node.find(XmlPath.BUILD_DISCARDER_STRATEGY)

    if strategy is None:
        return

    set_child(strategy, "daysToKeep", "-1")
    set_child(strategy, "numToKeep", "4")
    set_child(strategy, "artifactDaysToKeep", "-1")
    set_child(strategy, "artifactNumToKeep", "-1")


def edit_cron_trigger(node: ET.Element):

    cron = node.find(XmlPath.CRON_TRIGGER)

    if cron is not None and cron.text:
        set_child(node, "disabled", "true")


def edit_scm_params(node: ET.Element, record: dict):

    prop = node.find(XmlPath.SCM_URL)

    if prop is not None:
        prop.text = "https://gitlab.gbbper.priv/Devops/pipeline-build.git"

    prop = node.find(XmlPath.SCRIPT_PATH)

    if prop is not None:
        prop.text = record["SCM_JENKINSFILE"]

    prop = node.find(XmlPath.SCM_BRANCH)

    if prop is not None:
        prop.text = record["SCM_BRANCH"]


def edit_jdk_params(node: ET.Element):

    jdks = {
        "JDK_1.8.0_172_cifratura2048": "openjdk-1.8.0",
        "JDK_11_0_2"                 : "openjdk-11",
        "JDK_11+28"                  : "openjdk-11",
        "JDK_17.0.5"                 : "openjdk-17",
        "JDK_21.0.3"                 : "openjdk-21",
    }

    for param in node.findall(XmlPath.PARAMETERS):

        param_name = param.find("name")

        if param_name is None:
            continue

        if param_name.text != "jdkVersion":
            continue

        default = param.find("defaultValue")

        if default is not None and default.text in jdks:
            default.text = jdks[default.text]

        for choice in param.findall("./choices/a/string"):
            if choice.text in jdks:
                choice.text = jdks[choice.text]

        break


def edit_mvn_params(node: ET.Element):

    params = node.find(XmlPath.PARAMETER_DEFINITIONS)

    if params is None:
        return

    tokens = {
        "mvnBuild",
        "mvnUIT",
        "mvnArtifactDeploy",
        "JVMAdditionalParameters",
    }

    for param in list(params):

        param_name = param.find("name")

        if param_name is not None and param_name.text in tokens:
            params.remove(param)


def edit_jvm_params(node: ET.Element, record: dict):

    jenkinsfile = record.get("SCM_JENKINSFILE", "")

    found = any(token in jenkinsfile for token in ("Jenkins_fe", "Jenkins_be", "Jenkins_public"))
    if not found:
        return

    params   = get_or_create_parameter_definitions(node)
    existing = find_parameter(params, "JVMAdditionalParameters")

    if existing is not None:
        return

    element = ET.SubElement(params, XmlClass.PARAMETER_STRING)

    set_child(element, "name", "JVMAdditionalParameters")
    set_child(element, "defaultValue", "")
    set_child(element, "description", "Additional JVM Parameters")


def edit_app_params(node: ET.Element, record: dict):

    params   = get_or_create_parameter_definitions(node)
    existing = find_parameter(params, "applicationCode")

    if existing is not None:

        default = existing.find("defaultValue")

        if default is None:
            default = ET.SubElement(existing, "defaultValue")

        default.text = record["APPLICATION_CODE"]
        return

    element = ET.SubElement(params, XmlClass.PARAMETER_HIDDEN)

    set_child(element, "name", "applicationCode")
    set_child(element, "defaultValue", record["APPLICATION_CODE"])
    set_child(element, "description", "Application Code associated with the pipeline")


def edit_gitlab_project_url(node: ET.Element):

    for param in node.findall(XmlPath.PARAMETERS):

        param_name = param.find("name")
        param_value = param.find("defaultValue")

        if param_name is not None and param_name.text == "gitlabUrl":

            if param_value is not None:
                param_value.text = "https://gitlab.gbbper.priv"

            break


def edit_gitlab_project_name(node: ET.Element):

    for param in node.findall(XmlPath.PARAMETERS):

        param_name = param.find("name")

        if param_name is not None and param_name.text == "gitlabPproject":
            param_name.text = "gitlabProject"
            break
