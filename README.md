# LYNX lesson maker

Make lessons for **Clevertouch LYNX Whiteboard** (`.lynx` files) from a short
JSON description: multiple pages, headings, bullet points, pictures, video,
audio, and PowerPoint-style **click-by-click reveals**.

It works as a plain Python script and as an **Agent Skill** for Claude Code,
so you can ask Claude for "a LYNX lesson on ..." and get a ready-to-present file.

> Unofficial. Not made by or affiliated with Clevertouch or Boxlight. The file
> format notes come from studying lessons saved by LYNX, for interoperability.

## Quick start

Needs Python 3 (standard library only).

```bash
python3 scripts/make_lynx.py examples/reveal-demo/lesson.json Reveal-Demo.lynx
```

Open `Reveal-Demo.lynx` in LYNX Whiteboard, choose **View → Start Presenting**,
tap the heading, then tap each line as it appears.

A small lesson:

```json
{
  "pages": [
    {
      "heading": "The Water Cycle",
      "bullets_reveal": "fade",
      "bullets": ["Evaporation", "Condensation", "Precipitation"],
      "items": [
        {"type": "image", "path": "cycle.png", "x": 1050, "y": 200, "w": 700, "reveal": "fade"}
      ]
    }
  ]
}
```

## What you can put on a page

| Feature | How |
|---|---|
| Heading and subheading | `"heading"`, `"subheading"` |
| Bullet points | `"bullets": [...]` |
| Text boxes | `{"type": "text", ...}` with size, colour, bold, font |
| Pictures | `{"type": "image", "path": "photo.png", ...}` |
| Video and audio | `{"type": "video" / "audio", "path": ...}`, stored in the lesson |
| YouTube clips | `{"type": "youtube", "url": ...}`, played in LYNX's YouTube player |
| Screenshots of X posts | `scripts/x_post_shot.py` saves them; place with `"box"` |
| Captions and credits | `"caption": "..."` on a picture or video, revealed with it |
| Spaces for your own media | `{"type": "placeholder", "text": "Screenshot of ..."}` |
| Click-by-click reveal | `"reveal": "fade"` or `"appear"`, or `"bullets_reveal"` |
| Move when tapped | `"tap_move_to": [x, y]` |
| Tidy layouts | Long text is wrapped; overlapping or off-page items stop the build |

Full reference: [docs/LESSON-SPEC.md](docs/LESSON-SPEC.md).
How `.lynx` files work: [docs/FILE-FORMAT.md](docs/FILE-FORMAT.md).

## Using it as a Claude Code skill

Copy or link this folder into your skills folder:

```bash
ln -s "$PWD" ~/.claude/skills/lynx-lesson
```

Then ask Claude Code something like *"Make me a LYNX lesson on photosynthesis,
5 pages, each point revealed on tap."* Claude follows [SKILL.md](SKILL.md).

## Compatibility

| LYNX version | Opens lessons | Reveal and move effects |
|---|---|---|
| 8.7 (Windows, macOS, current boards) | Yes | Yes |
| 8.4 (older Android boards) | Yes | No: everything shows from the start |

Fly-in, zoom and spin effects exist in LYNX but aren't offered yet; they need
positions that LYNX works out itself.

## Examples

- [examples/reveal-demo](examples/reveal-demo): two pages showing reveals,
  placeholders and a tap-to-move answer.

## License

MIT. See [LICENSE](LICENSE).
