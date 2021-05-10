import argparse
import subprocess
import time

import numpy as np
import wbml.out as out

from .ec2 import (
    get_instances,
    get_num_instances,
    get_running_ips,
    get_state,
    check_all_running,
    run,
    start,
    stop,
    start_stopped,
)
from .util import Config, execute_command, ssh

__all__ = [
    "config",
    "spawn",
    "print_logs",
    "ssh_map",
    "shutdown_finished",
    "kill_all",
    "sync",
]

config = Config()  #: Config for the experiments.
config["setup_commands"] = []
config["teardown_commands"] = ["logout"]


def spawn(image_id, total_count, instance_type, key_name, security_group):
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
        run(
            image_id=image_id,
            count=total_count - available,
            instance_type=instance_type,
            key_name=key_name,
            security_group=security_group,
        )
    else:
        out.out("Already enough instances available.")


def print_logs(path):
    """Display the tail of logs on all running instances.

    Args:
        path (str): Path to the log.
    """
    for ip, log in ssh_map([f"tail -n100 {path}"], broadcast=True).items():
        with out.Section(ip):
            out.out(log)


def ssh_map(
    *commands,
    broadcast=False,
    in_experiment=False,
    start_experiment=False,
    start_monitor=False,
    monitor_aws_repo_venv="source /aws/venv/bin/activate",
    monitor_delay=600,
    monitor_call="shutdown_when_all_gpus_idle_for_a_while(duration=120)",
):
    """Execute a list of commands on different EC2 instances.

    Args:
        *commands (list[str]): Commands to execute. One list per instance.
        broadcast (bool, optional): If only one command is given, execute it on all
            instances. Defaults to `False`.
        in_experiment (bool, optional): Execute the command in the `experiment` tmux
            session. Defaults to `False`.
        start_experiment (bool, optional): Start the `experiment` tmux session.
            Defaults to `False`.
        start_monitor (bool, optional): Start the `monitor` tmux session. Defaults to
            `False`.
        monitor_aws_repo_venv (str, optional): Command that activates a virtual
            environment which has this package installed. This must be correct if
            `start_monitor` is set to `True`.
        monitor_delay (int, optional): Delay before starting the monitor.
        monitor_call (str, optional): Python call to start the monitor.
    """
    ips = get_running_ips()

    # Check that enough instances are available.
    if len(ips) < len(commands):
        raise RuntimeError(
            f"Executing {len(commands)} command(s), but "
            f"have {len(ips)} instance(s) available."
        )

    # Perform broadcasting.
    if len(commands) == 1 and broadcast:
        commands = commands * len(ips)

    # Define wrapping of commands so that it can be executing inside the tmux
    # session.
    if in_experiment:

        def wrap(command_, session):
            # Escape double quotes in the command because it will be wrapped
            # in double quotes. This will not further escape already escaped
            # quotes...
            command_ = command_.replace('"', '\\"')
            return f'tmux send -t {session} "{command_}" ENTER'

    else:

        def wrap(command_):
            return command_

    if start_experiment:
        # Setup experiment session.
        setup_commands = [
            "tmux new-session -d -s experiment",
            "tmux split-window -t experiment -h",
            wrap("watch -n0.1 nivida-smi", session="experiment"),
            "tmux split-window -t experiment -v",
            'tmux send-keys -t experiment "htop" ENTER "\\\\python" ENTER',
            "tmux select-pane -t experiment -L",
        ]

    else:
        setup_commands = []

    if start_monitor:
        # Setup monitor.
        setup_commands += [
            "tmux new-session -d -s monitor",
            wrap(monitor_aws_repo_venv, session="monitor"),
            wrap(f"sleep {minitor_delay}", session="monitor"),
            wrap(
                f'sudo python -c "import aws.monitor; aws.monitor.{monitor_call}',
                session="monitor",
            ),
        ]

    # Also execute configured setup commands.
    setup_commands += [wrap(command) for command in config["ssh_setup_commands"]]

    # Perform mapping.
    results = {}
    for ip, command in zip(ips, commands):
        results[ip] = ssh(
            f'{config["ssh_user"]}@{ip}',
            config["ssh_pem"],
            *setup_commands,
            *map(wrap, command),
        )
    return results


_shutdown_finished_command = "(tmux ls | grep -q experiment) || shutdown -h now"


def shutdown_finished():
    """Shutdown all instances that have no experiment tmux session running anymore."""
    ssh_map([_shutdown_finished_command], broadcast=True)


def kill_all():
    """Kill all tmux sessions."""
    ssh_map(["tmux kill-session || true"], broadcast=True)


def sync(sources, target, ips=None, shutdown=False):
    """Synchronise data.

    Args:
        sources (list[str]): List of sources to sync.
        target (str): Directory to sync to.
        ips (list[str], optional): IPs to sync. Defaults to all running IPs.
        shutdown (bool, optional): Shutdown machine after syncing if no tmux
            session is running anymore.
    """
    if ips is None:
        ips = get_running_ips()

    for ip in ips:
        with out.Section(ip):
            for folder in sources:
                out.kv("Syncing folder", folder)
                try:
                    execute_command(
                        "rsync",
                        "-Pav",
                        "-e",
                        (
                            f"ssh "
                            f"-oStrictHostKeyChecking=no "
                            f'-i {config["ssh_pem"]}'
                        ),
                        f'{config["ssh_user"]}@{ip}:{folder}',
                        target,
                    )
                except subprocess.CalledProcessError as e:
                    # rsync failed. This can happen because the output is being
                    # written at that time. Try again.
                    out.kv("Error", str(e))
                    out.out("Trying again.")
                    continue

            if shutdown:
                # All folders have synced. Check if the instance needs to be
                # shutdown.
                ssh(
                    f'{config["ssh_user"]}@{ip}',
                    config["ssh_pem"],
                    [_shutdown_finished_command],
                )


def manage_cluster(
    commands,
    instance_type,
    key_name,
    security_group,
    image_id,
    sync_sources=None,
    sync_target=None,
    monitor_call="shutdown_when_all_gpus_idle_for_a_while(duration=120)",
    monitor_delay=600,
    monitor_aws_repo_venv="source /aws/venv/bin/activate",
):
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync-stopped", action="store_true")
    parser.add_argument("--spawn", type=int)
    parser.add_argument("--kill", action="store_true")
    parser.add_argument("--start", action="store_true")
    args = parser.parse_args()

    if args.sync_stopped:
        with out.Section("Syncing all stopped instances in five batches"):
            for batch in np.array_split(get_state("stopped"), 5):
                # Start the instances.
                start(*batch)

                try:
                    # Wait for the instances to have booted.
                    out.out("Waiting a minute for the instances to have booted...")
                    time.sleep(60)

                    # Refresh the instances to get the IPs.
                    instance_ids = [instance["InstanceId"] for instance in batch]
                    batch = get_instances(*instance_ids)

                    # Setup the instances.
                    ssh_map([config["setup_commands"]], broadcast=True)

                    # Sync.
                    sync(
                        sources=sync_sources,
                        target=sync_target,
                        ips=[instance["PublicIpAddress"] for instance in batch],
                    )
                finally:
                    # Stop the instances again.
                    stop(*batch)

        out.out("Syncing completed: not continuing execution of script.")
        exit()

    if args.spawn:
        with out.Section("Starting all stopped instances"):
            start_stopped()

        with out.Section("Spawning instances"):
            spawn(
                image_id=image_id,
                total_count=args.spawn,
                instance_type=instance_type,
                key_name=key_name,
                security_group=security_group,
            )

        while not check_all_running():
            out.out("Waiting for all instances to be running...")
            time.sleep(5)

        out.out("Waiting a minute for all instances to have booted...")
        time.sleep(60)

    if args.kill:
        with out.Section("Killing all experiments"):
            kill_all()

    if args.start:
        num_instances = len(get_running_ips())
        pieces = np.array_split(commands, num_instances)

        with out.Section("Starting experiments"):
            out.kv("Number of commands", len(commands))
            out.kv("Number of instances", num_instances)
            out.kv("Maximum runs per instance", max([len(piece) for piece in pieces]))
            ssh_map(
                *[
                    [*config["setup_commands"], *piece, *config["teardown_commands"]]
                    for piece in pieces
                ],
                start_experiment=True,
                in_experiment=True,
                start_monitor=True,
                monitor_aws_repo_venv=monitor_aws_repo_venv,
                monitor_delay=monitor_delay,
                monitor_call=monitor_call,
            )

    while True:
        out.kv("Instances still running", len(get_running_ips()))
        sync(
            sources=sync_sources,
            target=sync_target,
            shutdown=True,
        )
        out.out("Sleeping for two minutes...")
        time.sleep(2 * 60)
