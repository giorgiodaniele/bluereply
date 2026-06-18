import logging
import os
import sys

import dotenv
import requests

from concurrent.futures   import ThreadPoolExecutor, as_completed
from owasp_dt             import Client
from owasp_dt.api.project import get_projects
from owasp_dt.api.team    import get_teams


dotenv.load_dotenv()


logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s %(levelname)s %(message)s",
    stream = sys.stdout,
)

logger = logging.getLogger(__name__)


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        logger.error(
            "Required environment variable '%s' is missing",
            name,
        )
        return ""

    return value


DEPENDENCY_TRACK_BASE_URL = get_required_env("DEPENDENCY_TRACK_BASE_URL")
DEPENDENCY_TRACK_API_KEY  = get_required_env("DEPENDENCY_TRACK_API_KEY")
TEAM_NAME                 = get_required_env("TEAM_NAME")


def create_client() -> Client:
    return Client(
        base_url   = DEPENDENCY_TRACK_BASE_URL,
        headers    = {
            "X-Api-Key": DEPENDENCY_TRACK_API_KEY,
        },
        verify_ssl = False,
    )


def get_team(client: Client, team_name: str):
    return next((team for team in get_teams.sync(client=client) if team.name == team_name), None)


def get_projects_list(client: Client):
    return get_projects.sync(client=client)


def assign(project, team) -> None:
    response = requests.put(
        f"{DEPENDENCY_TRACK_BASE_URL}/v1/acl/mapping",
        headers = {
            "X-Api-Key"   : DEPENDENCY_TRACK_API_KEY,
            "Content-Type": "application/json",
        },
        json = {
            "project": str(project.uuid),
            "team"   : str(team.uuid),
        },
        timeout = 30,
        verify  = False,
    )

    response.raise_for_status()


def main() -> None:
    team     = None
    projects = None

    try:
        client = create_client()

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(get_team, client, TEAM_NAME)
            f2 = executor.submit(get_projects_list, client)

            team     = f1.result()
            projects = f2.result()

    except Exception as exc:
        logger.error("Failed to initialize Dependency-Track client: %s", exc)
        return
    
    if team is None:
        logger.error("Team '%s' not found", TEAM_NAME)
        return

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(assign, project, team): project for project in projects
        }

        for future in as_completed(futures):
            project = futures[future]

            try:
                future.result()
                logger.info("Project '%s' successfully assigned to team '%s'", project.name, TEAM_NAME)

            except requests.HTTPError as e:
                if e.response and e.response.status_code == 409:
                    logger.error("Project '%s' is already assigned to team '%s'", project.name, TEAM_NAME)
                else:
                    logger.error("Failed to assign project '%s': %s", project.name, e)
            except Exception as e:
                logger.error("Failed to assign project '%s': %s", project.name, e)
    logger.info("Completed successfully")

if __name__ == "__main__":
    main()