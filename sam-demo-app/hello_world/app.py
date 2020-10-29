import argparse
import collections
import json
import logging
import multiprocessing
import os
import random
import uuid

import boto3

DEFAULT_LOG_LEVEL = logging.INFO
LOG_LEVELS = collections.defaultdict(
    lambda: DEFAULT_LOG_LEVEL,
    {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
    },
)

# Lambda initializes a root logger that needs to be removed in order to set a
# different logging config
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logging.basicConfig(
    format="%(asctime)s.%(msecs)03dZ [%(name)s][%(levelname)-5s]: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=LOG_LEVELS[os.environ.get("LOG_LEVEL", "").lower()],
)
log = logging.getLogger(__name__)


s3_client = boto3.client("s3")


def get_args():
    """
    Processes arguments passed on the command line

    Returns:
        dict: arguments passed on the command line
    """
    # parse args
    arg_parser = argparse.ArgumentParser(
        description="Generate Test Data for Data Lake Processing"
    )
    req = arg_parser.add_argument_group("required arguments")
    req.add_argument(
        "-s",
        "--src-bucket",
        required=True,
        action="store",
        type=str,
        help="S3 bucket for seed data",
    )
    req.add_argument(
        "-d",
        "--dest-bucket",
        required=True,
        action="store",
        type=str,
        help="S3 bucket for to send test data to",
    )
    arg_parser.add_argument(
        "-n",
        "--num-files",
        type=int,
        action="store",
        default="10",
        help="Number of files to send. default=10",
    )

    temp_args = arg_parser.parse_args()
    args = {
        "src_bucket": temp_args.src_bucket,
        "dest_bucket": temp_args.dest_bucket,
        "num_files": temp_args.num_files,
    }

    return args


def bucket_listing(bucket):
    """
    Takes a S3 bucket and gets a listing of the files within

    Args:
        bucket (String): Bucket to get file listing for

    Returns:
        list(dict): Key and size of every object in the s3 bucket
    """
    response = s3_client.list_objects(Bucket=bucket)

    file_listing = []
    for file_data in response["Contents"]:
        data = {"filename": file_data["Key"], "size": file_data["Size"]}
        file_listing.append(data)

    log.debug("File listing: {}".format(file_listing))
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
    s3_client.copy(copy_source, dest_bucket, random_name)


def worker(data):
    log.info(
        "Copying {} from {} to {}".format(
            data["filename"], data["src_bucket"], data["dest_bucket"]
        )
    )
    copy_to_bucket(data["src_bucket"], data["dest_bucket"], data["filename"])


def main(args):
    file_listing = bucket_listing(args["src_bucket"])
    file_listing_length = len(file_listing)
    size_difference = args["num_files"] - file_listing_length

    # requested number of files are greater than files in bucket
    if size_difference > 0:
        for _ in range(size_difference):
            file_listing.append(random.choice(file_listing))
    # requested number of files are less than files in bucket
    elif size_difference < 0:
        for _ in range(abs(size_difference)):
            file_listing.pop()

    log.debug("File listing: {}".format(file_listing))

    # generate the data for the workers
    worker_data = []
    for i in file_listing:
        worker_data.append(
            {
                "src_bucket": args["src_bucket"],
                "dest_bucket": args["dest_bucket"],
                "filename": i["filename"],
            }
        )
    log.debug("Worker data: {}".format(worker_data))

    num_workers = multiprocessing.cpu_count()
    log.info("Number of cores: {}".format(str(num_workers)))

    pool = multiprocessing.Pool(num_workers)
    pool.map(worker, worker_data)
    pool.close()
    pool.join()


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world"
        }),
    }


if __name__ == "__main__":
    args = get_args()
    main(args)
