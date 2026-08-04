import jenkins
import xml.etree.ElementTree as ET
import copy

server = jenkins.Jenkins('http://172.116.63.239/jenkins', username='jenkinsb', password='68q1tz4w', timeout=60)

def add_or_replace_jdk_version_param(parameters):
    """Add or replace the jdkVersion parameter using raw XML."""
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
    jdk_version_elem = ET.fromstring(jdk_version_xml)
    existing_jdk_version_param = parameters.find("hudson.model.ChoiceParameterDefinition[name='jdkVersion']")
    if existing_jdk_version_param is not None:
        parameters.remove(existing_jdk_version_param)
    parameters.insert(0, jdk_version_elem)

def add_jvm_additional_params_param(parameters):
    """Add the JVMAdditionalParameters parameter if it doesn't exist."""
    jvm_additional_params_xml = """
    <hudson.model.StringParameterDefinition>
        <name>JVMAdditionalParameters</name>
        <description>Additional JVM parameters (auto-migrated)</description>
        <defaultValue></defaultValue>
    </hudson.model.StringParameterDefinition>
    """
    jvm_additional_params_elem = ET.fromstring(jvm_additional_params_xml)
    existing_jvm_additional_params_param = parameters.find("hudson.model.StringParameterDefinition[name='JVMAdditionalParameters']")
    if existing_jvm_additional_params_param is None:
        parameters.append(jvm_additional_params_elem)

def perform_migration(job_name):
    pipelineSuffixPairs = [(None, "-old"), (None, "-develop"), (None, "-release"), (None, "-master")]
    
    try:
        for i, (xml,suffix) in enumerate(pipelineSuffixPairs):
           if (suffix != "-old"):
            print(f"[DEBUG] Checking job '{job_name}{suffix}'")
            xml = server.get_job_config(job_name+suffix)
            pipelineSuffixPairs[i] = (xml, suffix)
    except jenkins.JenkinsException as e:
        if 'does not exist' not in str(e):
            print(f"[ERROR] An error occurred while checking job '{job_name}': {e}")
        else:
            print(f"{e}")
            print(f"[ERROR] Required job does not exist. Aborting migration!")
        return None   

    develop_xml, _  = pipelineSuffixPairs[1]
    if develop_xml is not None:
        pipelineSuffixPairs[0] = (copy.deepcopy(develop_xml), "-old")

    print(f"[INFO] EXISTANCE CHECK SUCCESS! Validating jobs configuration for '{job_name}'")

    for i, (xml, suffix) in enumerate(pipelineSuffixPairs):
        if xml is not None and suffix != "-old":
            print(f"[DEBUG] Processing pipeline '{job_name}'")
            root = ET.fromstring(xml)
            parameters = root.find("./properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions")
            #pipelineScmElem = root.find("./definition/scm/userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url")
            #jvmAdditionalParamsParam = root.find("./properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions/hudson.model.StringParameterDefinition[name='JVMAdditionalParameters']")
            pipelineElem = root.find("./definition/scriptPath")

            if pipelineElem is not None:
                pipelineElem.text = "Jenkins_docker_slave_jdk17_sb3"
            else:
                print("[ERROR] Pipeline path not found. Non-standard pipeline detected, aborting process!")
                return None
            
            if parameters is None:
                parameters_property = root.find("./properties/hudson.model.ParametersDefinitionProperty")
                if parameters_property is None:
                    parameters_property = ET.SubElement(root.find("./properties"), 'hudson.model.ParametersDefinitionProperty')
                parameters = ET.SubElement(parameters_property, 'parameterDefinitions')

            add_or_replace_jdk_version_param(parameters)
            add_jvm_additional_params_param(parameters)
            
            # Convert the modified XML back to a string
            xml = ET.tostring(root, encoding='utf-8').decode('utf-8')
            pipelineSuffixPairs[i] = (xml, suffix)
            #print(xml)

    print(f"[INFO] VALIDATION SUCCESS! Creating/reconfiguring jobs for '{job_name}'")

    for (xml,suffix) in pipelineSuffixPairs:
        if xml is not None:
            #print(xml)
            try:
                if(suffix == "-old"):
                    server.create_job(job_name + suffix, xml)
                    print(f"[DEBUG] Job '{job_name}{suffix}' created.")
                else:
                    server.reconfig_job(job_name + suffix, xml)
                    print(f"[DEBUG] Job '{job_name}{suffix}' reconfigured.")
            except jenkins.JenkinsException as e:
                print(f"An error occurred while creating/reconfiguring job '{job_name}{suffix}': {e}")
                return None
            
with open("pipelines_to_migrate.txt", "r") as fp:
    for line in fp:
        job_name = line.strip()
        if '/' in job_name:
            group, name = job_name.split('/')
            full_job_name = f"{group}/{name}"
        else:
            full_job_name = job_name
        
        try:
            job_info = server.get_job_info(full_job_name+"-old")
            print(f"[WARN] Job '{full_job_name}-old' exists. Skipping migration.")
        except jenkins.JenkinsException as e:
            if 'does not exist' not in str(e):
                print(f"[ERROR] An error occurred while checking job '{full_job_name}': {e}")
            else:
                print(f"[INFO] Job '{full_job_name}-old' does not exist. Migrating...")
                perform_migration(full_job_name)