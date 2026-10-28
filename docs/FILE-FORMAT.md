# The .lynx file format

Notes from studying lessons saved by LYNX Whiteboard 8.7.6 (macOS) and the
LYNX 8.4.15 Android app. This is unofficial, written for interoperability, and
may not cover every feature.

## Container

A `.lynx` file is a ZIP archive:

| Path | Contents |
|---|---|
| `index.xml` | The lesson: page size, default background, list of pages |
| `pages/page0.xml`, `pages/page1.xml`, ... | The objects on each page |
| `pixmaps/<id>` | Pictures: the 4 bytes `00 00 00 01`, then the PNG or JPEG data |
| `resolved/<url-id>/<file name>` | Video and audio files stored in the lesson |
| `thumbnail.png`, `thumbnails/pageN.png` | Preview images (LYNX regenerates them) |

## index.xml

```xml
<?xml version="1.0"?>
<lesson version="8.7.6.0" timestamp="2026/10/28 06:04:27.508">
  <backgroundData uuid="..." sceneRect="0,0,1864,1024" fitHint="0"
                  infiniteCanvasEnabled="false" background="rgba(1,1,1,1)">
    <layout type="0" />
  </backgroundData>
  <frameMap>
    <mapping id="PAGE-UUID" path="pages/page0.xml" />
  </frameMap>
</lesson>
```

- `version` matters: LYNX 8.7 loads files stamped with an older version
  without their animations.
- Colours are `rgba(r,g,b,a)` with each channel from 0 to 1.

## Page files

```xml
<page version="8.7.6.0" timestamp="..." uuid="PAGE-UUID" sceneRect="0,0,1864,1024"
      fitHint="0" infiniteCanvasEnabled="false" background="rgba(1,1,1,1)">
  <layout type="0" />
  <list property="itemData">
    <item lynxType="TextItem" ... />
    <item lynxType="PictureItem" ... />
  </list>
  <urls>
    <url id="URL-ID" pid="file:///original/path.mp4" resolvable="true" />
  </urls>
</page>
```

### Attributes every item has

| Attribute | Meaning |
|---|---|
| `uuid` | Item id, referenced by animations |
| `scenePos`, `size` | Top-left position and size, as `x,y` and `w,h` |
| `layer`, `z` | Drawing layer (40 for normal content) and stacking order |
| `lynxRotation` | Rotation in degrees |
| `creationTimestamp`, `originTimestamp` | `YYYY/MM/DD hh:mm:ss.mmm` |
| `interactionMode`, `interactionScope` | `locked` / `whilePresenting` by default |
| `clickAction`, `clickActionScope` | What a tap does while presenting: `none`, `triggerAnimation`, ... |

LYNX's code also lists `coverEnabled`, `coverRows`, `coverColumns`,
`coverBrush`, `coverPen`, `coverDefaultActive`, `coverShowTileNumbers`,
`animationTriggers` and `link` as item attributes. Their exact saved values
haven't been checked yet.

### TextItem

- `html`: the text as Qt rich-text HTML (escaped in the XML).
- `font`: `base64:` followed by a Qt `QDataStream` serialization of a `QFont`
  (family as UTF-16, point size as a big-endian double, weight 400 or 700).
- `defaultColor`, `valign="32"`, `textWidth` (box width minus 52).
- LYNX also saves layout caches (`flowStart`, `lineWrapData`, `l6fmt`, ...);
  it recalculates them when they're missing.
- LYNX sizes a text box to its longest line rather than wrapping to `size`,
  so line breaks have to be written into the HTML (one `<p>` per line).

### PictureItem

- `md5hash`: a large decimal number naming the picture in `pixmaps/`. Any
  unique number works as long as the file name matches.
- `fillMode="1"`, plus `brightness`, `contrast`, `hue`, `saturation`.

### MediaItem (video and audio)

```xml
<item lynxType="MediaItem" ... mute="false" volume="0.75" looping="false" resolvedSize="true">
  <coverImage type="0" />
  <metaData loaded="false" hasVideo="true" hasAudio="true" isPanoramic="false" urlId="URL-ID" />
</item>
```
`urlId` matches a `<url>` on the page and a folder under `resolved/`.

A **YouTube video** is the same MediaItem whose `<url>` has a YouTube link as
its `pid` (`https://www.youtube.com/watch?v=...`) and no file under
`resolved/`. LYNX recognises the link and plays it in its YouTube player.

## Animations (LYNX 8.7)

An animation is a child of the item that is **tapped**, and that item has
`clickAction="triggerAnimation"`:

```xml
<animation durationMs="800" delayMs="0" easingType="7" animationType="4"
           targetItemId="UUID-OF-ITEM-TO-ANIMATE">
</animation>
```

- Without `targetItemId`, the item animates itself.
- `easingType` is a Qt `QEasingCurve::Type` (7 is ease in-out).
- `animationType` values, in LYNX's order:

| Value | Type | Value | Type |
|---|---|---|---|
| 0 | Toggle (between poses A and B) | 9 | FlyInDown |
| 1 | Set | 10 | FlyOutLeft |
| 2 | Appear | 11 | FlyOutRight |
| 3 | Disappear | 12 | FlyOutUp |
| 4 | FadeIn | 13 | FlyOutDown |
| 5 | FadeOut | 14 | ZoomIn |
| 6 | FlyInLeft | 15 | ZoomOut |
| 7 | FlyInRight | 16 | Spin |
| 8 | FlyInUp | | |

- **Entrance types** (Appear, FadeIn, FlyIn..., ZoomIn) hide their target
  when presenting starts and show it when triggered. FadeIn and Appear were
  confirmed in LYNX 8.7. A FlyIn without poses landed in the wrong place.
- **Toggle** moves between two saved poses. Each pose lists properties; the
  one seen so far is `origin`, the item's centre minus 26 units:

```xml
<animation durationMs="1000" delayMs="0" easingType="7" animationType="0">
  <pose dynamic="true"><property key="origin" type="point" value="1378.37,468.49" /></pose>
  <pose dynamic="true"><property key="origin" type="point" value="331.01,225.08" /></pose>
</animation>
```

## LYNX 8.4 (Android boards)

LYNX 8.4.15 uses the same container and page structure, but has no
`clickAction`, `interactionMode` or `<animation>` support. Lessons open, and
animated items simply show from the start.
