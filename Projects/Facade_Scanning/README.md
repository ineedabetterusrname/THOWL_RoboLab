# Façade Scanning — raster survey of a vertical surface

Single-file demo of robotic building inspection: a wrist-mounted sensor
(camera, thermal imager, ultrasonic probe…) sweeps a façade panel in a
**boustrophedon raster**, pausing at each grid point to capture. The same
motion pattern underlies photogrammetry capture, NDT testing and
paint/plaster quality control.

## Run it

**Simulator first** (no hardware needed): open the
[web simulator](https://ineedabetterusrname.github.io/ur10e-simulator/) →
teach pendant → **Code** tab → paste `facade_scan.py` → **Run**. Tip: mount
the *Wrist Camera* from the catalogue first and watch the scan through its
picture-in-picture view.

**Real robot:** `pip install ur_rtde`, set `ROBOT_IP`, pendant in
*Remote Control*, speed slider low. Replace the `time.sleep()` dwell with
your camera trigger.

## Ideas to extend

- Trigger the Tapo/IMX500 camera at each dwell (see the Tapo Vision Kit project)
- Tilt the pose per row for oblique coverage (photogrammetry overlap)
- Log captured positions to CSV for later image-to-location matching
