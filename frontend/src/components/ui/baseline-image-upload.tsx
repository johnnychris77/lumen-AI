import { useRef, useState } from "react";
import { Upload, Image, X, CheckCircle2 } from "lucide-react";
import { Button } from "./button";
import { Spinner } from "./spinner";
import { useAuth, API_BASE } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface BaselineImageUploadProps {
  value: string;
  onChange: (url: string) => void;
  className?: string;
}

export function BaselineImageUpload({ value, onChange, className }: BaselineImageUploadProps) {
  const { headers } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<string>("");

  async function handleFile(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("Only image files are accepted (JPEG, PNG, WebP).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File must be under 10 MB.");
      return;
    }

    // Show local preview immediately
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);

    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const hdrs = headers();
      // multipart — don't set Content-Type (browser sets it with boundary)
      const res = await fetch(
        `${API_BASE}/api/enterprise/vendor-baseline-subscription/baselines/upload-image`,
        {
          method: "POST",
          headers: {
            Authorization: hdrs["Authorization"],
            "X-LumenAI-Role": hdrs["X-LumenAI-Role"],
            "X-LumenAI-Actor": hdrs["X-LumenAI-Actor"],
          },
          body: form,
        }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Upload failed (${res.status})`);
      onChange(data.baseline_image_url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setPreview("");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  const displayUrl = preview || value;

  return (
    <div className={cn("space-y-2", className)}>
      {displayUrl ? (
        <div className="relative rounded-lg overflow-hidden border border-slate-200 bg-slate-50">
          <img
            src={displayUrl}
            alt="Baseline preview"
            className="w-full h-40 object-cover"
            onError={() => setPreview("")}
          />
          <div className="absolute top-2 right-2 flex gap-1.5">
            {value && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-600 text-white">
                <CheckCircle2 className="h-3 w-3" /> Uploaded
              </span>
            )}
            <button
              type="button"
              onClick={() => { onChange(""); setPreview(""); }}
              className="rounded-full bg-white/90 p-1 text-slate-600 hover:bg-white shadow-sm"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      ) : (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-6 cursor-pointer hover:bg-slate-100 transition-colors"
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? (
            <>
              <Spinner className="h-6 w-6 text-blue-500" />
              <p className="text-xs text-slate-500">Uploading…</p>
            </>
          ) : (
            <>
              <Image className="h-8 w-8 text-slate-300" />
              <div className="text-center">
                <p className="text-sm font-medium text-slate-600">Drop image here or click to browse</p>
                <p className="text-xs text-slate-400 mt-0.5">JPEG, PNG, WebP · max 10 MB</p>
              </div>
              <Button type="button" variant="outline" size="sm" className="gap-1.5">
                <Upload className="h-3.5 w-3.5" /> Choose File
              </Button>
            </>
          )}
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />

      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
