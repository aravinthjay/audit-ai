"use client";

import { BookOpen, RefreshCw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { KnowledgeSourceCard } from "@/components/knowledge-base/knowledge-source-card";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  useKnowledgeChunks,
  useKnowledgeSearch,
  useKnowledgeSources,
  useReindexKnowledge,
} from "@/hooks/use-knowledge";
import type { KnowledgeChunk, KnowledgeSource } from "@/types/domain";

const emptySources: KnowledgeSource[] = [];
const emptyChunks: KnowledgeChunk[] = [];

export function KnowledgeBaseView() {
  const { data, error, isLoading, refetch } = useKnowledgeSources();
  const chunkQuery = useKnowledgeChunks();
  const reindexMutation = useReindexKnowledge();
  const [sourceQuery, setSourceQuery] = useState("");
  const [ragQuery, setRagQuery] = useState("material consulting vendor approval threshold");
  const ragSearch = useKnowledgeSearch(ragQuery);
  const sources = data ?? emptySources;
  const chunks = chunkQuery.data ?? emptyChunks;
  const results = ragQuery.trim().length > 1 ? ragSearch.data ?? emptyChunks : chunks.slice(0, 6);
  const filtered = useMemo(() => {
    const normalizedQuery = sourceQuery.trim().toLowerCase();

    return sources.filter(
      (source) =>
        !normalizedQuery ||
        [source.title, source.description, source.owner, source.clausePreview, ...source.citationIds].some((value) =>
          value.toLowerCase().includes(normalizedQuery),
        ),
    );
  }, [sourceQuery, sources]);

  if (isLoading) {
    return <LoadingState label="Loading knowledge base" />;
  }

  if (error || !data) {
    return <ErrorState onRetry={() => void refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Knowledge base"
        title="Governed source library"
        description="Maintain audit methodology, client policies, evidence connectors, and registry integrations used by the agent workflow."
        actions={
          <>
            <Button
              variant="secondary"
              onClick={() => reindexMutation.mutate()}
              disabled={reindexMutation.isPending}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {reindexMutation.isPending ? "Indexing" : "Re-index"}
            </Button>
            <Button>Upload policy</Button>
          </>
        }
      />

      <section className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader>
            <CardTitle>RAG index</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <div>
                <span className="block text-xs text-muted-foreground">Sources</span>
                <span className="text-lg font-semibold text-foreground">{sources.length}</span>
              </div>
              <div>
                <span className="block text-xs text-muted-foreground">Chunks</span>
                <span className="text-lg font-semibold text-foreground">{chunks.length}</span>
              </div>
              <div>
                <span className="block text-xs text-muted-foreground">Mode</span>
                <span className="text-sm font-medium text-foreground">Hybrid local</span>
              </div>
            </div>
            <div className="mt-4 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs leading-5 text-muted-foreground">
              Search combines keyword overlap with deterministic vector scores from the backend
              embedding table.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Retrieval probe</CardTitle>
          </CardHeader>
          <CardContent>
            <label htmlFor="rag-search" className="sr-only">
              Search RAG chunks
            </label>
            <div className="flex gap-2">
              <Input
                id="rag-search"
                value={ragQuery}
                onChange={(event) => setRagQuery(event.target.value)}
                placeholder="Try: flight benchmark, related party, SoD override"
              />
              <Button variant="secondary" size="icon" aria-label="Search RAG chunks">
                <Search className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            <div className="mt-4 space-y-3">
              {(ragSearch.isLoading ? emptyChunks : results).map((chunk) => (
                <div key={chunk.id} className="rounded-md border border-border p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-semibold text-foreground">{chunk.title}</h2>
                    <Badge variant="primary">{chunk.id}</Badge>
                    {typeof chunk.score === "number" ? (
                      <Badge variant="info">score {chunk.score.toFixed(2)}</Badge>
                    ) : null}
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {chunk.sourceTitle} {chunk.section ? `/ ${chunk.section}` : ""}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{chunk.content}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {chunk.keywords.slice(0, 6).map((keyword) => (
                      <Badge key={keyword} variant="default">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <div className="max-w-md">
        <label htmlFor="knowledge-search" className="sr-only">
          Search knowledge sources
        </label>
        <Input
          id="knowledge-search"
          placeholder="Search policies, clauses, citations, or owners"
          value={sourceQuery}
          onChange={(event) => setSourceQuery(event.target.value)}
        />
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        {filtered.map((source) => (
          <KnowledgeSourceCard key={source.id} source={source} />
        ))}
      </section>

      {filtered.length === 0 ? (
        <EmptyState
          title="No knowledge sources"
          description="Knowledge sources will appear after policy or connector records are available from the backend."
          icon={BookOpen}
        />
      ) : null}
    </div>
  );
}
