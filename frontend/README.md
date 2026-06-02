# Rescue 1122 Evaluation Frontend

React/Vite frontend for the Rescue 1122 Evaluation System. It includes staff login, staff examination flow, results/history views, and admin dashboards.

## Stack

- React 18
- Vite
- React Router
- Axios
- Recharts
- Lucide icons

## Setup

Install dependencies only when needed:

```bash
npm install
```

Create a local `.env` from `.env.example` when required. Never commit real environment values.

## Environment

Common variables:

- `VITE_API_URL`
- `VITE_APP_NAME`

Example:

```bash
VITE_API_URL=https://rescue1122evaluationbackend.onrender.com
VITE_APP_NAME=Rescue 1122 Evaluation System
```

## Run Locally

```bash
npm run dev
```

The local app usually runs at:

```text
http://127.0.0.1:5173/
```

## Build

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Deployment

`vercel.json` is included for Vercel deployment. Set `VITE_API_URL` in the Vercel dashboard so the frontend points to the deployed FastAPI backend:

```text
https://rescue1122evaluationbackend.onrender.com
```

## Security Notes

- `.env`, `node_modules`, and `dist` are ignored.
- Do not commit real API URLs if they include secrets.
- The app uses token-based API calls and redirects to login on expired sessions.
- Security headers are configured in `vercel.json`.
