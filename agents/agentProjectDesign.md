# Project Design

## Design North Star
The interface should feel like stepping into a historic Grand Hotel between 1880 and 1914:

- luxurious before it feels mysterious
- immersive before it feels game-like
- elegant and legible for casual players
- atmospheric without becoming cluttered or theatrical

The default visual direction for this project is **the dossier-luxury hybrid defined in `moodboards/_merge_final.html`**.

Reference boards live in `moodboards/`:

- `moodboards/_merge_final.html`

Unless a human explicitly chooses another direction, design decisions should follow `moodboards/_merge_final.html`.

## Visual Tone
Think palace hotel dossier, not tech product:

- cream stationery, foxed paper, marble counters, polished walnut, brass trims, velvet accents
- warm light, quiet grandeur, and a sense of private privilege
- mystery should appear in details, paper trails, labels, shadow, dialogue, and scene transitions
- avoid sterile minimalism, bright startup aesthetics, or playful game UI tropes

The player should feel:

1. "I have entered an expensive historic place."
2. "Something is slightly off here."
3. "I want to keep looking."

## Color Palette

### Primary Colors
- **Lobby Parchment:** `#F3EADF`
- **Guest Ledger:** `#E9D8C0`
- **Aged Gold:** `#B08A3E`
- **Burgundy Velvet:** `#6F2430`
- **Parlor Green:** `#31463A`

### Supporting Neutrals
- **Guest Paper:** `#FCF6EE`
- **Walnut Ink:** `#2D1D16`
- **Warm Taupe:** `#6F584B`
- **Rule Line:** `rgba(45, 29, 22, 0.14)`

### Semantic Colors
- **Success:** `#31463A`
- **Error:** `#6F2430`
- **Warning:** `#8A5B24`
- **Info:** `#5E6F7B`

### Palette Rules
- Default backgrounds should be warm, not cold white.
- Use parchment, guest-paper, and ledger tones as the main surfaces.
- Gold is an accent, not a fill color for large surfaces.
- Burgundy should mark drama, focus, danger, or premium action moments.
- Green should support the hotel-world atmosphere, not overpower it.
- Pure black should be avoided in standard UI; use warm dark browns instead.

## Typography

### Font Families
- **Display / Scene Titles:** `Playfair Display`
- **Body / UI / Evidence Text:** `IBM Plex Mono`
- **Accents:** uppercase dossier labels, typed metadata, stamps, hotel labels, and chapter markers

### Typography Direction
- Headings should feel ceremonial, editorial, and hotel-branded.
- Body text should read like evidence, registry notes, and collected documents while remaining legible on mobile.
- Dialogue and clue text should feel intimate, investigative, and literary, not corporate.

### Type Scale
- **Hero (h1):** `48-56px`, line-height `1.1-1.2`
- **Heading 2 (h2):** `32-40px`, line-height `1.2-1.3`
- **Heading 3 (h3):** `22-28px`, line-height `1.3-1.4`
- **Body Large:** `18px`, line-height `1.6`
- **Body:** `16px`, line-height `1.6`
- **Small:** `14px`, line-height `1.5`
- **Micro labels:** `12-13px`, uppercase or small-caps styling when helpful

## Spacing System

### Base Unit
- Base: `4px`

### Scale
- `xs`: `4px`
- `sm`: `8px`
- `md`: `16px`
- `lg`: `24px`
- `xl`: `32px`
- `2xl`: `48px`
- `3xl`: `64px`

### Spatial Principles
- Give important scenes and clue cards room to breathe.
- Use spacing to create calm luxury, not app-density.
- Reserve tighter spacing for dialogue transcripts or compact clue lists.

## Surface Treatment
- Surfaces should feel like paper, linen, lacquered wood, leather, or softly polished stone.
- Prefer stacked document sheets, dossier panels, and stationery framing over flat white rectangles.
- Use subtle gradients and warm texture cues when they improve atmosphere.
- Borders should look like stationery rules, framing lines, or archival trim, not generic form borders.

## Component Styles

### Buttons
- **Primary:** rich burgundy or deep hotel green with warm ivory text
- **Secondary:** parchment or transparent button with fine framed border
- **Hover state:** gentle lift, glow, or deepen in tone; no playful bounce
- **Shape:** tailored pill or restrained rectangular buttons that still feel period-appropriate
- **Use:** primary actions should feel deliberate and premium

### Cards and Panels
- Use framed cards with warm surfaces, soft shadow, and paper-document logic.
- Corner radius should feel tailored, not overly soft.
- Important cards may use a double-border, gold divider, dossier label, or title plaque treatment.
- Scene cards should feel collectible and narrative, not dashboard-like.

### Inputs
- Inputs should feel like writing on elegant hotel stationery.
- Use warm backgrounds, subtle framed borders, and strong focus contrast.
- Avoid flat gray fields that feel generic or office-like.

### Chat and Dialogue Surfaces
- Dialogue areas should feel intimate, like a private conversation recorded on hotel stationery or internal telegram stock.
- Different speakers may be separated with subtle tone shifts, border accents, typed labels, or evidence headers.
- Avoid bright chat bubbles or consumer-messaging aesthetics.

### Modals and Overlays
- Overlays should dim the world as if entering a more private room or secret layer.
- Modal panels should feel like invitation cards, clue envelopes, guest folios, or case-file inserts.
- Use stronger shadows and richer contrast for reveal moments.

## Visual Effects

### Shadows
- **Small:** soft ambient elevation for cards
- **Medium:** noticeable depth for overlays, floating panels, and active clues
- **Large:** reserved for dramatic reveal moments

### Borders
- Use warm low-contrast borders by default.
- Accent borders may use brass, gold, or deep burgundy in special moments.
- Decorative dividers, ruled lines, and dossier separators are encouraged when they improve atmosphere and clarity.

### Motion
- Motion should be graceful and quiet, around `180-250ms` for most UI transitions.
- Favor fade, soft slide, and subtle scale over springy or playful motion.
- Scene changes should feel cinematic and deliberate.

## Imagery and Atmosphere
- Every visual should support the illusion of a luxury Grand Hotel stay.
- Rooms should feel materially rich: chandeliers, carpets, drapery, brass, polished wood, marble, stationery.
- Light should be warm and directional, not flat.
- Mystery should appear through contrast, occlusion, reflection, partial reveals, suspicious object placement, and paper-trail evidence.
- Avoid generic fantasy, horror, cartoon, or modern SaaS visuals.

## Icons and Graphic Details
- Icons should be elegant and restrained.
- Prefer thin to medium stroke icons with a timeless silhouette.
- Use decorative details sparingly: monograms, labels, seals, stamps, ruled lines, evidence markers, and filigree dividers.
- Ornament should come from the archival structure as often as possible, not from extra chrome.

## Responsive Breakpoints
- Mobile: `< 640px`
- Tablet: `640px - 1024px`
- Desktop: `> 1024px`
- Current implementation priority: desktop-first. Mobile adaptation is planned for a later phase.

## Layout Patterns

### Container
- Max width: generally `max-w-3xl` for narrative screens
- Padding: `px-4 sm:px-6 lg:px-8`
- Center content for focus, but allow wider scenic sections when environment visuals need room

### Screen Structure
- Top area: atmospheric title, hotel header, room context, or narrative framing
- Middle area: primary scene, dialogue, evidence, or object interaction
- Bottom or follow-up area: actions, clue review, or next-step prompts

### Layout Direction
- Interfaces should feel like handled hotel documents, not generic product screens.
- Prefer stacked paper sections, dossier sheets, telegram panels, evidence cards, and stationery framing.
- Ornament should come from archival structure: monograms, rules, labels, seals, and document edges.

### Clue and Score Moments
- Treat clue discovery as a premium reveal.
- Use framed cards, dossier labels, and stronger contrast to make discoveries memorable.
- Score screens should feel ceremonial, like a verdict, guest folio, or private hotel report.

## Implementation Notes
- Follow the currently approved delivery priority: desktop-first for the active prototype phase, then adapt for mobile in a later pass.
- Use Tailwind utility classes in service of this design system.
- Prefer warm neutrals over grayscale defaults.
- Test readability carefully on smaller screens and lower-brightness environments.
- Ensure all touch targets are at least `44px` tall.
- Preserve accessibility and clarity even when using decorative styling.

## What To Avoid
- Apple-inspired sterile minimalism as the main reference
- cold grayscale palettes
- overly glossy luxury that feels modern-fashion instead of historic-hotel
- exaggerated haunted-house horror styling
- game HUD patterns that break immersion
- dense dashboards or admin-panel layouts

## Decision Rule For Future Work
When a design choice is unclear, prefer the option that makes the experience feel more like:

1. a private stay in a beautiful historic hotel
2. a quiet unfolding mystery
3. a short elegant interactive story

Not more like:

1. a productivity app
2. a generic mobile game
3. a horror game
