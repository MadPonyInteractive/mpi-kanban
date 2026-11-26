#!/usr/bin/env python3
"""Machine-global GPU lease, so concurrent agents stop colliding on one device.

File claims cannot cover a GPU. They live in one repo's `state/`, they key on
paths, and they bind on writes. Two agents in two different repos running
sweeps on the same card write no shared file at all.

So the lease is machine-global and the lock is the kernel's:

    ~/.mpi-kanban/gpu/<index>.lock      one file per NVIDIA device

held by an OS exclusive lock (`msvcrt.locking` on Windows, `fcntl.flock`
elsewhere) for the lifetime of the wrapped command. That choice is what removes
the heartbeat: the kernel drops the lock when the holder exits, including on
crash, Ctrl-C, or `TaskStop`. There is no TTL to tune and no stale lease to
reclaim -- the failure mode that a heartbeat exists to paper over cannot happen.

Usage:

    python gpu_lease.py run -- python sweep.py --steps 4000
    python gpu_lease.py status

`run` takes the first free slot, sets `CUDA_VISIBLE_DEVICES` for the child, and
waits when every slot is busy. Run it as a background Bash call: the waiting
then costs no tokens at all, and the harness notifies you when it exits.

Waiters are served first come, first served:

    ~/.mpi-kanban/gpu/queue/<n>.ticket  one per waiter, numbered after every live one

and only the lowest live ticket may try a slot. Without it every waiter re-polled
the lock and whoever retried first after a release won, so a peer running batches
back to back re-took the GPU between them and a waiter could starve for an hour.
A ticket is live while its owner holds a kernel lock on it, so a killed waiter
drops out of line the same way a killed holder frees its slot.

Slots come from `nvidia-smi`, so an onboard Intel/AMD adapter never gets one and
no agent can be handed a device too weak to run on. A machine with no NVIDIA
device runs the command unleased rather than blocking work.

Ollama holds VRAM without holding a lease: a model stays loaded for its
keep-alive (5 min by default) after whatever asked for it is gone, and a leased
job that starts on top of it can crash the machine (MPI-41). So a model Ollama
has in VRAM counts as every slot busy -- `status` names it and `run` waits --
and when a leased command exits, every model Ollama holds is unloaded before the
slot is released, so nothing the command loaded outlives its lease.

System RAM gates a job that declares it (MPI-43): `run --ram 45 -- <cmd>` starts only
when 45 GB plus a floor (8 GB, `MPI_KANBAN_RAM_FLOOR_GB`) is Available. A leased job alone
once drove free RAM from 29 GB to 2.9 GB. Without `--ram` nothing waits; a warning prints
under the floor.

A job short of RAM never holds the line (MPI-52: one did, for 2.5 h, with the GPU free and
five sessions behind it). It keeps its place and the waiters behind it that fit go ahead.
At its turn with the GPU free it first takes idle RAM back -- Windows trims the memory other
programs are not using (nothing is closed), and an idle ComfyUI engine named in
`MPI_KANBAN_COMFYUI` or `<root>/config.json` {"comfyui": [url]} unloads its cached models --
and if it is still short after `--ram-wait` seconds (300) of that, it exits 75 saying how
much is missing and who holds the RAM. An ask bigger than the machine is refused at once.
Every leased run prints the RAM it really took, so `--ram` is a measurement, not a guess.

A person can take the GPU over (the Cubric-Vision GPU desk does this):

    python gpu_lease.py run --front -- <hold>   wait first in line, ahead of every agent
    python gpu_lease.py interrupt --by Fabio    stop the leased command now
    python gpu_lease.py pause 3 / unpause 3     hold queue ticket 3 in place, or let it go
    python gpu_lease.py status --json           all of it as data, sessions and progress included

A command may write its progress (0..1) to the file named by $MPI_KANBAN_GPU_PROGRESS;
`status --json` shows it, so whoever wants the GPU can see how far along the job is.

Exit codes: the child's; 75 when the child never ran (the wait timed out, or RAM stayed
short with the GPU free -- the message says which); 76 when a
person took the GPU over and stopped the child -- what it finished is kept, re-run only
the rest (a re-run waits in the queue until they release).

Run self-check:  python gpu_lease.py --selftest
"""
import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

SLOT_ENV = "MPI_KANBAN_GPU_SLOT"
PROGRESS_ENV = "MPI_KANBAN_GPU_PROGRESS"  # a file the command may write its progress to, 0..1
WAIT_TIMEOUT = 75  # EX_TEMPFAIL: the wait expired, the command did not run
TAKEN_OVER = 76  # a person took the GPU over (`interrupt`): the command was stopped, re-run what is left
TICKET_LOCK_AT = 1 << 20  # past the ticket's JSON: Windows refuses reads of a locked byte
RAM_FLOOR_GB = 8.0  # kept free on top of a job's --ram (MPI-43: a leased job ran the box to 2.9 GB)
RAM_WAIT = 300.0  # seconds a job stands at its turn, GPU free, short of RAM, before it gives up (MPI-52)
RAM_RECLAIM_EVERY = 120.0  # seconds between two tries at taking idle RAM back


def root():
    """Where leases live. Overridable so the self-check never touches the real one."""
    override = os.environ.get("MPI_KANBAN_GPU_ROOT")
    return override or os.path.join(os.path.expanduser("~"), ".mpi-kanban", "gpu")


def devices():
    """Leasable device indices, newest answer each call.

    `MPI_KANBAN_GPU_DEVICES=0,1` overrides discovery -- needed for the self-check,
    and for a box where `nvidia-smi` enumerates a card that should stay unleased.
    """
    override = os.environ.get("MPI_KANBAN_GPU_DEVICES")
    if override is not None:  # empty means "none", which is not the same as unset
        return [part.strip() for part in override.split(",") if part.strip()]
    try:
        proc = subprocess.run(["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _ollama():
    """Ollama's base URL, read from OLLAMA_HOST the way Ollama itself reads it."""
    host = os.environ.get("OLLAMA_HOST") or "127.0.0.1"
    url = urllib.parse.urlsplit(host if "://" in host else "http://" + host)
    name = url.hostname or "127.0.0.1"
    if name in ("0.0.0.0", "::"):  # a bind-all address: Ollama is reachable on loopback
        name = "127.0.0.1"
    return "%s://%s:%s" % (url.scheme, name, url.port or 11434)


def _ollama_ps():
    """Every model Ollama has loaded, or [] when Ollama is not running.

    The 1 s timeout is what a machine without Ollama pays per check.
    """
    try:
        with urllib.request.urlopen(_ollama() + "/api/ps", timeout=1) as reply:
            return json.load(reply).get("models") or []
    except Exception:  # not running, not Ollama, half an answer: nothing is loaded
        return []


def ollama_models():
    """Names of the models Ollama holds in VRAM right now.

    ponytail: Ollama does not say which GPU it loaded onto, so one loaded model
    marks EVERY slot busy. Right on a one-card box, too strict on several cards;
    per-device needs `nvidia-smi --query-compute-apps` matched to Ollama's pid.
    """
    return [m.get("name", "?") for m in _ollama_ps() if m.get("size_vram", 1)]


def ollama_unload():
    """Unload every model Ollama holds, and wait (15 s at most) until it has.

    Runs as a leased command exits, BEFORE the slot is released, so a model the
    command loaded -- directly or through an app it drove -- leaves with it.
    """
    loaded = [m.get("model") or m.get("name") for m in _ollama_ps()]
    for name in loaded:
        request = urllib.request.Request(
            _ollama() + "/api/generate", json.dumps({"model": name, "keep_alive": 0}).encode(),
            {"Content-Type": "application/json"})
        with contextlib.suppress(Exception):  # never fail the run over a cleanup call
            urllib.request.urlopen(request, timeout=30).close()
    deadline = time.monotonic() + 15
    while loaded and _ollama_ps() and time.monotonic() < deadline:
        time.sleep(0.5)
    if loaded:
        print("mpi-kanban: unloaded Ollama %s" % ", ".join(loaded), file=sys.stderr, flush=True)


def ram():
    """System RAM in GB: {available_gb, total_gb, commit_available_gb}, or {} when unreadable.

    Available counts standby memory (Task Manager's "Available"), which the OS hands
    back on demand. Commit headroom is shown by `status` but gates nothing: with a
    system-managed page file Windows grows the commit limit on demand, so headroom
    reads 16 GB on a box that can still commit a 45 GB job (measured 2026-11-21).
    `MPI_KANBAN_RAM_FILE` names a JSON file read instead, for the self-check.
    """
    fake = os.environ.get("MPI_KANBAN_RAM_FILE")
    if fake:
        return _read(fake)
    gb = 1024.0 ** 3
    try:
        if os.name == "nt":
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                    (name, ctypes.c_ulonglong) for name in (
                        "total", "avail", "total_page", "avail_page", "total_virtual",
                        "avail_virtual", "avail_extended")]

            status = Status(length=ctypes.sizeof(Status))
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return {}
            return {"available_gb": round(status.avail / gb, 1), "total_gb": round(status.total / gb, 1),
                    "commit_available_gb": round(status.avail_page / gb, 1)}
        with open("/proc/meminfo") as handle:
            info = {line.split(":")[0]: int(line.split()[1]) * 1024 for line in handle}
        return {"available_gb": round(info["MemAvailable"] / gb, 1),
                "total_gb": round(info["MemTotal"] / gb, 1),
                "commit_available_gb": round((info["CommitLimit"] - info["Committed_AS"]) / gb, 1)}
    except (OSError, ValueError, KeyError, IndexError, AttributeError):
        return {}  # ponytail: no reader for this OS (macOS) -- no RAM gate, never a hang


def ram_floor():
    """GB that must stay free on top of what a job declares (`MPI_KANBAN_RAM_FLOOR_GB`, default 8)."""
    try:
        return float(os.environ.get("MPI_KANBAN_RAM_FLOOR_GB") or RAM_FLOOR_GB)
    except ValueError:
        return RAM_FLOOR_GB


def _ram_short(need):
    """Why a job declaring `need` GB may not start yet, or None. Unreadable RAM never blocks."""
    if not need:
        return None
    free, floor = ram(), ram_floor()
    available = free.get("available_gb", float("inf"))
    if available < need + floor:
        return ("it needs %g GB of RAM free (%g GB declared + %g GB kept spare), %.1f GB is free: "
                "%.3g GB short" % (need + floor, need, floor, available, need + floor - available))
    return None


def _ram_never(need):
    """Why a job declaring `need` GB can never start on this machine, or None."""
    total = ram().get("total_gb") if need else None
    if total and need + ram_floor() > total:
        return ("it declares %g GB of RAM + %g GB kept spare, and this machine has %g GB in all"
                % (need, ram_floor(), total))
    return None


def ram_holders(top=6):
    """The apps holding the most RAM, biggest first: [{name, gb, count}], [] when unreadable.

    Processes are summed by name, so 40 small windows of one app show as the one big holder
    they are. `MPI_KANBAN_PROCS_FILE` names a JSON list of [name, GB] read instead (self-check).
    """
    rows = []
    try:
        fake = os.environ.get("MPI_KANBAN_PROCS_FILE")
        if fake:
            rows = [(name, float(size)) for name, size in _read(fake) or []]
        elif os.name == "nt":
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process | ForEach-Object { $_.ProcessName + '|' + $_.WorkingSet64 }"],
                capture_output=True, text=True, timeout=30, creationflags=0x08000000).stdout  # no window
            rows = [(line.rsplit("|", 1)[0], int(line.rsplit("|", 1)[1]) / 1024.0 ** 3)
                    for line in out.splitlines() if "|" in line]
        else:
            out = subprocess.run(["ps", "-eo", "rss=,comm="], capture_output=True, text=True,
                                 timeout=30).stdout
            rows = [(os.path.basename(line.split(None, 1)[1]), int(line.split(None, 1)[0]) / 1024.0 ** 2)
                    for line in out.splitlines() if len(line.split(None, 1)) == 2]
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return []
    apps = {}
    for name, size in rows:
        app = apps.setdefault(name, {"name": name, "gb": 0.0, "count": 0})
        app["gb"] += size
        app["count"] += 1
    biggest = sorted(apps.values(), key=lambda app: -app["gb"])[:top]
    return [dict(app, gb=round(app["gb"], 1)) for app in biggest]


def _holders_text(holders):
    return ", ".join("%s %g GB (%d)" % (app["name"], app["gb"], app["count"]) for app in holders)


def ram_trim():
    """Ask Windows to take idle memory back from every other program; how many it trimmed.

    What a "free memory" button does (`EmptyWorkingSet`): pages a program is not touching
    leave its working set and become Available. Nothing is closed and nothing is lost -- a
    program that wants a page back gets it back, a little slower the first time. Only
    programs this user may adjust are reached. Windows only; never run on a fake RAM
    reader, so the self-check does not trim the real machine.
    """
    if os.name != "nt" or os.environ.get("MPI_KANBAN_RAM_FILE"):
        return 0
    import ctypes
    from ctypes import wintypes
    kernel, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
    pids = (wintypes.DWORD * 8192)()
    used = wintypes.DWORD()
    if not psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(used)):
        return 0
    trimmed = 0
    for pid in pids[:used.value // ctypes.sizeof(wintypes.DWORD)]:
        if pid in (0, os.getpid()):
            continue
        handle = kernel.OpenProcess(0x0100 | 0x1000, False, pid)  # SET_QUOTA | QUERY_LIMITED_INFORMATION
        if not handle:
            continue  # not ours to adjust (system, another user)
        trimmed += bool(psapi.EmptyWorkingSet(handle))
        kernel.CloseHandle(handle)
    return trimmed


def _engines():
    """ComfyUI engines whose cached models the lease may unload: `MPI_KANBAN_COMFYUI`
    (comma-separated URLs), else `comfyui` in `<root>/config.json`. None by default."""
    override = os.environ.get("MPI_KANBAN_COMFYUI")
    if override is not None:
        return [url.strip().rstrip("/") for url in override.split(",") if url.strip()]
    return [url.rstrip("/") for url in _read(os.path.join(root(), "config.json")).get("comfyui") or []]


def comfy_free():
    """Ask every IDLE ComfyUI engine to unload its cached models; the URLs asked.

    An engine keeps the last job's models in RAM for the next one, which then unloads them
    itself -- so they are not RAM the next job lacks. Idle means nothing running or pending
    in its queue; an engine with a job is never touched. Call it holding the slot, so no
    leased job is mid-run.
    """
    asked = []
    for url in _engines():
        try:
            with urllib.request.urlopen(url + "/queue", timeout=3) as reply:
                queue = json.load(reply)
            if queue.get("queue_running") or queue.get("queue_pending"):
                continue
            request = urllib.request.Request(
                url + "/free", json.dumps({"unload_models": True, "free_memory": True}).encode(),
                {"Content-Type": "application/json"})
            urllib.request.urlopen(request, timeout=10).close()
            asked.append(url)
        except Exception:  # not running, not ComfyUI: nothing to free there
            continue
    return asked


def _ram_reclaim(need, short):
    """Take back RAM nobody is using, then say again why the job may not start (or None).

    Run by a job at its turn, holding the free slot, before RAM is called short.
    """
    trimmed, asked = ram_trim(), comfy_free()
    if trimmed:
        print("mpi-kanban: short of RAM, so asked Windows to take idle memory back from %d programs"
              % trimmed, file=sys.stderr, flush=True)
    if asked:
        print("mpi-kanban: short of RAM, so asked the idle engine at %s to unload its cached models"
              % ", ".join(asked), file=sys.stderr, flush=True)
    deadline = time.monotonic() + (20 if trimmed or asked else 0)
    while short and time.monotonic() < deadline:
        time.sleep(1)
        short = _ram_short(need)
    return short


def _take(handle, at=0):
    """Take the exclusive lock on byte `at`, or report that someone else holds it."""
    handle.seek(at)  # msvcrt locks from the CURRENT position, and 'a+' need not be 0
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def acquire(index):
    """An open handle holding device `index`, or None. Closing it releases."""
    os.makedirs(root(), exist_ok=True)
    handle = open(os.path.join(root(), "%s.lock" % index), "a+")
    if _take(handle):
        return handle
    handle.close()
    return None


def _owner_path(index):
    return os.path.join(root(), "%s.owner.json" % index)


def _who(argv, reason=None, ram_gb=None):
    """The holder or waiter record. `session` is the agent session that ran us, so an
    app that session launched can tell its own lease from a peer's (`status --json`).
    `ram` is the GB the job declared with `run --ram`, None when it declared none."""
    return {"pid": os.getpid(), "repo": os.getcwd(), "session": os.environ.get("CLAUDE_CODE_SESSION_ID"),
            "since": time.strftime("%Y-%m-%dT%H:%M:%S"), "command": " ".join(argv), "reason": reason,
            "ram": ram_gb}


def _side(index, kind):
    """`<index>.takeover` (who took the slot over) or `<index>.progress` (the command's own 0..1)."""
    return os.path.join(root(), "%s.%s" % (index, kind))


def _read(path):
    """A display record, or {} when it is gone or half-written."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def _describe(index, record):
    """Who holds the slot, for `status` and for the guard's block message.

    ponytail: display only. Liveness is decided by trying the lock, never by
    reading this -- a killed holder leaves the file behind and the lock gone.
    """
    try:
        with open(_owner_path(index), "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=1)
    except OSError:
        pass  # never fail the run over a display file


def _forget(index):
    for path in (_owner_path(index), _side(index, "progress"), _side(index, "takeover")):
        with contextlib.suppress(OSError):
            os.remove(path)


def _paused(ticket_path):
    return ticket_path[:-len(".ticket")] + ".paused"


def _queue_dir():
    return os.path.join(root(), "queue")


@contextlib.contextmanager
def _queue_lock():
    """Serialise the queue, so no ticket is ever probed between its creation and its lock.

    Held for a directory listing at most; a crashed holder drops it like any other.
    """
    os.makedirs(_queue_dir(), exist_ok=True)
    with open(os.path.join(_queue_dir(), "queue.lock"), "a+") as handle:
        while not _take(handle):
            time.sleep(0.01)
        yield


def _tickets():
    """Live ticket paths, first in line first. Call under `_queue_lock`.

    Live means the owner still holds the ticket's lock -- the kernel decides, never
    a pid, which Windows reuses. A dead ticket is deleted on sight.
    """
    live = []
    for name in sorted(os.listdir(_queue_dir())):  # zero-padded, so name order is number order
        if not name.endswith(".ticket"):
            continue
        path = os.path.join(_queue_dir(), name)
        try:
            with open(path, "r+b") as probe:
                if not _take(probe, TICKET_LOCK_AT):
                    live.append(path)
                    continue
        except OSError:
            continue  # its owner just left
        for dead in (path, _paused(path)):
            with contextlib.suppress(OSError):
                os.remove(dead)
    return live


def _enqueue(argv, reason=None, front=False, ram_gb=None):
    """Join the queue: (ticket, how many are ahead). Stay in line by keeping it open.

    `front` takes ticket 0, ahead of every numbered waiter: a person taking the GPU over
    (`run --front`). There is one front place; a second front waiter is refused.
    """
    with _queue_lock():
        live = _tickets()
        numbers = [int(name.split(".")[0]) for name in os.listdir(_queue_dir())
                   if name.endswith(".ticket")]
        number = 0 if front else max(numbers, default=0) + 1
        path = os.path.join(_queue_dir(), "%012d.ticket" % number)
        with contextlib.suppress(OSError):
            os.remove(_paused(path))  # a dead waiter's pause never passes to the next owner of the number
        ticket = open(path, "x+b")  # raises FileExistsError for a second live front waiter
        ticket.write(json.dumps(_who(argv, reason, ram_gb)).encode("utf-8"))
        ticket.flush()
        _take(ticket, TICKET_LOCK_AT)  # nobody can probe it yet: we hold the queue lock
    return ticket, 0 if front else len(live)


def _first(ticket):
    """True when it is `ticket`'s turn: no live waiter ahead of it could start now.

    A waiter ahead is passed while it is paused (`pause`) or short of the RAM it declared
    (MPI-52). Each keeps its place: the moment it could start, it is ahead again. Any waiter
    can tell, because a ticket records its `ram` and free RAM is one reading for the machine.
    Whether `ticket` itself has the RAM is its owner's check, not this one.
    """
    with _queue_lock():
        for path in _tickets():
            if os.path.exists(_paused(path)):
                if path == ticket.name:
                    return False
                continue
            if path == ticket.name:
                return True
            if not _ram_short(_read(path).get("ram")):
                return False
    return False


def _leave(ticket):
    """Step out of line, once. Under the queue lock, or a late delete could hit the
    next ticket to reuse this number."""
    if ticket.closed:
        return
    with _queue_lock():
        ticket.close()
        with contextlib.suppress(OSError):
            os.remove(ticket.name)


def _hold(index, argv, reason, ram_gb=None):
    """Run the command on slot `index` (lease already held): its exit code, or TAKEN_OVER."""
    record = _who(argv, reason, ram_gb)
    _describe(index, record)
    print("mpi-kanban: GPU %s leased" % index, file=sys.stderr, flush=True)
    child = dict(os.environ, CUDA_VISIBLE_DEVICES=str(index),
                 **{SLOT_ENV: str(index), PROGRESS_ENV: _side(index, "progress")})
    start = low = ram().get("available_gb")
    with subprocess.Popen(argv, env=child) as proc:
        _describe(index, dict(record, child_pid=proc.pid))  # what `interrupt` stops
        try:
            while True:
                try:
                    code = proc.wait(timeout=5)
                    break
                except subprocess.TimeoutExpired:  # sample free RAM: what did the job really take?
                    low = min(low, ram().get("available_gb", low)) if low is not None else None
        except BaseException:  # Ctrl-C, as subprocess.call does it
            proc.kill()
            raise
    if start is not None and (ram_gb or start - low >= 2):
        print("mpi-kanban: RAM free went from %.1f GB to %.1f GB at the lowest: the job took about "
              "%.0f GB%s. Declare a measured figure with `run --ram <GB>`, never a guess."
              % (start, low, start - low, " (it declared %g GB)" % ram_gb if ram_gb else ""),
              file=sys.stderr, flush=True)
    taken = _read(_side(index, "takeover"))
    if taken.get("lease_pid") == os.getpid():
        print("mpi-kanban: GPU %s taken over by %s, your command was stopped (exit %d).\n"
              "  Work it finished is kept: re-run only what did not finish. A re-run waits in\n"
              "  the queue and starts when %s releases the GPU."
              % (index, taken.get("by", "a person"), TAKEN_OVER, taken.get("by", "they")),
              file=sys.stderr, flush=True)
        return TAKEN_OVER
    return code


def cmd_run(argv, poll, timeout, reason=None, front=False, ram_gb=None, ram_wait=RAM_WAIT):
    if os.environ.get(SLOT_ENV):
        return subprocess.call(argv)  # already inside a lease; nesting must not deadlock
    slots = devices()
    if not slots:
        print("mpi-kanban: no NVIDIA device found, running unleased", file=sys.stderr)
        return subprocess.call(argv)
    never = _ram_never(ram_gb)
    if never:  # queueing it would only make it wait for RAM that cannot come
        print("mpi-kanban: command not run (exit %d): it can never start here, %s.\n"
              "  Do not re-run it as it is. Measure what the job takes (a leased run prints it) and\n"
              "  declare that, or run it on a bigger machine." % (WAIT_TIMEOUT, never),
              file=sys.stderr, flush=True)
        return WAIT_TIMEOUT

    deadline = time.monotonic() + timeout
    said = None  # what the wait was last announced as: "gpu" or "ram"
    stuck = 0.0  # seconds spent at our turn with a free GPU and too little RAM
    reclaimed = None  # when idle RAM was last taken back
    try:
        ticket, ahead = _enqueue(argv, reason, front, ram_gb)
    except FileExistsError:
        print("mpi-kanban: someone else is already first in line (run --front).", file=sys.stderr)
        return WAIT_TIMEOUT
    try:
        while True:
            first = _first(ticket)  # only the waiter whose turn it is may try a slot
            held = ollama_models() if first else []  # ...and not while Ollama sits in VRAM
            # ...nor does it start short of RAM (MPI-43). It keeps its place and the waiters
            # behind it that fit go ahead (`_first`), so a free GPU is never left idle (MPI-52).
            short = _ram_short(ram_gb)
            for index in (slots if first and not held else []):
                handle = acquire(index)
                if not handle:
                    continue
                if short and (reclaimed is None or time.monotonic() - reclaimed >= RAM_RECLAIM_EVERY):
                    # RAM alone holds us, and we hold the slot, so no leased job is mid-run:
                    # take back what nobody is using before calling RAM short
                    short = _ram_reclaim(ram_gb, short)
                    reclaimed = time.monotonic()
                if short:
                    handle.close()  # a free GPU we cannot use: leave it to a job that fits
                    stuck += poll
                    break
                _leave(ticket)  # the next waiter is first in line now
                free = ram()
                if not ram_gb and free.get("available_gb", float("inf")) < ram_floor():
                    print("mpi-kanban: warning: %.1f GB RAM available, under the %g GB floor. Running\n"
                          "  anyway; pass `run --ram <GB>` and the lease waits until the job fits."
                          % (free["available_gb"], ram_floor()), file=sys.stderr, flush=True)
                with handle:
                    try:
                        return _hold(index, argv, reason, ram_gb)
                    finally:
                        ollama_unload()
                        _forget(index)
            if short and stuck >= ram_wait:
                holders = _holders_text(ram_holders())
                print("mpi-kanban: command not run (exit %d): the GPU was free for %d s but RAM was not, "
                      "%s.\n"
                      "  Idle memory was already taken back. It starts when that much more RAM is freed%s,\n"
                      "  or when it is re-run declaring less: if `--ram %g` was a guess, measure it (a leased\n"
                      "  run prints the RAM it took). Tell the user this in these words; do not just re-run."
                      % (WAIT_TIMEOUT, stuck, short,
                         " (holding the most now: %s)" % holders if holders else "", ram_gb),
                      file=sys.stderr, flush=True)
                return WAIT_TIMEOUT
            if time.monotonic() >= deadline:
                print("mpi-kanban: still short of RAM after %gs, command not run: %s" % (timeout, short)
                      if short else
                      "mpi-kanban: every GPU still busy after %gs, command not run.\n"
                      "  `python gpu_lease.py status` names the holder." % timeout,
                      file=sys.stderr, flush=True)
                return WAIT_TIMEOUT
            if said != ("ram" if short else "gpu"):
                print("mpi-kanban: waiting for RAM, not a GPU: %s. It keeps its place; jobs that fit go "
                      "ahead of it meanwhile." % short if short else
                      "mpi-kanban: all %d GPU slots busy, waiting... (%d ahead in the queue)%s"
                      % (len(slots), ahead, "; Ollama holds " + ", ".join(held) if held else ""),
                      file=sys.stderr, flush=True)
                said = "ram" if short else "gpu"
            time.sleep(poll)
    finally:
        _leave(ticket)


def status_doc():
    """Every slot and waiter as data: what `status --json` prints.

    `holder` is the display record of a busy slot ({} when its holder never wrote one),
    `None` on a free slot. Busy is decided by the lock, as everywhere else.
    """
    held = ollama_models()
    slots = []
    for index in devices():
        handle = acquire(index)
        if handle:
            handle.close()  # a probe, as in cmd_status
            slots.append({"index": index, "busy": bool(held), "holder": None, "ollama": held})
        else:
            holder = _read(_owner_path(index))
            try:
                with open(_side(index, "progress"), encoding="utf-8") as handle:
                    holder["progress"] = max(0.0, min(1.0, float(handle.read().strip())))
            except (OSError, ValueError):
                pass  # the command reports none: most do not
            slots.append({"index": index, "busy": True, "holder": holder, "ollama": held})
    with _queue_lock():
        queue = [dict(_read(path), ticket=int(os.path.basename(path).split(".")[0]),
                      paused=os.path.exists(_paused(path))) for path in _tickets()]
    for waiter in queue:  # why it waits when it is not the GPU: a plain sentence, or None
        waiter["ram_short"] = _ram_short(waiter.get("ram"))
    memory = dict(ram(), floor_gb=ram_floor())
    if any(waiter["ram_short"] for waiter in queue):
        memory["holders"] = ram_holders()  # who has the RAM, only when someone lacks it
    return {"slots": slots, "queue": queue, "ram": memory}


def _kill_tree(pid):
    if os.name == "nt":
        return subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                              capture_output=True).returncode == 0
    try:  # ponytail: the child alone; its own children are its business on POSIX
        os.kill(pid, 15)
        return True
    except OSError:
        return False


def cmd_interrupt(by):
    """Stop every leased command now, so the slot frees for whoever is first in line.

    The holder's `run` sees the `<index>.takeover` record naming its own pid and exits
    TAKEN_OVER instead of the command's code, so the agent reads "taken over", not a failure.
    """
    stopped = 0
    for slot in status_doc()["slots"]:
        holder = slot["holder"] or {}
        if not holder.get("child_pid"):
            continue
        with open(_side(slot["index"], "takeover"), "w", encoding="utf-8") as handle:
            json.dump({"by": by, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "lease_pid": holder.get("pid")}, handle)
        if _kill_tree(holder["child_pid"]):
            stopped += 1
            print("GPU %s  stopped pid %s  %s" % (slot["index"], holder["child_pid"],
                                                 holder.get("command", "?")))
    return 0 if stopped else 1


def cmd_pause(number, on):
    """Hold queue ticket `number` in place (`on`) or let it go again. It keeps its place."""
    path = os.path.join(_queue_dir(), "%012d.ticket" % number)
    with _queue_lock():
        if path not in _tickets():
            print("no live ticket %d" % number, file=sys.stderr)
            return 1
        if on:
            open(_paused(path), "w").close()
        else:
            with contextlib.suppress(OSError):
                os.remove(_paused(path))
    return 0


def cmd_status(as_json=False):
    if as_json:
        print(json.dumps(status_doc()))
        return 0
    free = ram()
    print("RAM   %s GB available of %s GB, %s GB commit left, floor %g GB" % (
        free.get("available_gb", "?"), free.get("total_gb", "?"), free.get("commit_available_gb", "?"),
        ram_floor()) if free else "RAM   unreadable, no RAM gate")
    slots = devices()
    if not slots:
        print("no NVIDIA device found")
        return 0
    held = ollama_models()
    for index in slots:
        handle = acquire(index)
        if handle:
            handle.close()  # a probe: held for an instant, so a waiter may miss one poll
            print("GPU %s  busy   ollama holds %s" % (index, ", ".join(held)) if held
                  else "GPU %s  free" % index)
            continue
        owner = _read(_owner_path(index))
        print("GPU %s  busy   %s  pid %s  since %s%s  %s" % (
            index, owner.get("repo", "?"), owner.get("pid", "?"), owner.get("since", "?"),
            "  ram %g GB" % owner["ram"] if owner.get("ram") else "", owner.get("command", "?")))
    with _queue_lock():
        waiters = [_read(path) for path in _tickets()]
    blocked = []
    for place, waiter in enumerate(waiters, 1):
        print("queue %d  %s  pid %s  since %s%s  %s" % (
            place, waiter.get("repo", "?"), waiter.get("pid", "?"), waiter.get("since", "?"),
            "  ram %g GB" % waiter["ram"] if waiter.get("ram") else "", waiter.get("command", "?")))
        short = _ram_short(waiter.get("ram"))
        if short:
            blocked.append("Queue %d waits for RAM, not the GPU: %s. Jobs behind it that fit go ahead; "
                           "it starts when that much RAM is freed, or is re-run declaring less."
                           % (place, short))
    for line in blocked:
        print(line)
    holders = _holders_text(ram_holders())
    if holders:
        print("RAM is held mostly by: %s  (app, GB in RAM, how many processes)" % holders)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action")
    runner = sub.add_parser("run", help="hold a GPU slot for one command")
    runner.add_argument("--timeout", type=float, default=1800,
                        help="seconds to wait for a free slot (default 1800)")
    runner.add_argument("--poll", type=float, default=15,
                        help="seconds between retries (default 15)")
    runner.add_argument("--reason", help="what the job is, shown by status")
    runner.add_argument("--front", action="store_true",
                        help="go ahead of every waiter (a person taking the GPU over)")
    runner.add_argument("--ram", type=float, metavar="GB",
                        help="system RAM the job will use; it starts only when that much plus the "
                             "floor (MPI_KANBAN_RAM_FLOOR_GB, default 8) is available")
    runner.add_argument("--ram-wait", type=float, default=RAM_WAIT, metavar="S",
                        help="seconds to stand at its turn with a free GPU and too little RAM before "
                             "giving up with exit 75 (default %g)" % RAM_WAIT)
    runner.add_argument("argv", nargs=argparse.REMAINDER)
    status = sub.add_parser("status", help="which slots are free, and who holds the rest")
    status.add_argument("--json", action="store_true", help="print it as one JSON object")
    stop = sub.add_parser("interrupt", help="stop the leased command(s); they exit %d" % TAKEN_OVER)
    stop.add_argument("--by", default="a person", help="who took over, told to the holder")
    for name, text in (("pause", "hold a queued waiter in place"), ("unpause", "let it go again")):
        sub.add_parser(name, help=text).add_argument("ticket", type=int)
    args = parser.parse_args()

    if args.action == "status":
        return cmd_status(args.json)
    if args.action == "interrupt":
        return cmd_interrupt(args.by)
    if args.action in ("pause", "unpause"):
        return cmd_pause(args.ticket, args.action == "pause")
    if args.action == "run":
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        if not argv:
            parser.error("run needs a command: gpu_lease.py run -- python train.py")
        return cmd_run(argv, args.poll, args.timeout, args.reason, args.front, args.ram, args.ram_wait)
    parser.print_help()
    return 2


def _selftest():
    import http.server
    import threading

    loaded = []  # the fake Ollama's VRAM: what /api/ps answers
    comfy = {"running": [], "freed": 0, "frees_to": None}  # the fake ComfyUI engine, same server

    class FakeOllama(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # /api/ps, or ComfyUI's /queue
            if self.path == "/queue":
                return self._reply({"queue_running": comfy["running"], "queue_pending": []})
            self._reply({"models": loaded})

        def do_POST(self):  # /api/generate: keep_alive 0 unloads, anything else loads
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/free":  # ComfyUI drops its cached models: RAM comes back
                comfy["freed"] += 1
                set_ram(comfy["frees_to"])
                return self._reply({})
            if body.get("keep_alive") == 0:
                loaded[:] = [m for m in loaded if m["model"] != body["model"]]
            else:
                loaded.append({"name": body["model"], "model": body["model"], "size_vram": 1})
            self._reply({"done": True})

        def _reply(self, doc):
            data = json.dumps(doc).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_):
            pass

    # every child points at the fake: a selftest must never unload the user's real models
    fake = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    ollama_host = "127.0.0.1:%d" % fake.server_address[1]

    me = os.path.abspath(__file__)
    scratch = tempfile.mkdtemp(prefix="gpu-lease-")
    ram_file = os.path.join(scratch, "ram.json")  # the fake RAM reader: never this machine's

    def set_ram(available, commit=200):
        with open(ram_file, "w") as handle:
            json.dump({"available_gb": available, "total_gb": 64, "commit_available_gb": commit}, handle)

    set_ram(100)
    procs_file = os.path.join(scratch, "procs.json")  # the fake process list: [name, GB in RAM]
    with open(procs_file, "w") as handle:
        json.dump([["python", 17.0], ["electron", 9.0], ["python", 0.5]], handle)
    base = dict(os.environ, MPI_KANBAN_GPU_ROOT=scratch, MPI_KANBAN_GPU_DEVICES="0",
                OLLAMA_HOST=ollama_host, CLAUDE_CODE_SESSION_ID="selftest", MPI_KANBAN_RAM_FILE=ram_file,
                MPI_KANBAN_PROCS_FILE=procs_file)
    for name in (SLOT_ENV, "MPI_KANBAN_RAM_FLOOR_GB", "MPI_KANBAN_COMFYUI"):
        base.pop(name, None)

    def lease(env, *extra, script="import os;print(os.environ['CUDA_VISIBLE_DEVICES'])"):
        return subprocess.run([sys.executable, me, "run", *extra, "--",
                               sys.executable, "-c", script],
                              env=env, capture_output=True, text=True)

    def holding(seconds):
        proc = subprocess.Popen([sys.executable, me, "run", "--", sys.executable, "-c",
                                 "import time;time.sleep(%s)" % seconds],
                                env=base, stderr=subprocess.PIPE, text=True)
        assert "GPU 0 leased" in proc.stderr.readline(), "holder never took the slot"
        return proc

    log = os.path.join(scratch, "served.log")

    def queued(name, poll):
        """A waiter whose command logs `name`, returned once it is standing in line."""
        proc = subprocess.Popen([sys.executable, me, "run", "--timeout", "30", "--poll", poll,
                                 "--", sys.executable, "-c",
                                 "open(%r, 'a').write(%r)" % (log, name + " ")],
                                env=base, stderr=subprocess.PIPE, text=True)
        assert "waiting" in proc.stderr.readline(), "%s never queued" % name
        return proc

    def served():
        with open(log) as handle:
            names = handle.read().split()
        os.remove(log)
        return names

    holder = holding(30)

    busy = lease(base, "--timeout", "1", "--poll", "0.2")
    assert busy.returncode == WAIT_TIMEOUT, busy
    assert not busy.stdout.strip(), "the command ran without a slot"

    spare = lease(dict(base, MPI_KANBAN_GPU_DEVICES="0,1"), "--timeout", "5", "--poll", "0.2")
    assert spare.stdout.strip() == "1", spare  # multi-GPU: skip the busy slot

    # a wrapped script that wraps another command: pass through the slot it already
    # holds, or the inner call waits forever on a lock its own parent is holding
    nested = lease(dict(base, **{SLOT_ENV: "0"}), "--timeout", "1", script="print('through')")
    assert nested.returncode == 0 and nested.stdout.strip() == "through", nested

    # a waiter killed in line must not hold up the line: its ticket lock dies with it
    ghost = queued("GHOST", "0.2")
    ghost.kill()
    ghost.wait()

    holder.kill()
    holder.wait()
    freed = lease(base, "--timeout", "10", "--poll", "0.2")
    assert freed.stdout.strip() == "0", "the kernel did not release a killed holder"

    again = lease(base, "--timeout", "5", "--poll", "0.2")
    assert again.stdout.strip() == "0", "a holder that exited normally still holds it"

    # first come, first served: the slow poller queued first, so it goes first
    holder = holding(5)
    early, late = queued("EARLY", "1"), queued("LATE", "0.05")
    status = subprocess.run([sys.executable, me, "status"], env=base,
                            capture_output=True, text=True).stdout
    rows = [row for row in status.splitlines() if row.startswith("queue")]
    assert len(rows) == 2 and "EARLY" in rows[0] and "LATE" in rows[1], status
    # the same, as data, naming the session that holds and waits (an agent's app reads this)
    doc = json.loads(subprocess.run([sys.executable, me, "status", "--json"], env=base,
                                    capture_output=True, text=True).stdout)
    assert doc["slots"][0]["busy"] and doc["slots"][0]["holder"]["session"] == "selftest", doc
    assert [w["session"] for w in doc["queue"]] == ["selftest", "selftest"], doc
    assert "EARLY" in doc["queue"][0]["command"], doc
    for proc in (holder, early, late):
        proc.wait()
    assert served() == ["EARLY", "LATE"], "a later, faster-polling waiter jumped the queue"

    # a holder that re-queues the moment it releases goes BEHIND whoever was waiting
    holder = holding(3)
    waiter = queued("WAITER", "2")
    holder.wait()
    lease(base, "--poll", "0.05", "--timeout", "30", script="open(%r, 'a').write('HOLDER ')" % log)
    waiter.wait()
    assert served() == ["WAITER", "HOLDER"], "a re-queued holder starved the waiter"

    # --front goes ahead of a waiter that queued earlier
    holder = holding(3)
    waiter = queued("WAITER", "0.2")
    front = subprocess.Popen([sys.executable, me, "run", "--front", "--timeout", "30", "--poll", "0.2",
                              "--", sys.executable, "-c", "open(%r, 'a').write('FRONT ')" % log],
                             env=base, stderr=subprocess.PIPE, text=True)
    assert "waiting" in front.stderr.readline(), "front never queued"
    for proc in (holder, waiter, front):
        proc.wait()
    assert served() == ["FRONT", "WAITER"], "--front did not jump the queue"

    # a paused waiter keeps its place but is passed over until unpaused
    holder = holding(3)
    first, second = queued("FIRST", "0.2"), queued("SECOND", "0.2")
    tickets = json.loads(subprocess.run([sys.executable, me, "status", "--json"], env=base,
                                        capture_output=True, text=True).stdout)["queue"]
    number = [w["ticket"] for w in tickets if "FIRST" in w["command"]][0]
    subprocess.run([sys.executable, me, "pause", str(number)], env=base, check=True)
    assert [w["paused"] for w in json.loads(subprocess.run(
        [sys.executable, me, "status", "--json"], env=base, capture_output=True, text=True).stdout)["queue"]
            ] == [True, False]
    holder.wait()
    second.wait()
    subprocess.run([sys.executable, me, "unpause", str(number)], env=base, check=True)
    first.wait()
    assert served() == ["SECOND", "FIRST"], "a paused waiter was served, or never resumed"

    # interrupt: the command is stopped, its run exits TAKEN_OVER naming who, the slot frees,
    # and the progress the command wrote shows in status while it holds
    report = ("import os,time;open(os.environ[%r],'w').write('0.2');time.sleep(60)" % PROGRESS_ENV)
    victim = subprocess.Popen([sys.executable, me, "run", "--reason", "sweep", "--", sys.executable,
                               "-c", report], env=base, stderr=subprocess.PIPE, text=True)
    assert "GPU 0 leased" in victim.stderr.readline()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        slot = json.loads(subprocess.run([sys.executable, me, "status", "--json"], env=base,
                                         capture_output=True, text=True).stdout)["slots"][0]
        if slot["holder"].get("progress") is not None and slot["holder"].get("child_pid"):
            break
        time.sleep(0.2)
    assert slot["holder"]["progress"] == 0.2 and slot["holder"]["reason"] == "sweep", slot
    stop = subprocess.run([sys.executable, me, "interrupt", "--by", "Fabio"], env=base,
                          capture_output=True, text=True)
    assert stop.returncode == 0, stop
    assert victim.wait(timeout=20) == TAKEN_OVER, "an interrupted run did not exit TAKEN_OVER"
    assert "taken over by Fabio" in victim.stderr.read()
    after = lease(base, "--timeout", "5", "--poll", "0.2")
    assert after.returncode == 0 and after.stdout.strip() == "0", "the slot stayed held"
    assert subprocess.run([sys.executable, me, "interrupt"], env=base,
                          capture_output=True).returncode == 1, "nothing to stop must say so"

    none = lease(dict(base, MPI_KANBAN_GPU_DEVICES=""), "--timeout", "1")
    assert none.stdout.strip() == "", none
    assert none.returncode == 1, "no CUDA_VISIBLE_DEVICES is set when unleased"

    # MPI-43 still holds: a job that declares --ram never starts short of that much plus the floor.
    # MPI-52: but it no longer holds the line. The 2026-11-26 stall: GPU free, the head short of
    # RAM, five sessions frozen behind it for 2.5 h. A job behind it that fits goes ahead.
    set_ram(20)
    big = subprocess.Popen([sys.executable, me, "run", "--ram", "40", "--timeout", "30", "--poll", "0.2",
                            "--", sys.executable, "-c", "open(%r, 'a').write('BIG ')" % log],
                           env=base, stderr=subprocess.PIPE, text=True)
    said = big.stderr.readline()
    assert "waiting for RAM" in said and "20.0 GB is free" in said and "8 GB kept spare" in said, said
    small = lease(base, "--timeout", "10", "--poll", "0.05", script="open(%r, 'a').write('SMALL ')" % log)
    assert small.returncode == 0, "a job that fits stayed frozen behind one waiting for RAM: %s" % small.stderr
    fits = lease(base, "--ram", "5", "--timeout", "10", "--poll", "0.05")
    assert fits.returncode == 0 and "took about" in fits.stderr, fits  # ...and reports what it used
    assert big.poll() is None, "a job started while RAM was short"
    assert served() == ["SMALL"], "the job short of RAM ran, or the one that fits did not"
    doc = json.loads(subprocess.run([sys.executable, me, "status", "--json"], env=base,
                                    capture_output=True, text=True).stdout)
    assert doc["ram"]["available_gb"] == 20 and doc["ram"]["floor_gb"] == 8, doc
    assert [w["ram"] for w in doc["queue"]] == [40], doc
    assert "28 GB short" in doc["queue"][0]["ram_short"], doc
    assert doc["ram"]["holders"][0] == {"name": "python", "gb": 17.5, "count": 2}, doc
    status = subprocess.run([sys.executable, me, "status"], env=base, capture_output=True, text=True).stdout
    assert "RAM   20 GB available of 64 GB" in status and "ram 40 GB" in status, status
    assert "waits for RAM, not the GPU" in status and "python 17.5 GB (2)" in status, status

    # it kept its place: once RAM is back it goes before a job that queued after it
    holder = holding(4)
    later = queued("LATER", "0.2")
    set_ram(50)  # 50 >= 40 + 8
    for proc in (holder, big, later):
        assert proc.wait(timeout=20) == 0
    assert served() == ["BIG", "LATER"], "the job that waited for RAM lost its place"

    # an ask the machine can never meet (60 + 8 > 64) is refused at once instead of queueing
    began = time.monotonic()
    never = lease(base, "--ram", "60", "--timeout", "30")
    assert never.returncode == WAIT_TIMEOUT and not never.stdout.strip(), never
    assert "can never start" in never.stderr and time.monotonic() - began < 10, never.stderr

    # GPU free, RAM short: it gives up after --ram-wait with one plain sentence and the holders,
    # so its session is woken instead of dying silently at a two-hour timeout
    set_ram(30)
    gave_up = lease(base, "--ram", "40", "--ram-wait", "1", "--timeout", "30", "--poll", "0.2")
    assert gave_up.returncode == WAIT_TIMEOUT and not gave_up.stdout.strip(), gave_up
    assert "the GPU was free" in gave_up.stderr and "18 GB short" in gave_up.stderr, gave_up.stderr
    assert "python 17.5 GB (2)" in gave_up.stderr, gave_up.stderr

    # before RAM is called short, an idle ComfyUI engine is asked to unload its cached models
    # (the next job would unload them itself); one with a job in its queue is left alone
    engine = dict(base, MPI_KANBAN_COMFYUI="http://" + ollama_host)
    comfy["running"] = ["a peer's job"]
    busy_engine = lease(engine, "--ram", "40", "--ram-wait", "1", "--timeout", "30", "--poll", "0.2")
    assert busy_engine.returncode == WAIT_TIMEOUT and comfy["freed"] == 0, busy_engine
    comfy["running"] = []
    comfy["frees_to"] = 100
    unloaded = lease(engine, "--ram", "40", "--timeout", "30", "--poll", "0.2")
    assert unloaded.returncode == 0 and unloaded.stdout.strip() == "0", unloaded
    assert comfy["freed"] == 1 and "unload its cached models" in unloaded.stderr, unloaded.stderr

    # a timeout says it was RAM, not the GPU; low commit headroom alone never blocks
    set_ram(30)
    short = lease(base, "--ram", "40", "--timeout", "1", "--poll", "0.2")
    assert short.returncode == WAIT_TIMEOUT and not short.stdout.strip(), short
    assert "still short of RAM" in short.stderr, short.stderr
    set_ram(100, commit=10)
    committed = lease(base, "--ram", "40", "--timeout", "5", "--poll", "0.2")
    assert committed.returncode == 0 and committed.stdout.strip() == "0", committed

    # no --ram: today's behaviour, plus a warning under the floor
    set_ram(4)
    warned = lease(base, "--timeout", "5", "--poll", "0.2")
    assert warned.returncode == 0 and "under the 8 GB floor" in warned.stderr, warned
    floor = lease(dict(base, MPI_KANBAN_RAM_FLOOR_GB="2"), "--timeout", "5", "--poll", "0.2")
    assert floor.returncode == 0 and "warning" not in floor.stderr, floor

    # unreadable RAM never blocks
    blind = lease(dict(base, MPI_KANBAN_RAM_FILE=os.path.join(scratch, "missing.json")),
                  "--ram", "40", "--timeout", "5", "--poll", "0.2")
    assert blind.returncode == 0 and blind.stdout.strip() == "0", blind
    set_ram(100)

    # MPI-41: a model Ollama keeps in VRAM is the GPU busy, though no lease holds the slot
    loaded.append({"name": "big:9b", "model": "big:9b", "size_vram": 7400000000})
    status = subprocess.run([sys.executable, me, "status"], env=base,
                            capture_output=True, text=True).stdout
    assert "GPU 0  busy   ollama holds big:9b" in status, status
    blocked = lease(base, "--timeout", "1", "--poll", "0.2")
    assert blocked.returncode == WAIT_TIMEOUT and not blocked.stdout.strip(), blocked
    assert "Ollama holds big:9b" in blocked.stderr, blocked.stderr

    # a model in system RAM only is not on the GPU; and whatever the leased command
    # loads into Ollama is unloaded before the slot is released
    loaded[:] = [{"name": "cpu:1b", "model": "cpu:1b", "size_vram": 0}]
    load = ("import json,urllib.request as u;u.urlopen(u.Request('http://%s/api/generate',"
            "json.dumps({'model':'child:1b'}).encode())).close()" % ollama_host)
    used = lease(base, "--timeout", "5", "--poll", "0.2", script=load)
    assert used.returncode == 0, used
    assert loaded == [], "a model outlived the lease that loaded it: %s" % loaded
    assert "unloaded Ollama cpu:1b, child:1b" in used.stderr, used.stderr

    fake.shutdown()
    print("gpu_lease selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
