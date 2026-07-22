#!/usr/bin/env python3
__author__      = "Giorgio Daniele Luppina"
__version__     = "1.0"
__description__ = ""

import argparse
import logging
import os
import shutil
import threading
import datetime
import jenkins
import xml.etree.ElementTree as ET

from concurrent.futures import ThreadPoolExecutor, as_completed
from lib                import get_cron_config
from lib                import get_jdk_info
from lib                import get_scm_config
from lib                import has_jvm_additional_parameters

MAX_WORKERS = 20
OUTPUT_DIR  = "tmp"
FINAL_FILE  = f"pipelines_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
LOG_FORMAT  = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOGGER      = logging.getLogger("jenkins.dumper")

def configure_logging(level=logging.INFO):
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT)


def get_out_file():
    return os.path.join(OUTPUT_DIR, f"{threading.current_thread().name}.csv")

def generate_record(
    folder_name  : str,
    pipeline_name: str,
    scm          : dict      | None,
    cron         : str       | None,
    jdks         : list[str] | None,
    jvms         : bool,
):

    scm        = scm or {}
    scm_url    = scm.get("url")
    scm_path   = scm.get("path")
    scm_branch = scm.get("branch")

    is_standard = bool(scm_url and "Devops/pipeline-build.git" in scm_url)

    return ",".join([
        folder_name,
        pipeline_name,
        str(is_standard),
        str(not is_standard),
        scm_url    or "",
        scm_path   or "",
        scm_branch or "",
        cron       or "",
        " ".join(jdks or []),
        str(jvms),
    ])

def process_pipeline(
    server         : jenkins.Jenkins,
    folder_name    : str,
    folder_fullname: str,
    pipeline       : dict,
):

    pipeline_name = pipeline["name"]
    pipeline_path = f"{folder_fullname}/{pipeline_name}"

    try:
        xml  = server.get_job_config(pipeline_path)
        root = ET.fromstring(xml)

        scm  = get_scm_config(root)
        cron = get_cron_config(root)
        jdks = get_jdk_info(root)
        jvms = has_jvm_additional_parameters(root)

        LOGGER.info("Pipeline %s processata con successo!", pipeline_path)

        return generate_record(
            folder_name=folder_name,
            pipeline_name=pipeline_name,
            scm=scm,
            cron=cron,
            jdks=jdks,
            jvms=jvms,
        )

    except ET.ParseError as e:
        LOGGER.error("Errore parsing XML job=%s error=%s", pipeline_path, e)

    except Exception:
        LOGGER.exception("Errore inatteso durante il processing job=%s", pipeline_path)

    return None

def process_folder(
    folder  : dict,
    url     : str,
    username: str,
    password: str,
):

    folder_name     = folder["name"]
    folder_fullname = folder["fullname"]

    try:

        server = jenkins.Jenkins(
            url,
            username,
            password,
            timeout=30,
        )

        jobs = server.get_job_info(folder_fullname).get("jobs", [])

        pipelines = [
            job for job in jobs
            if job.get("_class")
            == "org.jenkinsci.plugins.workflow.job.WorkflowJob"
        ]

        with open(get_out_file(), "a", encoding="utf-8") as fd:
            for pipeline in pipelines:
                record = process_pipeline(server=server, folder_name=folder_name, folder_fullname=folder_fullname, pipeline=pipeline)
                if record:
                    fd.write(record + "\n")

    except Exception:

        LOGGER.exception(
            "Errore durante il processamento folder=%s",
            folder_fullname,
        )

def navigate(
    url     : str,
    username: str,
    password: str,
):

    try:
        server = jenkins.Jenkins(
            url,
            username,
            password,
            timeout=120,
        )

        LOGGER.info("Connessione avvenuta con successo a %s", url)

        jobs = server.get_jobs()

        folders = [
            job for job in jobs
            if job["_class"]
            == "com.cloudbees.hudson.plugins.folder.Folder"
        ]

        LOGGER.info("Cartelle trovate [%s]", len(folders))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = [pool.submit(process_folder, folder, url, username, password) for folder in folders]
            for future in as_completed(futures):
                future.result()

    except Exception:
        LOGGER.exception("Navigazione Jenkins fallita")

def merge():

    columns = ",".join([
        "FOLDER_NAME",
        "PIPELINE_NAME",
        "IS_STANDARD",
        "IS_INLINE",
        "SCM_REPOSITORY",
        "SCM_JENKINSFILE",
        "SCM_BRANCH",
        "CRON",
        "JDKS",
        "JVMS",
    ])

    with open(FINAL_FILE, "w", encoding="utf-8") as out:
        out.write(columns + "\n")
        for filename in sorted(os.listdir(OUTPUT_DIR)):
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as fd:
                out.write(fd.read())

    LOGGER.info(
        "CSV generato file=%s",
        FINAL_FILE,
    )

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--url",       required=True)
    parser.add_argument("--username",  required=True)
    parser.add_argument("--password",  required=True)

    args = parser.parse_args()

    configure_logging()

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    navigate(url=args.url, username=args.username, password=args.password)
    merge()

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)


#
# TO RUN, launch:
# python main.py --url http://172.16.63.239/jenkins --username u825816 --password <password>
#

if __name__ == "__main__":
    main()