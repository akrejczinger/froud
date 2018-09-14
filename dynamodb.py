import boto3
from botocore.exceptions import ClientError
import os
import argparse
from argparse import RawTextHelpFormatter
import json
import sys


parser = argparse.ArgumentParser(description=' !!! DESCRIPTION GOES HERE !!! \n\nExample: \n    python dynamo.py -t nameOfMyTable', formatter_class=RawTextHelpFormatter)
parser.add_argument('-t', '--tableName', help='Specify the name of the table.', required=False)
args = vars(parser.parse_args())


def load_config_json(config_json_filename):
    try:
        with open(config_json_filename) as config_file_handler:
            try:
                config_json = json.load(config_file_handler)
            except Exception as e:
                print("Error parsing config file: {}".format(e))
                sys.exit()
    except Exception as e:
        print("Error opening file: {}".format(e))
        return False

    try:
        region_name_for_logs = config_json["region_name_for_logs"]
    except Exception as e:
        print("Error parsing 'region_name_for_logs' from the config file: {}".format(e))
        sys.exit()

    return True, region_name_for_logs


def scan_table(table, region_name_for_logs):

    dynamo = boto3.client('dynamodb', region_name=region_name_for_logs)

    try:
        response = dynamo.scan(TableName=table)
    except ClientError as ce:
        if ce.response['Error']['Code'] == 'ResourceNotFoundException':
            print('Requested table not found.')
            sys.exit()

    print('Scanning the table...')
    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = dynamo.scan(TableName=table, ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])

    return data


def write_to_file(table, data):

    print('Writing files to currentpath/scan_results folder...')
    current_directory = os.getcwd()
    final_directory = os.path.join(current_directory, r'scan_results')
    if not os.path.exists(final_directory):
        os.makedirs(final_directory)

    count = 1
    filenames = []

    while len(data) > 0:

        if len(data) <= 1000:
            file_name = final_directory + '/' + table + '-' + str(count) + '-' + str(count+999) + '.txt'
            filenames.append(file_name)
            with open(file_name, 'w+') as f:
                for line in data:
                    f.write(str(line))
                del data[:]

        else:
            file_name = final_directory + '/' + table + str(count) + '.txt'
            filenames.append(file_name)
            with open(file_name, 'w+') as f:
                for line in data[:1000]:
                    f.write(str(line))
                del data[:1000]
        count += 1000

    return filenames


def upload_files(s3_client, filenames, bucket_name):

    print('Uploading files...')
    for file in filenames:
        try:
            key = file.split('/')[-2:]
            key = key[0] + '/' + key[1]
            tc = boto3.s3.transfer.TransferConfig()
            t = boto3.s3.transfer.S3Transfer(client=s3_client, config=tc)
            t.upload_file(file, bucket_name, key)
        except:
            print('File upload is not successful')


if __name__ == '__main__':

    config_parsing_was_successfull, region_name_for_logs = load_config_json("conf.json")

    if not config_parsing_was_successfull:
        region_name_for_logs = "N/A"

    if args['tableName']:
        table = str(args['tableName'])
        data = scan_table(table, region_name_for_logs)
        filenames = write_to_file(table, data)
    else:
        print ("Please specify a table name.")

