import os
import json
import uuid
import boto3
import botocore
import pandas as pd
import logging
from   datetime        import datetime, timedelta

logger = logging.getLogger(__name__)

#
# Utils function
#

def get_report_period(now: datetime) -> str:
    #
    # Return the billing period string 'YYYYMMDD-YYYYMMDD' spanning the current month
    #
    start      = now.replace(day=1)
    next_month = (start + timedelta(days=32)).replace(day=1)
    return f"{start.strftime('%Y%m%d')}-{next_month.strftime('%Y%m%d')}"

def convert_csv_to_parquet(csv_path: str) -> str:
    logger.info(f"Converting file | input={csv_path}")

    frame   = pd.read_csv(csv_path)
    parquet = csv_path.replace(".csv", ".parquet")
    frame.to_parquet(parquet, engine="pyarrow", compression="snappy")

    logger.info(f"Parquet file created | path={parquet}")
    return parquet


def generate_s3_key(report_period: str, epoch: str, filename: str, manifest_prefix: str) -> tuple[str, str]:

    #
    # Generate the key by which adddressing the S3 bucket
    #

    base_prefix  = f"focus/openai/OpenAI/{report_period}/{epoch}/"
    data_key     = f"{base_prefix}{filename}"
    manifest_key = f"{base_prefix}{manifest_prefix}-Manifest.json"
    return data_key, manifest_key


def build_manifest(bucket_name: str, data_key: str, now: datetime, parquet_path: str) -> tuple[dict, str]:
    #
    # Generate the manifest to be associated with data and save it to disk
    #
    manifest = {
        "compression"     : "SNAPPY",
        "content_type"    : "Parquet",
        "report_id"       : str(uuid.uuid4()),
        "root_dir"        : bucket_name,
        "all_report_keys" : [data_key],
        "updated_at"      : now.replace(microsecond=0).isoformat() + "Z",
        "focus_version"   : os.getenv("FOCUS_VERSION"),
    }
    local_manifest_path = parquet_path.replace(".parquet", "-Manifest.json")
    with open(local_manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest saved locally | path={local_manifest_path}")
    return manifest, local_manifest_path


#
# Functions for uploading data to S3 bucket
#

def upload_data(s3_client, parquet_path: str, bucket_name: str, data_key: str) -> None:
    
    #
    # Upload the data file (.parquet)
    #
    s3_client.upload_file(
        Filename=parquet_path,
        Bucket=bucket_name,
        Key=data_key,
        ExtraArgs={"ContentType": "application/octet-stream"},
    )

def upload_meta(s3_client, manifest_path: str, bucket_name: str, manifest_key: str) -> None:

    #
    # Upload the meta file (.json)
    #
    s3_client.upload_file(
        Filename=manifest_path,
        Bucket=bucket_name,
        Key=manifest_key,
        ExtraArgs={"ContentType": "application/json"},
    )

#
# Main function to upload toward AWS S3 bucket
# 

def aws_upload(file_path: str) -> None:
    s3              = boto3.client("s3")
    bucket_name     = os.getenv("S3_BUCKET_NAME")
    manifest_prefix = os.getenv("CLOUDABILITY_MANIFEST_PREFIX")

    now           = datetime.utcnow()
    report_period = get_report_period(now)
    epoch         = str(int(now.timestamp()))

    parquet_path = convert_csv_to_parquet(file_path)
    filename     = os.path.basename(parquet_path)

    data_key, meta_key = generate_s3_key(report_period, epoch, filename, manifest_prefix)
    logger.info(f"S3 destination | bucket={bucket_name}")
    logger.info(f"S3 data key    | {data_key}")
    logger.info(f"S3 manifest key| {meta_key}")

    manifest, manifest_path = build_manifest(bucket_name, data_key, now, parquet_path)

    try:
        upload_data(s3, parquet_path,  bucket_name, data_key)
        upload_meta(s3, manifest_path, bucket_name, meta_key)
        logger.info("FOCUS upload completed successfully")
    except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
        logger.error(f"AWS error | {e}")
        raise RuntimeError(f"AWS error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error | {e}")
        raise RuntimeError(f"Unexpected error: {e}")