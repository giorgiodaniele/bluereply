import os
import time
import requests
import dotenv

dotenv.load_dotenv()

API_KEY = os.getenv("OPENAI_SECRET_KEY")
API_URL = "https://api.openai.com/v1/organization/costs"

def fetch_costs_by_project(start_time, end_time):

    #
    #
    # OpenAI consente di recuperare i costi associati ai vari progetti
    # oppure ai vari utenti. Si definisce start_time ed end_time gli
    # indici di inizio e fine della finestra temporale dentro alla quale
    # ricercare i costi
    #
    # E possibile raggruppare i costi sia per project_id che per line_item
    #
    #

    headers = {"Authorization": f"Bearer {API_KEY}"}
    params  = {
        "start_time" : start_time,
        "end_time"   : end_time,
        "limit"      : 50,
        "group_by"   : ["project_id", "line_item"]
    }

    while True:
        try:
            response = requests.get(API_URL, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            time.sleep(2)
            continue
        
        #
        # Each bucket is associated to a day. Within that bucket
        # there are info about project_id and line_item that have
        # generated costs. Each bucket may contain dozen of items
        #
        for bucket in data.get("data", []):
            results = bucket.get("results", [])
            for result in results:
                yield {
                    "start_time"        : bucket["start_time"],
                    "end_time"          : bucket["end_time"],
                    "amount_value"      : result["amount"]["value"],
                    "amount_currency"   : result["amount"]["currency"],
                    "line_item"         : result["line_item"],
                    "project_id"        : result.get("project_id", None),
                    "organization_id"   : result.get("organization_id",   None),
                    "organization_name" : result.get("organization_name", None),
                    "user_id"           : result.get("user_id", None),
                }
        if not data.get("has_more"):
            break
        params["page"] = data.get("next_page")

        #
        #
        # Ogni riga riporta i dettagli di costi di un particolare 
        # modello OpenAI nel bucket
        #
        #
        #

def fetch_costs_by_user(start_time, end_time):

    #
    #
    # OpenAI consente di recuperare i costi associati ai vari progetti
    # oppure ai vari utenti. Si definisce start_time ed end_time gli
    # indici di inizio e fine della finestra temporale dentro alla quale
    # ricercare i costi
    #
    # E possibile raggruppare i costi sia per project_id che per line_item
    #
    #

    headers = {"Authorization": f"Bearer {API_KEY}"}
    params  = {
        "start_time" : start_time,
        "end_time"   : end_time,
        "limit"      : 50,
        "group_by"   : ["user_id"]
    }

    while True:
        try:
            response = requests.get(API_URL, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException:
            time.sleep(2)
            continue
        
        #
        # Each bucket is associated to a day. Within that bucket
        # there are info about project_id and line_item that have
        # generated costs. Each bucket may contain dozen of items
        #
        for bucket in data.get("data", []):
            results = bucket.get("results", [])
            for result in results:
                yield {
                    "start_time"      : bucket["start_time"],
                    "end_time"        : bucket["end_time"],
                    "amount_value"    : result["amount"]["value"],
                    "amount_currency" : result["amount"]["currency"],
                    "line_item"       : result["line_item"],
                    "project_id"      : result.get("project_id", None),
                    "organization_id" : result.get("organization_id", None),
                    "user_id"         : result.get("user_id", None),
                    "user_email"      : result.get("user_email", None),
                }
        if not data.get("has_more"):
            break
        params["page"] = data.get("next_page")

        #
        #
        # Ogni riga riporta i dettagli di costi di un particolare 
        # utente OpenAI nel bucket
        #
        #
        #