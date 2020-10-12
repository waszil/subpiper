import pytest
import time
import sys
import stat
import os
from pathlib import Path

from subpiper import subpiper


finished = False
so_buffer = []
se_buffer = []
retcode_saved = None


def my_out_callback(line):
    global so_buffer
    so_buffer.append(line)
    print(f"out: {line}")


def my_err_callback(line):
    global se_buffer
    se_buffer.append(line)
    print(f"err: {line}")


def my_finished_callback(retcode):
    global finished
    global retcode_saved
    retcode_saved = retcode
    print(f"done: {retcode}")
    finished = True


@pytest.mark.parametrize("blocking", [True, False])
def test_subpiper(blocking: bool):
    global so_buffer
    global se_buffer
    global retcode_saved

    blocking = True

    cbk = None if blocking else my_finished_callback

    if sys.platform == "win32":
        _ext = "bat"
    else:
        _ext = "sh"
    script = Path(__file__).parent / f"test_script.{_ext}"
    st = os.stat(script)
    os.chmod(script, st.st_mode | stat.S_IEXEC)

    so_buffer.clear()
    se_buffer.clear()
    retcode_saved = None

    # call the subprocess with subpiper
    return_value = subpiper(
        cmd=str(script),
        stdout_callback=my_out_callback,
        stderr_callback=my_err_callback,
        finished_callback=cbk,
    )

    timeout = 2
    timeout_happened = False
    if not blocking:
        start = time.time()
        while not finished:
            time.sleep(0.2)
            if time.time() - start > timeout:
                timeout_happened = True
                print("Timeout...")
                break

    so_expectation = ["Starting", "Finishing"]
    se_expectation = ["some error message to stderr"]
    retcode_expectation = 1

    if not blocking:
        assert finished
        assert not timeout_happened
        assert return_value is None
        assert so_buffer == so_expectation
        assert se_expectation == se_expectation
        assert retcode_saved is not None
        assert retcode_saved == retcode_expectation
    else:
        retcode, so, se = return_value
        assert retcode == retcode_expectation
        assert so == so_expectation
        assert se == se_expectation
