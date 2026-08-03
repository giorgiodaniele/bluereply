import csv
import fnmatch


INPUT_FILE      = r"..\dump\output\pipelines_20260729084244.csv"
PATTERNS_FILE   = r"resources\patterns.txt"
REDMINE_TICKETS = r"resources\redmine_tickets.csv"
VALIDATED_FILE  = r"validated.csv"
DISCARDED_FILE  = r"discarded.csv"

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

valid_suffixes = (
    "-master",
    "-develop",
    "-release",
    "-it",
    "-lab",
    "-old",
    "-chart",
    "-httpd",
    "upload-snapshot",
    "upload-release",
    "artifact-upload",
    "upload",
    "upload-chart",
)

valid_prefixes = (
    "standalone-",
    "BATCH",
)


validated  = []
discarded  = []
statistics = {
    "total"          : 0,
    "out_of_standard": 0,
    "ignored"        : 0,
    "invalid_name"   : 0,
    "validated"      : 0,
}

# Load redmine issues
issues = {}
with open(REDMINE_TICKETS, newline="", encoding="utf-8") as file:
    for record in csv.DictReader(file):
        key         = f"{record['TEAM'].strip()}/{record['LAYER'].strip()}-{record['COMPONENT'].strip()}"
        issues[key] = record["APPLICATION_CODE"].strip()

# Load patterns to ignore
with open(PATTERNS_FILE, encoding="utf-8") as file:
    ignored_patterns = { line.strip() for line in file if line.strip() }

# Process
with open(INPUT_FILE, newline="", encoding="utf-8") as file:
    reader     = csv.DictReader(file)
    fieldnames = reader.fieldnames

    for record in reader:
        statistics["total"] += 1

        fullname = record["fullname"]
        pipeline = fullname.rsplit("/", 1)[-1]

        #
        # STEP 1. Must be standard
        #
        if record["is_standard"] != "True":
            discarded.append({**record, "description": "out_of_standard" })
            statistics["out_of_standard"] += 1
            continue

        #
        # STEP 2. Must not match ignored patterns
        #
        if any(fnmatch.fnmatchcase(fullname, pattern) for pattern in ignored_patterns):
            discarded.append({**record, "description": "ignored"})
            statistics["ignored"] += 1
            continue

        #
        # STEP 3. Must have a valid suffix or prefix
        #
        has_valid_suffix = pipeline.endswith(valid_suffixes)
        has_valid_prefix = pipeline.startswith(valid_prefixes)

        if not (has_valid_suffix or has_valid_prefix):
            discarded.append({**record, "description": "invalid_suffix_or_prefix"})
            statistics["invalid_name"] += 1
            continue

        # Pipeline is valid. Not it is time to edit
        record["jenkinsfile_branch"]     = "*/new-master"
        record["jenkinsfile_name"]       = JENKINS_FILE_MAPPING.get(record["jenkinsfile_name"])
        record["jenkinsfile_repository"] = "https://gitlab.gbbper.priv/Devops/pipeline-build.git"
        if pipeline.startswith("fe"):
            record["jenkinsfile_name"]   = "Jenkins_fe"

        record["application_code"] = ""
        for issue in issues.keys():
            if issue in fullname:
                record["application_code"] = issues[issue]
                break

        # Continue to next
        validated.append(record)
        statistics["validated"] += 1

# Save valid pipelines
validated_fieldnames = fieldnames + ["application_code"]
with open(VALIDATED_FILE, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=validated_fieldnames)

    writer.writeheader()
    writer.writerows(validated)

# Save discarded pipelines
discarded_fieldnames = fieldnames + ["description"]
with open(DISCARDED_FILE, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=discarded_fieldnames)

    writer.writeheader()
    writer.writerows(discarded)

# Have a summary
print(f"Total pipelines:       {statistics['total']}")
print(f"Out of standard:       {statistics['out_of_standard']}")
print(f"Ignored:               {statistics['ignored']}")
print(f"Invalid naming:        {statistics['invalid_name']}")
print(f"Validated:             {statistics['validated']}")
print(f"Discarded:             {len(discarded)}")