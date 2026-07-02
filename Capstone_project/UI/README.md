# Professional-Skepticism Engine UI

Enterprise React and Next.js frontend for the Professional-Skepticism Engine, a multi-agent AI audit investigation platform.

The UI covers the full investigation workflow:

- Dashboard and analytics
- Investigation list and case workspace
- Live agent workflow graph
- Evidence explorer
- Challenger, defender, and adjudicator debate viewer
- Verification panel
- Human review queue
- Reports
- Immutable audit logs
- Investigation replay
- Knowledge base
- Settings and governance controls

## Tech Stack

- React 19
- Next.js 15 App Router
- TypeScript
- Tailwind CSS
- shadcn/ui-style component structure
- TanStack Query
- TanStack Table
- React Flow
- Recharts
- React Hook Form
- Zod
- Lucide React
- Vitest
- ESLint

## Prerequisites

Install these first:

- Node.js 20 or newer
- pnpm 9.x

Check your versions:

```powershell
node -v
pnpm -v
```

If pnpm is missing:

```powershell
npm install -g pnpm@9.15.9
```

## Install From Scratch

From the repository root:

```powershell
cd "C:\Users\athit\Skeptic Engine\UI"
pnpm install
```

React is installed as part of the project dependencies. You do not need to install React separately.

## Run Locally

Configure the backend API:

```powershell
copy .env.example .env.local
```

`NEXT_PUBLIC_API_BASE_URL` must point at the FastAPI backend, for example
`http://localhost:8000/api/v1`.

Start the development server:

```powershell
pnpm dev
```

Open:

```text
http://localhost:3000/dashboard
```

If port `3000` is already busy:

```powershell
pnpm dev -- -p 3001
```

Then open:

```text
http://localhost:3001/dashboard
```

## Useful Commands

```powershell
pnpm dev
pnpm build
pnpm start
pnpm lint
pnpm typecheck
pnpm test
pnpm format
```

Command purpose:

- `pnpm dev` starts the local Next.js dev server.
- `pnpm build` creates a production build.
- `pnpm start` runs the production build after `pnpm build`.
- `pnpm lint` runs ESLint.
- `pnpm typecheck` runs TypeScript without emitting files.
- `pnpm test` runs Vitest tests.
- `pnpm format` formats files with Prettier.

## Project Structure

```text
UI/
  app/                  Next.js App Router routes
  components/           Reusable UI, layout, charts, tables, workflow, and domain components
  constants/            Route and navigation constants
  features/             Feature-level page implementations
  hooks/                React Query hooks
  lib/                  Utility and status helpers
  providers/            App-level providers
  services/             Backend API data access layer
  store/                Client UI state
  tests/                Test setup
  types/                Domain, form, and feature types
```

## Main Routes

```text
/dashboard
/intake
/investigations
/investigations/[caseId]
/debate
/evidence
/verification
/review
/reports
/audit-logs
/replay
/knowledge-base
/analytics
/evaluation
/settings
```

Legacy routes:

- `/human-review` redirects to `/review`

## Development Notes

- Use `services/` for data access functions.
- Use `hooks/` for React Query integration.
- Keep page files thin and delegate UI to `features/`.
- Add reusable UI to `components/`.
- Avoid `any`; extend the domain types in `types/`.
- Prefer existing design tokens in `app/globals.css` and `tailwind.config.ts`.

Third-party evidence verification is exposed through:

- `services/evidence-verification.service.ts` for `/claims/{claimId}/verification` and `/claims/{claimId}/verify-evidence`.
- `hooks/use-evidence-verification.ts` for React Query loading, re-run, and cache invalidation.
- `components/evidence/evidence-verification-card.tsx` in the investigation workspace and human review panel.

## Verification Checklist

Before handing off changes, run:

```powershell
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

All four should pass before deploying or opening a pull request.

## Troubleshooting

If dependencies behave oddly, reinstall cleanly:

```powershell
pnpm install
```

If the dev server starts but the browser cannot connect, check whether another process is using the port:

```powershell
netstat -ano | findstr :3000
```

Then run on another port:

```powershell
pnpm dev -- -p 3001
```

If `pnpm` reports a non-interactive module removal prompt, run the install directly in your terminal instead of through a background process:

```powershell
pnpm install
```
