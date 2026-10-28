# lesson.json reference

A lesson is a JSON object with a list of pages. Every coordinate is in LYNX
page units: a page is **1864 wide × 1024 high**, with (0, 0) at the top left.

```json
{
  "background": "#ffffff",
  "pages": [ { ...page... }, { ...page... } ]
}
```

| Lesson key | Meaning | Default |
|---|---|---|
| `pages` | The pages, in order | required |
| `background` | Colour for pages that don't set their own | `#ffffff` |
| `lynx_version` | Version stamped in the file | `8.7.6.0` |

## Pages

| Page key | Meaning | Default |
|---|---|---|
| `heading` | Bold title at the top left. Tap it to start the page's reveals | none |
| `heading_size`, `heading_color` | Heading size (pt) and colour | `46`, `#1d3557` |
| `subheading` | Smaller grey line under the heading | none |
| `bullets` | List of points, one text box each, down the left side | none |
| `bullets_reveal` | `"fade"` or `"appear"` to reveal bullets one tap at a time | off |
| `bullets_y` | Top of the first bullet | `190`, or `230` with a subheading |
| `bullets_w` | Width of each bullet box | `900` |
| `bullet_size`, `bullet_gap` | Bullet text size and spacing | `28`, `110` |
| `background` | Page colour | lesson background |
| `items` | Extra objects, added after the heading and bullets | none |

## Items

Every item has a `type` and a position `x`, `y`. Most also take a width `w`
and height `h`.

### text
```json
{"type": "text", "text": "One line", "x": 70, "y": 300, "w": 900, "size": 30,
 "bold": false, "color": "#000000", "font": "Poppins"}
```
`text` can also be a list of lines. LYNX doesn't wrap text to the box (it
widens the box to the longest line instead), so the script breaks long lines
itself to fit `w`, and works out the height from the number of lines if `h` is
left out.

### image
```json
{"type": "image", "path": "photo.png", "x": 1000, "y": 200, "w": 700}
```
PNG or JPEG. Give `w` and the height follows the picture's shape, or give both.

### video and audio
```json
{"type": "video", "path": "clip.mp4", "x": 60, "y": 500, "w": 800, "h": 450,
 "volume": 0.75, "loop": false}
```
The file is copied into the lesson.

### youtube
```json
{"type": "youtube", "url": "https://www.youtube.com/watch?v=VIDEO_ID", "x": 940, "y": 250, "w": 850, "h": 478}
```
Plays in LYNX's own YouTube player. Nothing is stored in the lesson, so the
board or computer needs internet when presenting.

### Fitting pictures into a box
```json
{"type": "image", "path": "post.png", "box": [990, 150, 820, 770]}
```
`box` is `[x, y, w, h]`. The picture is scaled to fit inside it, keeping its
shape, and centred. Use it for screenshots of unpredictable size.

### Captions
Add `"caption": "Source or credit"` to a picture, video or YouTube item. A
small grey line is placed under it (under the `box`, if there is one). If the
item is revealed, its caption is too: tapping a picture brings in its caption,
and for videos (where a tap plays the video) the caption shows first and is
tapped to bring in the video.

### placeholder
```json
{"type": "placeholder", "text": "Screenshot of the X post", "x": 1050, "y": 200, "w": 700, "h": 400}
```
A grey labelled box showing where a picture or video will go. Replace it in
LYNX later.

## Effects

Both effects play while presenting, in LYNX 8.7 and later.

### Click-by-click reveal
Add `"reveal": "fade"` (or `"appear"`) to any item. Revealed items start
hidden. They show in page order: tap the item **just before** the first one
(normally the heading) to show it, then tap each newly shown item for the next.
`"duration_ms"` sets the fade length (default 800).

Reveals take effect when presenting **starts**. If LYNX opens a lesson while
it's already presenting, everything shows; choose View → Stop Presenting, then
View → Start Presenting.

### Move on tap
```json
{"type": "text", "text": "Answer", "x": 70, "y": 700, "tap_move_to": [1000, 700],
 "duration_ms": 1000, "easing": 7}
```
The item slides to the new position when tapped, and back again on the next
tap. An item can't both move and be the tap that reveals the next item.

## Layout check

Every build checks each page. It stops, naming the items, if any two items
overlap or any item runs off the page:

```
Can't build the lesson: page 2 layout:
  text "• The water cycle has four stages..." overlaps image diagram.png
```

Fix the positions (or bullet spacing) and build again. For an item that is
meant to sit on top of another, add `"allow_overlap": true`.

## Screenshots of X posts

`scripts/x_post_shot.py` saves public X posts as cropped PNGs, rendered from
X's own embed page in headless Google Chrome:

```bash
python3 scripts/x_post_shot.py media https://x.com/USER/status/ID [more links]
```

Files are named `USER-ID.png`. Use them with `"box"` so tall posts fit.
