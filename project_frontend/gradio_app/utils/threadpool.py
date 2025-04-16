from concurrent.futures import ThreadPoolExecutor
import functools

executor = ThreadPoolExecutor(max_workers=4)

def async_execution(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return executor.submit(func, *args, **kwargs)
    return wrapped

# 使用示例（修改gender_detection）:
@async_execution
def gender_detection():
    ...