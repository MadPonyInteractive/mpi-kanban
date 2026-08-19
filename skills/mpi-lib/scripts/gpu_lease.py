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

Slots come from `nvidia-smi`, so an onboard Intel/AMD adapter never gets one and
no agent can be handed a device too weak to run on. A machine with no NVIDIA
device runs the command unleased rather than blocking work.

Exit codes: the child's, or 75 when the wait timed out and the child never ran.

Run self-check:  python gpu_lease.py --selftest
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

SLOT_ENV = "MPI_KANBAN_GPU_SLOT"
WAIT_TIMEOUT = 75  # EX_TEMPFAIL: the wait expired, the command did not run


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


def _take(handle):
    """Take the exclusive lock on byte 0, or report that someone else holds it."""
    handle.seek(0)  # msvcrt locks from the CURRENT position, and 'a+' need not be 0
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


def _describe(index, argv):
    """Who holds the slot, for `status` and for the guard's block message.

    ponytail: display only. Liveness is decided by trying the lock, never by
    reading this -- a killed holder leaves the file behind and the lock gone.
    """
    try:
        with open(_owner_path(index), "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "repo": os.getcwd(),
                       "since": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "command": " ".join(argv)}, handle, indent=1)
    except OSError:
        pass  # never fail the run over a display file


def _forget(index):
    try:
        os.remove(_owner_path(index))
    except OSError:
        pass


def cmd_run(argv, poll, timeout):
    if os.environ.get(SLOT_ENV):
        return subprocess.call(argv)  # already inside a lease; nesting must not deadlock
    slots = devices()
    if not slots:
        print("mpi-kanban: no NVIDIA device found, running unleased", file=sys.stderr)
        return subprocess.call(argv)

    deadline = time.monotonic() + timeout
    announced = False
    while True:
        for index in slots:
            handle = acquire(index)
            if not handle:
                continue
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
            print("mpi-kanban: all %d GPU slots busy, waiting..." % len(slots),
                  file=sys.stderr, flush=True)
            announced = True
        time.sleep(poll)


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
        owner = {}
        try:
            with open(_owner_path(index), encoding="utf-8") as fh:
                owner = json.load(fh)
        except (OSError, ValueError):
            pass
        print("GPU %s  busy   %s  pid %s  since %s  %s" % (
            index, owner.get("repo", "?"), owner.get("pid", "?"),
            owner.get("since", "?"), owner.get("command", "?")))
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

    holder = subprocess.Popen(
        [sys.executable, me, "run", "--", sys.executable, "-c", "import time;time.sleep(30)"],
        env=base, stderr=subprocess.PIPE, text=True)
    assert "GPU 0 leased" in holder.stderr.readline(), "holder never took the slot"

    busy = lease(base, "--timeout", "1", "--poll", "0.2")
    assert busy.returncode == WAIT_TIMEOUT, busy
    assert not busy.stdout.strip(), "the command ran without a slot"

    spare = lease(dict(base, MPI_KANBAN_GPU_DEVICES="0,1"), "--timeout", "5", "--poll", "0.2")
    assert spare.stdout.strip() == "1", spare  # multi-GPU: skip the busy slot

    # a wrapped script that wraps another command: pass through the slot it already
    # holds, or the inner call waits forever on a lock its own parent is holding
    nested = lease(dict(base, **{SLOT_ENV: "0"}), "--timeout", "1", script="print('through')")
    assert nested.returncode == 0 and nested.stdout.strip() == "through", nested

    holder.kill()
    holder.wait()
    freed = lease(base, "--timeout", "10", "--poll", "0.2")
    assert freed.stdout.strip() == "0", "the kernel did not release a killed holder"

    again = lease(base, "--timeout", "5", "--poll", "0.2")
    assert again.stdout.strip() == "0", "a holder that exited normally still holds it"

    none = lease(dict(base, MPI_KANBAN_GPU_DEVICES=""), "--timeout", "1")
    assert none.stdout.strip() == "", none
    assert none.returncode == 1, "no CUDA_VISIBLE_DEVICES is set when unleased"

    print("gpu_lease selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
