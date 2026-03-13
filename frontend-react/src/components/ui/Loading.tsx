import { Loader2 } from "lucide-react";

export default function Loading({ message = "Loading…" }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3 text-text-secondary">
      <Loader2 className="h-8 w-8 animate-spin" aria-hidden />
      <span className="text-sm">{message}</span>
    </div>
  );
}
