"""Read RTSP camera streams from Python, reliably, on a local network.

Written for TP-Link Tapo cameras but not tied to them -- any camera with an
RTSP URL works (see `_URL` below). Copy this one file into your project, or run
the CLI tools next to it. Nothing here knows about robots.

    import tapocam

    cam = tapocam.open_camera("room")     # name comes from .env
    cam.wait_for_frame()
    frame, timestamp = cam.read()         # a BGR numpy array, newest available
    ...
    cam.stop()

The reader thread is the reason this module exists. RTSP over Wi-Fi arrives in
a buffer, so code that calls cap.read() itself gets the *oldest* queued frame
and works from a scene that has already moved on. Every camera here instead
gets a thread that drains its stream flat out and keeps only the newest frame.


Configuration
-------------
Put a `.env` next to this file (see `.env.example`). Cameras are discovered
from the variable names, so there is no list to edit and no limit on how many:

    TAPO_USER=camera_account_name        # shared by all cameras
    TAPO_PASS=camera_account_password
    TAPO_ROOM_HOST=192.168.0.50          # -> a camera called "room"
    TAPO_WRIST_HOST=192.168.0.51         # -> a camera called "wrist"

Per camera you may also set `_USER`, `_PASS` and `_PORT` to override the
shared values, or `_URL` to give a complete RTSP URL for a non-Tapo camera:

    CAM_DOORWAY_URL=rtsp://user:pw@10.0.0.9:554/h264/ch1/main/av_stream

`CAM_` and `TAPO_` are interchangeable prefixes. A single unnamed camera
(`TAPO_HOST=...`) is called "cam".
"""

import os

# FFmpeg reads this when a capture is opened, so it has to be in the
# environment before the first cv2.VideoCapture -- hence above the cv2 import
# rather than tucked inside a function.
#   rtsp_transport;tcp -- UDP is the RTSP default and drops packets silently on
#     a congested network, which shows up as torn macroblocks.
#   stimeout (microseconds) -- without it, a camera that vanishes mid-stream
#     leaves cap.read() blocked forever and the reader thread never recovers.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp|stimeout;5000000"
)

import base64  # noqa: E402  (all imports follow the environment setup above)
import hashlib  # noqa: E402
import re  # noqa: E402
import socket  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from collections import deque  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from urllib.parse import quote  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

try:
    from dotenv import load_dotenv
except ImportError:  # the library still works if you set real env vars
    def load_dotenv(*_args, **_kwargs):
        return False

HERE = os.path.dirname(os.path.abspath(__file__))

# Both locations are accepted because either is a reasonable place to keep it.
# The file next to this module wins; a variable already in the real environment
# beats both, since load_dotenv does not override.
ENV_FILES = [os.path.join(HERE, ".env"), os.path.join(os.path.dirname(HERE), ".env")]
for _env_file in ENV_FILES:
    load_dotenv(_env_file)

RTSP_PORT = 554
ONVIF_PORT = 2020

ENV_PREFIXES = ("TAPO_", "CAM_")
DEFAULT_NAME = "cam"  # the name given to a single unnamed camera


class ConfigError(RuntimeError):
    """Configuration problem. The message should say how to fix it."""


# ---------------------------------------------------------------- configuration


def _lookup(name, suffix):
    """Value of <PREFIX><NAME>_<SUFFIX>, trying every accepted prefix."""
    keys = []
    for prefix in ENV_PREFIXES:
        if name == DEFAULT_NAME:
            keys.append(prefix + suffix)
        keys.append("%s%s_%s" % (prefix, name.upper(), suffix))
    for key in keys:
        value = os.getenv(key, "")
        if value.strip():
            return value.strip()
    return ""


def _shared(suffix):
    """A value that applies to every camera, e.g. TAPO_USER."""
    for prefix in ENV_PREFIXES:
        value = os.getenv(prefix + suffix, "")
        if value.strip():
            return value.strip()
    return ""


def discover_cameras():
    """Names of every camera defined in the environment, sorted.

    A camera exists as soon as something gives it an address, so adding one is
    a line in .env rather than an edit to this file.

    An empty value does not count. The shipped .env lists TAPO_ROOM_HOST= and
    TAPO_WRIST_HOST= with nothing after the "=", and treating those as real
    cameras produced "No camera called 'room'. Cameras found: room, wrist."
    """
    names = set()
    for key, value in os.environ.items():
        if not value.strip():
            continue
        for prefix in ENV_PREFIXES:
            if not key.startswith(prefix):
                continue
            rest = key[len(prefix):]
            if rest in ("HOST", "URL"):
                names.add(DEFAULT_NAME)
            elif rest.endswith("_HOST"):
                names.add(rest[: -len("_HOST")].lower())
            elif rest.endswith("_URL"):
                names.add(rest[: -len("_URL")].lower())
    return sorted(names)


def redact(url):
    """Mask the password in an RTSP URL. Use before printing or logging one."""
    return re.sub(r"://([^:/@\s]+):([^@\s]+)@", r"://\1:***@", url)


@dataclass(frozen=True)
class CameraConfig:
    name: str
    host: str = ""
    user: str = ""
    password: str = ""
    port: int = RTSP_PORT
    # A complete RTSP URL, for cameras that are not Tapo. "{stream}" is
    # substituted with the stream number if present.
    url_template: str = ""

    def path(self, stream=1):
        """Tapo serves /stream1 (full resolution) and /stream2 (low)."""
        return "/stream%d" % stream

    def url(self, stream=1):
        if self.url_template:
            return self.url_template.replace("{stream}", str(stream))
        # A camera-account password or username may legitimately contain @ : /
        # or #, any of which would otherwise split the URL in the wrong place.
        # Tapo usernames are often email addresses, so this is not theoretical.
        return "rtsp://%s:%s@%s:%d%s" % (
            quote(self.user, safe=""), quote(self.password, safe=""),
            self.host, self.port, self.path(stream),
        )

    def display_url(self, stream=1):
        """The URL with the password masked. Use this in anything printed."""
        if self.url_template:
            return redact(self.url(stream))
        return "rtsp://%s:***@%s:%d%s" % (
            self.user, self.host, self.port, self.path(stream)
        )

    def base_url(self, stream=1):
        """URL without credentials -- what an RTSP request line should carry."""
        if self.url_template:
            return re.sub(r"://[^/@\s]+@", "://", self.url(stream))
        return "rtsp://%s:%d%s" % (self.host, self.port, self.path(stream))


def load_camera(name):
    """Build a CameraConfig from the environment, or explain what is missing."""
    name = name.lower()
    known = discover_cameras()

    url_template = _lookup(name, "URL")
    host = _lookup(name, "HOST")
    if not (url_template or host):
        raise ConfigError(
            "No camera called %r. %s Define one by adding TAPO_%s_HOST=<ip> to "
            "a .env file at %s"
            % (name,
               ("Cameras found: %s." % ", ".join(known)) if known
               else "No cameras are configured at all.",
               name.upper(), " or ".join(ENV_FILES))
        )

    user = _lookup(name, "USER") or _shared("USER")
    password = (_lookup(name, "PASS") or _lookup(name, "PASSWORD")
                or _shared("PASS") or _shared("PASSWORD"))
    if not url_template and not (user and password):
        raise ConfigError(
            "Camera %r has an address but no credentials. Set TAPO_USER and "
            "TAPO_PASS to the *camera account* created in the Tapo app under "
            "Settings > Advanced Settings > Camera Account -- not your Tapo "
            "login." % name
        )

    port_text = _lookup(name, "PORT")
    try:
        port = int(port_text) if port_text else RTSP_PORT
    except ValueError:
        raise ConfigError("Port for camera %r is not a number: %r" % (name, port_text))

    return CameraConfig(name=name, host=host, user=user, password=password,
                        port=port, url_template=url_template)


def load_cameras(names=None):
    """Configs for the named cameras, or for every camera that is configured."""
    if names is None:
        names = discover_cameras()
    # Also catches an empty list from parse_selection("all") when nothing is
    # configured -- without this the callers loop over zero cameras and report
    # success.
    if not names:
        raise ConfigError(
            "No cameras configured. Fill in TAPO_USER, TAPO_PASS and at least "
            "one TAPO_<NAME>_HOST in %s -- ask the CAAD lab administrator for "
            "the camera account and the camera IP addresses." % ENV_FILES[0]
        )
    return [load_camera(name) for name in names]


def parse_selection(text):
    """Turn a --camera argument into a list of names.

    Accepts "all", a single name, or a comma-separated list. Unknown names are
    rejected here rather than failing one at a time later.
    """
    known = discover_cameras()
    if text in (None, "", "all", "both"):
        return known
    names = [part.strip().lower() for part in text.split(",") if part.strip()]
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ConfigError(
            "Unknown camera(s): %s. Configured: %s"
            % (", ".join(unknown), ", ".join(known) or "(none)")
        )
    return names


# ------------------------------------------------------------------- streaming


@dataclass
class _State:
    frame: object = None
    frame_time: float = 0.0
    recent: deque = field(default_factory=lambda: deque(maxlen=90))
    frames: int = 0
    connects: int = 0
    failed_opens: int = 0
    max_gap: float = 0.0
    size: object = None
    connected: bool = False
    last_error: str = ""


class CameraStream:
    """One camera, drained by its own thread, newest frame only.

    Reconnects on its own with exponential backoff, because a Wi-Fi camera will
    drop eventually and a pipeline that dies with it is useless.
    """

    def __init__(self, config, stream=1, max_backoff=15.0):
        self.config = config
        self.stream = stream
        self.max_backoff = max_backoff
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._s = _State()

    @property
    def name(self):
        return self.config.name

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._run, name="cam-%s" % self.config.name, daemon=True
            )
            self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            # Can take up to the FFmpeg socket timeout if the camera went away
            # mid-read, which is the case this join exists to survive.
            self._thread.join(timeout=8.0)
            self._thread = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
        return False

    def wait_for_frame(self, timeout=15.0):
        """Block until the first frame lands. False if it never does."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if self._s.frame_time > 0:
                    return True
            time.sleep(0.05)
        return False

    def settle(self, seconds=2.0, timeout=20.0):
        """Wait for the first frame, then let the connection backlog drain.

        A camera hands over a second or so of *already recorded* frames the
        instant you connect, and wait_for_frame() returns the oldest of them.
        Measured on a Tapo C110: ~29 frames in the first second against a
        steady rate of 15, settling by about t+3s. Code that connects and
        immediately grabs a frame is therefore looking at the past.

        Call this instead of wait_for_frame() whenever the frame has to reflect
        *now*. It just waits -- read() only ever returns the newest frame, so
        the backlog discards itself.
        """
        if not self.wait_for_frame(timeout):
            return False
        self._stop.wait(seconds)
        return True

    def read(self):
        """(frame, capture_time), or (None, 0.0) before the first frame.

        The frame is not copied. The reader thread never writes into an array it
        has already published -- every cap.read() allocates a fresh one -- so
        holding this reference is safe. Copy it before drawing on it.
        """
        with self._lock:
            return self._s.frame, self._s.frame_time

    def stats(self):
        with self._lock:
            times = list(self._s.recent)
            fps = 0.0
            if len(times) >= 2 and times[-1] > times[0]:
                fps = (len(times) - 1) / (times[-1] - times[0])
            age = (time.time() - self._s.frame_time) if self._s.frame_time else float("inf")
            return {
                "name": self.config.name,
                "connected": self._s.connected,
                "frames": self._s.frames,
                "fps": fps,
                "reconnects": max(0, self._s.connects - 1),  # the first is not one
                "failed_opens": self._s.failed_opens,
                "age": age,
                "max_gap": self._s.max_gap,
                "size": self._s.size,
                "last_error": self._s.last_error,
            }

    def _run(self):
        url = self.config.url(self.stream)
        backoff = 1.0

        while not self._stop.is_set():
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                cap.release()
                with self._lock:
                    self._s.failed_opens += 1
                    self._s.connected = False
                    self._s.last_error = "could not open stream"
                self._stop.wait(backoff)
                backoff = min(backoff * 2, self.max_backoff)
                continue

            # Honoured by some FFmpeg builds and ignored by others; the drain
            # loop below is the real guarantee that we hold the newest frame.
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            with self._lock:
                self._s.connects += 1
                self._s.connected = True
                self._s.last_error = ""
            backoff = 1.0

            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    with self._lock:
                        self._s.connected = False
                        self._s.last_error = "stream dropped"
                    break

                now = time.time()
                with self._lock:
                    if self._s.frame_time:
                        # Gaps deliberately span reconnects: an outage is the
                        # longest gap there is, and that is what matters.
                        self._s.max_gap = max(self._s.max_gap, now - self._s.frame_time)
                    self._s.frame = frame
                    self._s.frame_time = now
                    self._s.frames += 1
                    self._s.recent.append(now)
                    if self._s.size is None:
                        self._s.size = (frame.shape[1], frame.shape[0])

            cap.release()

        with self._lock:
            self._s.connected = False


def open_camera(name, stream=1):
    """Start a single named camera."""
    return CameraStream(load_camera(name), stream=stream).start()


def open_streams(names=None, stream=1):
    """Start a stream per camera. Defaults to every camera in the environment."""
    return [CameraStream(cfg, stream=stream).start() for cfg in load_cameras(names)]


def close_streams(streams):
    for stream in streams:
        stream.stop()


# ------------------------------------------------------ RTSP diagnosis (no cv2)


def _md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def authorization(challenge, method, uri, user, password, cnonce=None):
    """Answer a 401 challenge.

    Digest is what Tapo firmware sends; Basic is handled too, because guessing
    the wrong scheme fails identically to getting the password wrong, and that
    ambiguity is the thing this whole diagnostic path exists to remove.
    """
    scheme = challenge.split(None, 1)[0].lower()

    if scheme == "basic":
        return "Basic " + base64.b64encode(
            ("%s:%s" % (user, password)).encode()).decode()
    if scheme != "digest":
        raise ValueError("unsupported auth scheme %r" % scheme)

    params = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', challenge))
    realm, nonce = params.get("realm", ""), params.get("nonce", "")
    ha1 = _md5("%s:%s:%s" % (user, realm, password))
    ha2 = _md5("%s:%s" % (method, uri))
    fields = [("username", user), ("realm", realm), ("nonce", nonce), ("uri", uri)]

    qop = params.get("qop", "").split(",")[0].strip()
    if qop:
        cnonce = cnonce or os.urandom(4).hex()
        nc = "00000001"
        fields.append(("response",
                       _md5("%s:%s:%s:%s:%s:%s" % (ha1, nonce, nc, cnonce, qop, ha2))))
        parts = ['%s="%s"' % kv for kv in fields]
        parts += ["qop=%s" % qop, "nc=%s" % nc, 'cnonce="%s"' % cnonce]
    else:
        fields.append(("response", _md5("%s:%s:%s" % (ha1, nonce, ha2))))
        parts = ['%s="%s"' % kv for kv in fields]

    if "opaque" in params:
        parts.append('opaque="%s"' % params["opaque"])
    return "Digest " + ", ".join(parts)


def _read_response(sock):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("camera closed the connection")
        data += chunk

    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode("utf-8", "replace").split("\r\n")
    try:
        status = int(lines[0].split()[1])
    except (IndexError, ValueError):
        raise ConnectionError("not an RTSP response: %r" % lines[0][:80])

    headers = {}
    for line in lines[1:]:
        key, _, value = line.partition(":")
        headers[key.strip().lower()] = value.strip()

    length = int(headers.get("content-length", 0) or 0)
    while len(body) < length:
        chunk = sock.recv(4096)
        if not chunk:
            break
        body += chunk
    return status, headers, body.decode("utf-8", "replace")


def _request(sock, method, url, cseq, extra=None):
    lines = ["%s %s RTSP/1.0" % (method, url), "CSeq: %d" % cseq,
             "User-Agent: tapocam-probe"]
    for key, value in (extra or {}).items():
        lines.append("%s: %s" % (key, value))
    sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
    return _read_response(sock)


def port_open(host, port, timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def describe(config, stream=1, timeout=6.0):
    """OPTIONS then DESCRIBE against the camera, answering any 401.

    Speaking RTSP directly is the point: OpenCV reports a wrong IP, a blocked
    port, a missing camera account and a typo'd password as the same unhelpful
    line, and those need different fixes.
    """
    url = config.base_url(stream)
    host, port = config.host, config.port
    if config.url_template:  # dig the address out of a supplied URL
        match = re.search(r"://(?:[^@/]+@)?([^:/]+)(?::(\d+))?", config.url(stream))
        if match:
            host, port = match.group(1), int(match.group(2) or RTSP_PORT)

    result = {"url": config.display_url(stream), "host": host, "port": port,
              "reachable": False, "authenticated": False, "status": None,
              "server": "", "sdp": "", "error": ""}
    try:
        with socket.create_connection((host, port), timeout) as sock:
            sock.settimeout(timeout)
            result["reachable"] = True

            _, headers, _ = _request(sock, "OPTIONS", url, 1)
            result["server"] = headers.get("server", "")

            status, headers, body = _request(
                sock, "DESCRIBE", url, 2, {"Accept": "application/sdp"}
            )
            if status == 401:
                challenge = headers.get("www-authenticate", "")
                if not challenge:
                    result["status"] = 401
                    result["error"] = "401 with no WWW-Authenticate header"
                    return result
                header = authorization(challenge, "DESCRIBE", url,
                                       config.user, config.password)
                status, headers, body = _request(
                    sock, "DESCRIBE", url, 3,
                    {"Accept": "application/sdp", "Authorization": header},
                )

            result["status"] = status
            result["authenticated"] = status == 200
            result["sdp"] = body
    except (OSError, ConnectionError, ValueError) as exc:
        result["error"] = str(exc)
    return result


def sdp_summary(sdp):
    """The few SDP lines worth reading: codec, resolution, track path."""
    keep = ("m=", "a=rtpmap:", "a=control:", "a=framerate:",
            "a=x-dimensions:", "a=x-framerate:")
    return [line.strip() for line in sdp.splitlines()
            if line.strip().startswith(keep)]


def local_subnet():
    """The /24 this machine sits on. No packets are sent to find it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


def scan_subnet(port=RTSP_PORT, timeout=0.6):
    """Addresses on the local /24 with the given TCP port open."""
    prefix = local_subnet().rsplit(".", 1)[0]
    hosts = ["%s.%d" % (prefix, n) for n in range(1, 255)]
    with ThreadPoolExecutor(max_workers=64) as pool:
        hits = list(pool.map(lambda h: port_open(h, port, timeout), hosts))
    return prefix, [h for h, ok in zip(hosts, hits) if ok]


# -------------------------------------------------------------- drawing helpers

FONT = cv2.FONT_HERSHEY_SIMPLEX
GREEN, AMBER, RED = (0, 220, 0), (0, 200, 255), (0, 0, 255)
STALE_SEC = 1.0  # older than this and acting on the frame would be a mistake


def fit(frame, width):
    """Downscale to a display width. width=0 leaves the frame alone."""
    if width and frame.shape[1] > width:
        scale = width / frame.shape[1]
        return cv2.resize(frame, (width, int(frame.shape[0] * scale)),
                          interpolation=cv2.INTER_AREA)
    return frame


def draw_status(frame, stats, extra=None):
    """Overlay stream health. Colour is the fast read: green means trust it."""
    age = stats["age"]
    colour = RED if not stats["connected"] else (
        AMBER if age > STALE_SEC else GREEN)
    size = stats["size"] or (0, 0)

    cv2.rectangle(frame, (0, 0), (frame.shape[1], 62), (0, 0, 0), -1)
    cv2.putText(frame, "%s  %dx%d  %.1f fps" % (stats["name"], size[0], size[1],
                                                stats["fps"]),
                (10, 24), FONT, 0.6, colour, 2, cv2.LINE_AA)
    cv2.putText(frame, "age %.2fs  reconnects %d  failed opens %d"
                % (age if age != float("inf") else -1, stats["reconnects"],
                   stats["failed_opens"]),
                (10, 50), FONT, 0.5, colour, 1, cv2.LINE_AA)

    if extra:
        (tw, th), _ = cv2.getTextSize(extra, FONT, 1.4, 3)
        y = frame.shape[0] - 20
        cv2.rectangle(frame, (10, y - th - 12), (20 + tw, y + 10), (0, 0, 0), -1)
        cv2.putText(frame, extra, (15, y), FONT, 1.4, (255, 255, 255), 3, cv2.LINE_AA)
    return frame


def placeholder(name, width=640, message="connecting..."):
    canvas = np.zeros((int(width * 9 / 16), width, 3), np.uint8)
    cv2.putText(canvas, "%s: %s" % (name, message), (20, canvas.shape[0] // 2),
                FONT, 0.7, AMBER, 2, cv2.LINE_AA)
    return canvas


# ------------------------------------------------------------ GUI availability


def gui_available():
    """Can this OpenCV build actually open a window?

    Asked by trying, not by parsing build flags: pip will happily install
    opencv-python and opencv-python-headless side by side, and whichever landed
    last owns the binaries. The version number tells you nothing.
    """
    try:
        cv2.namedWindow("__tapocam_gui_probe", cv2.WINDOW_AUTOSIZE)
        cv2.destroyWindow("__tapocam_gui_probe")
        return True
    except cv2.error:
        return False


def gui_help():
    """Text explaining how to get a working GUI build, for this interpreter."""
    import sys
    return "\n".join([
        "This OpenCV build has no GUI support, so no window can be opened.",
        "",
        "  interpreter : %s" % sys.executable,
        "  opencv      : %s" % cv2.__version__,
        "",
        "Almost always this means opencv-python-headless is installed and has",
        "overwritten the windowing build. Both packages unpack into the same",
        "cv2/ folder, so the last one installed wins. Fix it with:",
        "",
        "  \"%s\" -m pip uninstall -y opencv-python opencv-python-headless" % sys.executable,
        "  \"%s\" -m pip install opencv-python" % sys.executable,
        "",
        "If another interpreter on this machine already has a working build,",
        "using that one is simpler than repairing this one.",
        "",
        "Or skip the GUI entirely -- serve.py streams to a browser and does not",
        "need one:  python serve.py",
    ])
