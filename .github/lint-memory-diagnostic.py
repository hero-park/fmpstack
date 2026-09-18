"""Temporary hosted experiment observer; remove after the single diagnostic run.

Reads only memory counters and lint-owned output, never environment or argv.
Hard links retain GNU time's exact worker/descendant peak RSS after lint cleanup.
Live VmHWM samples are lower bounds if a process dies between samples.
"""

import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time


destination = Path(sys.argv[1])
stopping = False


def stop(_signum, _frame):
    global stopping
    stopping = True


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)


def read(path):
    try:
        return path.read_text()
    except OSError:
        return "unavailable"


def emit(kind, **values):
    line = json.dumps(dict(kind=kind, epoch=time.time(), **values), sort_keys=True)
    print(line, flush=True)
    with (destination / "observations.jsonl").open("a") as output:
        output.write(line + "\n")


# Resolve the observer's actual cgroup and every ancestor limiting that group.
# The standard hosted Ubuntu runner uses cgroup v2; explicitly report absence.
cgroups = []
for row in read(Path("/proc/self/cgroup")).splitlines():
    if row.startswith("0::"):
        group = Path("/sys/fs/cgroup") / row[3:].lstrip("/")
        while group.is_relative_to("/sys/fs/cgroup"):
            cgroups.append(group)
            group = group.parent
emit("limits", process_limits=read(Path("/proc/self/limits")),
     cgroup_paths=[str(group) for group in cgroups])

seen = {}
next_sample = 0.0
while True:
    # Timing files are opened before each worker starts. Linking keeps the
    # inode alive through the lint owner's normal temporary-directory cleanup.
    for root in (destination / "tmp").glob("fm-lint.*"):
        timings = list(root.glob("timing.*"))
        # The owner replaces manifests when sorting them, before starting time.
        # Wait for worker startup so links capture the actual sorted inputs.
        if not timings:
            continue
        for source in timings + list(root.glob("manifest.[01]")):
            target = destination / source.name
            try:
                if not target.exists():
                    os.link(source, target)
            except FileNotFoundError:
                pass
    for target in sorted(destination.glob("timing.*")) + sorted(destination.glob("manifest.[01]")):
        content = read(target)
        if content and seen.get(target.name) != content:
            seen[target.name] = content
            emit("lint_output", name=target.name, content=content,
                 count=len(content.splitlines()),
                 sha256=hashlib.sha256(content.encode()).hexdigest())
    if time.monotonic() >= next_sample or stopping:
        memory = read(Path("/proc/meminfo"))
        emit("host_memory", counters=[row for row in memory.splitlines()
             if row.split(":")[0] in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}])
        for group in cgroups:
            emit("cgroup_memory", path=str(group), counters={name: read(group / name)
                 for name in ("memory.max", "memory.high", "memory.current", "memory.peak",
                              "memory.swap.max", "memory.events", "memory.events.local")})
        processes = {}
        for proc in Path("/proc").glob("[0-9]*"):
            if read(proc / "comm").strip() == "shellcheck":
                processes[proc.name] = [row for row in read(proc / "status").splitlines()
                                       if row.split(":")[0] in {"VmRSS", "VmHWM"}]
        emit("shellcheck_memory", processes=processes)
        next_sample = time.monotonic() + 5
    if stopping:
        break
    time.sleep(0.1)
