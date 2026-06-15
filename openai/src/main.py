import os
import logging
import pandas as pd

from utils import *
from apis.usage_api  import *
from apis.key_api    import *
from apis.cost_api   import *
from cloud.aws       import *

#
# Logger setting
#
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("app.log", encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)


#
# Global variables
#
OPENAI_ORG_ID   = os.getenv("OPENAI_ORGANIZATION_ID")
OPENAI_ORG_NAME = os.getenv("OPENAI_ORGANIZATION_NAME")


def save_csv(data, filename, output_dir):
    dataframe = pd.DataFrame(data)
    file_path = os.path.join(output_dir, filename)

    dataframe.to_csv(file_path, index=False)

    logger.info(f"File CSV salvato | path={file_path} | righe={len(dataframe)}")

    return dataframe


def main():
    try:
        logger.info("Avvio esecuzione script raccolta dati OpenAI")

        #
        # Define timespan and generate the folder where output
        # is going to be saved
        #
        ts, te = get_time_horizon()

        base_dir   = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "..", f"{ts}_{te}")
        output_dir = os.path.abspath(output_dir)

        os.makedirs(output_dir, exist_ok=True)

        #
        # Fetch all existing projects
        #
        logger.info("Recupero elenco progetti OpenAI")
        projects = fetch_projects()
        projects_frame = save_csv(projects, "projects.csv", output_dir)

        #
        # Fetch all existing keys
        #
        logger.info("Recupero chiavi API associate ai progetti")
        keys = list(fetch_all_project_keys())
        keys_frame = save_csv(keys, "keys.csv", output_dir)

        #
        # Fetch costs by project
        #
        logger.info("Recupero costi aggregati per progetto")
        project_costs = fetch_costs_by_project(ts, te)
        project_costs_frame = save_csv(project_costs, "project_cost.csv", output_dir)

        #
        # Fetch costs by user
        #
        logger.info("Recupero costi aggregati per utente")
        user_costs = fetch_costs_by_user(ts, te)
        user_costs_frame = save_csv(user_costs, "user_cost.csv", output_dir)

        #
        # Filtro utenti validi (con chiave associata)
        #
        valid_user_ids        = {record["user_id"] for record in keys if record.get("user_id")}
        filtered_user_cost_df = user_costs_frame[user_costs_frame["user_id"].isin(valid_user_ids)]

        #
        # Generazione dataset FOCUS
        #
        logger.info("Generazione dataset FOCUS in corso")

        focus_frame = generate_focus(
            frame=filtered_user_cost_df,
            start_time=ts,
            end_time=te,
            project_id=None,
            project_name=None,
            organization_id=OPENAI_ORG_ID,
            organization_name=OPENAI_ORG_NAME
        )

        focus_file_path = os.path.join(output_dir, "focus.csv")
        focus_frame.to_csv(focus_file_path, index=False)

        logger.info(f"File FOCUS generato | path={focus_file_path} | righe={len(focus_frame)}")
        logger.info(f"Range temporale dataset FOCUS | min={focus_frame['BillingPeriodStart'].min()} | max={focus_frame['BillingPeriodEnd'].max()}")

        #
        # Upload verso S3
        #
        aws_upload(focus_file_path)

        logger.info("Upload dataset FOCUS verso S3 completato")

        #
        # (Opzionale) Usage API
        #
        # save_csv(fetch_usage_completions(ts, te),          "usage_completions.csv", output_dir)
        # save_csv(fetch_usage_embeddings(ts, te),           "usage_embeddings.csv", output_dir)
        # save_csv(fetch_usage_images(ts, te),               "usage_images.csv", output_dir)
        # save_csv(fetch_usage_audio_speech(ts, te),         "usage_audio_speech.csv", output_dir)
        # save_csv(fetch_usage_audio_transcriptions(ts, te), "usage_audio_transcriptions.csv", output_dir)

        logger.info("Esecuzione script completata con successo")

    except Exception:
        logger.exception("Errore durante l'esecuzione dello script principale")
        raise


if __name__ == "__main__":
    main()