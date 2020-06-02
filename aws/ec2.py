import logging

import wbml.out as out
from plum import Dispatcher

from .util import execute_command

__all__ = ['get_instances',
           'get_num_instances',
           'get_running_ips',
           'get_state',
           'check_all_running',
           'run',
           'terminate_all',
           'start',
           'stop',
           'start_stopped',
           'stop_running']

log = logging.getLogger(__name__)

_dispatch = Dispatcher()


@_dispatch()
def get_instances():
    """Get all EC2 instances or select them by ID.

    Args:
        *instance_ids (str): IDs of EC2 instances to get.

    Returns:
        list[dict]: List of EC2 instances.
    """
    reservations = execute_command('aws', 'ec2', 'describe-instances',
                                   parse_json=True)['Reservations']

    # Walk through all reservations and filter by valid status.
    instances = []
    for reservation in reservations:
        for instance in reservation['Instances']:
            if instance['State']['Name'] in {'running', 'pending', 'stopped'}:
                instances.append(instance)

    # Sort by instance ID.
    instances = sorted(instances, key=lambda x: x['InstanceId'])

    return instances


@_dispatch(str, [str])
def get_instances(*instance_ids):
    # Set `None`s for all instances.
    instances = [None for _ in instance_ids]

    # Fill the instances that can be found.
    for instance in get_instances():
        if instance['InstanceId'] in instance_ids:
            instances[instance_ids.index(instance['InstanceId'])] = instance

    # Check that all instances have been found.
    if any([instance is None for instance in instances]):
        not_found = [instance_id
                     for instance_id, instance in zip(instance_ids, instances)
                     if instance is None]
        raise RuntimeError('Could not find instances corresponding to the '
                           'following IDs: ' + ', '.join(not_found) + '.')

    return instances


def get_num_instances():
    """Get the number of available EC2 instances.

    Returns:
        int: Number of available EC2 instances.
    """
    return len(get_instances())


def get_running_ips():
    """Get the IPs corresponding to running EC2 instances.

    Returns:
        list[str]: List of IPs.
    """
    return [instance['PublicIpAddress'] for instance in get_state('running')]


def get_state(state):
    """Get all EC2 instances of a certain state.

    Args:
        state (str): State to filter for.

    Returns:
        list[dict]: List of EC2 instances in state `state`.
    """
    return [instance for instance in get_instances()
            if instance['State']['Name'] == state]


def check_all_running():
    """Check whether all EC2 instances are running.

    Returns:
        bool: `True` if all EC2 instances are running, else `False`.
    """
    for instance in get_instances():
        if instance['State']['Name'] != 'running':
            return False

    return True


def run(image_id, instance_type, count, key_name, security_group):
    """Run new EC2 instances.

    Args:
        image_id (str): Image ID.
        instance_type (str): Type of the instance.
        count (int): Number of such instances to run.
        key_name (str): Name of the key pair.
        security_group (str): Security group.
    """
    execute_command('aws', 'ec2', 'run-instances',
                    '--image-id', image_id,
                    '--count', str(count),
                    '--instance-type', instance_type,
                    '--key-name', key_name,
                    '--security-groups', security_group)


def terminate_all():
    """Terminate all EC2 instances."""
    instance_ids = [instance['InstanceId'] for instance in get_instances()]
    if len(instance_ids) > 0:
        execute_command('aws', 'ec2', 'terminate-instances',
                        '--instance-ids', *instance_ids)
    else:
        out.out('No instances to terminate.')


def start(*instances):
    """Start EC2 instances.

    Args:
        *instances (dict): Instances to start.
    """
    instance_ids = [instance['InstanceId'] for instance in instances]
    execute_command('aws', 'ec2', 'start-instances',
                    '--instance-ids', *instance_ids)


def stop(*instances):
    """Stop EC2 instances.

    Args:
        *instances (dict): Instances to stop.
    """
    instance_ids = [instance['InstanceId'] for instance in instances]
    execute_command('aws', 'ec2', 'stop-instances',
                    '--instance-ids', *instance_ids)


def start_stopped():
    """Start all stopped EC2 instances."""
    instances = [instance for instance in get_state('stopped')]
    if len(instances) > 0:
        start(*instances)
    else:
        out.out('No stopped instances.')


def stop_running():
    """Stop all running EC2 instances."""
    instances = [instance for instance in get_state('running')]
    if len(instances) > 0:
        stop(*instances)
    else:
        out.out('No running instances.')
