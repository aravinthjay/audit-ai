"use client";

import { FileSearch } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { routes } from "@/constants/routes";
import { useInvestigations } from "@/hooks/use-cases";

export default function WorkspacePage() {
  const router = useRouter();
  const { data, error, isLoading, refetch } = useInvestigations();
  const firstInvestigation = data?.[0];

  useEffect(() => {
    if (firstInvestigation) {
      router.replace(routes.caseWorkspace(firstInvestigation.id));
    }
  }, [firstInvestigation, router]);

  if (isLoading || firstInvestigation) {
    return <LoadingState label="Opening workspace" />;
  }

  if (error) {
    return <ErrorState onRetry={() => void refetch()} />;
  }

  return (
    <EmptyState
      title="No case workspace yet"
      description="Create cases from intake or add an investigation before opening the workspace."
      icon={FileSearch}
    />
  );
}
