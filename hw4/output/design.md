# Campus Customs — 8-bit Yale Design

**Theme:** a retro, 8-bit game look in Yale blue and white. Pixel headings,
chunky borders, and buttons that work like an old game menu. The parts
shoppers need to read and compare stay clean and modern: product photos,
descriptions, prices and forms.

## Design system

| Element | Choice |
|---|---|
| **Colors** | Yale Blue `#00356b`, deep navy `#00254a`, light Yale blue `#286dc0`, sky accent `#63aaff`, white. Status colors: green = in stock, amber = low, red = sold out |
| **Fonts** | **Press Start 2P** (pixel) for headings, nav, buttons and labels. **VT323** (taller pixel font) for accents: prices, counts, badges, filter chips. **Inter** for all body text, descriptions, chat messages and form inputs. All three are self-hosted with `@fontsource`, so no external font CDN is needed |
| **Borders & shadows** | 3px solid navy borders, square corners, hard offset "pixel" shadows (`4px 4px 0`), no blur |
| **Background** | Light blue-gray with a faint 16px pixel grid, like graph paper in an old game manual |
| **Motion** | All animations use `steps()` timing so they move in frames like a sprite, not smoothly. They're short (90–320ms) and fully turned off for shoppers with `prefers-reduced-motion` |

## What changed, page by page

**Navigation**
- A pixel-art "Y" logo (8×8 SVG) next to "Campus Customs" in the pixel font.
- Nav links are uppercase pixel text. Hovering or being on a page shows a
  blinking **▶** cursor, like choosing an option in a game menu.
- The announcement bar uses VT323 with blinking stars: "★ Official Yale
  gear · Visit us at 57 Broadway, New Haven ★".

**Home**
- Hero headline in the pixel font with a hard navy text shadow.
- An animated pixel campus scene behind it:
  - a **Harkness Tower** silhouette
  - twinkling pixel stars
  - a striped ground line
  - a pixel **Handsome Dan** in a Yale-blue sweater who walks back and forth
    with a 2-frame leg animation and turns around at each end
- Buttons read "▶ Start shopping" and "Our story".
- "Shop by style" tiles are chunky cards with a ▶ that nudges on hover. Each
  tile opens the Products page with that category already selected.

**Product cards** (Products page, Home "Fresh picks", chat results)
- Square-cornered white cards with 3px navy borders and pixel shadows.
- On hover the card hops up and its shadow turns light blue in two frames,
  and a pixel **"VIEW ▶"** tag appears.
- **Photos keep normal smooth image rendering**, so they stay sharp. Only the
  interface around them is pixelated.
- Names are in bold Inter, prices in large VT323, and descriptions in Inter
  (two lines max) for easy scanning.
- Filter chips look like pixel buttons. Chat-search results pop in one by
  one, a few at a time.

**Product page**
- Large photo in a chunky frame with a deep pixel shadow.
- Pixel-font name, a large VT323 price, and the full description in Inter.
- The size table became a **size tile grid**, like an inventory screen in a
  game:
  - each size is a tile with a green "In stock", amber "Only N left" or red
    "Sold out" label
  - sold-out tiles are grayed with diagonal stripes, so availability is clear
    at a glance
- The "💬 Ask about this item" panel is styled as a game dialog box.

**Log in / Create account**
- Forms look like a game dialog box: chunky border, deep shadow,
  pixel-font labels, square inputs with a pixel focus shadow.
- Friendly retro subtitles: "Welcome back, Player 1. Your saved chat is
  waiting." / "New player? Make an account to save your chat with our
  assistant."

**Chat widget**
- The **💬 CHAT** button is a pixel button that gently bobs (2-frame idle
  animation, like an item waiting to be picked up). It presses down when
  clicked.
- **Opening animation:** the panel "unfolds" from the bottom-right corner in
  6 stepped frames (a `clip-path` reveal), like a game dialog box opening.
- Pixel-font header, chunky message bubbles with hard shadows, new messages
  pop in, and **three blinking pixel blocks** replace "Thinking…".
- Suggested questions are ▶ menu options, and the "✓ Prices & stock checked"
  note is in green VT323.

**Footer & 404**
- Footer has a thick light-blue top border and pixel-font links.
- The 404 page is a **"GAME OVER"** screen with Handsome Dan and a
  "▶ Continue" button back to Home.

## Readability safeguards

- Pixel fonts are only used for short text: headings, labels, buttons,
  prices. Anything you read as sentences (descriptions, chat, About Us,
  forms) is in Inter at 15–17px.
- Strong contrast throughout (navy on white, white on Yale blue).
- Focus outlines are visible (dashed light blue) for keyboard users.
- Decorative art (the hero scene) is hidden from screen readers. The logo
  has a text label.
- The layout is unchanged on small screens. The hero headline shrinks and
  the size grid drops to 2 columns.

## Why this could help shoppers stay and buy

We can't promise more sales just because we added pixels, but each choice
supports a step from "landed on the site" to "found something to buy":

1. **Memorable.** Most college stores look the same. A pixel Handsome Dan
   walking past Harkness Tower is something a visitor remembers, mentions to
   friends, and comes back to. That's brand recall for Campus Customs.
2. **School spirit.** Using only Yale blue and white, plus campus icons
   (Harkness, Handsome Dan, the Y), ties every page to Yale. The people
   buying here (students, alumni, families) are buying school pride, and the
   site's look backs that up.
3. **Little touches encourage exploring.** Cards that hop on hover, the ▶
   cursor, the chat button that bobs, and the dialog-box opening make
   clicking around fun. More exploring means more products seen, and more
   chances to find the right one.
4. **Clear cards and obvious buttons turn interest into finding something.**
   The fun stays around the products, not in front of them. Photos are
   sharp, prices are large, descriptions are readable, buttons look like
   buttons, and the size tiles answer "is my size available?" at a glance.
   That clarity is what turns a curious visitor into someone adding an item
   to their list.
5. **Quick and gentle.** Animations are under a third of a second, stepped,
   and off for anyone who prefers reduced motion, so the personality never
   slows down browsing.

## Files

- `frontend/src/index.css`: the full theme (colors, fonts, borders,
  components, stepped animations, reduced-motion rules)
- `frontend/src/components/PixelArt.tsx`: tiny pixel-art renderer plus the
  Handsome Dan (2 walk frames), Harkness Tower and "Y" logo sprites
- `frontend/src/components/HeroScene.tsx`: animated Home hero scene
- `frontend/src/main.tsx`: self-hosted font imports (`@fontsource/press-start-2p`, `vt323`, `inter`)
- Small markup changes for the theme: `NavBar.tsx` (logo, blinking stars),
  `Home.tsx` (scene, ▶ buttons), `ProductCard.tsx` ("VIEW ▶" tag),
  `ProductPage.tsx` (size tile grid), `Login.tsx` / `CreateAccount.tsx`
  (subtitles), `ChatWidget.tsx` (pixel typing dots), `NotFound.tsx`
  (Game Over)
