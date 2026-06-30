import os
import json
import uuid
import boto3
import pandas as pd

from datetime import datetime, timedelta


def get_report_period(now: datetime) -> str:
    start = now.replace(day=1)
    next_month = (start + timedelta(days=32)).replace(day=1)
    return f"{start.strftime('%Y%m%d')}-{next_month.strftime('%Y%m%d')}"


def to_parquet(csv_path: str) -> str:
    parquet_path = csv_path.replace(".csv", ".parquet")
    pd.read_csv(csv_path).to_parquet(parquet_path, engine="pyarrow", compression="snappy")
    return parquet_path


def upload_to_s3(s3_client, local_path: str, bucket: str, s3_key: str, content_type: str) -> None:
    s3_client.upload_file(
        Filename=local_path,
        Bucket=bucket,
        Key=s3_key,
        ExtraArgs={"ContentType": content_type},
    )


def aws_upload(csv_path: str) -> None:
    
    s3              = boto3.client("s3")
    bucket          = os.getenv("S3_BUCKET_NAME")
    manifest_prefix = os.getenv("CLOUDABILITY_MANIFEST_PREFIX")
    now             = datetime.utcnow()
    
    # Prepare paths and keys
    parquet_path    = to_parquet(csv_path)
    filename        = os.path.basename(parquet_path)
    report_period   = get_report_period(now)
    epoch           = str(int(now.timestamp()))
    base_prefix     = f"focus/openai/OpenAI/{report_period}/{epoch}/"
    data_key        = f"{base_prefix}{filename}"
    manifest_key    = f"{base_prefix}{manifest_prefix}-Manifest.json"
    
    # Build and save manifest
    manifest = {
        "compression"       : "SNAPPY",
        "content_type"      : "Parquet",
        "report_id"         : str(uuid.uuid4()),
        "root_dir"          : bucket,
        "all_report_keys"   : [data_key],
        "updated_at"        : now.replace(microsecond=0).isoformat() + "Z",
        "focus_version"     : os.getenv("FOCUS_VERSION"),
    }
    manifest_path = parquet_path.replace(".parquet", "-Manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Upload to S3
    try:
        upload_to_s3(s3, parquet_path, bucket, data_key, "application/octet-stream")
        upload_to_s3(s3, manifest_path, bucket, manifest_key, "application/json")
    except Exception as e:
        raise RuntimeError(f"S3 upload failed: {e}") from e