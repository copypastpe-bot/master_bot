# Master promo landing output v1

Canonical generated output for a private-master promo mini-landing in the Telegram mini app.

This package is the handoff version of the prototype. Treat it as the contract between the constructor and the rendered landing page.

## Files

- `template.html` - human-designed HTML template. Layout, CSS, icons, themes, and responsive behavior live here.
- `data.json` - compact example payload that the constructor should generate.
- `artifact.json` - live artifact declaration used by Open Design validation/preview.
- `provenance.json` - source notes for the design/spec handoff.

Use `template.html` + `data.json` as the implementation source of truth. The generated preview `index.html` is derived and should not be edited by hand.

## Output Contract

The constructor should generate this top-level shape:

```json
{
  "meta": {},
  "constructor": {},
  "landing": {}
}
```

### `constructor`

Required fields:

- `outputType`: must be `master_promo_landing`.
- `schemaVersion`: currently `promo_landing_v1`.
- `themeId`: selected visual theme, for example `fresh_green`.
- `categoryId`: service category, for example `cleaning`, `beauty`, `barber`.
- `iconSetId`: icon system version, currently `service_soft_v1`.

### `landing`

Required content fields:

- `themeClass` - CSS theme class applied to the landing root.
- `photoClass` - optional category/photo class for future local photo mapping.
- `badge` - short uppercase promo line over the hero photo.
- `masterName`
- `specialization`
- `tagline`
- `serviceLabel`
- `serviceName`
- `pricePrefix`
- `price`
- `currency`
- `offerText`
- `offerIconClass`
- `benefitOneText`
- `benefitOneIconClass`
- `benefitTwoText`
- `benefitTwoIconClass`
- `benefitThreeText`
- `benefitThreeIconClass`
- `ctaText`
- `ctaHref`
- `subtext`

Keep these values plain text. Do not put HTML into data fields.

## Current Themes

The template currently supports three theme choices:

- `theme-fresh` - green, clean, service-oriented. This is the default `.landing` variable set; the class is still emitted by data for explicit theme identity.
- `theme-warm` - beige/brown, softer and more premium. Good for beauty, massage, wellness.
- `theme-dark` - dark/gold, higher contrast. Good for barbers, tattoo, men's services.

Current default:

```json
{
  "themeId": "fresh_green",
  "themeClass": "theme-fresh",
  "categoryId": "cleaning"
}
```

Theme selection should map `themeId` to `themeClass` in the constructor or renderer.

## Current Icons

Allowed promo icon classes:

- `icon-discount`
- `icon-gift`
- `icon-star`

Allowed benefit icon classes:

- `icon-clock`
- `icon-sparkle`
- `icon-bell`

The comparison prototype also explored these extra icon classes and they can be restored from the earlier version if needed:

- `icon-shield`
- `icon-brush`
- `icon-calendar`
- `icon-scissors`
- `icon-bottle`

For v1, prefer using the existing icons before adding a new icon. If a category needs new icons, add them to `template.html` as CSS mask data URIs and expose the class name in this README.

## Renderer Notes

- Mobile-first target is Telegram WebApp.
- On small screens, the landing becomes full-screen without the desktop preview frame.
- There is one primary CTA. Do not add competing secondary buttons in generated output.
- Hero photo is currently theme-controlled CSS. Later the constructor can map `photoClass` or a sanitized media field to a real uploaded image.
- `ctaHref` is stored in `data.json`, but the current safe live-artifact template uses a fixed `#subscribe` link in HTML. When integrating into the real app, wire this to the Telegram/bot action layer rather than interpolating arbitrary URLs.

## Integration Steps

1. Generate a `data.json` object matching `promo_landing_v1`.
2. Map service category and selected style to `themeId`, `themeClass`, `photoClass`, and icon classes.
3. Render `template.html` with escaped text interpolation only.
4. In the Telegram mini app, connect the CTA to the bot subscription/booking flow.
5. Add local or uploaded master photos through the app media pipeline, not as raw untrusted URLs in generated data.

## Design Boundaries

Do not change the layout for each generated page. The constructor should vary:

- text content;
- price and currency;
- category/theme;
- hero photo;
- offer text;
- three benefit labels and icons;
- CTA text/action.

The base composition, spacing, typography, card structure, and icon style are the v1 design system.
