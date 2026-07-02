"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getKnowledgeChunks,
  getKnowledgeSources,
  reindexKnowledge,
  searchKnowledge,
} from "@/services/knowledge.service";

export function useKnowledgeSources() {
  return useQuery({
    queryKey: ["knowledge-sources"],
    queryFn: getKnowledgeSources,
  });
}

export function useKnowledgeChunks() {
  return useQuery({
    queryKey: ["knowledge-chunks"],
    queryFn: getKnowledgeChunks,
  });
}

export function useKnowledgeSearch(query: string) {
  return useQuery({
    queryKey: ["knowledge-search", query],
    queryFn: () => searchKnowledge(query),
    enabled: query.trim().length > 1,
  });
}

export function useReindexKnowledge() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reindexKnowledge,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["knowledge-sources"] }),
        queryClient.invalidateQueries({ queryKey: ["knowledge-chunks"] }),
        queryClient.invalidateQueries({ queryKey: ["knowledge-search"] }),
      ]);
    },
  });
}
