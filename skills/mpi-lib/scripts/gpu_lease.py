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

A person can take the GPU over (the Cubric-Vision GPU desk does this):

    python gpu_lease.py run --front -- <hold>   wait first in line, ahead of every agent
    python gpu_lease.py interrupt --by Fabio    stop the leased command now
    python gpu_lease.py pause 3 / unpause 3     hold queue ticket 3 in place, or let it go
    python gpu_lease.py status --json           all of it as data, sessions and progress included

A command may write its progress (0..1) to the file named by $MPI_KANBAN_GPU_PROGRESS;
`status --json` shows it, so whoever wants the GPU can see how far along the job is.

Exit codes: the child's; 75 when the wait timed out and the child never ran; 76 when a
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


def _who(argv, reason=None):
    """The holder or waiter record. `session` is the agent session that ran us, so an
    app that session launched can tell its own lease from a peer's (`status --json`)."""
    return {"pid": os.getpid(), "repo": os.getcwd(), "session": os.environ.get("CLAUDE_CODE_SESSION_ID"),
            "since": time.strftime("%Y-%m-%dT%H:%M:%S"), "command": " ".join(argv), "reason": reason}


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


def _enqueue(argv, reason=None, front=False):
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
        ticket.write(json.dumps(_who(argv, reason)).encode("utf-8"))
        ticket.flush()
        _take(ticket, TICKET_LOCK_AT)  # nobody can probe it yet: we hold the queue lock
    return ticket, 0 if front else len(live)


def _first(ticket):
    """True when `ticket` is the first live waiter that is not paused (`pause`)."""
    with _queue_lock():
        ready = [path for path in _tickets() if not os.path.exists(_paused(path))]
        return ready[:1] == [ticket.name]


def _leave(ticket):
    """Step out of line, once. Under the queue lock, or a late delete could hit the
    next ticket to reuse this number."""
    if ticket.closed:
        return
    with _queue_lock():
        ticket.close()
        with contextlib.suppress(OSError):
            os.remove(ticket.name)


def _hold(index, argv, reason):
    """Run the command on slot `index` (lease already held): its exit code, or TAKEN_OVER."""
    record = _who(argv, reason)
    _describe(index, record)
    print("mpi-kanban: GPU %s leased" % index, file=sys.stderr, flush=True)
    child = dict(os.environ, CUDA_VISIBLE_DEVICES=str(index),
                 **{SLOT_ENV: str(index), PROGRESS_ENV: _side(index, "progress")})
    with subprocess.Popen(argv, env=child) as proc:
        _describe(index, dict(record, child_pid=proc.pid))  # what `interrupt` stops
        try:
            code = proc.wait()
        except BaseException:  # Ctrl-C, as subprocess.call does it
            proc.kill()
            raise
    taken = _read(_side(index, "takeover"))
    if taken.get("lease_pid") == os.getpid():
        print("mpi-kanban: GPU %s taken over by %s, your command was stopped (exit %d).\n"
              "  Work it finished is kept: re-run only what did not finish. A re-run waits in\n"
              "  the queue and starts when %s releases the GPU."
              % (index, taken.get("by", "a person"), TAKEN_OVER, taken.get("by", "they")),
              file=sys.stderr, flush=True)
        return TAKEN_OVER
    return code


def cmd_run(argv, poll, timeout, reason=None, front=False):
    if os.environ.get(SLOT_ENV):
        return subprocess.call(argv)  # already inside a lease; nesting must not deadlock
    slots = devices()
    if not slots:
        print("mpi-kanban: no NVIDIA device found, running unleased", file=sys.stderr)
        return subprocess.call(argv)

    deadline = time.monotonic() + timeout
    announced = False
    try:
        ticket, ahead = _enqueue(argv, reason, front)
    except FileExistsError:
        print("mpi-kanban: someone else is already first in line (run --front).", file=sys.stderr)
        return WAIT_TIMEOUT
    try:
        while True:
            first = _first(ticket)  # only the head of the queue may try a slot
            held = ollama_models() if first else []  # ...and not while Ollama sits in VRAM
            for index in (slots if first and not held else []):
                handle = acquire(index)
                if not handle:
                    continue
                _leave(ticket)  # the next waiter is first in line now
                with handle:
                    try:
                        return _hold(index, argv, reason)
                    finally:
                        ollama_unload()
                        _forget(index)
            if time.monotonic() >= deadline:
                print("mpi-kanban: every GPU still busy after %gs, command not run.\n"
                      "  `python gpu_lease.py status` names the holder." % timeout,
                      file=sys.stderr, flush=True)
                return WAIT_TIMEOUT
            if not announced:
                print("mpi-kanban: all %d GPU slots busy, waiting... (%d ahead in the queue)%s"
                      % (len(slots), ahead, "; Ollama holds " + ", ".join(held) if held else ""),
                      file=sys.stderr, flush=True)
                announced = True
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
    return {"slots": slots, "queue": queue}


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
    runner.add_argument("--reason", help="what the job is, shown by status")
    runner.add_argument("--front", action="store_true",
                        help="go ahead of every waiter (a person taking the GPU over)")
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
        return cmd_run(argv, args.poll, args.timeout, args.reason, args.front)
    parser.print_help()
    return 2


def _selftest():
    import http.server
    import threading

    loaded = []  # the fake Ollama's VRAM: what /api/ps answers

    class FakeOllama(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # /api/ps
            self._reply({"models": loaded})

        def do_POST(self):  # /api/generate: keep_alive 0 unloads, anything else loads
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
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
    base = dict(os.environ, MPI_KANBAN_GPU_ROOT=scratch, MPI_KANBAN_GPU_DEVICES="0",
                OLLAMA_HOST=ollama_host, CLAUDE_CODE_SESSION_ID="selftest")
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
