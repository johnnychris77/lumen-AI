import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Retained-image bytes are access-controlled (`GET /api/ml/images/{id}/bytes`
 * requires a bearer token), so a plain `<img src>` can't load them — the
 * browser never attaches our Authorization header to an image request. This
 * fetches the bytes through the authenticated API client and renders them as
 * an object URL instead (Project Canvas Section 6A/24: deferred-loading,
 * safely cached, never a fabricated thumbnail pipeline).
 */
export function AuthenticatedImage({
  retainedImageId,
  alt,
  className,
}: {
  retainedImageId: number;
  alt: string;
  className?: string;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setFailed(false);
    setSrc(null);

    apiFetch(`/api/ml/images/${retainedImageId}/bytes`, { raw: true })
      .then(async (res) => {
        if (!res.ok || cancelled) {
          if (!cancelled) setFailed(true);
          return;
        }
        objectUrl = URL.createObjectURL(await res.blob());
        if (!cancelled) setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [retainedImageId]);

  if (failed || !retainedImageId) {
    return (
      <div className={cn("flex items-center justify-center bg-slate-100 text-slate-300", className)}>
        <ImageIcon className="h-8 w-8" />
      </div>
    );
  }

  if (!src) {
    return <div className={cn("animate-pulse bg-slate-100", className)} />;
  }

  return <img src={src} alt={alt} loading="lazy" className={className} />;
}
