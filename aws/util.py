import json
import subprocess
import plum
from typing import Union, Optional
import abc
import time

import wbml.out as out

__all__ = [
    "assert_set",
    "Config",
    "execute_command",
    "join_command",
    "Remote",
    "Path",
    "LocalPath",
    "RemotePath",
    "ssh",
]

_dispatch = plum.Dispatcher()


def assert_set(**kw_args):
    """Assert that the values of keyword arguments are not `None`."""
    for k, v in kw_args.items():
        if v is None:
            raise ValueError(f'Keyword argument "{k}" must be set.')


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


@_dispatch
def execute_command(*cmd: str, parse_json=False):
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


class Remote:
    """Remote server.

    Args:
        user (str): User.
        host (str): Host.
        key (str or None): Path to private key.
    """

    def __init__(self, user: str, host: str, key: Optional[str] = None):
        self.user = user
        self.host = host
        self.key = key


class Path(metaclass=abc.ABCMeta):
    """A path."""


class LocalPath(Path):
    """A local path.

    Args:
        path (str): Local path.
    """

    @_dispatch
    def __init__(self, path: str):
        self.path = path


class RemotePath(Path):
    """A path on a remote server.

    Args:
        remote (:class:`.Remote`): Remote.
        path (str): Path on remote.
    """

    @_dispatch
    def __init__(self, remote: Remote, path: str):
        self.remote = remote
        self.path = path


@_dispatch
def ssh(remote: Remote, *commands: str, retry_until_success=True):
    """Execute commands on a host.

    Args:
        remote (:class:`.Remote`): Remote.
        *commands (str): Commands to execute on host.
        retry_until_success (bool, optional): Retry until the command succeeds. Defaults
            to `True`.

    Returns:
        object: Results of command.
    """
    # Merge all commands into one.
    command = join_command(commands)

    # Perform command.
    with out.Section(f"Executing command on {remote.host}"):
        out.out(command)

    # Attempt the SSH command until it works.
    res = None
    while res is None:
        try:
            res = execute_command(
                "ssh",
                *(("-i", remote.key) if remote.key else ()),
                "-oStrictHostKeyChecking=no",
                f"{remote.user}@{remote.host}",
                command,
            )
        except subprocess.CalledProcessError as e:
            # It failed. Print the error and try again.
            out.kv("Error", str(e))
            if retry_until_success:
                out.out("Sleeping and then trying again.")
                time.sleep(1)
                continue
            else:
                break

    return res
