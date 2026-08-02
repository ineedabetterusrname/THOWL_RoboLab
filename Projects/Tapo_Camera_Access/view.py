"""Live view of your cameras in a desktop window.

    python view.py                    # every camera in .env
    python view.py --camera room
    python view.py --latency          # measure glass-to-Python delay

Keys: q or Esc to quit, s to save a snapshot of every window.

Needs an OpenCV build with GUI support. If yours has not got one, this says so
and tells you how to fix it -- or use serve.py, which streams to a browser and
needs no GUI at all.
"""

import argparse
import os
import sys
import time

import cv2

import tapocam
from tapocam import ConfigError

CAPTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")


def clock_text(seconds):
    return "%02d:%06.3f" % (int(seconds) // 60, seconds % 60)


def clock_frame(seconds, size=(900, 420)):
    """A big readable clock to point a camera at."""
    import numpy as np
    width, height = size
    canvas = np.zeros((height, width, 3), np.uint8)
    text = clock_text(seconds)
    (tw, th), _ = cv2.getTextSize(text, tapocam.FONT, 4.0, 8)
    cv2.putText(canvas, text, ((width - tw) // 2, (height + th) // 2),
                tapocam.FONT, 4.0, (255, 255, 255), 8, cv2.LINE_AA)
    return canvas


def snapshot(streams, start, latency):
    os.makedirs(CAPTURES, exist_ok=True)
    tag = time.strftime("%Y%m%d_%H%M%S")
    for stream in streams:
        frame, frame_time = stream.read()
        if frame is None:
            continue
        stamp = clock_text(frame_time - start) if latency else None
        shot = tapocam.draw_status(frame.copy(), stream.stats(), stamp)
        path = os.path.join(CAPTURES, "%s_%s.png" % (stream.name, tag))
        cv2.imwrite(path, shot)
        print("saved %s" % path)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--camera", default="all",
                        help="camera name, comma-separated list, or 'all'")
    parser.add_argument("--stream", type=int, default=1, choices=(1, 2),
                        help="1 = full resolution, 2 = low (default: 1)")
    parser.add_argument("--width", type=int, default=960,
                        help="display width; 0 shows native resolution")
    parser.add_argument("--latency", action="store_true",
                        help="show a clock window and stamp capture time on frames")
    args = parser.parse_args()

    # Checked before opening any stream, so a broken build fails in a second
    # with an explanation rather than mid-loop with a traceback.
    if not tapocam.gui_available():
        print(tapocam.gui_help())
        return 3

    try:
        streams = tapocam.open_streams(tapocam.parse_selection(args.camera),
                                       stream=args.stream)
    except ConfigError as exc:
        print("Configuration problem:\n  %s" % exc)
        return 2

    print("Opening: %s"
          % ", ".join(s.config.display_url(args.stream) for s in streams))
    print("Keys: q/Esc quit, s snapshot -> %s" % CAPTURES)

    if args.latency:
        print("\nLatency method: point the camera at the 'latency clock' window.")
        print("Press s, then open the saved image. It holds two numbers -- the")
        print("clock as the sensor saw it, and the stamp for the moment that")
        print("frame reached Python. The difference is the delay you must plan")
        print("around. (The monitor adds a few ms of its own; ignore it, it is")
        print("noise next to Wi-Fi RTSP.)")

    start = time.time()
    try:
        while True:
            if args.latency:
                cv2.imshow("latency clock", clock_frame(time.time() - start))

            for stream in streams:
                frame, frame_time = stream.read()
                if frame is None:
                    canvas = tapocam.placeholder(stream.name)
                else:
                    stamp = clock_text(frame_time - start) if args.latency else None
                    canvas = tapocam.draw_status(
                        tapocam.fit(frame.copy(), args.width), stream.stats(), stamp)
                cv2.imshow("camera %s" % stream.name, canvas)

            key = cv2.waitKey(15) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                snapshot(streams, start, args.latency)
    except KeyboardInterrupt:
        pass
    finally:
        tapocam.close_streams(streams)
        # Guarded: if the GUI died mid-run, this would otherwise raise and bury
        # whatever the real failure was.
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass

    for stream in streams:
        s = stream.stats()
        print("%-8s %d frames, %.1f fps, %d reconnects, longest gap %.2fs"
              % (s["name"], s["frames"], s["fps"], s["reconnects"], s["max_gap"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
