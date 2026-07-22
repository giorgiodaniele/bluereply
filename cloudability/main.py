import os
import requests
import pandas
from dotenv import load_dotenv

load_dotenv()
pandas.set_option("future.infer_string", False)

API_KEY  = os.getenv("CLOUDABILITY_API_KEY")
BASE_URL = "https://api-eu.cloudability.com"
OUTPUT   = "results"


def fetch(endpoint: str, params: dict = None) -> list:

    #
    # A wrapper arounda an endpoint
    #

    url = f"{BASE_URL}/v3/{endpoint}"
    res = requests.get(
        url, auth=(API_KEY, ""), params=params,
        headers={"Accept": "application/json"},
    )

    if res.status_code != 200:
        print(f"[{endpoint}] Error {res.status_code}: {res.text[:300]}")
        return []

    data = res.json()


    if isinstance(data, dict) and "result" in data:
        data = data["result"]
    if not isinstance(data, list):
        data = [data]

    return data


def save_to_csv(records: list, filename: str):
    frame = pandas.DataFrame(records)
    frame.to_csv(f"{OUTPUT}/{filename}.csv", index=False)


def save_users():
    save_to_csv(fetch("users"), "users")


if __name__ == "__main__":
    if not os.path.exists(OUTPUT):
        os.makedirs(OUTPUT)

    #
    # Save all users
    #
    save_users()