import xml.etree.ElementTree as ET

def add_jdk_option(node: ET.Element, jdk: str = "JDK_17.0.5"):

    for param in node.findall("properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions/*"):
        name = param.find("name")
        if name is not None and name.text == "jdkVersion":
            container = param.find("./choices/a")
            if container is not None:
                existing = [c.text for c in container.findall("string")]
                if jdk not in existing:
                    #
                    # Insert new option
                    #
                    new_opt      = ET.Element("string")
                    new_opt.text = jdk
                    container.insert(0, new_opt)
            break
    return node