import os
import time
import requests
import dotenv

dotenv.load_dotenv()

API_KEY = os.getenv("OPENAI_SECRET_KEY")
ORG_ID  = os.getenv("OPENAI_ORGANIZATION_ID")

def fetch_projects():
    url = "https://api.openai.com/v1/organization/projects"

    headers = {
        "Authorization"         : f"Bearer {API_KEY}",
        "Content-Type"          : "application/json",
        "OpenAI-Organization"   : ORG_ID,
    }

    params = {"limit": 100}
    cursor = None

    while True:
        query = params.copy()
        if cursor:
            query["after"] = cursor

        response = requests.get(url, headers=headers, params=query)
        response.raise_for_status()

        data = response.json()
        items = data.get("data", [])

        for project in items:
            yield {
                "project_id"         : project.get("id"),
                "project_name"       : project.get("name"),
                "project_created_at" : project.get("created_at"),
            }

        if not data.get("has_more") or not items:
            break

        cursor = items[-1].get("id")
        if not cursor:
            break


def fetch_keys_project(project_id):
    url = f"https://api.openai.com/v1/organization/projects/{project_id}/api_keys"

    headers = {
        "Authorization"         : f"Bearer {API_KEY}",
        "Content-Type"          : "application/json",
        "OpenAI-Organization"   : ORG_ID,
    }

    params = {"limit": 100}
    cursor = None

    while True:
        query = params.copy()
        if cursor:
            query["after"] = cursor

        response = requests.get(url, headers=headers, params=query)
        response.raise_for_status()

        data = response.json()
        items = data.get("data", [])

        for key in items:
            yield key

        if not data.get("has_more") or not items:
            break

        cursor = items[-1].get("id")
        if not cursor:
            break


def fetch_all_project_keys():
    for project in fetch_projects():
        project_id = project["project_id"]

        for key in fetch_keys_project(project_id):
            owner = key.get("owner", {})
            user  = owner.get("user", {})

            yield {
                # project
                "project_id"         : project_id,
                "project_name"       : project["project_name"],
                "project_created_at" : project["project_created_at"],

                # key
                "key_id"            : key.get("id"),
                "key_name"          : key.get("name"),
                "key_created_at"    : key.get("created_at"),

                # user
                "user_id"   : user.get("id"),
                "user_name" : user.get("name"),
                "user_email": user.get("email"),
            }