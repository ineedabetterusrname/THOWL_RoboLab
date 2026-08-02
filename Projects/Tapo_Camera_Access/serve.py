"""Re-serve the cameras as MJPEG over HTTP, so anything on the network can watch.

    python serve.py                  # all cameras, http://<this-machine>:8000
    python serve.py --port 8080 --fps 5
    python serve.py --host 127.0.0.1 # this machine only

Useful for three separate reasons:

  * A browser needs no OpenCV at all, so a headless or broken cv2 build stops
    mattering -- including on phones and tablets.
  * Several people can watch at once. The cameras themselves only serve a
    couple of RTSP clients before refusing more; this holds one connection per
    camera and fans it out.
  * Any language can consume it. `/snapshot/<name>` is a plain JPEG.

Endpoints:  /                    index page with every camera
            /stream/<name>       MJPEG stream
            /snapshot/<name>     single JPEG

NO AUTHENTICATION. Anyone who can reach this port sees the cameras. That is
the point when you are sharing with the room, but do not port-forward it.
"""

import argparse
import html
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import cv2

import tapocam
from tapocam import ConfigError

STREAMS = {}
OPTIONS = {"fps": 10.0, "quality": 80, "width": 960, "overlay": True}

INDEX = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cameras</title>
<style>
  body {{ margin: 0; padding: 1rem; background: #14171a; color: #e8e8e8;
         font: 15px/1.5 system-ui, sans-serif; }}
  h1 {{ font-size: 1.1rem; font-weight: 600; margin: 0 0 1rem; }}
  .grid {{ display: grid; gap: 1rem;
           grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
  figure {{ margin: 0; background: #1e2226; border-radius: 8px; overflow: hidden; }}
  img {{ display: block; width: 100%; height: auto; background: #000; }}
  figcaption {{ padding: .5rem .75rem; font-size: .85rem; }}
  a {{ color: #7fb3ff; }}
  footer {{ margin-top: 1.5rem; font-size: .8rem; color: #8a9199; }}
</style>
<h1>Cameras</h1>
<div class="grid">{cards}</div>
<footer>MJPEG at <code>/stream/&lt;name&gt;</code>, single frame at
<code>/snapshot/&lt;name&gt;</code>. No authentication -- anyone on this
network can watch.</footer>
"""

CARD = """<figure>
  <a href="/stream/{name}"><img src="/stream/{name}" alt="{name}"></a>
  <figcaption><strong>{name}</strong> &middot;
    <a href="/snapshot/{name}">snapshot</a></figcaption>
</figure>"""


def encode(stream, want_overlay):
    """Newest frame as JPEG bytes, or None if nothing has arrived yet."""
    frame, frame_time = stream.read()
    if frame is None:
        frame = tapocam.placeholder(stream.name, width=640)
    else:
        frame = tapocam.fit(frame.copy(), OPTIONS["width"])
        if want_overlay:
            tapocam.draw_status(frame, stream.stats())
    ok, buf = cv2.imencode(".jpg", frame,
                           [cv2.IMWRITE_JPEG_QUALITY, OPTIONS["quality"]])
    return (buf.tobytes(), frame_time) if ok else (None, frame_time)


class Handler(BaseHTTPRequestHandler):
    # HTTP/1.0 on purpose: an MJPEG response has no length and never ends, and
    # 1.0's close-when-done semantics keep that honest without chunking.
    protocol_version = "HTTP/1.0"
    server_version = "tapocam/1.0"

    def log_message(self, fmt, *args):
        pass  # the access log drowns out the startup banner

    def _not_found(self, message):
        body = message.encode()
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._index()
        for prefix, handler in (("/stream/", self._stream),
                                ("/snapshot/", self._snapshot)):
            if path.startswith(prefix):
                name = unquote(path[len(prefix):]).strip("/").lower()
                stream = STREAMS.get(name)
                if stream is None:
                    return self._not_found(
                        "No camera %r. Available: %s"
                        % (name, ", ".join(sorted(STREAMS))))
                return handler(stream)
        self._not_found("Not found. Try / for the index.")

    def _index(self):
        cards = "".join(CARD.format(name=html.escape(n)) for n in sorted(STREAMS))
        body = INDEX.format(cards=cards).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _snapshot(self, stream):
        jpeg, _ = encode(stream, OPTIONS["overlay"])
        if jpeg is None:
            return self._not_found("Could not encode a frame.")
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(jpeg)

    def _stream(self, stream):
        self.send_response(200)
        self.send_header("Content-Type",
                         "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        interval = 1.0 / max(OPTIONS["fps"], 0.1)
        last_sent = 0.0
        try:
            while True:
                jpeg, frame_time = encode(stream, OPTIONS["overlay"])
                # Skip re-encoding a frame nobody has replaced yet: the camera
                # runs at ~15 fps and a browser gains nothing from duplicates.
                if jpeg is not None and frame_time != last_sent:
                    last_sent = frame_time
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                     b"Content-Length: " + str(len(jpeg)).encode()
                                     + b"\r\n\r\n" + jpeg + b"\r\n")
                time.sleep(interval)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # the viewer closed the tab; entirely normal


def lan_address():
    try:
        return tapocam.local_subnet()
    except OSError:
        return socket.gethostname()


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--camera", default="all",
                        help="camera name, comma-separated list, or 'all'")
    parser.add_argument("--stream", type=int, default=1, choices=(1, 2),
                        help="1 = full resolution, 2 = low (default: 1)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="bind address; 127.0.0.1 for this machine only")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--fps", type=float, default=10.0,
                        help="frames per second sent to each viewer")
    parser.add_argument("--quality", type=int, default=80, help="JPEG quality 1-100")
    parser.add_argument("--width", type=int, default=960,
                        help="width sent to viewers; 0 for native resolution")
    parser.add_argument("--no-overlay", action="store_true",
                        help="send clean frames, without the status banner")
    args = parser.parse_args()

    OPTIONS.update(fps=args.fps, quality=args.quality, width=args.width,
                   overlay=not args.no_overlay)

    try:
        streams = tapocam.open_streams(tapocam.parse_selection(args.camera),
                                       stream=args.stream)
    except ConfigError as exc:
        print("Configuration problem:\n  %s" % exc)
        return 2
    STREAMS.update({s.name: s for s in streams})

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True

    where = ("http://127.0.0.1:%d" % args.port if args.host == "127.0.0.1"
             else "http://%s:%d" % (lan_address(), args.port))
    # flush: this banner carries the URL people need, and it is commonly run
    # with stdout redirected to a file or pipe, where Python would hold it.
    print("Serving %s on %s" % (", ".join(sorted(STREAMS)), where), flush=True)
    if args.host != "127.0.0.1":
        print("Anyone on this network can watch -- there is no password.", flush=True)
    print("Ctrl-C to stop.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.shutdown()
        server.server_close()
        tapocam.close_streams(streams)
    return 0


if __name__ == "__main__":
    sys.exit(main())
