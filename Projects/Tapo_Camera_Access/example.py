"""Starting point for your own project. Copy this file and edit it.

    python example.py            # uses the first camera in your .env
    python example.py room

What it does: grabs frames for ten seconds and reports how bright each one was.
Replace the marked section with whatever you actually want -- detection,
recording, counting things, sending frames somewhere.
"""

import sys
import time

import tapocam


def main():
    # Pick a camera. Names come from .env: TAPO_ROOM_HOST defines "room".
    names = tapocam.discover_cameras()
    if not names:
        print("No cameras configured. Copy .env.example to .env and fill it in.")
        return 2
    name = sys.argv[1].lower() if len(sys.argv) > 1 else names[0]
    print("Cameras available: %s -- using %r" % (", ".join(names), name))

    # `with` guarantees the reader thread is shut down even if your code raises.
    with tapocam.open_camera(name) as cam:
        # settle() rather than wait_for_frame(): the camera dumps a second or
        # so of already-recorded frames when you connect, and the first one you
        # can read is the oldest of them. Use wait_for_frame() only if you do
        # not care whether the picture is current.
        if not cam.settle():
            print("No frame arrived. Run 'python probe.py' to find out why.")
            return 1

        print("Streaming %s. Ctrl-C to stop early.\n" % (cam.stats()["size"],))
        deadline = time.time() + 10
        last_time = 0.0

        while time.time() < deadline:
            frame, frame_time = cam.read()

            # read() returns the newest frame, which may be one you have already
            # handled -- it does not block or queue. Skipping repeats is the
            # caller's job, and it is this one line.
            if frame_time == last_time:
                time.sleep(0.01)
                continue
            last_time = frame_time

            # ---- your code goes here -------------------------------------
            # `frame` is a BGR numpy array, exactly what OpenCV expects.
            brightness = frame.mean()
            print("frame at %.3fs  mean brightness %.1f" % (frame_time % 60, brightness))
            # --------------------------------------------------------------

        s = cam.stats()
        print("\n%d frames, %.1f fps, %d reconnects"
              % (s["frames"], s["fps"], s["reconnects"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
