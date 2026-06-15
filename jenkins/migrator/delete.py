#!/usr/bin/env python3
__author__      = "Giorgio Daniele Luppina"
__version__     = "1.0"
__description__ = "Eliminate any job configured in a Jenkins server."

import argparse
import logging
import os
import sys
import jenkins
from   concurrent.futures import ThreadPoolExecutor, as_completed

LOG_FORMAT  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_WORKERS = 10

def config_logger(level=logging.INFO):
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger("jenkins.delete")

os.environ["REQUESTS_CA_BUNDLE"] = "res/bperROOTCA.crt"

def delete(url, username, password):

    try:
        client = jenkins.Jenkins(url, username=username, password=password, timeout=60)
        jobs   = client.get_all_jobs()

        logger.info(f"In {url} ci sono {len(jobs)} job Jenkins da cancellare...")

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
                logger.info(f"Eliminazione {fullname} completata!")
            except Exception as e:
                logger.error(f"Eliminazione {fullname}: {e}")

        def process_batch(jobs: list[jenkins._Job]):
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = [pool.submit(delete_job, job) for job in jobs]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(e)

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

        logger.info("Pulizia completata con successo!")

    except Exception as e:
        raise RuntimeError(e)

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--url",      required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)

    args = parser.parse_args()

    confirm = input("Questa operazione è distruttiva. Digitare YES per continuare: ").strip()
    if confirm != "YES":
        sys.exit(0)

    try:
        delete(url=args.url, username=args.username, password=args.password)
        logger.info("Eliminazione completata!")
    except Exception as e:
        logger.error(e)
        sys.exit(1)

if __name__ == "__main__":
    config_logger()
    main()

# python delete.py --username <> --password <> --url http://172.16.63.239/jenkins/