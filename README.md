# subpiper
Subprocess wrapper for separate, unbuffered capturing / redirecting of stdout and stderr

## Usage:

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

# call subpiper to take care everyting
retcode = subpiper(cmd='echo magic',
                   stdout_callback=my_stdout_callback,
                   stderr_callback=my_stderr_callback,
                   add_path_list=my_additional_path_list)
```
