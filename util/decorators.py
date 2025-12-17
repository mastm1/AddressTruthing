import functools
import time

def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        timing_string = f"Finished {func.__name__}() in {run_time:.4f} secs"
        return value,timing_string
    return wrapper_timer
