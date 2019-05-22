# -*- coding: utf-8 -*-
# Target:   Python 3.7

"""
Subprocess wrapper for separate, unbuffered capturing / redirecting of stdout and stderr
"""

import os
import sys
import subprocess
from threading import Thread
from queue import Queue
from typing import Iterable, Callable, IO, Union, Any, Optional

_FILE = Union[None, int, IO[Any]]

__all__ = ['subpiper']


def subpiper(cmd: str,
             stdout_callback: Callable[[str], None] = None,
             stderr_callback: Callable[[str], None] = None,
             add_path_list: Iterable[str] = (),
             finished_callback: Callable[[int], None] = None) -> Optional[int]:
    """
    Launches a subprocess with the specified command, and captures stdout and stderr separately and unbuffered.
    The user can provide callbacks for printing/logging these outputs.

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
        >>> # blocking call
        >>> retcode = subpiper(cmd='echo magic',
        >>>                    stdout_callback=my_stdout_callback,
        >>>                    stderr_callback=my_stderr_callback,
        >>>                    add_path_list=my_additional_path_list)
        >>>
        >>> # non-blocking call with finished callback
        >>> def finished(retcode: int):
        >>>     print(f'subprocess finished with return code {retcode}.')
        >>>
        >>> retcode = subpiper(cmd='echo magic',
        >>>                    stdout_callback=my_stdout_callback,
        >>>                    stderr_callback=my_stderr_callback,
        >>>                    add_path_list=my_additional_path_list,
        >>>                    finished_callback=finished)


    :param cmd: command to launch in the subprocess. Passed directly to Popen.
    :param stdout_callback: user callback for capturing the subprocess unbuffered stdout.
                            if None, stdout is printed to sys.stdout
    :param stderr_callback: user callback for capturing the subprocess unbuffered stderr
                            if None, stderr is printed to sys.stderr
    :param add_path_list: additional path list to add to local PATH
    :param finished_callback: if not None, this will be called when the subprocess is finished.
                              In this case this function is non-blocking.
    :return: subprocess return code, if blocking (finished_callback specified), else None.
    """
    _subpiper = _SubPiper(cmd, stdout_callback, stderr_callback, add_path_list, finished_callback)
    return _subpiper.execute()


class _SubPiper:

    def __init__(self,
                 cmd: str,
                 stdout_callback: Callable[[str], None] = None,
                 stderr_callback: Callable[[str], None] = None,
                 add_path_list: Iterable[str] = (),
                 finished_callback: Callable[[int], None] = None):

        self.cmd = cmd
        self.finished_callback = finished_callback
        self.stdout_callback = stdout_callback
        self.stderr_callback = stderr_callback
        self.add_path_list = add_path_list
        self.proc = None
        # create queues for stdout and stderr
        self.out_queue = Queue()
        self.err_queue = Queue()

    def execute(self) -> Optional[int]:
        # add user path
        local_env = os.environ.copy()
        for add_path in self.add_path_list:
            local_env["PATH"] = rf'{add_path};{local_env["PATH"]}'

        # open subprocess
        self.proc = subprocess.Popen(self.cmd, env=local_env, shell=False,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     universal_newlines=True)
        # create and start listener threads for stdout and stderr
        out_listener = Thread(target=self._enqueue_lines, args=(self.proc.stdout, self.out_queue), daemon=True)
        err_listener = Thread(target=self._enqueue_lines, args=(self.proc.stderr, self.err_queue), daemon=True)
        out_listener.start()
        err_listener.start()

        if self.finished_callback is None:
            # poll the subprocess and meanwhile get any outputs from the queues,
            # and pass it on to the user callbacks
            retcode = self._wait_for_process()
            return retcode
        else:
            # start the subprocess in a thread and return immediately.
            wait_thread = Thread(target=self._wait_for_process, daemon=True)
            wait_thread.start()
            return None

    def _enqueue_lines(self, out: _FILE, queue: Queue):
        """
        Helper method
        Enqueues lines from out to the queue
        """
        for line in iter(out.readline, b''):
            queue.put(line.rstrip())
        out.close()

    def _wait_for_process(self) -> int:
        """
        Helper method
        Waits for the subprocess to finish and also captures the process's stdout and stderr from their queues,
        and passes them to the user callbacks. If the process finishes, calls the finish_callback, if specified.
        """
        while True:
            # get lines
            oline = '' if self.out_queue.empty() else self.out_queue.get_nowait()
            eline = '' if self.err_queue.empty() else self.err_queue.get_nowait()

            # pass them to user callbacks
            if oline:
                if self.stdout_callback is not None:
                    self.stdout_callback(oline)
                else:
                    print(oline, file=sys.stdout)
            if eline:
                if self.stderr_callback is not None:
                    self.stderr_callback(eline)
                else:
                    print(oline, file=sys.stderr)

            # check if the subprocess has finished
            retcode = self.proc.poll()
            if retcode is not None:
                break

        if self.finished_callback is not None:
            self.finished_callback(retcode)


if __name__ == '__main__':
    import time
    import tempfile

    finished = False

    def ocb(line):
        print(f'out: {line}')

    def ecb(line):
        print(f'err: {line}')

    def done(retcode):
        global finished
        print(f'done: {retcode}')
        finished = True


    with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False) as temp_batch:
        temp_batch.write("""
            @echo off
            echo %time%
            sleep 3
            echo %time%
            exit 1
        """)

    with open(temp_batch.name, 'r'):
        print('1')
        time.sleep(0.5)
        print('2')
        time.sleep(0.5)
        ret = subpiper(cmd=temp_batch.name, stdout_callback=ocb, stderr_callback=ecb, finished_callback=done)
        print('ret:', ret)
        print('3')
        time.sleep(0.5)
        print('4')
        time.sleep(0.5)
        while not finished:
            print('not finished yet')
            time.sleep(0.5)

    os.remove(temp_batch.name)
