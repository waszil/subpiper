"""
Subprocess wrapper for separate, unbuffered capturing / redirecting of stdout and stderr.
"""

import time
import os
import sys
import shlex
import subprocess
from threading import Thread
from queue import Queue
from typing import Iterable, Callable, IO, Union, Any, Optional, List, Tuple

_FILE = Union[None, int, IO[Any]]
CallbackType = Callable[[str], None]
FinishedCallbackType = Callable[[int], None]

__all__ = ["subpiper"]


def subpiper(
    cmd: Union[str, List[str]],
    stdout_callback: Optional[CallbackType] = None,
    stderr_callback: Optional[CallbackType] = None,
    add_path_list: Iterable[str] = (),
    finished_callback: Optional[FinishedCallbackType] = None,
    hide_console: bool = True,
    silent: bool = False,
) -> Optional[Tuple[int, List[str], List[str]]]:
    """Launches a subprocess with the specified command, and captures stdout and stderr separately and unbuffered.
    The user can provide callbacks for printing/logging these outputs.

    Example usage:

        >>> from subpiper import subpiper
        ...
        ... def my_stdout_callback(line: str):
        ...     print(f'STDOUT: {line}')
        ...
        ... def my_stderr_callback(line: str):
        ...     print(f'STDERR: {line}')
        ...
        ... my_additional_path_list = ['c:\\important_location']
        ...
        ... # blocking call
        ... retcode, stdout, stderr = subpiper(
        ...     cmd='echo magic',
        ...     stdout_callback=my_stdout_callback,
        ...     stderr_callback=my_stderr_callback,
        ...     add_path_list=my_additional_path_list
        ... )
        ...
        ... # non-blocking call with finished callback
        ... def finished(retcode: int):
        ...     print(f'subprocess finished with return code {retcode}.')
        ...
        ... subpiper(
        ...     cmd='echo magic',
        ...     stdout_callback=my_stdout_callback,
        ...     stderr_callback=my_stderr_callback,
        ...     add_path_list=my_additional_path_list,
        ...     finished_callback=finished
        ... )

    :param cmd: command to launch in the subprocess. Passed directly to Popen.
    :param stdout_callback: user callback for capturing the subprocess unbuffered stdout.
                            if None, stdout is printed to sys.stdout
    :param stderr_callback: user callback for capturing the subprocess unbuffered stderr
                            if None, stderr is printed to sys.stderr
    :param add_path_list: additional path list to add to local PATH
    :param finished_callback: if not None, this will be called when the subprocess is finished.
                              In this case this function is non-blocking.
    :param hide_console: if True, hides new console window
    :param silent: if True, does not print to the stdout, only buffers.
    :return: subprocess return code, if blocking (finished_callback specified), else None.
    """
    _subpiper = _SubPiper(
        cmd,
        stdout_callback,
        stderr_callback,
        add_path_list,
        finished_callback,
        hide_console,
        silent,
    )
    return _subpiper.execute()


class _SubPiper:
    def __init__(
        self,
        cmd: Union[str, List[str]],
        stdout_callback: Optional[CallbackType] = None,
        stderr_callback: Optional[CallbackType] = None,
        add_path_list: Iterable[str] = (),
        finished_callback: Optional[FinishedCallbackType] = None,
        hide_console: bool = True,
        silent: bool = False,
    ):

        if isinstance(cmd, list):
            _command = cmd
        elif isinstance(cmd, str):
            _command = shlex.split(cmd, posix=False)
        else:
            raise TypeError("Command must be either str or List[str].")

        self.cmd: List[str] = _command
        self._stdout_buffer = []
        self._stderr_buffer = []
        self.finished_callback = finished_callback
        self.stdout_callback = stdout_callback
        self.stderr_callback = stderr_callback
        self.add_path_list = add_path_list
        self.hide_console = hide_console
        self.silent = silent
        self.proc = None
        # create queues for stdout and stderr
        self.out_queue = Queue()
        self.err_queue = Queue()

    def execute(self) -> Optional[Tuple[int, List[str], List[str]]]:
        # add user path
        local_env = os.environ.copy()
        for add_path in self.add_path_list:
            local_env["PATH"] = rf'{add_path}{os.pathsep}{local_env["PATH"]}'

        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            if self.hide_console:
                # add flag to hide new console window
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

        # open subprocess
        self.proc = subprocess.Popen(
            self.cmd,
            env=local_env,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            startupinfo=startupinfo,
        )
        # create and start listener threads for stdout and stderr
        out_listener = Thread(
            target=self._enqueue_lines,
            args=(self.proc.stdout, self.out_queue),
            daemon=True,
        )
        err_listener = Thread(
            target=self._enqueue_lines,
            args=(self.proc.stderr, self.err_queue),
            daemon=True,
        )
        out_listener.start()
        err_listener.start()

        if self.finished_callback is None:
            # poll the subprocess and meanwhile get any outputs from the queues,
            # and pass it on to the user callbacks
            retcode = self._wait_for_process()
            return retcode, self._stdout_buffer, self._stderr_buffer
        else:
            # start the subprocess in a thread and return immediately.
            wait_thread = Thread(target=self._wait_for_process, daemon=True)
            wait_thread.start()
            return None

    @staticmethod
    def _enqueue_lines(out: _FILE, queue: Queue):
        """
        Helper method
        Enqueues lines from out to the queue
        """
        for line in iter(out.readline, b""):
            if isinstance(line, bytes):
                if hasattr(out, "encoding"):
                    line = line.decode(out.encoding)
            queue.put(line.rstrip())
        out.close()

    def _handle_lines(self):
        """
        Helper method
        Gets lines from the queues and handles them
        """
        # get lines
        oline = "" if self.out_queue.empty() else self.out_queue.get_nowait()
        eline = "" if self.err_queue.empty() else self.err_queue.get_nowait()

        # pass them to user callbacks
        if oline:
            self._stdout_buffer.append(oline)
            if self.stdout_callback is not None:
                self.stdout_callback(oline)
            else:
                if not self.silent:
                    print(oline, file=sys.stdout)
        if eline:
            self._stderr_buffer.append(eline)
            if self.stderr_callback is not None:
                self.stderr_callback(eline)
            else:
                if not self.silent:
                    print(eline, file=sys.stderr)

    def _wait_for_process(self) -> int:
        """
        Helper method
        Waits for the subprocess to finish and also captures the process's stdout and stderr from their queues,
        and passes them to the user callbacks. If the process finishes, calls the finish_callback, if specified.
        """
        while True:
            self._handle_lines()
            # check if the subprocess has finished
            retcode = self.proc.poll()
            if retcode is not None:
                # before exiting, check if the process put extra lines to the outputs, catch them as well.
                while True:
                    time.sleep(0.001)
                    self._handle_lines()
                    # no more lines, we can really finish.
                    if self.out_queue.empty() and self.err_queue.empty():
                        break
                    if not any(self.out_queue.queue) or not any(self.err_queue.queue):
                        break
                break

        if self.finished_callback is not None:
            self.finished_callback(retcode)

        return retcode
