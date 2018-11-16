from botocore.exceptions import ClientError
import common
import sys


def scan_queue(queue_name, sqs):
    try:
        queue = sqs.create_queue(QueueName=queue_name)
    except ClientError as err:
        print(err)
        sys.exit()

    # get messages
    msgs = []
    while True:
        messages = queue.receive_messages(VisibilityTimeout=120, WaitTimeSeconds=60)
        for message in messages:
            print(message.body)
            msgs.append(message.body)
        if not messages or len(msgs) > 100:
            break
    return msgs


def main():

    description = '\n[*] SQS message scanner.\n' \
                  '[*] Specify the name of the queue to save the messages from.\n' \
                  '[*] If a bucket is provided, the results are uploaded to the bucket. \n\n'

    required_params = [['-q', '--queueName', 'Specify the name of the queue.']]
    optional_params = [['-b', '--bucketName', 'Specify the name of the bucket.']]

    args, sqs, s3_client = common.init(description, 'sqs', optional_params=optional_params,
                                       required_params=required_params)

    data = scan_queue(str(args['queueName']), sqs)
    filenames = common.write_to_file_1000('sqs', str(args['queueName']), data)

    if args['bucketName']:
        common.bucket_upload(args['bucket'], s3_client, filenames)


if __name__ == '__main__':
    main()
