# Tapo Camera Access

Read the lab's TP-Link Tapo cameras from Python over RTSP. A single module,
`tapocam.py`, plus five command-line tools built on it. Nothing here knows
about the robot, so you can drop it into any project that needs a camera.

---

## ⚠️ Important Note — read first

**Contact the CAAD lab administrator to obtain the Tapo camera credentials and
the camera IP addresses.**

No usernames, passwords, or IP addresses are stored in this repository, and
none ever should be. The `.env` file ships empty; you fill it in locally after
the lab administrator gives you the values.

Three rules that go with that:

1. **Never commit a filled-in `.env`.** Once you have entered the credentials,
   that file is a secret. Do not commit it, do not paste it into a chat, an
   issue, or a project report, and do not include it in a screenshot.
2. **The cameras are on the lab network only.** They are not reachable from
   outside it. Being on the lab Wi-Fi is a precondition for everything below.
3. **Do not expose the cameras to the internet.** `serve.py` has no
   authentication by design — that is acceptable on a closed lab network and
   nowhere else. Never port-forward it.

If credentials are ever committed by accident, tell the lab administrator
immediately so they can be rotated. Deleting the commit is not enough.

---

## Setup

```bash
python -m pip install -r requirements.txt
```

Then open `.env` and fill in the four values the lab administrator gave you:

```
TAPO_USER=          # the camera account name
TAPO_PASS=          # the camera account password
TAPO_ROOM_HOST=     # IP address of the room camera
TAPO_WRIST_HOST=    # IP address of the wrist camera
```

The middle word of each `_HOST` line becomes the camera's name, so
`TAPO_ROOM_HOST` gives you a camera called `room`. Add as many as you want —
no code needs editing.

Check it works:

```bash
python probe.py     # is it reachable, are the credentials right
python view.py      # look at it
```

---

## The tools

| Tool | What it does |
|---|---|
| `probe.py` | Diagnoses the connection. **Run this first when anything is wrong.** |
| `view.py` | Live view in a desktop window. `--latency` measures the delay. |
| `serve.py` | Re-serves the cameras over HTTP so a browser can watch. |
| `soak.py` | Leaves the streams running and logs whether they hold up. |
| `example.py` | Short template to copy into your own project. |

### Sharing the cameras with your group

**The cameras only accept a couple of RTSP clients before refusing new ones.**
Two people running `view.py` will lock a third out. Run `serve.py` once
instead — it holds one connection per camera and fans it out over HTTP, so any
number of people can watch from a browser with no Python installed:

```bash
python serve.py                 # then open http://<your-ip>:8000
```

- `/` — index page with every camera
- `/stream/<name>` — MJPEG, works in an `<img>` tag
- `/snapshot/<name>` — a single JPEG, for any language that can fetch a URL

Use `--host 127.0.0.1` to restrict it to your own machine.

---

## Using it in your own project

Start from `example.py`:

```python
import tapocam

with tapocam.open_camera("room") as cam:
    cam.settle()                      # discard the connect backlog
    frame, frame_time = cam.read()    # BGR numpy array, newest available
```

Two things worth understanding before you build on it:

**Use `settle()`, not `wait_for_frame()`, if the picture must show *now*.** A
camera hands over about a second of *already recorded* frames the instant you
connect. `wait_for_frame()` returns as soon as the first of those arrives —
which is the oldest one. `settle()` waits for that backlog to drain instead.

**`read()` never blocks and never queues.** It returns whatever is newest,
which may be a frame you have already processed — compare `frame_time` to skip
repeats. This is deliberate: for anything live, a frame from 400 ms ago is
worse than no frame.

### Pairing it with the robot

The camera code is independent of `ur_rtde`, so combining them is just two
imports in one script. The usual pattern is: move the robot, `settle()`, read a
frame, decide, move again. Remember that the robot must be in **Remote
Control** mode and that all the usual lab rules apply — see the
[Safety & Hardware](../../hardware.html) page, and note that **robot use
requires prior permission from the CAAD department and a supervisor present**.

---

## Troubleshooting

Run `python probe.py` first. It speaks RTSP directly, so it can tell apart
causes that OpenCV reports identically.

| Symptom | Cause |
|---|---|
| `cannot reach <ip>:554` | Wrong IP, different subnet or VLAN, or a firewall. Check you are on the lab network. Try `python probe.py --scan`. |
| `401 Unauthorized` | Wrong camera account. Check for whitespace in `.env`, then ask the lab administrator to confirm the credentials. |
| Probe says OK but `view.py` shows nothing | The camera's RTSP client limit — someone else is already connected. Use `serve.py`. |
| `The function is not implemented. Rebuild the library with ... GTK+ 2.x ...` | Your OpenCV has no GUI build. See below. |
| Torn or smeared image | Wi-Fi packet loss. TCP transport is already forced; beyond that it is signal strength or a congested 2.4 GHz channel. |

### "The function is not implemented" / no GUI

`opencv-python` and `opencv-python-headless` unpack into the *same* `cv2/`
folder, so whichever was installed last owns the binaries. If that is headless,
`imshow` is compiled out. The version number gives no hint, and the error
mentions GTK even on Windows.

```bash
python -m pip uninstall -y opencv-python opencv-python-headless
python -m pip install opencv-python
```

…or use `serve.py` and watch in a browser, which needs no GUI at all.

On Windows, check *which* Python you are running first — typing `python` in a
fresh terminal can land on the Microsoft Store stub rather than your Anaconda
install. `python -c "import sys; print(sys.executable)"` settles it.

---

## What a Tapo C110 actually gives you

Measured rather than taken from a spec sheet — check yours with `probe.py`,
since firmware varies:

- **`/stream1` is 2304×1296 H.264 at ~15 fps.** Many sources claim Tapo RTSP
  caps at 1080p; that was not true of the firmware tested here (July 2026).
- `/stream2` is a low-resolution feed.
- **Frames arrive in bursts, not on a metronome.** Median gap ~9 ms with maxima
  around 400 ms, averaging to 15 fps. Judge stream health by reconnects, not by
  `max_gap`.
- ONVIF Profile S on port 2020, same camera-account credentials.
- Fixed focus, tuned for surveillance distance — check sharpness yourself if
  you need close-up detail.
- No global shutter, no external trigger, **no hardware sync between cameras**,
  so there is no genuinely simultaneous multi-camera frame to be had.
- Expect **200–500 ms** end-to-end latency over Wi-Fi. Measure it with
  `view.py --latency` rather than assuming.

## Sources

- [How to View Tapo Camera on PC, NAS, or NVR Using RTSP/ONVIF](https://www.tp-link.com/us/support/faq/2680/) — camera account, URL format, ports
- [Tapo Camera ONVIF and RTSP Common Questions](https://www.tp-link.com/us/support/faq/4465/) — the two-of-three storage conflict
- [FAQ: the "Third-Party Compatibility" feature](https://www.tapo.com/us/faq/714/)
