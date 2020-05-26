import subprocess

import wbml.out as out

from .ec2 import (
    run,
    get_num_instances,
    get_running_ips
)
from .util import Config, execute_command, ssh

__all__ = ['config',
           'spawn',
           'print_logs',
           'ssh_map',
           'shutdown_finished',
           'kill_all',
           'sync']

config = Config()  #: Config for the experiments.
config['ssh_setup_commands'] = []


def spawn(image_id,
          total_count,
          instance_type,
          key_name,
          security_group):
    """Spawn new EC2 instances to make a total.

    Args:
        image_id (str): Image ID.
        total_count (int): Desired number of instances.
        instance_type (str): Type of the instance.
        key_name (str): Name of the key pair.
        security_group (str): Security group.
    """
    available = get_num_instances()
    if available < total_count:
        run(image_id=image_id,
            count=total_count - available,
            instance_type=instance_type,
            key_name=key_name,
            security_group=security_group)
    else:
        out.out('Already enough instances available.')


def print_logs(path):
    """Display the tail of logs on all running instances.

    Args:
        path (str): Path to the log.
    """
    for ip, log in ssh_map([['tail', path]], broadcast=True).items():
        with out.Section(ip):
            out.out(log)


def ssh_map(*commands,
            broadcast=False,
            in_tmux=False,
            start_tmux=False):
    """Execute a list of commands on different EC2 instances.

    Args:
        *commands (list[list[str]]): List of commands.
        broadcast (bool, optional): If only one command is given, execute it on
            all instances. Defaults to `False`.
        in_tmux (bool, optional): Execute the command in the `experiment` tmux
            session. Defaults to `False`.
        start_tmux (bool, optional): Start the `experiment` tmux session.
            Defaults to `False`.
    """
    ips = get_running_ips()

    # Check that enough instances are available.
    if len(ips) < len(commands):
        raise RuntimeError(f'Executing {len(commands)} command(s), but '
                           f'have {len(ips)} instance(s) available.')

    # Perform broadcasting.
    if len(commands) == 1 and broadcast:
        commands = commands * len(ips)

    # Define wrapping of commands so that it can be executing inside the tmux
    # session.
    if in_tmux:
        def wrap(command_):
            # Escape double quotes in the command because it will be wrapped
            # in double quotes. This will not further escape already escaped
            # quotes...
            command_ = " ".join(command_).replace('"', '\\"')
            return ['tmux', 'send', '-t', 'experiment',
                    f'"{command_}"', 'ENTER']
    else:
        def wrap(command_):
            return command_

    # Start a tmux session, if necessary.
    if start_tmux:
        setup_commands = [['tmux', 'new-session -d -s experiment']]
    else:
        setup_commands = []

    # Also execute configured setup commands.
    setup_commands += \
        [wrap(command) for command in config['ssh_setup_commands']]

    # Perform mapping.
    results = {}
    for ip, command in zip(ips, commands):
        results[ip] = ssh(f'ubuntu@{ip}',
                          config['ssh_pem'],
                          *setup_commands,
                          *map(wrap, command))
    return results


def shutdown_finished():
    """Shutdown all instances that have no tmux sessions running anymore."""
    ssh_map([['([[ $(tmux ls 2>&1) =~ "no server running" ]] && sudo shutdown)',
              '||',
              'true']], broadcast=True)


def kill_all():
    """Kill all tmux sessions."""
    ssh_map([['tmux', 'kill-session', '||', 'true']], broadcast=True)


def sync(sources, target):
    """Synchronise data.

    Args:
        sources (list[str]): List of sources to sync.
        target (str): Directory to sync to.
    """
    for ip in get_running_ips():
        with out.Section(ip):
            for folder in sources:
                out.kv('Folder', folder)
                try:
                    execute_command('rsync',
                                    '-Pav',
                                    '-e', (f'ssh '
                                           f'-oStrictHostKeyChecking=no '
                                           f'-i {config["ssh_perm"]}'),
                                    f'{config["ssh_user"]}@{ip}:{folder}',
                                    target)
                except subprocess.CalledProcessError as e:
                    # rsync failed. This can happen because the output is being
                    # writting at that time. Try again.
                    out.kv('Error', str(e))
                    out.out('Trying again.')
                    continue
