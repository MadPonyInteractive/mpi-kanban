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

Exit codes: the child's, or 75 when the wait timed out and the child never ran.

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

SLOT_ENV = "MPI_KANBAN_GPU_SLOT"
WAIT_TIMEOUT = 75  # EX_TEMPFAIL: the wait expired, the command did not run
TICKET_LOCK_AT = 1 << 20  # past the ticket's JSON: Windows refuses reads of a locked byte


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


def _who(argv):
    return {"pid": os.getpid(), "repo": os.getcwd(),
            "since": time.strftime("%Y-%m-%dT%H:%M:%S"), "command": " ".join(argv)}


def _read(path):
    """A display record, or {} when it is gone or half-written."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def _describe(index, argv):
    """Who holds the slot, for `status` and for the guard's block message.

    ponytail: display only. Liveness is decided by trying the lock, never by
    reading this -- a killed holder leaves the file behind and the lock gone.
    """
    try:
        with open(_owner_path(index), "w", encoding="utf-8") as handle:
            json.dump(_who(argv), handle, indent=1)
    except OSError:
        pass  # never fail the run over a display file


def _forget(index):
    try:
        os.remove(_owner_path(index))
    except OSError:
        pass


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
        with contextlib.suppress(OSError):
            os.remove(path)
    return live


def _enqueue(argv):
    """Join the back of the queue: (ticket, how many are ahead). Stay in line by keeping it open."""
    with _queue_lock():
        ahead = len(_tickets())
        numbers = [int(name.split(".")[0]) for name in os.listdir(_queue_dir())
                   if name.endswith(".ticket")]
        ticket = open(os.path.join(_queue_dir(), "%012d.ticket" % (max(numbers, default=0) + 1)),
                      "x+b")
        ticket.write(json.dumps(_who(argv)).encode("utf-8"))
        ticket.flush()
        _take(ticket, TICKET_LOCK_AT)  # nobody can probe it yet: we hold the queue lock
    return ticket, ahead


def _first(ticket):
    with _queue_lock():
        return _tickets()[:1] == [ticket.name]


def _leave(ticket):
    """Step out of line, once. Under the queue lock, or a late delete could hit the
    next ticket to reuse this number."""
    if ticket.closed:
        return
    with _queue_lock():
        ticket.close()
        with contextlib.suppress(OSError):
            os.remove(ticket.name)


def cmd_run(argv, poll, timeout):
    if os.environ.get(SLOT_ENV):
        return subprocess.call(argv)  # already inside a lease; nesting must not deadlock
    slots = devices()
    if not slots:
        print("mpi-kanban: no NVIDIA device found, running unleased", file=sys.stderr)
        return subprocess.call(argv)

    deadline = time.monotonic() + timeout
    announced = False
    ticket, ahead = _enqueue(argv)
    try:
        while True:
            turn = slots if _first(ticket) else []  # only the head of the queue may try a slot
            for index in turn:
                handle = acquire(index)
                if not handle:
                    continue
                _leave(ticket)  # the next waiter is first in line now
                with handle:
                    _describe(index, argv)
                    print("mpi-kanban: GPU %s leased" % index, file=sys.stderr, flush=True)
                    child = dict(os.environ, CUDA_VISIBLE_DEVICES=str(index),
                                 **{SLOT_ENV: str(index)})
                    try:
                        return subprocess.call(argv, env=child)
                    finally:
                        _forget(index)
            if time.monotonic() >= deadline:
                print("mpi-kanban: every GPU still busy after %gs, command not run.\n"
                      "  `python gpu_lease.py status` names the holder." % timeout,
                      file=sys.stderr, flush=True)
                return WAIT_TIMEOUT
            if not announced:
                print("mpi-kanban: all %d GPU slots busy, waiting... (%d ahead in the queue)"
                      % (len(slots), ahead), file=sys.stderr, flush=True)
                announced = True
            time.sleep(poll)
    finally:
        _leave(ticket)


def cmd_status():
    slots = devices()
    if not slots:
        print("no NVIDIA device found")
        return 0
    for index in slots:
        handle = acquire(index)
        if handle:
            handle.close()  # a probe: held for an instant, so a waiter may miss one poll
            print("GPU %s  free" % index)
            continue
        owner = _read(_owner_path(index))
        print("GPU %s  busy   %s  pid %s  since %s  %s" % (
            index, owner.get("repo", "?"), owner.get("pid", "?"),
            owner.get("since", "?"), owner.get("command", "?")))
    with _queue_lock():
        waiters = [_read(path) for path in _tickets()]
    for place, waiter in enumerate(waiters, 1):
        print("queue %d  %s  pid %s  since %s  %s" % (
            place, waiter.get("repo", "?"), waiter.get("pid", "?"),
            waiter.get("since", "?"), waiter.get("command", "?")))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action")
    runner = sub.add_parser("run", help="hold a GPU slot for one command")
    runner.add_argument("--timeout", type=float, default=1800,
                        help="seconds to wait for a free slot (default 1800)")
    runner.add_argument("--poll", type=float, default=15,
                        help="seconds between retries (default 15)")
    runner.add_argument("argv", nargs=argparse.REMAINDER)
    sub.add_parser("status", help="which slots are free, and who holds the rest")
    args = parser.parse_args()

    if args.action == "status":
        return cmd_status()
    if args.action == "run":
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        if not argv:
            parser.error("run needs a command: gpu_lease.py run -- python train.py")
        return cmd_run(argv, args.poll, args.timeout)
    parser.print_help()
    return 2


def _selftest():
    me = os.path.abspath(__file__)
    scratch = tempfile.mkdtemp(prefix="gpu-lease-")
    base = dict(os.environ, MPI_KANBAN_GPU_ROOT=scratch, MPI_KANBAN_GPU_DEVICES="0")
    base.pop(SLOT_ENV, None)

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

    none = lease(dict(base, MPI_KANBAN_GPU_DEVICES=""), "--timeout", "1")
    assert none.stdout.strip() == "", none
    assert none.returncode == 1, "no CUDA_VISIBLE_DEVICES is set when unleased"

    print("gpu_lease selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
