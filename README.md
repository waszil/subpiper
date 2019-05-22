# subpiper
Subprocess wrapper for separate, unbuffered capturing / redirecting of stdout and stderr

## Usage

### Blocking mode

```python
from subpiper import subpiper

def my_stdout_callback(line: str):
    # do whatever you like with stdout lines
    print(f'STDOUT: {line}')

def my_stderr_callback(line: str):
    # do whatever you like with stderr lines
    print(f'STDERR: {line}')

# add some path to the PATH for your subprocess
my_additional_path_list = [r'c:\important_location']

# call subpiper to take care everyting in blocking mode
retcode = subpiper(cmd='echo magic',
                   stdout_callback=my_stdout_callback,
                   stderr_callback=my_stderr_callback,
                   add_path_list=my_additional_path_list)
# blocks until subprocess finishes
```

### Non-blocking mode

```python
from subpiper import subpiper

def process_done(retcode: int):
    print(f'Subprocess finished with return code: {retcode}')

# call subpiper to take care everyting in non-blocking mode
retcode = subpiper(cmd='echo magic',
                   stdout_callback=my_stdout_callback,
                   stderr_callback=my_stderr_callback,
                   add_path_list=my_additional_path_list,
                   finished_callback=process_done)
# do your other stuff
...
# when the subprocess finishes, your process_done callback will be invoked.
```
