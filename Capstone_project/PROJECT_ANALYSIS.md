# Skeptic Engine — Project Analysis

**Date**: June 26, 2026  
**Project**: Professional-Skepticism Engine (v0.1.0)  
**Repository**: C:\Users\athit\Skeptic Engine

---

## Executive Summary

Skeptic Engine is an enterprise audit investigation platform powered by multi-agent AI. It automates fraud detection and risk assessment by orchestrating specialized AI agents through an adversarial debate framework, with mandatory human-in-the-loop review and immutable audit logging.

**Key characteristics**:
- **Multi-agent crew**: Supervisor, Evidence, Challenger, Defender, Adjudicator, Verifier
- **Adversarial debate**: Challenger vs. Defender rounds to uncover risk from opposing angles
- **Human-in-the-loop**: Manual review gates on high-risk cases before decisions
- **Audit compliance**: Immutable, hash-chained transaction log of all decisions and sources
- **Enterprise-ready**: Role-based governance, segregation of duties, configurable thresholds

---

## Project Structure

```
Skeptic Engine/
├── UI/                          # Next.js 15 React frontend
│   ├── app/                     # Next.js App Router
│   ├── components/              # Reusable UI, domain, and chart components
│   ├── features/                # Page-level feature implementations
│   ├── services/                # Data access layer (mock data for now)
│   ├── hooks/                   # React Query hooks for data fetching
│   ├── types/                   # Full TypeScript domain model
│   ├── lib/                     # Utilities and helpers
│   ├── constants/               # Route constants, navigation
│   ├── data/                    # Mock data fixtures
│   └── providers/               # App-level providers
├── Docs/                        # Documentation artifacts
│   ├── Architecture/            # System architecture diagrams
│   ├── High Level Design/       # HLD documents
│   ├── Low Level Design/        # LLD documents
│   ├── Sample_output/           # Example reports and PDFs
│   └── Skeptic_Engine_PRD.pdf   # Product requirements document
├── Prototype/                   # Early HTML prototype
└── .git/                        # Git repository (main + Develop branches)
```

---

## Technology Stack

### Frontend (UI/)

**Framework & Libraries**:
- **React 19** — Latest React with hooks and RSC support
- **Next.js 15** — App Router, server components, file-based routing
- **TypeScript** — Full type safety (strict: true, noImplicitAny enforced)
- **Tailwind CSS** — Utility-first styling with animations
- **Radix UI primitives** — Accessible dialog, tabs, slot components

**Data & State Management**:
- **TanStack Query (React Query)** — Server state, caching, background sync
- **TanStack Table** — Advanced table component with sorting, filtering, pagination
- **React Hook Form** — Form state and validation
- **Zod** — TypeScript-first schema validation

**Visualization & UX**:
- **Recharts** — Composable React charts (line, bar, pie)
- **React Flow** — Interactive workflow/DAG visualization (agent debug/replay)
- **Lucide React** — Consistent icon library

**Developer Tools**:
- **Vitest** — Unit and integration tests
- **ESLint** — Code linting with Next.js config
- **Prettier** — Code formatting
- **Husky + lint-staged** — Pre-commit hooks for code quality
- **pnpm 9.15.9** — Package manager

**Build**:
- **Node 20+** required
- **ES2022 target** in TypeScript

---

## Domain Model

### Core Types

**Investigation** — A single audit case
```typescript
type Investigation = {
  id: string;                    // Unique case ID
  transactionId: string;         // GL transaction
  vendor: string;                // Vendor name
  category: string;              // GL account category
  amount: number;                // USD amount
  confidence: number;            // AI confidence (0–1)
  risk: RiskLevel;               // critical | high | medium | low | cleared
  flags: string[];               // Triggered pre-filter rules
  status: InvestigationStatus;   // intake → collecting_evidence → ... → closed
  owner: string;                 // Assigned reviewer
  reviewer?: string;             // Final human approver
  postedAt: string;              // Transaction date
  dueAt: string;                 // Review deadline
  materiality: number;           // Materiality threshold ($)
  description: string;           // Case summary
};
```

**Pipeline Stages**:
- `intake` — Initial flagging from CSV rules
- `collecting_evidence` — Evidence agents fetch & aggregate context
- `agent_debate` — Challenger ↔ Defender debate rounds
- `verification` — Verifier QA gates claims
- `human_review` — Manual reviewer approval required
- `report_ready` — Artifact generated, decision finalized
- `closed` — Case archived

**Agent Roles** (WorkState):
- `Supervisor` — Orchestrates workflow, routes to specialists
- `Evidence agent` — RAG over policies + historical data → citations
- `Challenger` — Argues worst-case risk interpretation
- `Defender` — Argues legitimate transaction rationale
- `Adjudicator` — Weighs debate → risk verdict
- `Verifier` — QA-gates: every claim grounded & supported?
- `Human review` — Manual approval stage
- `Confidence gate` — Routes by confidence score

**Risk Levels**: `critical` | `high` | `medium` | `low` | `cleared`

**Work States**: `idle` | `running` | `queued` | `done` | `failed` | `retry` | `blocked` | `escalated` | `review` | `challenger` | `debate`

---

## Architecture Overview

### Investigation Workflow (5 Phases)

```
PHASE 0: CASE INTAKE
  CSV upload → normalize transactions → rule-based pre-filter
  ↓
PHASE 1: EVIDENCE COLLECTION
  Supervisor decomposes case → Evidence agent (RAG + live APIs) → citations + summaries
  ↓
PHASE 2: DEBATE + VERIFICATION
  Challenger (red flags) ↔ Defender (legitimate rationale) ≤2 rounds
  ↓ (pass verification)
  Adjudicator weighs both sides → risk verdict + confidence
  ↓
PHASE 3: DECISION + HUMAN-IN-LOOP
  Confidence gate routes:
    ≥0.90 & verified & Low risk → auto-clear
    0.70–0.90 → manual review queue
    <0.70 → escalated review
  ↓
PHASE 4: REPORT + AUDIT
  Report generated (MD + HTML + PDF)
  Immutable audit log (hash-chained, append-only)
  Case closed
```

### Shared State

All phases operate on **InvestigationState** (TypedDict, SQLite-checkpointed):
- case metadata
- evidence{} collected
- debate_transcript[]
- challenger_view / defender_view
- adjudication{}
- verification{}
- routing decision
- review_history[]
- audit_history[] (immutable)
- report artifact

### External Integrations

- **Claude API** (Anthropic)
  - Sonnet for reasoning (debate, evidence synthesis)
  - Haiku for lightweight report generation
- **Policy KB (RAG)** — Vector embeddings of approval matrices, SOPs, related-party rules
- **FX API** (Frankfurter) — Live foreign exchange rates with cache fallback
- **Registry API** — Vendor master data lookups
- **GL data feed** — CSV ingestion (sample_gl_1000.csv)

---

## UI Pages & Features

### Main Routes

| Route | Purpose |
|-------|---------|
| `/dashboard` | Executive overview (metrics, risk distribution, agent health, case trends) |
| `/intake` | CSV upload & rule pre-filter configuration |
| `/investigations` | List all cases + filtering |
| `/investigations/[caseId]` | Case workspace (full investigation state) |
| `/debate` | Viewer for challenger ↔ defender debate transcript |
| `/evidence` | Evidence explorer (sources, citations, RAG results) |
| `/verification` | Verification panel (claim grounding QA) |
| `/review` | Human review queue (approve/reject/escalate) |
| `/reports` | Generated reports (MD, HTML, PDF) |
| `/audit-logs` | Immutable transaction history |
| `/replay` | Investigation replay (step-by-step debug playback) |
| `/analytics` | Metrics (confidence trend, verifier accuracy, hallucination rate) |
| `/evaluation` | A/B evaluation (multi-agent crew vs. single-prompt baseline) |
| `/knowledge-base` | Manage policy sources, embedding status, freshness |
| `/settings` | Governance controls (thresholds, models, SoD, audit retention) |

### Key Components

**Dashboard**:
- Summary metrics (cases, confidence, risk distribution)
- Risk distribution pie/bar chart
- Agent health panel (latency, load, state)
- Case trend chart over time
- API health & cost tracker

**Case Workspace**:
- Investigation details card
- Pipeline status (visual steps with timestamps)
- Evidence explorer (sources, citations)
- Debate viewer (interactive message stream)
- Verification checklist
- Review actions (approve, reject, request evidence, escalate)
- Audit trail (all events, immutable)

**Human Review Queue**:
- Sortable table (risk, confidence, due date)
- Bulk actions
- Case detail modal
- Signature capture

**Analytics**:
- Confidence trend (weekly)
- Verifier accuracy rate
- Hallucination detection (count vs. total)
- Agent accuracy breakdown
- KPI tracking vs. targets

**Evaluation**:
- A/B comparison (crew vs. baseline)
- KPI cards with pass/fail
- Hallucination results
- Comparison table (metric, single-prompt, crew, delta)

---

## Development Workflow

### Setup

```bash
cd "C:\Users\athit\Skeptic Engine\UI"
pnpm install
pnpm dev
```

Then open: `http://localhost:3000/dashboard`

### Key Commands

```bash
pnpm dev          # Start dev server (hot reload)
pnpm build        # Production build
pnpm start        # Run production build
pnpm lint         # ESLint
pnpm typecheck    # TypeScript check (no emit)
pnpm test         # Vitest unit tests
pnpm format       # Prettier format
```

### Code Structure Patterns

**Services** (`services/*.ts`):
- Pure data access functions
- Return typed data (Investigation[], etc.)
- Ready to be swapped for real API calls (currently mock data)

**Hooks** (`hooks/use-*.ts`):
- Wrap React Query useQuery
- One hook per domain (useCases, useEvidence, etc.)
- Used in feature/page components

**Features** (`features/*/...view.tsx`):
- Feature-level implementations
- Use hooks to fetch data
- Delegate to components
- Handle loading/error states

**Components** (`components/`):
- Reusable UI components
- Domain-specific components (EvidenceCard, DebateMessage, etc.)
- Layout components (AppShell, PageHeader, etc.)
- Chart/table components (CaseTrendChart, InvestigationsTable, etc.)

**Types** (`types/*.ts`):
- Full domain model (domain.ts)
- Feature-specific types
- No `any` — extend domain types

### Pre-commit Checks

Husky enforces:
- ESLint --fix
- Prettier --write
- TypeScript typecheck (implicit via ESLint)

Must pass before PR:
```bash
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

---

## Current State & Maturity

### What's Implemented

✅ **Complete UI** — All pages and components built  
✅ **Domain model** — Fully typed TypeScript types  
✅ **Data access layer** — Service functions with React Query integration  
✅ **Mock data** — Representative fixtures for all domains  
✅ **Layouts & components** — AppShell, tables, charts, forms  
✅ **Routing** — Full Next.js App Router with dynamic routes  
✅ **Form validation** — React Hook Form + Zod  
✅ **Visualization** — Workflow DAG (React Flow), charts (Recharts)  
✅ **Testing setup** — Vitest configuration, sample tests  
✅ **Build & lint** — ESLint, Prettier, Husky pre-commit

### What's Missing/In Progress

🔄 **Backend APIs** — Services currently use mock data; need real API integration  
🔄 **Claude API integration** — Agent orchestration not yet wired in UI  
🔄 **Database layer** — SQLite/Postgres for InvestigationState checkpoint  
🔄 **Auth/RBAC** — Role-based access control not implemented  
🔄 **WebSockets** — Real-time agent status updates not yet connected  
🔄 **PDF export** — Report generation (reports page partially mocked)  
🔄 **Deployment** — No production deployment configured  
🔄 **Analytics tracking** — No event tracking/metrics collection  
🔄 **E2E tests** — No Playwright/Cypress tests yet

---

## Key Decisions & Trade-offs

### Tech Stack

**Why React + Next.js?**
- Server components for efficiency
- File-based routing clarity
- Built-in API route support for future backend
- Strong TypeScript support

**Why TanStack Query?**
- Decouples UI from API layer
- Automatic caching, background sync
- Easy to integrate with real backends
- Refetch/polling for real-time updates

**Why Tailwind + shadcn patterns?**
- Rapid iteration (utility-first)
- Design consistency (no custom CSS chaos)
- Accessible components out-of-box
- Easy dark mode support

### Architecture

**Feature-based organization** (not type-based):
- `features/dashboard/` — all dashboard logic together
- `features/debate/` — all debate logic together
- Reduces coupling, easier to move/delete features

**Service layer abstraction**:
- Decouples business logic from React
- Easy to mock for tests
- Easy to swap backend (REST → GraphQL → tRPC)

**Mock data in `data/`, not components**:
- Single source of truth for test data
- Easier to update fixtures
- Components stay clean and focused

---

## Dependencies & Versions

| Package | Version | Purpose |
|---------|---------|---------|
| react | 19.1.0 | UI library |
| next | 15.3.4 | Framework |
| typescript | 5.8.3 | Type safety |
| tailwindcss | 3.4.17 | Styling |
| @tanstack/react-query | 5.80.7 | Server state |
| @tanstack/react-table | 8.21.3 | Data tables |
| react-hook-form | 7.58.1 | Forms |
| zod | 3.25.67 | Validation |
| recharts | 2.15.3 | Charts |
| reactflow | 11.11.4 | Workflow DAG |
| lucide-react | 0.468.0 | Icons |
| vitest | 3.2.4 | Testing |

All dependencies are current (as of June 2026).

---

## Deployment & Scaling Considerations

### Frontend Hosting
- **Candidate**: Vercel (Next.js native)
- **Alternative**: AWS S3 + CloudFront, Google Cloud Run

### Backend Services (Future)
- **Agent orchestration** (Python FastAPI or Node.js)
- **Database** (PostgreSQL for production; SQLite for local dev)
- **Vector DB** (Pinecone, Weaviate, or pgvector for RAG)
- **Message queue** (Redis/SQS for async agent tasks)
- **Logging** (Datadog, Cloudwatch, ELK)

### Performance
- **Code-split components** (dynamic imports for charts)
- **Image optimization** (next/image)
- **CDN for static assets**
- **Database connection pooling** (PgBouncer)
- **API pagination** (TanStack Table pagination)

---

## Next Steps & Roadmap

### Immediate (P0)
1. **Integrate Claude API** — Wire agent orchestration into investigation flow
2. **Build backend APIs** — REST or tRPC endpoints for case management
3. **Connect to database** — SQLite (dev) → PostgreSQL (prod)
4. **Implement auth** — OIDC or Okta SSO; role-based access control

### Short-term (P1)
5. Implement PDF report generation
6. Add WebSocket updates for real-time agent status
7. Build admin console for configuration
8. Wire up knowledge base sync (RAG embeddings)

### Medium-term (P2)
9. E2E test suite (Playwright)
10. Analytics & observability (Datadog, custom events)
11. Production deployment pipeline
12. Performance optimization & monitoring

---

## Git Branches

- `main` — Production ready
- `Develop` — Active development branch
- Feature branches off Develop

---

## Useful Entry Points

**To understand the system**:
1. Read `types/domain.ts` — core data model
2. Read `features/dashboard/dashboard-view.tsx` — main page pattern
3. Look at `services/cases.service.ts` — data access pattern
4. Check `hooks/use-cases.ts` — React Query integration

**To add a new feature**:
1. Add types in `types/your-feature.types.ts`
2. Create service functions in `services/your-feature.service.ts`
3. Create hook in `hooks/use-your-feature.ts`
4. Create feature view in `features/your-feature/your-feature-view.tsx`
5. Create page in `app/(app)/your-feature/page.tsx`
6. Add components as needed in `components/`

**To integrate APIs**:
1. Replace mock data in `services/` with fetch() or axios
2. Add error handling, retries, timeouts
3. Update React Query configuration for polling/refetch
4. Add loading/error states in features

---

## Summary

Skeptic Engine is a well-structured, modern React/TypeScript application with a comprehensive UI for enterprise audit investigations. The architecture cleanly separates concerns (services, hooks, features, components) and is well-positioned for backend integration. All pages are built, types are solid, and the development workflow is professional (linting, formatting, testing infrastructure). The next phase is connecting this UI to a real backend and Claude API orchestration.

