import csv
import os
import gitlab

from   datetime import datetime


GITLAB_URL   = "http://172.116.63.237"
GITLAB_TOKEN = "glpat-1XAvxpjvx-QQPt_cGg51"

# Connessione
gl = gitlab.Gitlab(url=GITLAB_URL, private_token=GITLAB_TOKEN, keep_base_url=True)
gl.auth()

print(f"Connected as {gl.user.username}")

projects = gl.projects.list(get_all=True, order_by="id", sort="asc")
rows     = []

TECH_FILES = {
    "pom.xml"         : "Java Maven",
    "build.gradle"    : "Java Gradle",
    "build.gradle.kts": "Java Gradle Kotlin",
    "package.json"    : "NodeJS",
    "requirements.txt": "Python",
    "pyproject.toml"  : "Python",
    "Pipfile"         : "Python",
    "go.mod"          : "Go",
    "Cargo.toml"      : "Rust",
    "composer.json"   : "PHP",
    "Gemfile"         : "Ruby"
}

for p in projects:

    project   = gl.projects.get(p.id)
    languages = project.languages()

    try:
        default_branch = project.default_branch
    except Exception:
        default_branch = ""

    #
    # Branch
    #

    try:
        branches = project.branches.list(get_all=True)
        branch_count = len(branches)
    except Exception:
        branch_count = 0


    #
    # Score
    #

    score = 0
    if not project.archived:
        score += min(branch_count, 20)

    rows.append({

        "score"         : score,
        "id"            : project.id,
        "name"          : project.name,
        "path"          : project.path_with_namespace,
        "languages"     : ", ".join(languages.keys()),
        "branch_count"  : branch_count,
        "visibility"    : project.visibility,
        "default_branch": default_branch,
        "archived"      : project.archived,
        "empty_repo"    : project.empty_repo,
        "last_activity" : project.last_activity_at,
        "created_at"    : project.created_at,
        "web_url"       : project.web_url

    })

rows.sort(key=lambda r: r["score"], reverse=True)

with open("inventory.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Exported {len(rows)} repositories to inventory.csv")