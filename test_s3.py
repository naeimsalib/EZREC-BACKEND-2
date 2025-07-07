# Save this as test_s3.py
import boto3, os
from dotenv import load_dotenv
load_dotenv("/opt/ezrec-backend/.env")
s3 = boto3.client("s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"))
bucket = os.getenv("AWS_S3_BUCKET")
key = "YOUR/REAL/VIDEO/KEY.mp4"
try:
    s3.head_object(Bucket=bucket, Key=key)
    print("Object exists and credentials work!")
except Exception as e:
    print("S3 ERROR:", e)