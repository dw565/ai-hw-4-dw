# Campus Customs — frontend

React + Vite + TypeScript storefront with the 8-bit Yale theme and the chat widget.

```bash
npm install
npm run dev     # http://localhost:5173, proxies /api and /images to the backend on :8000
npm run build   # type-check + production build into dist/
```

Set `BACKEND_PORT` if the FastAPI backend isn't on port 8000. See the top-level
`README.md` and `output/harness.md` for the full setup.
