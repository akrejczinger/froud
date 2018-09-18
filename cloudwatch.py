import boto3
import datetime
import re
import os
import sys
import json
import argparse
from argparse import RawTextHelpFormatter
from prettytable import PrettyTable


def init():
    parser = argparse.ArgumentParser(description=' !!! DESCRIPTION GOES HERE !!! \n\nExample: \n    python cloudw.py -b nameOfMyBucket', formatter_class=RawTextHelpFormatter)
    parser.add_argument('-b', '--bucketName', help='Specify the name of the bucket.', required=False)
    parser.add_argument('-t', '--time', help='The logs will be read from x hours ago, until now. Please, specify x or the default value is 24 (1 day)', required=False)

    args = vars(parser.parse_args())

    # If the config file cannot be loaded then boto3 will use its cached data because the global variables contain nonesens ("N/A")
    config_parsing_was_successful, region_name_for_logs = load_config_json(
        "conf.json")

    if not config_parsing_was_successful:
        region_name_for_logs = "N/A"

    logs_client = boto3.client('logs', region_name=region_name_for_logs)

    return args, region_name_for_logs, logs_client


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


def list_and_save(logs_client, args):
    try:
        groups = logs_client.describe_log_groups()['logGroups']
        values = []
        filenames = []

        if args['time']:
            hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=int(args['time']))
        else:
            hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        start_time = int(hours_ago.strftime("%s")) * 1000
        stop_time = int(datetime.datetime.utcnow().strftime("%s")) * 1000

        for group in groups:
            group_name = group['logGroupName']
            streams = logs_client.describe_log_streams(logGroupName=group_name)['logStreams']
            for stream in streams:
                stream_name = stream['logStreamName']
                values.append(str(group_name))

                log_events = logs_client.get_log_events(logGroupName=group_name, logStreamName=stream_name,
                                                        startTime=start_time, endTime=stop_time)
                events = log_events['events']

                gr_st = group_name + '/' + stream_name
                gr_st = re.sub('[^\w\s-]', '', gr_st)

                current_directory = os.getcwd()
                final_directory = os.path.join(current_directory, r'cw_logs')
                if not os.path.exists(final_directory):
                    os.makedirs(final_directory)

                file_name = final_directory + '/' + gr_st + '.txt'
                filenames.append(file_name)

                try:
                    message = ''
                    for event in events:
                        if event['message']:
                            message = message + event['message'] + '\n'
                    if message:
                        with open(file_name, 'w+') as f:
                            f.write(message)

                except Exception as e:
                    print('File is skipped: {}, due to: {}'.format(file_name, e))
        print('Files downloaded to $currentpath/cw_logs folder.')
        values = set(values)
        return filenames, values

    except Exception as e:
            print(e)


def upload_files(s3_client, filenames, bucket_name):

        print('Uploading files...')
        for f in filenames:
            try:
                key = f.split('/')[-2:]
                key = key[0] + '/' + key[1]

                tc = boto3.s3.transfer.TransferConfig()
                t = boto3.s3.transfer.S3Transfer(client=s3_client, config=tc)

                t.upload_file(f, bucket_name, key)

            except:
                print('File upload is not successful')


def print_table(values):
    nums = range(len(values))
    nums = [x + 1 for x in nums]
    values_to_print = [list(a) for a in zip(nums, values)]

    values_to_print.sort()
    x = PrettyTable()
    x.field_names = ["No.", "Groups"]
    x.align["Groups"] = "l"

    for value in values_to_print:
        x.add_row(value)

    print('\nAvailable Cloudwatch logs: \n')
    print(x)


def main():

    args, region_name_for_logs, logs_client = init()

    try:
        print('Collecting CloudWatch logs...')
        filenames, values = list_and_save(logs_client, args)

    except:
        print('Error collecting logs.')
        sys.exit()

    print_table(values)

    try:
        session = boto3.Session()
        s3_client = session.client('s3')

        if args['bucketName']:
            bucket_name = args['bucketName']
            upload_files(s3_client, filenames, bucket_name)
            print ("Files are uploaded to the given bucket.")

    except:
        print('Error while creating the S3 client.')


if __name__ == '__main__':
    main()
