import csv
import fnmatch

from pathlib import Path


INPUT_FILE           = Path("jenkins_pipelines_20260909_122234.csv")
OUTPUT_FILE          = Path("jenkins_pipelines_20260909_122234_filtered.csv")
PATTERNS_FILE        = Path("resources/patterns.txt")
REDMINE_TICKETS_FILE = Path("resources/redmine_tickets.csv")
JENKINS_REPOSITORY   = "https://gitlab.gbbper.priv/Devops/pipeline-build.git"
JENKINS_BRANCH       = "*/new-master"

VALID_SUFFIXES = (
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

VALID_PREFIXES = (
    "standalone-",
    "BATCH",
)

JENKINS_FILE_MAPPING = {
    "Jenkins_docker_in_docker":                        "Jenkins_be_java",
    "Jenkins_no_docker_new_maven_master":              "Jenkins_be_java",
    "Jenkinsfile_docker":                              "Jenkins_be_java",
    "Jenkinsfile_free_bash_stage":                     "Jenkins_be_java",
    "Jenkinsfile_JDK_7_NO_SONAR":                      "Jenkins_be_java",
    "Jenkinsfile_JDK_7_PROFILE_JACOCO":                "Jenkins_be_java",
    "Jenkinsfile_no_clean":                            "Jenkins_be_java",
    "Jenkinsfile_no_post":                             "Jenkins_be_java",
    "Jenkinsfile_prova":                               "Jenkins_be_java",
    "Jenkinsfile_slave_test":                          "Jenkins_be_java",
    "Jenkinsfile_Smartweb_Jenkinsv2.330":              "Jenkins_be_java",
    "Jenkinsfile_test":                                "Jenkins_be_java",
    "Jenkinsfile-Jenkinsv2.330":                       "Jenkins_be_java",
    "Jenkinsfile-Jenkinsv2.330-JDK7":                  "Jenkins_be_java",
    "Jenkins_dockerimage_builder":                     "Jenkins_be_java",
    "Jenkins_no_docker_JDK_11":                        "Jenkins_be_java",
    "Jenkins_no_docker_no_registry_slave_quarkus":     "Jenkins_be_quarkus",
    "Jenkins_no_docker_singleDeploy":                  "Jenkins_be_java",
    "Jenkins_sgw":                                     "Jenkins_sgw",
    "Jenkinsfile_JDK_7_NO_INSTALL":                    "Jenkins_be_java",
    "Jenkinsfile_it":                                  "Jenkins_be_java",
    "Jenkinsfile_public_libs_JDK11":                   "Jenkins_public_libs",
    "Jenkinsfile_public_plugins":                      "Jenkins_be_java",
    "Jenkins_no_docker_no_registry_slave_FE":          "Jenkins_fe",
    "Jenkins_no_docker_JDK_11_slave":                  "Jenkins_be_java",
    "Jenkins_no_docker_master":                        "Jenkins_be_java",
    "Jenkinsfile_public_libs_JDK17":                   "Jenkins_public_libs",
    "Jenkins_artifact_upload":                         "Jenkins_upload_artifact",
    "Jenkins_upload_helm":                             "Jenkins_upload_helm",
    "Jenkinsfile_public_libs":                         "Jenkins_public_libs",
    "Jenkinsfile_Smartweb":                            "Jenkins_be_java",
    "Jenkins_no_docker_NPM":                           "Jenkins_be_java",
    "Jenkinsfile_JDK_7":                               "Jenkins_be_java",
    "Jenkins_no_docker_new_maven_393":                 "Jenkins_be_java",
    "Jenkins_no_docker_no_qa_no_deploy":               "Jenkins_be_java",
    "Jenkins_docker_python_app":                       "Jenkins_python_app",
    "Jenkins_no_docker_slave":                         "Jenkins_be_java",
    "Jenkins_docker_python_lib":                       "Jenkins_python_lib",
    "Jenkins_docker_slave_libNPM":                     "Jenkins_libNPM",
    "Jenkins_no_docker_no_registry_slave_FE_improved": "Jenkins_fe",
    "Jenkins_docker_slave_quarkus":                    "Jenkins_be_quarkus",
    "Jenkins_no_docker_no_registry_slave":             "Jenkins_be_java",
    "Jenkins_upload_docker_image":                     "Jenkins_upload_docker_image",
    "Jenkins_no_docker_no_registry":                   "Jenkins_be_java",
    "Jenkins_no_docker_no_registry_slave_FE_improved2": "Jenkins_fe",
    "Jenkins_no_docker":                               "Jenkins_be_java",
    "Jenkins_docker_slave_jdk17_sb3":                  "Jenkins_be_sb3",
    "Jenkins_no_docker_new_maven":                     "Jenkins_be_java",
    "Jenkinsfile":                                     "Jenkins_be_java",
    "Jenkins_upload_generic_artifact":                 "Jenkins_upload_generic_artifact",
    "Jenkins_dotnetcore_sast_from_JSON":               "Jenkins_dotnetcore_QA",
    "Jenkins_generic_sast_from_JSON":                  "Jenkins_generic_QA",
}


def load_redmine_issues(path: Path) -> dict[str, str]:
    issues = {}

    with path.open(newline="", encoding="utf-8") as file:
        for record in csv.DictReader(file):
            key         = f"{record['TEAM'].strip()}/{record['LAYER'].strip()}-{record['COMPONENT'].strip()}"
            issues[key] = record["APPLICATION_CODE"].strip()

    return issues


def load_ignored_patterns(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as file:
        return {line.strip() for line in file if line.strip()}


def get_pipeline_name(fullname: str) -> str:
    return fullname.rsplit("/", 1)[-1]


def find_application_code(
    fullname: str,
    issues  : dict[str, str],
) -> str:

    for issue_key, application_code in issues.items():
        if issue_key in fullname:
            return application_code

    return ""


def validate_pipeline(
    record          : dict[str, str],
    ignored_patterns: set[str],
) -> str:

    fullname = record["fullname"]
    pipeline = get_pipeline_name(fullname)

    if record["is_standard"] != "True":
        return "Pipeline is out of standard"

    if any(fnmatch.fnmatchcase(fullname, pattern) for pattern in ignored_patterns):
        return "Pipeline matches an ignored pattern"

    if not pipeline.startswith(VALID_PREFIXES) and not pipeline.endswith(VALID_SUFFIXES):
        return "Pipeline has an invalid prefix or suffix"

    return ""


def prepare_pipeline(
    record: dict[str, str],
    issues: dict[str, str],
) -> dict[str, str]:

    fullname         = record["fullname"]
    pipeline         = get_pipeline_name(fullname)
    jenkinsfile_name = JENKINS_FILE_MAPPING.get(record["jenkinsfile_name"])
    application_code = find_application_code(fullname, issues)

    if pipeline.startswith("fe"):
        jenkinsfile_name = "Jenkins_fe"

    return {
        **record,
        "jenkinsfile_branch":     JENKINS_BRANCH,
        "jenkinsfile_name":       jenkinsfile_name,
        "jenkinsfile_repository": JENKINS_REPOSITORY,
        "application_code":       application_code,
    }


def process_pipelines(
    input_file      : Path,
    ignored_patterns: set[str],
    issues          : dict[str, str],
) -> tuple[list[dict[str, str]], list[str]]:

    validated = []
    discarded = []

    with input_file.open(newline="", encoding="utf-8") as file:
        for record in csv.DictReader(file):
            fullname = record["fullname"]
            reason   = validate_pipeline(record, ignored_patterns)

            if reason:
                discarded.append(f"{fullname} - {reason}")
                continue

            validated.append(
                prepare_pipeline(record, issues)
            )

    return validated, discarded


def write_csv(
    path      : Path,
    records   : list[dict[str, str]],
    fieldnames: list[str],
) -> None:

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    ignored_patterns = load_ignored_patterns(PATTERNS_FILE)
    issues           = load_redmine_issues(REDMINE_TICKETS_FILE)

    validated, discarded = process_pipelines(INPUT_FILE, ignored_patterns,issues)

    with INPUT_FILE.open(newline="", encoding="utf-8") as file:
        fieldnames = csv.DictReader(file).fieldnames or []

    write_csv(
        OUTPUT_FILE,
        validated,
        fieldnames + ["application_code"],
    )

    for message in discarded:
        print(f"DISCARDED  {message}")

    print()
    print(f"Validated: {len(validated)}")
    print(f"Discarded: {len(discarded)}")
    print(f"Output:    {OUTPUT_FILE}")


if __name__ == "__main__":
    main()