import json
import logging
import os
import time
from   pathlib import Path

import dotenv
import gitlab
import urllib3
import requests

dotenv.load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#
# Remote services
#
GITLAB_URL    = os.getenv("GITLAB_URL")
GITLAB_TOKEN  = os.getenv("GITLAB_API_TOKEN")
SONAR_URL     = os.getenv("SONAR_URL")
SONAR_TOKEN   = os.getenv("SONAR_API_TOKEN", "").strip()

#
# Output files
#
GITLAB_OUTPUT = Path("projects_gitlab.json")
SONAR_OUTPUT  = Path("projects_soqube.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-2s %(filename)s - %(message)s",
    handlers=[
        logging.FileHandler("main.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

def gitlab_projects():
    gl       = gitlab.Gitlab(url=GITLAB_URL, private_token=GITLAB_TOKEN, ssl_verify=False)
    projects = gl.projects.list(membership=True, simple=True, iterator=True, per_page=100)

    result = []
    for i, p in enumerate(projects, 1):
        log.info("[%d] %s", i, p.path_with_namespace)
        branches = [b.name for b in p.branches.list(iterator=True, per_page=100)]
        result.append({
            "id"      : p.id,
            "name"    : p.name,
            "path"    : p.path_with_namespace,
            "branches": branches,
        })

    GITLAB_OUTPUT.write_text(json.dumps(result, indent=4), encoding="utf-8")
    log.info("saved %d projects to %s", len(result), GITLAB_OUTPUT)

def sonarqube_projects():
    result    = []
    page      = 1
    page_size = 500
    while True:
        r = requests.get(
            f"{SONAR_URL}/api/components/search",
            params={"qualifiers": "TRK", "ps": page_size, "p": page},
            auth=(SONAR_TOKEN, ""),
            verify=False,
        )
        r.raise_for_status()
        data       = r.json()
        components = data.get("components", [])
        for c in components:
            result.append({
                "key" : c.get("key"),
                "name": c.get("name"),
            })
        paging = data.get("paging", {})
        total  = paging.get("total", 0)
        log.info("fetched page %d (%d/%d)", page, len(result), total)
        if len(result) >= total or not components:
            break
        page += 1
    log.write_text(json.dumps(result, indent=4), encoding="utf-8")
    log.info("saved %d projects to %s", len(result))
    return result

if __name__ == "__main__":
    
    ts = time.perf_counter()
    gitlab_projects()
    log.info("elapsed: %.2fs", time.perf_counter() - ts)

    # sonarqube_projects()

    # with open("gitlab_projects.json", "r", encoding="utf-8") as f:
    #     data = json.load(f)

    # #
    # # Write on disk which project do exists in SonarQube
    # #
    # full_names = []
    # with open("sonarqube_projects.txt", "w", encoding="utf-8") as f:
    #     for repo in data:
    #         for branch in repo['branches']:
    #             name  = f"{repo['name']}-{branch}".replace("/", "-")
    #             valid = is_sonarqube_valid(name)
    #             line  = f"{name} {valid}"
    #             print(line)
    #             f.write(line + '\n')