import { useRef, useState } from "react";
import { Camera, Upload, ImageIcon, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { BorescopeCapturePanel, BORESCOPE_FILENAME_PREFIX, type BorescopeEvent } from "./borescope-capture";

/**
 * ImageAcquisition — one reusable "Add Image" surface for the whole platform.
 *
 * Wherever LumenAI needs an inspection or baseline image, this component gives
 * the user a single, consistent choice of image *source* — capture live from
 * the borescope, upload an existing file, or drag & drop — without leaving the
 * active workflow. The borescope is presented here as just another camera/image
 * source, exactly like a webcam or file picker.
 *
 * Design principle: **the active workflow owns the image.** This component is
 * intentionally controlled (`files` + `onChange`) and network-free: it only
 * produces `File` objects. The parent workflow keeps using its existing,
 * governed upload endpoint, so tenant isolation, authorization, EXIF-stripping,
 * SHA-256 hashing, audit logging, and retention rules are all unchanged — there
 * is no second, weaker upload path.
 */

export type ImageSource = "borescope_capture" | "file_upload";

/**
 * Recover which source a file came from. Borescope frames are minted with a
 * known filename prefix (see BorescopeCapturePanel); everything else is a file
 * upload. Lets a parent record a per-image `image_source` in existing metadata
 * without threading extra state through the component tree.
 */
export function imageAcquisitionSource(file: File): ImageSource {
  return file.name.startsWith(BORESCOPE_FILENAME_PREFIX) ? "borescope_capture" : "file_upload";
}

interface ImageAcquisitionProps {
  /** Controlled list of acquired files. */
  files: File[];
  /** Receives the next full list (append/remove handled internally). */
  onChange: (files: File[]) => void;
  /** Visible action label, e.g. "Add Inspection Image" / "Add Baseline Image". */
  label?: string;
  /** Allow more than one image (default true). */
  multiple?: boolean;
  /** Cap on total files retained (default 10). */
  maxFiles?: number;
  /** Per-file size cap in bytes (default 10 MB — matches the backend). */
  maxBytes?: number;
  /** Read-only / disabled (e.g. viewer role, or a locked record). */
  disabled?: boolean;
  /** Show thumbnail previews of acquired files (default true). */
  showPreviews?: boolean;
  /** Optional telemetry hook. Never receives image data or PHI. */
  onEvent?: (name: BorescopeEvent | "image_source_opened" | "file_upload_completed", detail?: string) => void;
  className?: string;
  /** Stable id prefix for inputs/labels. */
  id?: string;
}

const DEFAULT_MAX_BYTES = 10 * 1024 * 1024;

export function ImageAcquisition({
  files,
  onChange,
  label = "Add Image",
  multiple = true,
  maxFiles = 10,
  maxBytes = DEFAULT_MAX_BYTES,
  disabled = false,
  showPreviews = true,
  onEvent,
  className,
  id = "image-acquisition",
}: ImageAcquisitionProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"picker" | "borescope">("picker");
  const [dragOver, setDragOver] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  function validate(incoming: File[]): File[] {
    const errs: string[] = [];
    const valid: File[] = [];
    for (const f of incoming) {
      if (!f.type.startsWith("image/")) {
        errs.push(`${f.name}: not an image file`);
      } else if (f.size > maxBytes) {
        errs.push(`${f.name}: exceeds ${Math.round(maxBytes / (1024 * 1024))} MB`);
      } else {
        valid.push(f);
      }
    }
    setErrors(errs);
    return valid;
  }

  function add(incoming: File[], source: "file_upload" | "borescope_capture") {
    if (disabled) return;
    const valid = validate(incoming);
    if (valid.length === 0) return;
    const next = multiple ? [...files, ...valid].slice(0, maxFiles) : valid.slice(0, 1);
    onChange(next);
    if (source === "file_upload") onEvent?.("file_upload_completed");
  }

  function remove(idx: number) {
    onChange(files.filter((_, i) => i !== idx));
  }

  function openBorescope() {
    if (disabled) return;
    setMode("borescope");
    onEvent?.("image_source_opened", "borescope");
  }

  return (
    <div className={cn("space-y-3", className)}>
      {mode === "borescope" ? (
        <BorescopeCapturePanel
          disabled={disabled}
          onEvent={onEvent}
          onAttach={(captured) => {
            add(captured, "borescope_capture");
            if (!multiple) setMode("picker");
          }}
          onCancel={() => setMode("picker")}
        />
      ) : (
        <>
          <p className="text-sm font-medium text-slate-700">{label}</p>
          <p className="text-xs text-slate-500 -mt-1">Choose image source:</p>

          {/* Source options — stacked on mobile, side by side on wider screens. */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button
              type="button"
              onClick={openBorescope}
              disabled={disabled}
              className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 hover:border-blue-400 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Camera className="h-5 w-5 text-blue-600" aria-hidden="true" />
              Capture from Borescope
            </button>
            <button
              type="button"
              onClick={() => { if (!disabled) inputRef.current?.click(); }}
              disabled={disabled}
              className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 hover:border-blue-400 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload className="h-5 w-5 text-blue-600" aria-hidden="true" />
              Upload Existing Image
            </button>
          </div>

          {/* Drag & drop target (also click-to-browse). */}
          <div
            onDragOver={(e) => { if (!disabled) { e.preventDefault(); setDragOver(true); } }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (!disabled) add(Array.from(e.dataTransfer.files), "file_upload");
            }}
            onClick={() => { if (!disabled) inputRef.current?.click(); }}
            role="button"
            tabIndex={disabled ? -1 : 0}
            aria-label={`${label} — drag and drop an image here or press Enter to browse`}
            onKeyDown={(e) => {
              if (disabled) return;
              if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click(); }
            }}
            className={cn(
              "flex flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed p-5 transition-colors",
              disabled
                ? "border-slate-200 bg-slate-50 cursor-not-allowed opacity-60"
                : dragOver
                  ? "border-blue-400 bg-blue-50 cursor-pointer"
                  : "border-slate-300 bg-slate-50 hover:bg-slate-100 cursor-pointer",
            )}
          >
            <ImageIcon className="h-6 w-6 text-slate-400" aria-hidden="true" />
            <p className="text-sm font-medium text-slate-600">Drag &amp; drop an image here</p>
            <p className="text-xs text-slate-400">
              JPEG, PNG, WebP · max {Math.round(maxBytes / (1024 * 1024))} MB{multiple ? ` · up to ${maxFiles} files` : ""}
            </p>
          </div>

          <input
            ref={inputRef}
            id={`${id}-file`}
            type="file"
            accept="image/*"
            multiple={multiple}
            className="hidden"
            disabled={disabled}
            onChange={(e) => {
              if (e.target.files) add(Array.from(e.target.files), "file_upload");
              e.target.value = ""; // allow re-selecting the same file
            }}
          />
        </>
      )}

      {errors.map((err, i) => (
        <p key={i} className="text-xs text-red-600" role="alert">{err}</p>
      ))}

      {/* Acquired previews with source + remove. */}
      {showPreviews && files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((f, i) => {
            const url = URL.createObjectURL(f);
            const source = imageAcquisitionSource(f);
            return (
              <div
                key={`${f.name}-${f.size}-${i}`}
                className="relative rounded-lg overflow-hidden border border-slate-200 w-24 bg-slate-50 shrink-0"
              >
                <img src={url} alt={f.name} className="w-24 h-20 object-cover" />
                <span className="block px-1 py-0.5 text-[10px] font-medium text-slate-500 truncate">
                  {source === "borescope_capture" ? "Borescope" : "Upload"}
                </span>
                {!disabled && (
                  <button
                    type="button"
                    onClick={() => remove(i)}
                    aria-label={`Remove ${f.name}`}
                    className="absolute top-0.5 right-0.5 rounded-full bg-white/90 p-0.5 text-slate-600 hover:bg-white shadow-sm"
                  >
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default ImageAcquisition;
