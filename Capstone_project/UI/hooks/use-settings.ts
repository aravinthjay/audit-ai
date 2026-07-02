"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getLlmSettings, getSettings, updateLlmSettings, updateSettings } from "@/services/settings.service";
import type { AppSettings, LLMSettingsUpdate } from "@/types/domain";

export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AppSettings) => updateSettings(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["settings"], data);
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}

export function useLlmSettings() {
  return useQuery({
    queryKey: ["settings", "llm"],
    queryFn: getLlmSettings,
  });
}

export function useUpdateLlmSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LLMSettingsUpdate) => updateLlmSettings(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["settings", "llm"], data);
      void queryClient.invalidateQueries({ queryKey: ["settings", "llm"] });
    },
  });
}
