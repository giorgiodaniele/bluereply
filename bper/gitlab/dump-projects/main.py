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

    projects = server.projects.list(simple=True, order_by="id", sort="asc", get_all=True)
    
    logging.info(f"Found {len(projects)} projects ... Writing on disk!")

    with open("gitlab-repositories.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "id"])
        for project in projects:
            writer.writerow([project.path_with_namespace, project.id])


if __name__ == "__main__":
    main()