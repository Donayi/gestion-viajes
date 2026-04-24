import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function ErrorState({
  message,
  onRetry
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="p-8">
      <h3 className="text-lg font-semibold text-red-700">No fue posible continuar</h3>
      <p className="mt-2 text-sm text-slate-600">{message}</p>
      {onRetry ? (
        <Button className="mt-5" onClick={onRetry} type="button">
          Reintentar
        </Button>
      ) : null}
    </Card>
  );
}
