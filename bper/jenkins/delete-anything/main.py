#
# Use this script to delete any job configured in a Jenkins server.
# USE THIS SCRIPT AT YOUR OWN RISK
#

#!/usr/bin/env python3

import csv
import os
import sys
import logging
import dotenv
import jenkins
import datetime
import xml.etree.ElementTree as ET
from   concurrent.futures import ThreadPoolExecutor, as_completed

dotenv.load_dotenv()

JENKINS_URL      = os.getenv("JENKINS_URL")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
JENKINS_PASSWORD = os.getenv("JENKINS_PASSWORD")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s - %(message)s")


def delete(url, username, password):

    try:
        client = jenkins.Jenkins(url, username=username, password=password, timeout=60)
        jobs   = client.get_all_jobs()

        logging.info(f"There are {len(jobs)} jobs in Jenkins to be deleted ... ")

        def delete_job(job: jenkins._Job):
            fullname  = job.get("fullname", "")
            #
            # DO NOT DELETE DevOpsAmdinistrator
            #
            if "DevOpsAdministrator" in fullname:
                return
            # if "Anagrafe" in fullname:
            #     return
            # if "ConsoleFusione" in fullname:
            #     return
            # if "BigliettoDigitale" in fullname:
            #     return
            # if "PrinterCicoRepository" in fullname:
            #     return
            # if "NPM" in fullname:
            #     return
            try:
                client.delete_job(fullname)
                logging.info(f"Eliminated {fullname}")
            except Exception as e:
                logging.error(f"Could not delete {fullname}: {e}")

        def process_batch(jobs: list[jenkins._Job]):
            with ThreadPoolExecutor(max_workers=10) as pool:
                futures = [pool.submit(delete_job, job) for job in jobs]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logging.error(e)

        #
        # Select all jobs which are folders
        #
        folders = [job for job in jobs if job.get("_class", "").endswith("Folder")]
        process_batch(folders)

        #
        # Select all jobs which are pipelines
        #
        # pipelines = [job for job in jobs if not job.get("_class", "").endswith("Folder")]
        # process_batch(pipelines)

        logging.info(f"All jobs have been completed")

    except Exception as e:
        raise RuntimeError(e)

def connect_server(url: str, username: str, password: str):
    try:
        return jenkins.Jenkins(url=url, username=username, password=password)
    except Exception as e:
        return f"Failed to connect to Jenkins: {e}"

def main():

    server = None
    server = connect_server(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)

    if isinstance(server, str):
        logging.error(server)
        sys.exit(1)

    #
    # Ask for confirmation
    #
    answer = input(f"This operation is distructive and it will delete anything configured in {JENKINS_URL}. Type YES to continue: ").strip()
    if answer != "YES":
        sys.exit(0)

    delete(url=JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)

if __name__ == "__main__":
    main()