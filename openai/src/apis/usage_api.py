import os
import time
import requests
import dotenv

dotenv.load_dotenv()

API_KEY  = os.getenv("OPENAI_SECRET_KEY")
ORG_ID   = os.getenv("OPENAI_ORG_ID")
BASE_URL = "https://api.openai.com/v1"


#
# Completions: stima di utilizzo dei modelli LLM per
# la generazione di testi, per chatbot, generazione di
# contenuti, automazioni
#

def fetch_usage_completions(start_time, end_time):
    headers = {
        "Authorization"      : f"Bearer {API_KEY}",
        "Content-Type"       : "application/json",
        "OpenAI-Organization": ORG_ID,
    }

    endpoint = "/organization/usage/completions"

    cursor = None

    while True:
        params = {
            "start_time"   : start_time,
            "end_time"     : end_time,
            "group_by"     : ["api_key_id", "model", "project_id"],
            "bucket_width" : "1d",
            "limit"        : 31,
        }

        if cursor:
            params["after"] = cursor

        try:
            res  = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
        except requests.exceptions.HTTPError:
            print("HTTP ERROR:", res.status_code, res.text)
            break
        except requests.exceptions.RequestException:
            continue

        items = data.get("data", [])
        if not items:
            break

        for bucket in items:
            for result in bucket.get("results", []):
                yield {
                    "start_time"               : bucket.get("start_time"),
                    "end_time"                 : bucket.get("end_time"),
                    "project_id"               : result.get("project_id"),
                    "num_model_requests"       : result.get("num_model_requests", 0),
                    "user_id"                  : result.get("user_id"),
                    "api_key_id"               : result.get("api_key_id"),
                    "model"                    : result.get("model"),
                    "batch"                    : result.get("batch"),
                    "service_tier"             : result.get("service_tier"),
                    "input_tokens"             : result.get("input_tokens", 0),
                    "output_tokens"            : result.get("output_tokens", 0),
                    "input_cached_tokens"      : result.get("input_cached_tokens", 0),
                    "input_uncached_tokens"    : result.get("input_uncached_tokens", 0),
                    "input_text_tokens"        : result.get("input_text_tokens", 0),
                    "output_text_tokens"       : result.get("output_text_tokens", 0),
                    "input_cached_text_tokens" : result.get("input_cached_text_tokens", 0),
                    "input_audio_tokens"       : result.get("input_audio_tokens", 0),
                    "input_cached_audio_tokens": result.get("input_cached_audio_tokens", 0),
                    "output_audio_tokens"      : result.get("output_audio_tokens", 0),
                    "input_image_tokens"       : result.get("input_image_tokens", 0),
                    "input_cached_image_tokens": result.get("input_cached_image_tokens", 0),
                    "output_image_tokens"      : result.get("output_image_tokens", 0),
                }

        if not data.get("has_more"):
            break

        cursor = data.get("next_page")
        if not cursor:
            break


#
# Embeddings: stima di utilizzo dei modelli che trasformno
# i testi in vettori
#

def fetch_usage_embeddings(start_time, end_time):
    headers = {
        "Authorization"      : f"Bearer {API_KEY}",
        "Content-Type"       : "application/json",
        "OpenAI-Organization": ORG_ID,
    }

    endpoint = "/organization/usage/embeddings"

    cursor = None

    while True:
        params = {
            "start_time"   : start_time,
            "end_time"     : end_time,
            "group_by"     : ["api_key_id", "model", "project_id"],
            "bucket_width" : "1d",
            "limit"        : 31,
        }

        if cursor:
            params["after"] = cursor

        try:
            res  = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
        except requests.exceptions.HTTPError:
            print("HTTP ERROR:", res.status_code, res.text)
            break
        except requests.exceptions.RequestException:
            continue

        items = data.get("data", [])
        if not items:
            break

        for bucket in items:
            for result in bucket.get("results", []):
                yield {
                    "start_time"            : bucket.get("start_time"),
                    "end_time"              : bucket.get("end_time"),
                    "project_id"            : result.get("project_id"),
                    "num_model_requests"    : result.get("num_model_requests", 0),
                    "user_id"               : result.get("user_id"),
                    "api_key_id"            : result.get("api_key_id"),
                    "model"                 : result.get("model"),
                    "batch"                 : result.get("batch"),
                    "service_tier"          : result.get("service_tier"),
                    "input_tokens"          : result.get("input_tokens", 0),
                    "input_cached_tokens"   : result.get("input_cached_tokens", 0),
                    "input_uncached_tokens" : result.get("input_uncached_tokens", 0),
                }

        if not data.get("has_more"):
            break

        cursor = data.get("next_page")
        if not cursor:
            break


#
# Images: stima di utilizzo dei modelli che generano oppure
# modificano delle immagini
#

def fetch_usage_images(start_time, end_time):
    headers = {
        "Authorization"      : f"Bearer {API_KEY}",
        "Content-Type"       : "application/json",
        "OpenAI-Organization": ORG_ID,
    }

    endpoint = "/organization/usage/images"

    cursor = None

    while True:
        params = {
            "start_time"   : start_time,
            "end_time"     : end_time,
            "group_by"     : ["api_key_id", "model", "project_id"],
            "bucket_width" : "1d",
            "limit"        : 31,
        }

        if cursor:
            params["after"] = cursor

        try:
            res  = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
        except requests.exceptions.HTTPError:
            print("HTTP ERROR:", res.status_code, res.text)
            break
        except requests.exceptions.RequestException:
            continue

        items = data.get("data", [])
        if not items:
            break

        for bucket in items:
            for result in bucket.get("results", []):
                yield {
                    "start_time"            : bucket.get("start_time"),
                    "end_time"              : bucket.get("end_time"),
                    "project_id"            : result.get("project_id"),
                    "num_model_requests"    : result.get("num_model_requests", 0),
                    "user_id"               : result.get("user_id"),
                    "api_key_id"            : result.get("api_key_id"),
                    "model"                 : result.get("model"),
                    "input_tokens"          : result.get("input_tokens", 0),
                    "input_cached_tokens"   : result.get("input_cached_tokens", 0),
                    "input_uncached_tokens" : result.get("input_uncached_tokens", 0),
                    "output_image_tokens"   : result.get("output_image_tokens", 0),
                }

        if not data.get("has_more"):
            break

        cursor = data.get("next_page")
        if not cursor:
            break


#
# Audio speeches (TTS): stima di utilizzo dei modelli che generano
# a partire dal testo una traccia audio
#

def fetch_usage_audio_speech(start_time, end_time):
    headers = {
        "Authorization"      : f"Bearer {API_KEY}",
        "Content-Type"       : "application/json",
        "OpenAI-Organization": ORG_ID,
    }

    endpoint = "/organization/usage/audio_speeches"

    cursor = None

    while True:
        params = {
            "start_time"   : start_time,
            "end_time"     : end_time,
            "group_by"     : ["api_key_id", "model", "project_id"],
            "bucket_width" : "1d",
            "limit"        : 31,
        }

        if cursor:
            params["after"] = cursor

        try:
            res  = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
        except requests.exceptions.HTTPError:
            print("HTTP ERROR:", res.status_code, res.text)
            break
        except requests.exceptions.RequestException:
            continue

        items = data.get("data", [])
        if not items:
            break

        for bucket in items:
            for result in bucket.get("results", []):
                yield {
                    "start_time"            : bucket.get("start_time"),
                    "end_time"              : bucket.get("end_time"),
                    "project_id"            : result.get("project_id"),
                    "num_model_requests"    : result.get("num_model_requests", 0),
                    "user_id"               : result.get("user_id"),
                    "api_key_id"            : result.get("api_key_id"),
                    "model"                 : result.get("model"),
                    "input_audio_tokens"    : result.get("input_audio_tokens", 0),
                    "output_audio_tokens"   : result.get("output_audio_tokens", 0),
                }

        if not data.get("has_more"):
            break

        cursor = data.get("next_page")
        if not cursor:
            break


#
# Audio transcription (STT): stima di utilizzo dei modelli che generano
# a partire da una traccia audio un testo
#

def fetch_usage_audio_transcriptions(start_time, end_time):
    headers = {
        "Authorization"      : f"Bearer {API_KEY}",
        "Content-Type"       : "application/json",
        "OpenAI-Organization": ORG_ID,
    }

    endpoint = "/organization/usage/audio_transcriptions"

    cursor = None

    while True:
        params = {
            "start_time"   : start_time,
            "end_time"     : end_time,
            "group_by"     : ["api_key_id", "model", "project_id"],
            "bucket_width" : "1d",
            "limit"        : 31,
        }

        if cursor:
            params["after"] = cursor

        try:
            res  = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
        except requests.exceptions.HTTPError:
            print("HTTP ERROR:", res.status_code, res.text)
            break
        except requests.exceptions.RequestException:
            continue

        items = data.get("data", [])
        if not items:
            break

        for bucket in items:
            for result in bucket.get("results", []):
                yield {
                    "start_time"            : bucket.get("start_time"),
                    "end_time"              : bucket.get("end_time"),
                    "project_id"            : result.get("project_id"),
                    "num_model_requests"    : result.get("num_model_requests", 0),
                    "user_id"               : result.get("user_id"),
                    "api_key_id"            : result.get("api_key_id"),
                    "model"                 : result.get("model"),
                    "input_audio_tokens"    : result.get("input_audio_tokens", 0),
                }

        if not data.get("has_more"):
            break

        cursor = data.get("next_page")
        if not cursor:
            break