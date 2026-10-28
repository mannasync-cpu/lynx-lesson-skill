#!/usr/bin/env python3
"""Build a LYNX Whiteboard lesson (.lynx) from a simple JSON description.

Usage: python3 make_lynx.py lesson.json output.lynx

The .lynx layout was worked out from a lesson saved by LYNX 8.7.6:
a zip holding index.xml (lesson + page list), pages/pageN.xml (the objects
on each page), pixmaps/<id> (pictures) and resolved/<id>/<file> (audio/video).

lesson.json:
{
  "background": "#ffffff",
  "pages": [
    {"background": "#ffffff",
     "items": [
       {"type": "text",  "text": "Title", "x": 60, "y": 60, "w": 1700, "size": 48, "bold": true, "color": "#1a1a1a"},
       {"type": "text",  "text": ["Line one", "Line two"], "x": 60, "y": 200, "w": 900, "size": 30},
       {"type": "image", "path": "photo.png", "x": 1000, "y": 200, "w": 700},
       {"type": "video", "path": "clip.mp4",  "x": 60,   "y": 500, "w": 800, "h": 450},
       {"type": "audio", "path": "song.mp3",  "x": 900,  "y": 700, "w": 450, "h": 280}
     ]}
  ]
}
Pages are 1864 x 1024 units. Text "text" may be a string or a list of lines.

Click-by-click reveal, like PowerPoint builds (LYNX 8.7 animations; the
board's LYNX 8.4 doesn't have them). Mark items with "reveal": they start
hidden when presenting and show in page order. Tap the item before the first
one (e.g. the title) to show it, then tap each newly shown item for the next:
  "reveal": "fade"      (or "appear"; "duration_ms": 800)

Any item that isn't part of a reveal chain can instead move when tapped:
  "tap_move_to": [x, y], "duration_ms": 1000, "easing": 7

Page shortcuts, added before the page's own "items":
  "heading": "Page title"                  (bold, top left; tap it to start reveals)
  "subheading": "Smaller line under it"
  "bullets": ["Point one", "Point two"]    (one text box each, down the left half)
  "bullets_reveal": "fade"                 (reveal the bullets one tap at a time)
Item type "placeholder" is a grey labelled box marking where your own picture
or video goes: {"type": "placeholder", "text": "Screenshot of ...", "x", "y", "w", "h"}
Item type "youtube" streams a YouTube video in LYNX's player: {"type": "youtube", "url": ...}
Pictures can be fitted into a box, keeping their shape: "box": [x, y, w, h]
Pictures and videos can carry a "caption", placed under them and revealed with them.
The build stops with a message if items overlap or run off the page; set
"allow_overlap": true on an item that is meant to sit on top of another.
"""
import base64
import datetime
import html
import json
import os
import struct
import sys
import uuid
import zipfile
import zlib

# Older version numbers make LYNX 8.7 load the file without its animations,
# so match the Mac's LYNX unless the lesson sets "lynx_version".
DEFAULT_LYNX_VERSION = "8.7.6.0"
SCENE_W, SCENE_H = 1864, 1024


def now_stamp():
    return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S.") + "%03d" % (datetime.datetime.now().microsecond // 1000)


def rgba(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return "rgba(%g,%g,%g,1)" % (r, g, b)


def qfont(family, point_size, bold=False):
    """QFont as LYNX stores it: Qt's QDataStream encoding, base64'd."""
    fam = family.encode("utf-16-be")
    weight = 700 if bold else 400
    out = b"\x00\x03\x37\x63" + struct.pack(">I", 0x17)
    out += struct.pack(">I", len(fam)) + fam
    out += b"\xff\xff\xff\xff"                      # no style name
    out += struct.pack(">d", float(point_size))
    out += b"\xff\xff\xff\xff"                      # pixel size: unset
    out += b"\x05\x00\x01" + struct.pack(">H", weight) + b"\x10\x00\x00\x01"
    out += b"\x00" * 12 + struct.pack(">I", 1)       # one family in the list
    out += struct.pack(">I", len(fam)) + fam + b"\x00" * 8
    return "base64:" + base64.b64encode(out).decode()


def rich_text(lines, family, size, bold, color):
    """The Qt rich-text HTML that LYNX keeps for a text box."""
    weight = 700 if bold else 400
    para = ('<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; '
            '-qt-block-indent:0; text-indent:0px;"><span style=" color:%s;">%s</span></p>')
    body = "\n".join(para % (color, html.escape(line)) for line in lines)
    return ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">\n'
            '<html><head><meta name="qrichtext" content="1" /><meta charset="utf-8" /><style type="text/css">\n'
            'p, li { white-space: pre-wrap; }\nhr { height: 1px; border-width: 0; }\n'
            '</style></head><body style=" font-family:\'%s\'; font-size:%gpt; font-weight:%d; font-style:normal;">\n'
            '%s</body></html>') % (family, size, weight, body)


def png_size(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":  # JPEG: walk segments to the size marker
        i = 2
        while i < len(data):
            marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + length
    raise ValueError("pictures must be PNG or JPEG")


def blank_png(w, h, color=(255, 255, 255)):
    raw = b"".join(b"\x00" + bytes(color) * w for _ in range(h))
    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def attr(**kv):
    return " ".join('%s="%s"' % (k, html.escape(str(v), quote=True)) for k, v in kv.items())


def common(z, ts, it, item_id, reveals):
    tappable = "tap_move_to" in it or reveals is not None
    return dict(uuid=item_id, layer=40, z=z, lynxRotation=0,
                creationTimestamp=ts, originTimestamp=ts,
                interactionMode="locked", interactionScope="whilePresenting",
                clickAction="triggerAnimation" if tappable else "none",
                clickActionScope="whilePresenting")


# LYNX's AnimationType values that bring a hidden item in. Fade was checked on
# LYNX 8.7; fly-ins need start poses that LYNX computes itself, so they're left out.
REVEAL_TYPES = {"appear": 2, "fade": 4}

# LYNX animates an item's "origin": its centre, less the 26-unit frame margin.
FRAME_MARGIN = 26


def reveal_chain(items):
    """Map each tapped item's index to the (index, item) it reveals."""
    chain, prev = {}, None
    for i, it in enumerate(items):
        if it.get("reveal"):
            if it["reveal"] not in REVEAL_TYPES:
                raise ValueError("reveal must be one of: %s" % ", ".join(REVEAL_TYPES))
            if prev is None:
                raise ValueError("the first revealed item needs an item before it to tap")
            if "tap_move_to" in items[prev]:
                raise ValueError("an item can't both move when tapped and reveal the next item")
            chain[prev] = (i, it)
        prev = i
    return chain


def animation(it, x, y, w, h, reveal=None, target_id=None):
    """The tap animation LYNX 8.7 saves on an item: reveal the next one, or move."""
    if reveal is not None:
        return ('\n\t\t\t<animation %s>\n\t\t\t</animation>' % attr(
            durationMs=reveal.get("duration_ms", 800), delayMs=0, easingType=7,
            animationType=REVEAL_TYPES[reveal["reveal"]], targetItemId=target_id))
    if "tap_move_to" not in it:
        return ""
    tx, ty = it["tap_move_to"]
    origin = lambda px, py: "%g,%g" % (px + w / 2 - FRAME_MARGIN, py + h / 2 - FRAME_MARGIN)
    pose = ('\n\t\t\t\t<pose dynamic="true">\n\t\t\t\t\t<property key="origin" type="point" value="%s" />'
            '\n\t\t\t\t</pose>')
    return ('\n\t\t\t<animation %s>%s%s\n\t\t\t</animation>' % (
        attr(durationMs=it.get("duration_ms", 1000), delayMs=it.get("delay_ms", 0),
             easingType=it.get("easing", 7), animationType=0),
        pose % origin(x, y), pose % origin(tx, ty)))


def element(lynx_type, a, children=""):
    if not children:
        return "<item %s/>" % attr(lynxType=lynx_type, **a)
    return "<item %s>%s\n\t\t</item>" % (attr(lynxType=lynx_type, **a), children)


HEADING_COLOR = "#1d3557"


def expand_page(page):
    """Turn a page's heading/bullets shortcuts into ordinary items."""
    items = []
    # The subheading goes first so the heading is the item just before the
    # bullets, making the heading what you tap to start the reveals.
    if "subheading" in page:
        items.append({"type": "text", "text": page["subheading"], "x": 70, "y": 140, "w": 1720,
                      "size": 26, "color": "#555555"})
    if "heading" in page:
        items.append({"type": "text", "text": page["heading"], "x": 70, "y": 40, "w": 1720,
                      "size": page.get("heading_size", 46), "bold": True,
                      "color": page.get("heading_color", HEADING_COLOR)})
    reveal = page.get("bullets_reveal")
    top = page.get("bullets_y", 230 if "subheading" in page else 190)
    for k, line in enumerate(page.get("bullets", [])):
        b = {"type": "text", "text": "• " + line, "x": 70, "y": top + k * page.get("bullet_gap", 110),
             "w": page.get("bullets_w", 900), "size": page.get("bullet_size", 28)}
        if reveal:
            b["reveal"] = reveal
        items.append(b)
    return items + with_captions(page.get("items", []))


def with_captions(items):
    """Expand "caption" on pictures and videos into a small text line under them.

    A caption of revealed media reveals with it: it comes up when the picture is
    tapped, or for videos (where a tap plays the video) it shows first and is
    tapped to bring in the video.
    """
    out = []
    for it in items:
        if "caption" not in it:
            out.append(it)
            continue
        it = dict(it)
        text = it.pop("caption")
        x, y, w, h = it.get("box") or (it.get("x", 60), it.get("y", 60), it.get("w", 800), it.get("h", 450))
        cap = {"type": "text", "text": text, "x": x, "y": y + h + 10, "w": w, "size": 18, "color": "#777777"}
        if it.get("reveal"):
            cap["reveal"] = "appear"
        if it["type"] in ("video", "audio", "youtube") and it.get("reveal"):
            out += [cap, it]
        else:
            out += [it, cap]
    return out


def placeholder_to_text(it):
    """A placeholder is a grey italic text box saying what media goes there."""
    t = dict(it, type="text", color=it.get("color", "#8a8a8a"), size=it.get("size", 24))
    t["text"] = ["[ " + it["text"] + " ]", "Replace with your own picture or video"]
    return t


def wrap_lines(lines, width, size, bold):
    """Word-wrap lines to fit width, estimating Poppins character widths."""
    per_line = max(1, int(width / (size * (0.64 if bold else 0.6))))
    out = []
    for line in lines:
        indent = "    " if line.startswith("• ") else ""
        words, current = line.split(" "), ""
        for word in words:
            candidate = (current + " " + word) if current else word
            if len(candidate) <= per_line or not current:
                current = candidate
            else:
                out.append(current)
                current = indent + word
        out.append(current)
    return out


def describe(it):
    """A short label for an item, used in layout error messages."""
    if it["type"] == "text":
        first = it["text"][0] if isinstance(it["text"], list) else it["text"]
        return 'text "%s"' % (first[:40] + ("..." if len(first) > 40 else ""))
    return "%s %s" % (it["type"], os.path.basename(it.get("path", it.get("url", ""))))


def check_layout(page_no, boxes):
    """Stop the build if items run off the page or sit on top of each other."""
    problems = []
    for label, x, y, w, h, _ in boxes:
        if x < 0 or y < 0 or x + w > SCENE_W or y + h > SCENE_H:
            problems.append("%s runs off the page (%g,%g to %g,%g)" % (label, x, y, x + w, y + h))
    for i, (la, ax, ay, aw, ah, oka) in enumerate(boxes):
        for lb, bx, by, bw, bh, okb in boxes[i + 1:]:
            if oka or okb:
                continue
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                problems.append("%s overlaps %s" % (la, lb))
    if problems:
        raise ValueError("page %d layout:\n  " % (page_no + 1) + "\n  ".join(problems))


def build(spec, out_path, base_dir):
    ts = now_stamp()
    version = spec.get("lynx_version", DEFAULT_LYNX_VERSION)
    zf = zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED)
    frames = []
    for n, page in enumerate(spec["pages"]):
        page_id = str(uuid.uuid4())
        bg = rgba(page.get("background", spec.get("background", "#ffffff")))
        items, urls = [], []
        page_items = [placeholder_to_text(it) if it["type"] == "placeholder" else it
                      for it in expand_page(page)]
        ids = [str(uuid.uuid4()) for _ in page_items]
        chain = reveal_chain(page_items)
        boxes = []
        for z, it in enumerate(page_items):
            kind = it["type"]
            x, y = it.get("x", 60), it.get("y", 60)
            target, reveal = chain.get(z, (None, None))
            target_id = ids[target] if target is not None else None
            if kind == "text":
                lines = it["text"] if isinstance(it["text"], list) else [it["text"]]
                size = it.get("size", 30)
                family = it.get("font", "Poppins")
                w = it.get("w", 1700)
                # LYNX sizes text boxes to their longest line instead of wrapping,
                # so break long lines ourselves to keep them inside the box.
                lines = wrap_lines(lines, w - 2 * FRAME_MARGIN, size, it.get("bold", False))
                h = it.get("h", int(size * 1.6 * len(lines)) + 10)
                a = common(z, ts, it, ids[z], reveal)
                a.update(font=qfont(family, size, it.get("bold", False)),
                         defaultColor=rgba(it.get("color", "#000000")),
                         html=rich_text(lines, family, size, it.get("bold", False), it.get("color", "#000000")),
                         valign=32, textWidth=w - 2 * FRAME_MARGIN, size="%g,%g" % (w, h), scenePos="%g,%g" % (x, y))
                items.append(element("TextItem", a, animation(it, x, y, w, h, reveal, target_id)))
                boxes.append((describe(it), x, y, w, h, it.get("allow_overlap", False)))
            elif kind == "image":
                data = open(os.path.join(base_dir, it["path"]), "rb").read()
                pw, ph = png_size(data)
                if "box" in it:  # fit inside [x, y, w, h], keeping the picture's shape, centred
                    bx, by, bw, bh = it["box"]
                    scale = min(bw / pw, bh / ph)
                    w, h = pw * scale, ph * scale
                    x, y = bx + (bw - w) / 2, by + (bh - h) / 2
                else:
                    w = it.get("w", pw)
                    h = it.get("h", w * ph / pw)
                pix_id = str(uuid.uuid4().int)
                zf.writestr("pixmaps/" + pix_id, b"\x00\x00\x00\x01" + data)
                a = common(z, ts, it, ids[z], reveal)
                a.update(md5hash=pix_id, size="%g,%g" % (w, h), scenePos="%g,%g" % (x, y),
                         panoramic="false", panoramicLocked="false", panoramicFOV=90, panoramicRotation="0,0",
                         fillMode=1, brightness=0, contrast=0, hue=0, saturation=0)
                items.append(element("PictureItem", a, animation(it, x, y, w, h, reveal, target_id)))
                boxes.append((describe(it), x, y, w, h, it.get("allow_overlap", False)))
            elif kind in ("video", "audio", "youtube"):
                url_id = str(uuid.uuid4())
                if kind == "youtube":
                    # LYNX streams YouTube links in its own player, so nothing is stored in the lesson.
                    urls.append('<url %s/>' % attr(id=url_id, pid=it["url"], resolvable="true"))
                else:
                    path = os.path.join(base_dir, it["path"])
                    zf.write(path, "resolved/%s/%s" % (url_id, os.path.basename(path)))
                    urls.append('<url %s/>' % attr(id=url_id, pid="file://" + os.path.abspath(path), resolvable="true"))
                w, h = it.get("w", 800), it.get("h", 450)
                a = common(z, ts, it, ids[z], reveal)
                a.update(mute="false", volume=it.get("volume", 0.75), looping=str(it.get("loop", False)).lower(),
                         panoramicLocked="false", panoramicFOV=90, panoramicRotation="0,0",
                         size="%g,%g" % (w, h), resolvedSize="true", scenePos="%g,%g" % (x, y))
                meta = attr(loaded="false", hasVideo=str(kind != "audio").lower(), hasAudio="true",
                            isPanoramic="false", urlId=url_id)
                items.append(element("MediaItem", a, '\n\t\t\t<coverImage type="0"/>\n\t\t\t<metaData %s/>%s'
                                     % (meta, animation(it, x, y, w, h, reveal, target_id))))
                boxes.append((describe(it), x, y, w, h, it.get("allow_overlap", False)))
            else:
                raise ValueError("unknown item type: %s" % kind)
        check_layout(n, boxes)
        page_xml = ('<?xml version="1.0"?>\n<page %s>\n\t<layout type="0" />\n\t<list property="itemData">\n\t\t%s\n\t</list>\n'
                    '\t<urls>\n\t\t%s\n\t</urls>\n</page>\n') % (
            attr(version=version, timestamp=ts, uuid=page_id, sceneRect="0,0,%d,%d" % (SCENE_W, SCENE_H),
                 fitHint=0, infiniteCanvasEnabled="false", background=bg),
            "\n\t\t".join(items), "\n\t\t".join(urls))
        zf.writestr("pages/page%d.xml" % n, page_xml)
        zf.writestr("thumbnails/page%d.png" % n, blank_png(186, 102))
        frames.append('<mapping id="%s" path="pages/page%d.xml" />' % (page_id, n))
    index = ('<?xml version="1.0"?>\n<lesson %s>\n\t<backgroundData %s>\n\t\t<layout type="0" />\n\t</backgroundData>\n'
             '\t<frameMap>\n\t\t%s\n\t</frameMap>\n</lesson>\n') % (
        attr(version=version, timestamp=ts),
        attr(uuid=str(uuid.uuid4()), sceneRect="0,0,%d,%d" % (SCENE_W, SCENE_H), fitHint=0,
             infiniteCanvasEnabled="false", background=rgba(spec.get("background", "#ffffff"))),
        "\n\t\t".join(frames))
    zf.writestr("index.xml", index)
    zf.writestr("thumbnail.png", blank_png(186, 102))
    zf.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    spec_path = sys.argv[1]
    try:
        build(json.load(open(spec_path)), sys.argv[2], os.path.dirname(os.path.abspath(spec_path)))
    except ValueError as err:
        if os.path.exists(sys.argv[2]):
            os.remove(sys.argv[2])
        sys.exit("Can't build the lesson: %s" % err)
    print("wrote", sys.argv[2])
