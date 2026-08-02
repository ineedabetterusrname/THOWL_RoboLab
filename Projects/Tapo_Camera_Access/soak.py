"""Prove the streams stay up: run them for a while and log what happens.

A camera that drops once an hour looks perfect for the two minutes you watch
it, and then ruins a long recording or strands whatever depends on it. Thirty
minutes clean is a reasonable bar before trusting one.

    python soak.py                  # 30 minutes, every camera
    python soak.py --minutes 5      # quick shakedown first

No window is opened, so this can run in the background. Ctrl-C reports on what
it has so far.
"""

import argparse
import csv
import os
import sys
import time

import tapocam
from tapocam import ConfigError

LOGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")

# A gap longer than this means frames stopped arriving for long enough that
# anything acting on them was working from a stale scene.
GAP_LIMIT_SEC = 2.0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--camera", default="all",
                        help="camera name, comma-separated list, or 'all'")
    parser.add_argument("--stream", type=int, default=1, choices=(1, 2))
    parser.add_argument("--minutes", type=float, default=30.0)
    parser.add_argument("--interval", type=float, default=5.0,
                        help="seconds between samples (default: 5)")
    parser.add_argument("--gap-limit", type=float, default=GAP_LIMIT_SEC,
                        help="longest acceptable gap between frames, seconds")
    parser.add_argument("--csv", help="where to write samples (default: captures/)")
    args = parser.parse_args()

    try:
        streams = tapocam.open_streams(tapocam.parse_selection(args.camera),
                                       stream=args.stream)
    except ConfigError as exc:
        print("Configuration problem:\n  %s" % exc)
        return 2

    for stream in streams:
        if not stream.wait_for_frame(timeout=20.0):
            print("%s: no frame within 20s. Run probe.py before soaking."
                  % stream.name)
            tapocam.close_streams(streams)
            return 2
        print("%s: first frame, %s" % (stream.name, stream.stats()["size"]))

    os.makedirs(LOGS, exist_ok=True)
    csv_path = args.csv or os.path.join(
        LOGS, "soak_%s.csv" % time.strftime("%Y%m%d_%H%M%S"))

    deadline = time.time() + args.minutes * 60
    start = time.time()
    interrupted = False

    print("\nSoaking for %.0f min, sampling every %.0fs -> %s\n"
          % (args.minutes, args.interval, csv_path))

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["elapsed_s", "camera", "frames", "fps", "reconnects",
                         "failed_opens", "age_s", "max_gap_s", "connected"])
        try:
            while time.time() < deadline:
                time.sleep(min(args.interval, max(0.0, deadline - time.time())))
                elapsed = time.time() - start
                for stream in streams:
                    s = stream.stats()
                    writer.writerow([
                        "%.1f" % elapsed, s["name"], s["frames"], "%.2f" % s["fps"],
                        s["reconnects"], s["failed_opens"], "%.2f" % s["age"],
                        "%.2f" % s["max_gap"], int(s["connected"]),
                    ])
                    # flush: the whole point of this script is running it in the
                    # background, where stdout is a pipe and Python would
                    # otherwise hold every line until the run ends.
                    print("%6.0fs %-8s %6.2f fps  age %4.2fs  reconnects %d  "
                          "gap %.2fs%s"
                          % (elapsed, s["name"], s["fps"], s["age"],
                             s["reconnects"], s["max_gap"],
                             "" if s["connected"] else "  DISCONNECTED"),
                          flush=True)
                handle.flush()
        except KeyboardInterrupt:
            interrupted = True
            print("\nInterrupted.")

    elapsed = time.time() - start
    tapocam.close_streams(streams)

    print("\n%s after %.1f min"
          % ("Partial run" if interrupted else "Finished", elapsed / 60))
    passed = not interrupted
    for stream in streams:
        s = stream.stats()
        problems = []
        if s["reconnects"]:
            problems.append("%d reconnect(s)" % s["reconnects"])
        if s["failed_opens"]:
            problems.append("%d failed open(s)" % s["failed_opens"])
        if s["max_gap"] > args.gap_limit:
            problems.append("longest gap %.2fs > %.2fs" % (s["max_gap"], args.gap_limit))
        if problems:
            passed = False
        print("  %-8s %d frames, %.2f fps mean, longest gap %.2fs -- %s"
              % (s["name"], s["frames"], s["frames"] / elapsed if elapsed else 0,
                 s["max_gap"], ", ".join(problems) if problems else "clean"))

    print("\nSamples: %s" % csv_path)
    if interrupted:
        print("Run the full %.0f minutes before trusting the result." % args.minutes)
    elif passed:
        print("PASS.")
    else:
        print("FAIL. Reconnects usually mean Wi-Fi, not code: check signal at the")
        print("camera, move it off a congested 2.4 GHz channel, or wire it.")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
