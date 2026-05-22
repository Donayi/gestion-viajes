import { EmptyState } from "@/components/ui/empty-state";

export function AdminEmptyState({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return <EmptyState description={description} title={title} />;
}
