#!/usr/bin/env python3
__author__      = "Giorgio Daniele Luppina"
__version__     = "1.0"
__description__ = "Import job folder exported into a new Jenkins installation"

import argparse
import logging
import os
import jenkins
from   concurrent.futures import ThreadPoolExecutor, as_completed

LOG_FORMAT     = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT    = "%Y-%m-%d %H:%M:%S"
MAX_WORKERS    = 10

def config_logger(level=logging.INFO):
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger("jenkins.import")    
os.environ["REQUESTS_CA_BUNDLE"] = "res/bperROOTCA.crt"

def import_jobs(files: list, server: jenkins.Jenkins, base_dir: str, max_workers=MAX_WORKERS):

    folders   = []
    pipelines = []

    for file in files:
        filename: str = os.path.basename(file)
        if filename.startswith("__IS_A_FOLDER__") and not os.path.isdir(file):
            folders.append(file)
        elif os.path.isdir(file):
            for item in os.listdir(file):
                path = os.path.join(file, item)
                if os.path.isfile(path) and path.endswith(".xml"):
                    pipelines.append(path)
    try:
        jobs = {job['fullname'] for job in server.get_jobs()}
    except Exception:
        jobs = set()

    # folders   = []
    # pipelines = []

    # for root, _, filenames in os.walk(base_dir):

    #     for filename in filenames:
    #         path = os.path.join(root, filename)
    #         if filename.startswith("__IS_A_FOLDER__"):
    #             folders.append(path)
    #         elif filename.endswith(".xml"):
    #             pipelines.append(path)

    #
    # Helper function to create folder jobs
    #
    def __create_folders(file):
        fullname = os.path.relpath(file, base_dir)
        fullname = os.path.splitext(fullname)[0].replace("__IS_A_FOLDER__", "").replace("\\", "/")
        try:
            with open(file, 'r') as file:
                config = file.read()
        except Exception:
            return

        if fullname in jobs:
            logger.info(f"Cartella {fullname} esiste già...")
            return

        try:
            server.create_job(fullname, config)
            logger.info(f"Cartella {fullname} creata!")
        except Exception:
            pass

    #
    # Helper function to create pipeline jobs
    #
    def __create_pipelines(file):
        rel_path = os.path.relpath(file, base_dir)
        fullname = rel_path[:-4].replace("__", "/").replace("\\", "/")
        try:
            with open(file, 'r') as file:
                config = file.read()
        except Exception:
            return

        if fullname in jobs:
            logger.info(f"Pipeline {fullname} esiste già...")
            return

        try:
            server.create_job(fullname, config)
            logger.info(f"Pipeline {fullname} creata!")
        except Exception:
            pass

    #
    # Create folders in parallel
    #
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(__create_folders, f) for f in sorted(folders)]
        for _ in as_completed(futures):
            continue

    #
    # Create pipelines in parallel
    #
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(__create_pipelines, f) for f in sorted(pipelines)]
        for _ in as_completed(futures):
            continue


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--url",      help="URL Jenkins", required=True)
    parser.add_argument("--username", help="Username",    required=True)
    parser.add_argument("--password", help="Password",    required=True)
    parser.add_argument("--path",     help="Percorso al file system da importare", required=True)

    args = parser.parse_args()

    if not os.path.isdir(args.path):
        logger.error(f"Il percorso {args.path} non è una cartella!")
        raise Exception

    server = jenkins.Jenkins(args.url, args.username, args.password, timeout=60)
    files  = [os.path.join(args.path, f) for f in os.listdir(args.path)]
    import_jobs(files=files, server=server, base_dir=args.path)

if __name__ == "__main__":
    config_logger()
    main()

# python import.py --username <> --password <> --url http://172.16.63.239/jenkins/ AcquisizioniDocumenti