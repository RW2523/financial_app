import type { ReactNode } from "react";
import Loading from "./Loading";
import ErrorMessage from "./ErrorMessage";

type Props = {
  loading?: boolean;
  error?: string | null;
  loadingMessage?: string;
  children: ReactNode;
};

export default function PageContent({ loading, error, loadingMessage, children }: Props) {
  if (loading) return <div className="p-6"><Loading message={loadingMessage} /></div>;
  return (
    <div className="p-6">
      {error && <div className="mb-4"><ErrorMessage message={error} /></div>}
      {children}
    </div>
  );
}
