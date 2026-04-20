# Master Mini App Style Unification Design

Date: 2026-04-20
Project: Master_bot
Scope: Master-facing Mini App visual unification and targeted UX update for order creation

## Goal

Bring the master Mini App screens into one coherent visual system so they feel like one product instead of a mix of old and new patterns. The immediate target is to remove style-breaking screens, unify the top area and surface treatment, and update the order creation screen so the client list is visible immediately.

## Problem Statement

The current master Mini App already has a partially unified dark visual language, but several screens still break the style:

- the top area can read as a separate dark strip instead of part of one page scene;
- transparency and layered surfaces are inconsistent between screens;
- some screens feel like old technical forms placed onto the newer shell;
- empty states can feel visually unfinished;
- the order creation flow hides the client list until search input, which slows down common usage.

## Design Direction

The redesign uses one shared master visual layer rather than per-screen cosmetic tweaks.

Core principles:

- one continuous background scene across all master screens;
- one shared surface material for cards, filters, tabs, sheets, and navigation;
- no random transparency bands or visually detached top stripes;
- stronger compositional unity between page background, header zone, content cards, and bottom navigation;
- dark, premium, calm interface with subtle cold gradients and depth, not a literal iOS glass clone.

## Visual System

### Background

Use a single master background scene for all master-facing screens:

- dark base;
- soft cold blue highlights;
- subtle uneven light distribution so the page feels alive;
- no hard separation between top and content area.

The background should stay supportive, not decorative. It must improve cohesion without reducing readability.

### Surface Material

All master UI blocks should use one shared material language:

- matching radii;
- matching border treatment;
- consistent shadow depth;
- consistent internal spacing;
- the same contrast logic for cards, segmented controls, and sheets.

This applies to:

- page cards;
- tab and filter groups;
- empty state containers;
- bottom sheets;
- bottom navigation;
- call-to-action blocks.

### Header Zone

The top area should visually belong to the page rather than act as a detached overlay. This means:

- removing the impression of a separate horizontal strip;
- reducing accidental transparency mismatches;
- aligning header chips and title containers with the same surface rules as the rest of the app.

## Screen Scope

### 1. Shared Master Shell

Files expected to be affected first:

- `miniapp/src/theme.css`
- shared master shell components such as `MasterNav`, `AppHeader`, and reusable card-like elements where needed.

Expected result:

- one shared background scene;
- one shared surface material;
- aligned header, page, and nav styling.

### 2. Order Create

File:

- `miniapp/src/master/pages/OrderCreate.jsx`

Visual changes:

- move the screen from a technical step form feel into the shared master visual system;
- keep the page readable with keyboard open;
- align controls and action hierarchy with the new shell.

UX changes:

- show the client list immediately on screen open;
- sort the visible clients alphabetically;
- keep search at the top as a filter, not the only entry point;
- place an explicit `Add client` action at the top of the client step.

Behavioral note:

This is a UX update, not a new data model. Existing client creation flow should be reused where possible.

### 3. Order Detail

File:

- `miniapp/src/master/pages/OrderDetail.jsx`

Expected result:

- detail sections should read as part of the same design language as dashboard and calendar;
- action sheets for move/complete/cancel should visually continue the same material system;
- primary, secondary, and destructive actions should be visually distinct at a glance.

### 4. Requests

File:

- `miniapp/src/master/pages/Requests.jsx`

Expected result:

- filter controls should match the same shared visual language;
- empty states should look deliberately designed, not like an empty placeholder box;
- request cards should inherit the same surface logic as the rest of the app.

### 5. Calendar

File:

- `miniapp/src/master/pages/Calendar.jsx`

Expected result:

- the calendar card and selected day block should feel like one composition;
- the `+ Add booking` action should be visible and native to the same style;
- empty day states should preserve visual structure and not create a composition gap.

## Out Of Scope

- client-facing Mini App screens;
- backend or API behavior changes unrelated to the order creation list loading;
- automation or auto-test coverage;
- full information architecture changes beyond the approved screens;
- redesign of every deep master screen in one pass outside the agreed set.

## Implementation Order

1. Shared visual layer in `theme.css` and shared master shell components.
2. `OrderCreate` visual update plus immediate visible client list and top `Add client` action.
3. `OrderDetail` alignment with new shell and sheet styling.
4. `Requests` alignment, including empty states and filter treatment.
5. `Calendar` alignment, including CTA and empty day composition.
6. Build verification and manual QA by the user.

## Acceptance Criteria

- the master screens read as one product with one background scene and one surface system;
- the top area no longer feels like a disconnected dark strip;
- `OrderCreate` shows clients immediately, sorted alphabetically;
- `OrderCreate` includes a visible top-level `Add client` action;
- `OrderDetail`, `Requests`, and `Calendar` no longer visually break from the shared style;
- the Mini App builds successfully;
- final QA is performed manually by the user.

## Risks And Constraints

- keyboard behavior in Telegram WebView must remain usable after the `OrderCreate` restyle;
- stronger background treatment must not reduce text contrast;
- bottom sheet restyling must preserve action clarity, especially destructive actions;
- unifying the shell may expose additional one-off inline styles in deeper components, but this pass remains focused on the agreed screens.

## Verification Strategy

- run `npm run build` in `miniapp/`;
- manually inspect the updated screens in the Mini App;
- manually test the `OrderCreate` flow with:
  - visible client list on load;
  - alphabetical ordering;
  - search filtering;
  - top `Add client` action;
  - keyboard open behavior.
