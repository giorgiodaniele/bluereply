import csv
import re
import argparse

VALID_SUFFIXES       = ("-master", "-develop", "-release", "-it", "-lab", "-old", "-chart", "-httpd", "upload-snapshot", "upload-release", "artifact-upload", "upload", "upload-chart")
VALID_PREFIXES       = ("standalone-", "BATCH")
JENKINS_FILE_MAPPING = {
    "Jenkins_docker_in_docker"                        : "Jenkins_be_java",
    "Jenkins_no_docker_new_maven_master"              : "Jenkins_be_java",
    "Jenkinsfile_docker"                              : "Jenkins_be_java",
    "Jenkinsfile_free_bash_stage"                     : "Jenkins_be_java",
    "Jenkinsfile_JDK_7_NO_SONAR"                      : "Jenkins_be_java",
    "Jenkinsfile_JDK_7_PROFILE_JACOCO"                : "Jenkins_be_java",
    "Jenkinsfile_no_clean"                            : "Jenkins_be_java",
    "Jenkinsfile_no_post"                             : "Jenkins_be_java",
    "Jenkinsfile_prova"                               : "Jenkins_be_java",
    "Jenkinsfile_slave_test"                          : "Jenkins_be_java",
    "Jenkinsfile_Smartweb_Jenkinsv2.330"              : "Jenkins_be_java",
    "Jenkinsfile_test"                                : "Jenkins_be_java",
    "Jenkinsfile-Jenkinsv2.330"                       : "Jenkins_be_java",
    "Jenkinsfile-Jenkinsv2.330-JDK7"                  : "Jenkins_be_java",
    "Jenkins_dockerimage_builder"                     : "Jenkins_be_java",
    "Jenkins_no_docker_JDK_11"                        : "Jenkins_be_java",
    "Jenkins_no_docker_no_registry_slave_quarkus"     : "Jenkins_be_quarkus",
    "Jenkins_no_docker_singleDeploy"                  : "Jenkins_be_java",
    "Jenkins_sgw"                                     : "Jenkins_sgw",
    "Jenkinsfile_JDK_7_NO_INSTALL"                    : "Jenkins_be_java",
    "Jenkinsfile_it"                                  : "Jenkins_be_java",
    "Jenkinsfile_public_libs_JDK11"                   : "Jenkins_public_libs",
    "Jenkinsfile_public_plugins"                      : "Jenkins_be_java",
    "Jenkins_no_docker_no_registry_slave_FE"          : "Jenkins_fe",
    "Jenkins_no_docker_JDK_11_slave"                  : "Jenkins_be_java",
    "Jenkins_no_docker_master"                        : "Jenkins_be_java",
    "Jenkinsfile_public_libs_JDK17"                   : "Jenkins_public_libs",
    "Jenkins_artifact_upload"                         : "Jenkins_upload_artifact",
    "Jenkins_upload_helm"                             : "Jenkins_upload_helm",
    "Jenkinsfile_public_libs"                         : "Jenkins_public_libs",
    "Jenkinsfile_Smartweb"                            : "Jenkins_be_java",
    "Jenkins_no_docker_NPM"                           : "Jenkins_be_java",
    "Jenkinsfile_JDK_7"                               : "Jenkins_be_java",
    "Jenkins_no_docker_new_maven_393"                 : "Jenkins_be_java",
    "Jenkins_no_docker_no_qa_no_deploy"               : "Jenkins_be_java",
    "Jenkins_docker_python_app"                       : "Jenkins_python_app",
    "Jenkins_no_docker_slave"                         : "Jenkins_be_java",
    "Jenkins_docker_python_lib"                       : "Jenkins_python_lib",
    "Jenkins_docker_slave_libNPM"                     : "Jenkins_libNPM",
    "Jenkins_no_docker_no_registry_slave_FE_improved" : "Jenkins_fe",
    "Jenkins_docker_slave_quarkus"                    : "Jenkins_be_quarkus",
    "Jenkins_no_docker_no_registry_slave"             : "Jenkins_be_java",
    "Jenkins_upload_docker_image"                     : "Jenkins_upload_docker_image",
    "Jenkins_no_docker_no_registry"                   : "Jenkins_be_java",
    "Jenkins_no_docker_no_registry_slave_FE_improved2": "Jenkins_fe",
    "Jenkins_no_docker"                               : "Jenkins_be_java",
    "Jenkins_docker_slave_jdk17_sb3"                  : "Jenkins_be_sb3",
    "Jenkins_no_docker_new_maven"                     : "Jenkins_be_java",
    "Jenkinsfile"                                     : "Jenkins_be_java",
    "Jenkins_upload_generic_artifact"                 : "Jenkins_upload_generic_artifact",
    "Jenkins_dotnetcore_sast_from_JSON"               : "Jenkins_dotnetcore_QA",
    "Jenkins_generic_sast_from_JSON"                  : "Jenkins_generic_QA",
}
JDKS_MAPPING         = {
    "JDK_1.8.0_172_cifratura2048": "openjdk-1.8.0",
    "JDK_11_0_2"                 : "openjdk-11",
    "JDK_11.0.2"                 : "openjdk-11",
    "JDK_11+28"                  : "openjdk-11",
    "JDK_17.0.5"                 : "openjdk-17",
    "JDK_21.0.3"                 : "openjdk-21",
    "JDK_21_0_9"                 : "openjdk-21",
}


def main():

    parser = argparse.ArgumentParser(description="Save BPER Jenkins pipelines to a CSV file")
    parser.add_argument("--input", type=str, help="Input file for the CSV file", default="")
    args = parser.parse_args()

    src_file = args.input
    dst_file = f"{src_file.replace(".csv", "")}_filtered.csv"

    records = []
    records_with_application_code = []

    # Load patterns by which filtering pipelines according to their fullname
    with open("resources/patterns.txt", "r", encoding="utf-8") as file:
        ignored_patterns = [ re.compile(line.strip()) for line in file if line.strip() ]

    with open(src_file, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for record in reader:
            fullname = record["fullname"]
            for pattern in ignored_patterns:
                if pattern.match(fullname):
                    break
            records.append(record)

    # Load pipelines with application code
    with open("resources/pipelinesWithApplicationCode.csv", "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for record in reader:
            records_with_application_code.append(record)

    components_app_code = {}

    for record in records:
        fullname = record["fullname"]

        for valid_prefix in VALID_PREFIXES:
            if not fullname.startswith(valid_prefix):
                continue
        for valid_suffix in VALID_SUFFIXES:
            if not fullname.endswith(valid_suffix):
                continue

        record["jdkVersion"]            = ";".join(JDKS_MAPPING.get(jdk, "") for jdk in record["jdkVersion"].split(";"))
        record["jenkinsfileName"]       = JENKINS_FILE_MAPPING.get(record["jenkinsfileName"])
        record["jenkinsfileRepository"] = "https://gitlab.gbbper.priv/Devops/pipeline-build.git"
        record["jenkinsfileBranch"]     = "*/new-master"

        app_code = ""
        for record_with_app_code in records_with_application_code:
            if record_with_app_code["jenkinsJobName"] == record["fullname"]:
                app_code    = record_with_app_code["applicationCode"]
                break

        components_app_code[f"{record['gitlabGroup']}/{record['gitlabPproject']}"] = app_code

        record["applicationCode"] = app_code

    # Write the output file
    with open(dst_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    import json
    with_out_app_code = list(filter(lambda x: x["applicationCode"] == "", records))
    with_app_code     = list(filter(lambda x: x["applicationCode"] != "", records))
    print(f"Without app code: {len(with_out_app_code)}")
    print(f"With app code:    {len(with_app_code)}")
    with open("components_vs_app_code.json", "w", encoding="utf-8") as file:
        json.dump(components_app_code, file, indent=4)


if __name__ == "__main__":
    main()