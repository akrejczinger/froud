import boto3
import requests
import json
import argparse
from argparse import RawTextHelpFormatter
import re
from common import init_keys
from common import print_table


def init():
    init_keys()

    parser = argparse.ArgumentParser(
        description='[*] List of policies attached to the role of the instance profile.\n'
                    '[*] The results can be filtered by any of the returned attributes using regular expressions.\n'
                    '[*] Returned policy attributes:\n'
                    '   [+] Service: The name of the service.\n'
                    '   [+] Action: Describes the specific action(s) that will be allowed or denied.\n'
                    '   [+] Resource: Specifies the object or objects that the statement covers.\n'
                    '   [+] Effect: Specifies whether the statement results in an allow or an explicit deny.\n'
                    '   [+] Policy name: The name of the AWS managed or inline policy.'
                    ' \n\nExample: \n    python rolepolicies.py -s ec2 -a Desc* -r \* -e Allow -p ^Amazon',
        formatter_class=RawTextHelpFormatter)
    parser.add_argument('-s', '--service', help='Regular expression filter for the Service column.', required=False)
    parser.add_argument('-a', '--action', help='Regular expression filter for the Action column.', required=False)
    parser.add_argument('-r', '--resource', help='Regular expression filter for the Resource column.',
                        required=False)
    parser.add_argument('-e', '--effect', help='Regular expression filter for the Effect column.', required=False)
    parser.add_argument('-p', '--policyname', help='Regular expression filter for the Policy name column.',
                        required=False)
    args = vars(parser.parse_args())

    return args


def policy_enumerate():
    iam = boto3.client('iam')
    iamres = boto3.resource('iam')
    r = requests.get('http://169.254.169.254/latest/meta-data/iam/info')
    role_arn = json.loads(r.text)['InstanceProfileArn']
    role = role_arn.split('/')[1]

    response1 = iam.list_attached_role_policies(RoleName=role)
    response2 = iam.list_role_policies(RoleName=role)

    print('\nThe following permissions belong to the role {}: \n'.format(role))

    values = []

    for attached_policy in response1['AttachedPolicies']:
        role_policy1 = iamres.Policy(attached_policy['PolicyArn'])

        policy = iam.get_policy(PolicyArn=role_policy1.arn)
        policy_version = iam.get_policy_version(PolicyArn=role_policy1.arn,
                                                VersionId=policy['Policy']['DefaultVersionId'])

        for statement in policy_version['PolicyVersion']['Document']['Statement']:
            resource = statement['Resource']
            effect = statement['Effect']
            actions = statement['Action']

            if type(actions) is list:
                for action in actions:
                    values.append(compose_value(action, resource, effect, role_policy1.arn.split('/')[-1]))
            else:
                values.append(compose_value(actions, resource, effect, role_policy1.arn.split('/')[-1]))

    for policy_name in response2['PolicyNames']:
        role_policy2 = iamres.RolePolicy(role, policy_name)
        policy_statement = role_policy2.policy_document['Statement']

        for pol_stat in policy_statement:
            resource = pol_stat['Resource']
            effect = pol_stat['Effect']
            actions = pol_stat['Action']

            if type(actions) is list:
                for action in actions:
                    values.append(compose_value(action, resource, effect, role_policy2.name))
            else:
                values.append(compose_value(actions, resource, effect, role_policy2.name))

    values_to_print = filter_results(values)

    print_table(values_to_print, ["Service", "Action", "Resource", "Effect", "Policy name"])


def compose_value(action, resource, effect, name):
    val = [action.split(':')[0], action.split(':')[1], resource, effect, name]
    return val


def filter_results(values):
    values_to_print = []

    match_all = True

    for value in values:
        match = True

        if args['service'] and re.match(args['service'], value[0]):
            values_to_print.append(value)
            match = False
            match_all = False
        if match and args['resource'] and re.match(args['resource'], value[2]):
            values_to_print.append(value)
            match = False
            match_all = False
        if match and args['effect'] and re.match(args['effect'], value[3]):
            values_to_print.append(value)
            match = False
            match_all = False
        if match and args['policyname'] and re.match(args['policyname'], value[4]):
            values_to_print.append(value)
            match = False
            match_all = False
        if match and args['action'] and (re.match(args['action'], value[1]) or
                                         (value[1] == '*' and value[0] in ["iam", "s3", "dynamodb", "lambda"])):
            values_to_print.append(value)
            match = False
            match_all = False

    if match_all:
        values_to_print = values

    return values_to_print


if __name__ == '__main__':

    args = init()
    policy_enumerate()
