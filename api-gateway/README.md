# Automated Testing

A testing framework which utilizs API Gateway to generate data and
ultimately, evaluate the metadata extraction solution

## Table of Contents

* [Architecture](#architecture)
* [Deployment](#deployment)
  * [IAM Stack](#iam-stack)
  * [Resources Stack](#resources-stack)
* [API Gateway](#api-gateway)
* [Testing](#testing)

## Architecture

![System Diagram](architecture.png)

## Deployment

Deployment entails the following steps:

1. Create S3 bucket to store lambda functions
2. Zip generate_data.py
3. Place zipped function into s3 bucket created in step 1
4. [Deploy the IAM stack](#iam-stack)
5. [Deploy the resources stack](#resource-stack)

### IAM Stack

The customer wishes to separate IAM from the remaining resources so all 
of the IAM roles are separated into their own cloudformation stack. You
may deploy this stack by utlizing the CloudFormation console and deploying
`iam.template.cfn.yml`. This stack will create the various IAM roles/policies
needed as inputs for the resources stack

### Resources Stack

The resources stack may be deployed using `automated-testing.cfn.yml` in
the CloudFormation console.

## API Gateway

### /test/generate

The /test/generate endpoint copies files from one bucket to another. This endpoint
serves as a mechanism to generate test data for the metadata extraction. In order
for this to be successful, there must be seed data in the source bucket.

**Parameters**:

* `src_bucket` (Required) - the S3 bucket where seed data is being stored
* `dest_bucket` (Required) - the S3 bucket that serves as the input bucket for the
metadata extraction function
* `num_files` - The number of files to copy from the src_bucket to the dest_bucket.
Default: 10
* `size` (not implemented) - The size of the files to send from the src_bucket
to the dest_bucket. Default: **M**. Options: [`S`, `M`, `L`]

## Testing

### Console Testing

#### Genereate

Testing for /test/generate can be done directly in the API Gateway console. From
within the console you can send variables in the request body following the format:
src_bucket=[bucket_name]&dest_bucket=[bucket_name]...

### Programmatic Testing

```python
import json
import requests


def main(api_url, data):
    headers = {"Content-Type": "application/json"}

    response = requests.post(api_url, headers=headers, data=payload)
    print(response.json())


if __name__ == "__main__":
    payload = {
        "src_bucket": [insert_bucket],
        "dest_bucket": [insert_bucket],
        "num_files": [insert_num_files],
        "size": [insert_size]
    }
    main(api_url, data)
```
