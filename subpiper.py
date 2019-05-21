# -*- coding: utf-8 -*-
# Target:   Python 3.7

import os
import subprocess
from threading import Thread
from queue import Queue
from typing import Iterable, Callable, IO, Union, Any

_FILE = Union[None, int, IO[Any]]


def subpiper(cmd: str,
             stdout_callback: Callable[[str], None] = None,
             stderr_callback: Callable[[str], None] = None,
             add_path_list: Iterable[str] = ()) -> int:
    """
    Launches a subprocess with the specified command, and captures stdout and stderr separately and unbuffered.
    The user can provide callbacks for printing/logging these outputs.
    Blocks until the subprocess finished, but the callbacks provide realtime access to stdout/err.

    Example usage:

        >>> from subpiper import subpiper
        >>>
        >>> def my_stdout_callback(line: str):
        >>>     print(f'STDOUT: {line}')
        >>>
        >>> def my_stderr_callback(line: str):
        >>>     print(f'STDERR: {line}')
        >>>
        >>> my_additional_path_list = [r'c:\important_location']
        >>>
        >>> retcode = subpiper(cmd='echo magic',
        >>>                    stdout_callback=my_stdout_callback,
        >>>                    stderr_callback=my_stderr_callback,
        >>>                    add_path_list=my_additional_path_list)


    :param cmd: command to launch in the subprocess. Passed directly to Popen.
    :param stdout_callback: user callback for capturing the subprocess unbuffered stdout
    :param stderr_callback: user callback for capturing the subprocess unbuffered stderr
    :param add_path_list: additional path list to add to local PATH
    :return: subprocess return code
    """

    def enqueue_lines(out: _FILE, queue: Queue):
        """
        Enqueues lines from out to the queue
        """
        for line in iter(out.readline, b''):
            queue.put(line.rstrip())
        out.close()

    # add user path
    local_env = os.environ.copy()
    for add_path in add_path_list:
        local_env["PATH"] = rf'{add_path};{local_env["PATH"]}'

    # open subprocess
    proc = subprocess.Popen(cmd, env=local_env, shell=False,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    # create queues for stdout and stderr
    out_queue = Queue()
    err_queue = Queue()
    # create and start listener threads for stdout and stderr
    out_listener = Thread(target=enqueue_lines, args=(proc.stdout, out_queue), daemon=True)
    err_listener = Thread(target=enqueue_lines, args=(proc.stderr, err_queue), daemon=True)
    out_listener.start()
    err_listener.start()

    # poll the subprocess and meanwhile dequeue any outputs from the queues,
    # and pass it on to the user callbacks
    while True:
        # get lines
        oline = '' if out_queue.empty() else out_queue.get_nowait()
        eline = '' if err_queue.empty() else err_queue.get_nowait()

        # pass them to user callbacks
        if oline and stdout_callback is not None:
            stdout_callback(oline)
        if eline and stderr_callback is not None:
            stderr_callback(eline)

        # check if the subprocess has finished
        retcode = proc.poll()
        if retcode is not None:
            break

    return retcode
