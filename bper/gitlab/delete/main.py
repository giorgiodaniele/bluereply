#!/usr/bin/env python3

import csv
import os
import gitlab
import dotenv
import sys
import logging

dotenv.load_dotenv()

GITLAB_SERVER = os.getenv("GITLAB_SERVER")
GITLAB_TOKEN  = os.getenv("GITLAB_TOKEN")
INPUT_FILE    = "resources.csv"

#
# Python will not trust BPER SSL certificate, so import it explicitly
#
os.environ["REQUESTS_CA_BUNDLE"] = "../../bperROOTCA.crt"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s - %(message)s")

def connect_server(url: str, private_token: str) -> gitlab.Gitlab | str:
    try:
        gl = gitlab.Gitlab(url=url, private_token=private_token, ssl_verify=False, keep_base_url=True)
        gl.auth()
        return gl
    except Exception as e:
        return f"Failed to connect to Gitlab: {e}"

def read_resources(filename: str) -> list[str]:
    with open(filename, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [f"{record['namespace'].strip()}/{record['component'].strip()}" for record in reader]


def main():
    
    server = connect_server(url=GITLAB_SERVER, private_token=GITLAB_TOKEN)
    if type(server) == str:
        logging.error(server)
        sys.exit(1)

    resources = read_resources(INPUT_FILE)
    for resource in resources:
        try:
            # Check if project exists. In case of the project not existing, 
            # GitLab will throw an exception and nothing will be deleted
            # If the project exists, it will be deleted
            server.projects.get(resource)
            logging.info(f"Project exists: {resource}")
            server.projects.delete(resource)
            logging.info(f"Deleted project {resource}")
        except Exception as e:
            logging.error(f"Failed to delete project '{resource}': {e}")


if __name__ == "__main__":
    main()