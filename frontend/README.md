# Campus Customs HQ — Dashboard

React + Vite + TypeScript dashboard for the HW 5 agent team. It calls the FastAPI backend at `http://localhost:8000` (see `../backend/README.md`).

## Run

Start the backend first (from `../backend`, with the HW 5 virtual environment active):

```powershell
uvicorn main:app --reload --port 8000
```

Then, from this `frontend` folder:

```powershell
npm install      # first time only
npm run dev
```

Open **http://127.0.0.1:5455** (or http://localhost:5455).

- Port 5455 is fixed in `vite.config.ts` (`strictPort`), because 5173 and other 5xxx ports are used by other course projects. The backend's CORS settings allow this origin.
- To point at a different backend, copy `.env.example` to `.env` and set `VITE_API_BASE`.
- `npm run build` type-checks and builds a production bundle into `dist/`.

## What is where

| File | Role |
|---|---|
| `src/App.tsx` | State, polling, and the approve / deny / re-run / resolve actions |
| `src/api.ts` | Calls to the backend routes |
| `src/heroes.tsx` | The five original hero characters (SVG) and their expressions |
| `src/heroState.ts` | Turns the live event feed into speech bubbles, moods, and beams |
| `src/expected.ts` | The owner's Expected plans (from `output/desk_tickets.html`) for the comparison tab |
| `src/sound.ts` | Synthesized sound effects (off by default) |
| `src/components/` | Mission board, hero bay, decision desk, balance, cash outlook, token gauge, comms drawer, transactions |

Design notes: `../output/design.md`.
