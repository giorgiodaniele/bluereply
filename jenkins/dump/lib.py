import xml.etree.ElementTree as ET


class XmlClass:

    PARAMETER_STRING = "hudson.model.StringParameterDefinition"
    PARAMETER_HIDDEN = "com.wangyin.parameter.WHideParameterDefinition"


class XmlPath:

    PROPERTIES = "properties"

    #
    # Log rotation
    #
    BUILD_DISCARDER          = "properties/jenkins.model.BuildDiscarderProperty"
    BUILD_DISCARDER_STRATEGY = "properties/jenkins.model.BuildDiscarderProperty/strategy"

    #
    # Cron
    #
    CRON_TRIGGER = "properties/org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty/triggers/hudson.triggers.TimerTrigger/spec"

    #
    # SCM
    #
    SCM_URL     = "definition/scm/userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url"
    SCRIPT_PATH = "definition/scriptPath"
    SCM_BRANCH  = "definition/scm/branches/hudson.plugins.git.BranchSpec/name"

    #
    # Parameters
    #
    PARAMETER_PROPERTY    = "properties/hudson.model.ParametersDefinitionProperty"
    PARAMETER_DEFINITIONS = "properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions"
    PARAMETERS            = "properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions/*"


#
# Generic getters
#
def get_child_text(node: ET.Element, path: str) -> str | None:
    child = node.find(path)
    if child is None:
        return None
    return child.text

#
# Cron
#
def get_cron_config(node: ET.Element) -> str | None:
    cron = node.find(XmlPath.CRON_TRIGGER)
    return cron.text if cron is not None else None


#
# SCM
#
def get_scm_config(node: ET.Element) -> dict | None:
    url    = get_child_text(node, XmlPath.SCM_URL)
    path   = get_child_text(node, XmlPath.SCRIPT_PATH)
    branch = get_child_text(node, XmlPath.SCM_BRANCH)

    if not any([url, path, branch]):
        return None

    return {
        "url"        : url,
        "path"       : path,
        "branch"     : branch,
    }



#
# JDK info
#
def get_jdk_info(node: ET.Element) -> list[str] | None:
    for param in node.findall(XmlPath.PARAMETERS):
        param_name = param.find("name")

        if param_name is None or param_name.text != "jdkVersion":
            continue

        choices = []
        for choice in param.findall("./choices/a/string"):
            if choice.text:
                choices.append(choice.text)
        return choices

    return None


#
# JVM / Parameter info
#
def has_jvm_additional_parameters(node: ET.Element) -> bool:
    for param in node.findall(XmlPath.PARAMETERS):
        param_name = param.find("name")
        if param_name is not None and param_name.text == "JVMAdditionalParameters":
            return True
    return False
