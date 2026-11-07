import os
import boto3


def client(endpoint=None):
    return boto3.client(
        "s3",
        endpoint_url=endpoint or os.environ["S3_ENDPOINT"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name="us-east-1",
    )
