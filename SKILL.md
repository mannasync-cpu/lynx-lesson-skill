---
name: lynx-lesson
description: Create Clevertouch LYNX Whiteboard lessons (.lynx files) with multiple pages, headings, bullet points, pictures, video, audio and click-by-click reveal effects, ready to open and present in LYNX. Use when the user asks for a LYNX lesson, a .lynx file, a presentation for their Clevertouch board or LYNX Whiteboard, or wants slides with PowerPoint-style "appear on click" effects in LYNX.
---

# LYNX lesson maker

Builds `.lynx` lesson files for Clevertouch LYNX Whiteboard from a JSON
description, using `scripts/make_lynx.py` (Python 3 standard library only).

## Workflow

1. **Plan the pages** with the user: a heading per page, the points to show,
   and which pictures, videos or audio go where.
2. **Gather media.** For public X posts, save screenshots with
   `python3 scripts/x_post_shot.py media <post links>`. For YouTube clips, use
   a `youtube` item with the link; it streams, nothing is downloaded.
3. **Write `lesson.json`** next to the media files (see `docs/LESSON-SPEC.md`).
   Prefer the page shortcuts (`heading`, `subheading`, `bullets`,
   `bullets_reveal`) and add extra objects under `items`. Put screenshots in a
   `box` and credit them with `caption`.
4. **Build it**:
   ```
   python3 scripts/make_lynx.py path/to/lesson.json path/to/Output.lynx
   ```
   Media paths in the JSON are relative to the JSON file. If the build stops
   with a layout message, move or resize the named items and build again.
5. **Check it in LYNX** if you can: every page, in editing view, then a
   presenting run of at least one page's reveals.
6. **Hand it over** with how to present it: open in LYNX, choose
   View → Start Presenting, tap the heading to start each page's reveals,
   then tap each newly shown item to reveal the next.

## Rules of thumb

- Pages are **1864 × 1024** units. Keep text inside x 60–1800, y 30–990.
- Layouts that work: bullets on the left at `bullets_w` 880 with media in a
  `box` at x 990, w 820; or three screenshots across at x 70 / 652 / 1234,
  w 560 each. Use a `bullet_gap` of 140–150 when bullets wrap onto 2–3 lines.
- LYNX doesn't wrap text, so the script wraps it; the build refuses
  overlapping or off-page items. Don't work around that with `allow_overlap`
  unless the overlap is intended.
- Put the heading first; it is what the presenter taps to start a page's reveals.
- One reveal per tap, in page order. Group a caption with its picture by
  putting the caption right after the picture.
- Use `"placeholder"` items where the user will drop in their own screenshots
  or clips later, so the layout is ready before the media exists.
- Write the content in your own words and attribute facts to their sources.
  Don't copy someone else's video, slides or analysis wholesale, and don't
  download videos from YouTube or X; link YouTube clips instead.
- Reveals start when presenting starts. If a lesson opens already presenting,
  stop and start presenting again.
- Pictures must be PNG or JPEG. Video and audio are stored inside the lesson,
  so large clips make large files.

## Compatibility

- Reveal and move effects are **LYNX 8.7 features**. Older LYNX (8.4, as on
  some Android boards) opens the lessons but shows every item from the start.
- Files are stamped as LYNX 8.7.6. Older version numbers make LYNX 8.7 skip
  the animations; set `"lynx_version"` only if you know you need to.
- Fly-in, zoom and spin effects exist in LYNX but need positions LYNX
  calculates itself, so the script only offers `fade` and `appear`.

See `docs/FILE-FORMAT.md` for how `.lynx` files are put together.
