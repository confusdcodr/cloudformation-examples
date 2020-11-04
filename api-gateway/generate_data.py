import json
import os
import random
import urllib.parse
import uuid

import boto3

sqs = boto3.client("sqs")
s3 = boto3.client("s3")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")


def bucket_listing(bucket):
    """
    Takes a S3 bucket and gets a listing of the files within

    Args:
        bucket (String): Bucket to get file listing for

    Returns:
        list(dict): Key and size of every object in the s3 bucket
    """
    response = s3.list_objects(Bucket=bucket)

    file_listing = []
    for file_data in response["Contents"]:
        data = {"filename": file_data["Key"], "size": file_data["Size"]}
        file_listing.append(data)

    print("File listing: {}".format(file_listing))
    return file_listing


def copy_to_bucket(src_bucket, dest_bucket, filename):
    """
    Copy file from source bucket to destination bucket

    Args:
        src_bucket (string): source s3 bucket to copy file from
        dest_bucket (string): destination s3 bucket to copy file to
        filename (string): name of the file within the source bucket to copy over
    """
    copy_source = {"Bucket": src_bucket, "Key": filename}

    file_extension = os.path.splitext(filename)[1]
    random_name = "{}{}".format(uuid.uuid1().hex, file_extension)
    s3.copy(copy_source, dest_bucket, random_name)


def delete_message(sqs_url, receipt_handle):
    """
    Remove message from sqs queue

    Args:
        sqs_url (string): URL for the SQS Queue
        receipt_handle (string): The id of a specific instance of a message
    """
    sqs.delete_message(QueueUrl=sqs_url, ReceiptHandle=receipt_handle)


def main(src_bucket, dest_bucket, num_files=10, size="M"):
    file_listing = bucket_listing(src_bucket)
    size_difference = num_files - len(file_listing)

    # requested number of files are greater than files in bucket
    if size_difference > 0:
        for _ in range(size_difference):
            file_listing.append(random.choice(file_listing))
    # requested number of files are less than files in bucket
    elif size_difference < 0:
        for _ in range(abs(size_difference)):
            file_listing.pop()

    # shuffle up the files
    random.shuffle(file_listing)

    for i in file_listing:
        print("Copying {} from {} to {}".format(i["filename"], src_bucket, dest_bucket))
        copy_to_bucket(src_bucket, dest_bucket, i["filename"])


def lambda_handler(event, context):
    print("Received event: {}".format(event))

    message = event["Records"][0]
    receipt_handle = (message["receiptHandle"])
    params = urllib.parse.parse_qs(message["body"])

    src_bucket = params["src_bucket"][0]
    dest_bucket = params["dest_bucket"][0]

    num_files = 10
    try:
        num_files = int(params.get("num_files")[0])
    except:
        print("Either didn't provide or failed to provide a valid num_files argument. Defaulting to 10")

    size = "M"
    try:
        size = params.get("size")[0]
    except:
        print("Either didn't provide or failed to provide a valid size argument. Defaulting to M")

    main(src_bucket, dest_bucket, num_files, size)
    delete_message(SQS_QUEUE_URL, receipt_handle)
