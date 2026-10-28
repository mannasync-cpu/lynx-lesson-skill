#!/usr/bin/env python3
"""Save screenshots of public X (Twitter) posts as PNGs for use in a lesson.

Usage: python3 x_post_shot.py OUTPUT_DIR POST_URL [POST_URL ...]

Each post is rendered from X's own embed page (platform.twitter.com) in
headless Google Chrome, then cropped to the post card. Files are named
<handle>-<post id>.png. Needs Google Chrome; uses only the Python standard library.
"""
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]
WIDTH, HEIGHT, SCALE = 550, 1800, 2


def chrome():
    for path in CHROME_PATHS:
        if path and os.path.exists(path):
            return path
    sys.exit("Google Chrome not found")


def read_png(path):
    """Decode an 8-bit RGB/RGBA PNG into (width, height, channels, rows)."""
    data = open(path, "rb").read()
    pos, idat, w = 8, b"", 0
    while pos < len(data):
        length, tag = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
            if depth != 8 or ctype not in (2, 6):
                raise ValueError("unsupported PNG type")
            ch = 4 if ctype == 6 else 3
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    raw, stride = zlib.decompress(idat), w * ch
    rows, prev = [], bytearray(stride)
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b, c = prev[i], prev[i - ch] if i >= ch else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, ch, rows


def write_png(path, w, ch, rows):
    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))
    raw = b"".join(b"\x00" + r for r in rows)
    ihdr = struct.pack(">IIBBBBB", w, len(rows), 8, 6 if ch == 4 else 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def crop_blank_bottom(path):
    """Cut the white space below the post card."""
    w, h, ch, rows = read_png(path)
    white = bytes([255] * ch)
    last = h - 1
    while last > 0 and all(rows[last][i:i + ch] in (white, bytes(ch)) for i in range(0, w * ch, ch * 8)):
        last -= 1
    write_png(path, w, ch, rows[:min(h, last + 2 * SCALE)])


def shoot(url, out_dir):
    m = re.search(r"(?:x|twitter)\.com/(\w+)/status/(\d+)", url)
    if not m:
        raise ValueError("not an X post link: %s" % url)
    handle, post_id = m.groups()
    out = os.path.join(out_dir, "%s-%s.png" % (handle, post_id))
    embed = ("https://platform.twitter.com/embed/Tweet.html?id=%s&dnt=true&hideThread=true&theme=light&lang=en"
             % post_id)
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--user-data-dir=" + profile, "--window-size=%d,%d" % (WIDTH, HEIGHT),
                        "--force-device-scale-factor=%d" % SCALE, "--virtual-time-budget=25000",
                        "--screenshot=" + out, embed],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=120)
    crop_blank_bottom(out)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    os.makedirs(sys.argv[1], exist_ok=True)
    for link in sys.argv[2:]:
        print(shoot(link, sys.argv[1]))
