# Autonomus-Agents-Hackathon

### Patch answer service (data lake)

Node.js data lake service with **Postgres** storage.

- **Ingests release records** into Postgres, keyed by `versionSearchTags`.
- **Fact APIs** for backend: `GET /facts/latest`, `GET /facts/on-date`.
- **Post** `/answer` for natural-language questions.

### Install and run

```bash
cd Documents/HackathonFeb27
npm install
```

Set `DATABASE_URL` (required for Postgres). For local dev, use a local Postgres or Render external URL:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname?sslmode=require"
npm run dev
```

The service listens on `http://localhost:3000`.

### API

- **GET** `/facts/latest?vendor=<from_user>`
  - Vendor from user input (e.g. `android`, `linux`).
  - Returns latest fact for that vendor.

- **GET** `/facts/on-date?vendor=<from_user>&date=<YYYY-MM-DD>`
  - Vendor and date from user input (e.g. `vendor=linux&date=2026-02-27`).
  - Returns fact for that vendor on that exact date.

- **POST** `/ingest`
  - Body: `{ "records": [ /* ReleaseTrain records */ ] }`

- **POST** `/answer`
  - Body: `{ "question": "What is the patch for Linux on 14-02-2026?" }`

All fact/answer responses:

```json
{
  "mainData": "1.1.1",
  "additionalInformation": {
    "versionUrl": "...",
    "versionReleaseNotes": "..."
  },
  "raw": { /* full record */ }
}
```
