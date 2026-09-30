# Unblock Me

Sliding-block puzzle (6x6 grid) with a drag-and-drop map builder and a play mode. React SPA.

## What it is / how it works
- Vite + React 19, Tailwind v4 (`@tailwindcss/vite`), `motion`; `@` alias → `src/` (vite.config.js).
- Almost everything is in `src/App.jsx` (~1400 lines): grid logic, builder, play mode (drag / arrow keys,
  undo, restart, win detection), glassmorphic styling. Entry: `index.html` → `src/main.jsx`.
- `src/components/ui/glowing-effect.tsx` is used by App; `demo.tsx` is an unused component demo.
- Entirely client-side. Saved maps live in an in-memory array (`savedMapsStore`) — lost on reload, no
  localStorage, no backend. No fetch calls; only external resource is Google Fonts (Space Grotesk).

## Hosting
- Cloudflare Worker `unblock-me-game` (static assets only) — live at https://app.luke-abraham.com
  (also https://unblock-me-game.lukeabraham06.workers.dev).
- Config: `wrangler.jsonc` (`assets.directory: "dist"`, `not_found_handling: "single-page-application"`).
- Deploys via Cloudflare Workers Builds on push to `cloudflare-migration`: build `npm run build`,
  deploy `npx wrangler deploy`. Once merged into `main`, the build trigger will be switched to `main`.
- No server code, no database, no secrets, no bindings.
- Moved off Vercel; there is no vercel.json, but the README still describes Vercel.

## Run locally
- `npm install`, then `npm run dev` (http://localhost:5173).
- `npm run build` → `dist/`; `npm run preview` or `npx wrangler dev` to serve the build. `npm run lint` for ESLint.

## Gotchas
- `dist/` and `.wrangler/` are gitignored build output — never edit or commit them; Cloudflare builds `dist/`.
- Static files that must be served as-is go in `public/` (copied into `dist/` by Vite).
- SPA fallback: any unknown path returns `index.html` with 200, so there are no real 404s.
- `@vercel/analytics` `<Analytics />` is still mounted in App.jsx; off Vercel it has no endpoint and
  collects nothing (its script request just falls back to index.html). Safe to remove.
