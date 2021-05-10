import subprocess
import numpy as np
import time

__all__ = [
    "all_gpus_idle",
    "all_gpus_idle_for_a_while",
    "shutdown_when_all_gpus_idle_for_a_while",
    "shutdown_when_all_gpus_idle_for_a_while_call",
    "shutdown_after_a_while",
    "shutdown_after_a_while_call",
]


def as_int(x, default=0):
    """Convert a thing to an integer.

    Args:
        x (object): Thing to convert.
        default (int, optional): Default value to return in case the conversion fails.

    Returns:
        int: `x` as an integer.
    """
    try:
        return int(x)
    except ValueError:
        return default


def all_gpus_idle():
    """Check if all GPUs are idle.

    Returns:
        bool: `True` if all GPUs are idle, `False` if not.
    """
    p = subprocess.Popen(
        [
            "nvidia-smi",
            "--query-gpu=utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        stdout=subprocess.PIPE,
    )
    res, _ = p.communicate()
    utilisations = np.array([as_int(x.decode()) for x in res.splitlines()])
    idle = np.all(utilisations == 0)
    return idle


def all_gpus_idle_for_a_while(duration=120):
    """Check if all GPUs are idle for a while.

    Args:
        duration (int, optional): Number of seconds to check. Defaults to two minutes.

    Returns:
        bool: `True` if all GPUs are idle for a while, `False` if not.
    """
    start = time.time()
    while time.time() < start + duration:
        if not all_gpus_idle():
            return False
        time.sleep(0.1)
    return True


def shutdown():
    """Shutdown."""
    subprocess.call(["shutdown", "-h", "now"])


def shutdown_when_all_gpus_idle_for_a_while(duration=120):
    """Shutdown when all GPUs are idle for a while.

    Args:
        duration (int, optional): Number of seconds to check the GPUs. Defaults to two
            minutes.
    """
    while True:
        if all_gpus_idle_for_a_while(duration=duration):
            shutdown()
        time.sleep(60)


def shutdown_when_all_gpus_idle_for_a_while_call(duration=120):
    return f"shutdown_when_all_gpus_idle_for_a_while(duration={duration})"


def shutdown_after_a_while(duration=120):
    """Shutdown.

    Args:
        duration (int, optional): Number of seconds to wait before shutting down.
    """
    time.sleep(duration)
    shutdown()


def shutdown_after_a_while_call(duration=120):
    return f"shutdown_after_a_while(duration={duration})"
