# Multi-stage production build for the Next.js UI.

FROM node:22-alpine AS deps

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./
RUN pnpm install --frozen-lockfile

FROM deps AS builder

ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_API_TOKEN
ARG NEXT_PUBLIC_API_USERNAME
ARG NEXT_PUBLIC_API_PASSWORD
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_API_TOKEN=${NEXT_PUBLIC_API_TOKEN}
ENV NEXT_PUBLIC_API_USERNAME=${NEXT_PUBLIC_API_USERNAME}
ENV NEXT_PUBLIC_API_PASSWORD=${NEXT_PUBLIC_API_PASSWORD}
ENV NEXT_TELEMETRY_DISABLED=1

COPY . .
RUN pnpm build

FROM node:22-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/next.config.ts ./next.config.ts

USER nextjs
EXPOSE 3000

CMD ["node_modules/.bin/next", "start"]
