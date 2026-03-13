export default function SuccessMessage({ message }: { message: string }) {
  return (
    <div className="p-4 rounded-lg bg-accent-muted border border-accent/30 text-accent text-sm" role="status">
      {message}
    </div>
  );
}
