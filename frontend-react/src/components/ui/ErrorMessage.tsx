export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm" role="alert">
      {message}
    </div>
  );
}
