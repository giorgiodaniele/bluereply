#!/usr/bin/env python3
__author__      = "Giorgio Daniele Luppina"
__version__     = "1.0"
__description__ = "Generate a folder containing all jobs edited according to BPER-driver logic."

import argparse
import csv
import logging
import os
import sys
import jenkins
import xml.etree.ElementTree as ET

from   concurrent.futures                import ThreadPoolExecutor, as_completed
from   datetime                          import datetime
from   setter                            import *

PIPELINES_PATH = "res/pipelines.csv"
OUTPUT_FOLDER  = f"jenkinsDump_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"
LOG_FORMAT     = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT    = "%Y-%m-%d %H:%M:%S"
MAX_WORKERS    = 10

def config_logger(level=logging.INFO):
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger("jenkins.export")    
os.environ["REQUESTS_CA_BUNDLE"] = "res/bperROOTCA.crt"

def save_xml_config(fullname: str, xml: ET.Element, out: str, is_folder: bool):

    pces = fullname.split("/")
    path = os.path.join(out, *pces[:-1])

    os.makedirs(path, exist_ok=True)

    file_name = f"__IS_A_FOLDER__{pces[-1]}.xml" if is_folder else f"{pces[-1].replace('/', '__')}.xml"
    file_path = os.path.join(path, file_name)

    tree = ET.ElementTree(xml)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)

    logger.info("Salvataggio completato per %s", fullname)

def edit_xml_config(fullname: str, node: ET.Element, out: str, record: dict, 
                #official_codes: dict, 
                #redmine_codes: dict
                ):

    edit_concurrent_build(node)
    edit_log_params(node)
    edit_cron_trigger(node)
    edit_scm_params(node, record)
    edit_jdk_params(node)
    edit_mvn_params(node)
    edit_jvm_params(node, record)
    edit_app_params(node, record)
    edit_gitlab_project_url(node)
    edit_gitlab_project_name(node)

    save_xml_config(fullname=fullname, xml=node, out=out, is_folder=False)
   
def fetch_job_info(server: jenkins.Jenkins, job):
    xml = server.get_job_config(job["fullname"])
    return job["fullname"], ET.fromstring(xml)

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--url",      required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)

    args   = parser.parse_args()
    jobs   = []
    server = None
    try:
        server = jenkins.Jenkins(args.url, args.username, args.password, timeout=30)
        jobs   = server.get_all_jobs()
    except Exception as e:
        logger.info(f"Impossibile proseguire! Errore: {e}")
        sys.exit(0)

    pipelines_records = {}
    with open(PIPELINES_PATH, encoding="utf-8") as file:
        for record in csv.DictReader(file):
            pipelines_records[f"{record['FOLDER_NAME']}/{record['PIPELINE_NAME']}"] = record

    with ThreadPoolExecutor(max_workers=int(MAX_WORKERS)) as pool:
        futures = [pool.submit(fetch_job_info, server, job) for job in jobs]

        for future in as_completed(futures):
            result = future.result()
            if not result:
                continue

            fullname, xml = result
            if xml.tag == "com.cloudbees.hudson.plugins.folder.Folder":
                save_xml_config(fullname, xml, OUTPUT_FOLDER, True)
            if xml.tag == "project":
                save_xml_config(fullname, xml, OUTPUT_FOLDER, True)
            if xml.tag == "flow-definition":
                record = pipelines_records.get(fullname)
                if record is not None:
                    edit_xml_config(fullname, xml, OUTPUT_FOLDER, record, 
                                  #off_app_codes, 
                                  # rem_app_codes
                                  )
    
#
# MAIN
#
# python exporter.py --url http://172.16.63.239/jenkins --username u825816 --password <>

if __name__ == "__main__":
    config_logger()
    main()