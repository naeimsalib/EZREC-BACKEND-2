import boto3
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="/opt/ezrec-backend/.env")

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

bucket = os.getenv("AWS_S3_BUCKET")
key = "65aa2e2a-e463-424d-b88f-0724bb0bea3a/2025-07-04/raw_b65bcf41-b109-40b1-bb3b-a54707adc239_032903.mp4"

try:
    print("Checking object existence...")
    resp = s3.head_object(Bucket=bucket, Key=key)
    print("Object exists! Metadata:", resp)
except Exception as e:
    print("S3 ERROR:", e)