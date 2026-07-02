import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function UnauthorizedPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center text-center">
      <ShieldAlert className="h-8 w-8 text-warning-foreground" aria-hidden="true" />
      <h1 className="mt-3 text-xl font-semibold">Unauthorized</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        This workspace requires an audit team role with case review permissions.
      </p>
      <Button asChild className="mt-5">
        <Link href="/dashboard">Return to dashboard</Link>
      </Button>
    </div>
  );
}
