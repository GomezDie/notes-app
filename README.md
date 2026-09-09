# notes-app

A small notes demo built with **Next.js 16 (App Router)**, TypeScript, and Tailwind CSS v4.

Notes are held in an in-memory store on the server — there is no database, so all
notes are lost when the server restarts. The feature exists to exercise route
handlers, server/client component boundaries, and client-side data mutations.

## Features

- `/notes` page — add, edit (inline), and delete notes
- JSON API under `/api/notes`

## Requirements

- Node.js 20+ (developed on 24)
- npm

## Setup

```bash
git clone https://github.com/GomezDie/notes-app.git
cd notes-app
npm install
```

## Run

```bash
npm run dev
```

Open [http://localhost:3000/notes](http://localhost:3000/notes).

## Other scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Start the dev server (hot reload) |
| `npm run build` | Production build |
| `npm start` | Serve the production build (run `npm run build` first) |
| `npm test` | Run the Vitest unit tests |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint |

## API

Base path: `/api/notes`

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/api/notes` | — | `200 { notes: Note[] }` (newest first) |
| `POST` | `/api/notes` | `{ "text": string }` | `201 { note: Note }` · `400` on missing/blank text or invalid JSON |
| `PATCH` | `/api/notes/:id` | `{ "text": string }` | `200 { note: Note }` · `400` invalid body · `404` unknown id |
| `DELETE` | `/api/notes/:id` | — | `204` · `404` unknown id |

```ts
type Note = { id: string; text: string; createdAt: number };
```

## Project layout

```
app/
  api/notes/route.ts        GET (list), POST (create)
  api/notes/[id]/route.ts   PATCH (update), DELETE (remove)
  lib/notes-store.ts        in-memory store + helpers
  lib/notes-store.test.ts   unit tests
  notes/page.tsx            server component (reads store, seeds client)
  notes/notes-client.tsx    client component (form, list, edit/delete)
```
