"""Diagnose the RTSP path to a camera before OpenCV gets involved.

OpenCV's failure mode for a camera it cannot open is one unhelpful line, and it
is the same line whether the IP is wrong, the port is firewalled, the camera
account was never created, or the password has a trailing space. This talks
RTSP directly over a socket so it can say *which* of those it is.

    python probe.py                    # check every camera in .env
    python probe.py --camera room
    python probe.py --scan             # find cameras on the local network
    python probe.py --host 192.168.0.51
"""

import argparse
import sys

import tapocam
from tapocam import ConfigError


def report(config, stream, timeout):
    print("[%s] %s" % (config.name, config.display_url(stream)))

    result = tapocam.describe(config, stream=stream, timeout=timeout)
    host, port = result["host"], result["port"]

    if not result["reachable"]:
        print("  FAIL  cannot reach %s:%d -- %s" % (host, port, result["error"]))
        print("        Check the IP (Tapo app > camera > Settings > Device Info)")
        print("        and that this machine is on the same network as the camera.")
        print("        'python probe.py --scan' will list what it can see.")
        return False

    if result["error"]:
        print("  FAIL  %s" % result["error"])
        return False

    if result["status"] == 401:
        print("  FAIL  401 Unauthorized -- the camera is there, the credentials are not.")
        print("        Use the Camera Account (Tapo app > camera > Settings >")
        print("        Advanced Settings > Camera Account), 6-32 characters, not")
        print("        your Tapo login. Watch for stray spaces in .env.")
        print("        If that is definitely right, try turning on Me >")
        print("        Third-Party Services > Third-Party Compatibility.")
        return False

    if result["status"] != 200:
        print("  FAIL  DESCRIBE returned %s" % result["status"])
        return False

    print("  OK    authenticated, stream%d described" % stream)
    if result["server"]:
        print("        server: %s" % result["server"])
    for line in tapocam.sdp_summary(result["sdp"]):
        print("        %s" % line)
    if tapocam.port_open(host, tapocam.ONVIF_PORT, timeout=1.0):
        print("        ONVIF port %d also open" % tapocam.ONVIF_PORT)
    return True


def run_scan(timeout):
    prefix, found = tapocam.scan_subnet(timeout=timeout)
    print("Scanning %s.0/24 for port %d ..." % (prefix, tapocam.RTSP_PORT))
    if not found:
        print("  nothing listening on %d. Are the cameras on this network?"
              % tapocam.RTSP_PORT)
        return
    for host in found:
        onvif = tapocam.port_open(host, tapocam.ONVIF_PORT, timeout)
        print("  %-15s  %s" % (host, "RTSP + ONVIF -- looks like a Tapo" if onvif
                               else "RTSP only"))
    print("\nAdd one to .env as e.g. TAPO_ROOM_HOST=%s" % found[0])


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--camera", default="all",
                        help="camera name, comma-separated list, or 'all'")
    parser.add_argument("--host", help="probe this address instead of .env")
    parser.add_argument("--stream", type=int, default=1, choices=(1, 2),
                        help="1 = full resolution, 2 = low (default: 1)")
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--scan", action="store_true",
                        help="scan the local network for cameras and exit")
    args = parser.parse_args()

    if args.scan:
        run_scan(min(args.timeout, 1.0))
        return 0

    try:
        if args.host:
            configs = [tapocam.CameraConfig(
                name="manual", host=args.host,
                user=tapocam._shared("USER"), password=tapocam._shared("PASS"))]
        else:
            configs = tapocam.load_cameras(tapocam.parse_selection(args.camera))
    except ConfigError as exc:
        print("Configuration problem:\n  %s" % exc)
        return 2

    print("Cameras configured: %s\n" % ", ".join(tapocam.discover_cameras()))

    ok = True
    for config in configs:
        ok = report(config, args.stream, args.timeout) and ok
        print("")

    print("All cameras reachable and authenticated." if ok
          else "At least one camera failed. Fix that before running view.py.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
