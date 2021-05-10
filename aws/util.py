import json
import subprocess
import plum
from typing import Union

import wbml.out as out

__all__ = ["Config", "execute_command", "join_command", "ssh"]

_dispatch = plum.Dispatcher()


class Config:
    """Config that acts as a dictionary."""

    def __init__(self):
        self.data = {}

    def __getitem__(self, item):
        try:
            return self.data[item]
        except KeyError:
            raise RuntimeError(
                f'Attempt to access config key "{item}", '
                f'but it is not available. Please set "{item}".'
            )

    def __setitem__(self, key, value):
        self.data[key] = value


def execute_command(*cmd, parse_json=False):
    """Execute a command.

    Args:
        *cmd (str): Parts of the command.
        parse_json (bool, optional): Parse the output as JSON. Defaults to
            `False`.

    Returns:
        str or dict: Output of command.
    """
    res = subprocess.check_output(cmd)
    if parse_json:
        return json.loads(res)
    else:
        return res.decode()


@_dispatch
def join_command(command: Union[list, tuple]):
    """Join a command in list form to make a string.

    Args:
        command (list[str] or tuple[str]): Command to join.

    Return:
        str: Everyone as one command.
    """
    return "(" + "; ".join(command) + ")"


@_dispatch
def join_command(command: str):
    return "(" + command + ")"


def ssh(host, pem, *commands):
    """Execute commands on a host.

    Args:
        host (str): Host to execute command on.
        pem (str): Path to key to use to login.
        *commands (str): List of commands to execute on host.

    Returns:
        object: Results of command.
    """
    # Merge all commands into one.
    command = join_command(commands)

    # Perform command.
    with out.Section(f"Executing command on {host}"):
        out.out(command)

    # Attempt the SSH command until it works.
    res = None
    while res is None:
        try:
            res = execute_command(
                "ssh", "-i", pem, "-oStrictHostKeyChecking=no", host, command
            )
        except subprocess.CalledProcessError as e:
            # It failed. Print the error and try again.
            out.kv("Error", str(e))
            out.out("Trying again.")
            continue

    return res
