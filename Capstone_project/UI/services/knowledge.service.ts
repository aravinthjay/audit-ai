import { apiRequest } from "@/services/api";
import type { KnowledgeChunk, KnowledgeSource } from "@/types/domain";

type ApiKnowledgeSource = {
  id: string;
  title: string;
  description: string;
  owner: string;
  count: string;
  freshness: string;
  status: KnowledgeSource["status"];
  clause_preview: string;
  version_history: string[];
  citation_ids: string[];
  embedding_status: KnowledgeSource["embeddingStatus"];
};

type ApiKnowledgeChunk = {
  id: string;
  source_id: string;
  source_title?: string;
  section?: string;
  title: string;
  content: string;
  keywords?: string[];
  score?: number;
  lexical_score?: number;
  vector_score?: number;
};

function mapChunk(row: ApiKnowledgeChunk): KnowledgeChunk {
  return {
    id: row.id,
    sourceId: row.source_id,
    sourceTitle: row.source_title ?? row.source_id,
    section: row.section ?? "",
    title: row.title,
    content: row.content,
    keywords: row.keywords ?? [],
    score: row.score,
    lexicalScore: row.lexical_score,
    vectorScore: row.vector_score,
  };
}

export async function getKnowledgeSources(): Promise<KnowledgeSource[]> {
  const rows = await apiRequest<ApiKnowledgeSource[]>("/knowledge/sources");

  return rows.map((row) => ({
    id: row.id,
    title: row.title,
    description: row.description,
    owner: row.owner,
    count: row.count,
    freshness: row.freshness,
    status: row.status,
    clausePreview: row.clause_preview,
    versionHistory: row.version_history,
    citationIds: row.citation_ids,
    embeddingStatus: row.embedding_status,
  }));
}

export async function getKnowledgeChunks(): Promise<KnowledgeChunk[]> {
  const rows = await apiRequest<ApiKnowledgeChunk[]>("/knowledge/chunks");
  return rows.map(mapChunk);
}

export async function searchKnowledge(query: string): Promise<KnowledgeChunk[]> {
  const params = new URLSearchParams({ q: query, limit: "8" });
  const rows = await apiRequest<ApiKnowledgeChunk[]>(`/knowledge/search?${params.toString()}`);
  return rows.map(mapChunk);
}

export async function reindexKnowledge(): Promise<{ status: string; synced_chunks: number }> {
  return apiRequest<{ status: string; synced_chunks: number }>("/knowledge/reindex", {
    method: "POST",
  });
}
