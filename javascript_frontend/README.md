# SGJobs React frontend (Overview page)

React + Vite client for the **existing** SGJobs FastAPI backend. This step
migrates the Overview page only: the ten sidebar filters, the five primary
KPI cards, the four bridge KPI cards, the DAX-equivalent measures and the
four Overview charts.

Everything else — Salary Analysis, Opportunity Analysis, Demand &
Seniority, Skills & Categories, Data Quality, Repost Analysis, Detail
Drillthrough — is still served by the Streamlit app.

## What this app does and does not do

It **does**:

- keep the sidebar selections in React state,
- call three endpoints (`/api/filters`, `/api/overview`,
  `/api/overview/charts`),
- render the returned JSON.

It **does not** read Parquet, use pandas, compute opportunity scores,
aggregate job rows or repeat any business rule. Multi-select filters are
forwarded verbatim as repeated query parameters and FastAPI does the
filtering:

```
?skill_bridge=Python&skill_bridge=SQL
```

## Prerequisites

- Node.js 18 or newer
- The backend running:

```powershell
# from the repository root (one level up)
uvicorn backend.main:app --reload --port 8000
```

## Install and run

```powershell
cd javascript_frontend
npm install
npm run dev
```

Then open <http://localhost:5173>.

Other scripts:

```powershell
npm run build     # production bundle in dist/
npm run preview   # serve the built bundle locally
```

## Configuration and the CORS question

`VITE_API_URL` decides how the browser reaches the API.

| `VITE_API_URL`      | Browser calls                | CORS on the backend |
| ------------------- | ---------------------------- | ------------------- |
| empty / not set     | `/api/...` on the Vite server | **not needed**      |
| `http://localhost:8000` | the API cross-origin     | **needed**          |

The current backend has **no CORS middleware** — it was written for a
Streamlit client that calls it server-to-server. So the dev proxy is the
path that works with no backend change:

```powershell
# .env  (copy from .env.example, then edit)
VITE_API_URL=
```

If you prefer to call the API directly (`VITE_API_URL=http://localhost:8000`),
the backend needs CORS enabled. Adding this to `backend/main.py` is all it
takes:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # vite preview
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

For production the JS build is a static bundle, so either serve it behind
the same origin as the API or enable CORS for the deployed frontend origin.

## Project layout

```
javascript_frontend/
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── index.css
    ├── api/
    │   ├── client.js        fetch wrapper, ApiError, base URL
    │   ├── query.js         repeated query params, selection pruning
    │   └── overviewApi.js   the three allowed endpoints
    ├── hooks/
    │   └── useDashboardData.js
    ├── utils/
    │   └── format.js        number / currency / percent formatting
    └── components/
        ├── FilterSidebar.jsx
        ├── MultiSelect.jsx
        ├── KpiCards.jsx
        ├── DaxPanel.jsx
        ├── States.jsx
        └── charts/
            ├── ChartKit.jsx
            └── OverviewCharts.jsx
```