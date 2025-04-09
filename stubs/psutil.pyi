# Stubs for psutil (Python 3.7)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any

PROCFS_PATH: str
RLIMIT_MSGQUEUE: Any
RLIMIT_NICE: Any
RLIMIT_RTPRIO: Any
RLIMIT_RTTIME: Any
RLIMIT_SIGPENDING: Any
version_info: Any
AF_LINK: Any
POWER_TIME_UNLIMITED: Any
POWER_TIME_UNKNOWN: Any

class Process:
    def __init__(self, pid: Any | None = ...) -> None: ...
    def __eq__(self, other: Any): ...
    def __ne__(self, other: Any): ...
    def __hash__(self): ...
    @property
    def pid(self): ...
    def oneshot(self) -> None: ...
    def as_dict(self, attrs: Any | None = ..., ad_value: Any | None = ...): ...
    def parent(self): ...
    def is_running(self): ...
    def ppid(self): ...
    def name(self): ...
    def exe(self): ...
    def cmdline(self): ...
    def status(self): ...
    def username(self): ...
    def create_time(self): ...
    def cwd(self): ...
    def nice(self, value: Any | None = ...): ...
    def uids(self): ...
    def gids(self): ...
    def terminal(self): ...
    def num_fds(self): ...
    def io_counters(self): ...
    def ionice(self, ioclass: Any | None = ..., value: Any | None = ...): ...
    def rlimit(self, resource: Any, limits: Any | None = ...): ...
    def cpu_affinity(self, cpus: Any | None = ...): ...
    def cpu_num(self): ...
    def environ(self): ...
    def num_handles(self): ...
    def num_ctx_switches(self): ...
    def num_threads(self): ...
    def threads(self): ...
    def children(self, recursive: bool = ...): ...
    def cpu_percent(self, interval: Any | None = ...): ...
    def cpu_times(self): ...
    def memory_info(self): ...
    def memory_info_ex(self): ...
    def memory_full_info(self): ...
    def memory_percent(self, memtype: str = ...): ...
    def memory_maps(self, grouped: bool = ...): ...
    def open_files(self): ...
    def connections(self, kind: str = ...): ...
    def send_signal(self, sig: Any) -> None: ...
    def suspend(self) -> None: ...
    def resume(self) -> None: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def wait(self, timeout: Any | None = ...): ...

class Popen(Process):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def __dir__(self): ...
    def __enter__(self): ...
    def __exit__(self, *args: Any, **kwargs: Any): ...
    def __getattribute__(self, name: Any): ...
    def wait(self, timeout: Any | None = ...): ...

def pids(): ...
def pid_exists(pid: Any): ...
def process_iter(attrs: Any | None = ..., ad_value: Any | None = ...): ...
def wait_procs(procs: Any, timeout: Any | None = ..., callback: Any | None = ...): ...
def cpu_count(logical: bool = ...): ...
def cpu_times(percpu: bool = ...): ...
def cpu_percent(interval: Any | None = ..., percpu: bool = ...): ...
def cpu_times_percent(interval: Any | None = ..., percpu: bool = ...): ...
def cpu_stats(): ...
def cpu_freq(percpu: bool = ...): ...
def virtual_memory(): ...
def swap_memory(): ...
def disk_usage(path: Any): ...
def disk_partitions(all: bool = ...): ...
def disk_io_counters(perdisk: bool = ..., nowrap: bool = ...): ...
def net_io_counters(pernic: bool = ..., nowrap: bool = ...): ...
def net_connections(kind: str = ...): ...
def net_if_addrs(): ...
def net_if_stats(): ...
def sensors_temperatures(fahrenheit: bool = ...): ...
def sensors_fans(): ...
def sensors_battery(): ...
def boot_time(): ...
def users(): ...
def getloadavg(): ...

# Names in __all__ with no definition:
#   __version__
