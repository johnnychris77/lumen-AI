import { useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch, ApiError } from "@/lib/api";
import { OBSERVATION_TAXONOMY, REGION_TYPES } from "@/lib/canvasTypes";

// Project Canvas — Sections 7 & 8: Annotation Tools + Approved Observation
// Taxonomy. Only the 10 approved LCID categories are selectable; bounding
// boxes get a real click-free numeric entry (x1,y1,x2,y2 normalized 0-1),
// other region types accept a raw coordinate array — an honest, disclosed
// simplification rather than a full freehand drawing tool (see
// docs/annotation-workspace/ANNOTATION_WORKSPACE.md).
export function NewAnnotationForm({ retainedImageId, onCreated }: { retainedImageId: number; onCreated: () => void }) {
  const [observation, setObservation] = useState("");
  const [severity, setSeverity] = useState("");
  const [location, setLocation] = useState("");
  const [confidence, setConfidence] = useState("");
  const [comments, setComments] = useState("");
  const [regionType, setRegionType] = useState("whole_image_classification");
  const [box, setBox] = useState({ x1: "", y1: "", x2: "", y2: "" });
  const [rawCoords, setRawCoords] = useState("[]");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setResult(null);
    if (!observation) {
      setResult({ type: "error", message: "Select an observation category from the approved taxonomy." });
      return;
    }

    let regionCoordinates: number[] = [];
    try {
      if (regionType === "bounding_box") {
        const vals = [box.x1, box.y1, box.x2, box.y2].map(Number);
        if (vals.some((v) => Number.isNaN(v))) throw new Error("All four box coordinates are required.");
        regionCoordinates = vals;
      } else if (regionType !== "whole_image_classification") {
        const parsed = JSON.parse(rawCoords);
        if (!Array.isArray(parsed)) throw new Error("Region coordinates must be a JSON array.");
        regionCoordinates = parsed;
      }
    } catch (err) {
      setResult({ type: "error", message: err instanceof Error ? err.message : "Invalid region coordinates." });
      return;
    }

    setSubmitting(true);
    try {
      await apiFetch("/api/annotations", {
        method: "POST",
        body: {
          retained_image_id: retainedImageId,
          primary_observation: observation,
          severity,
          location,
          confidence: confidence ? Number(confidence) : null,
          comments,
          region_type: regionType,
          region_coordinates: regionCoordinates,
        },
      });
      setResult({ type: "success", message: "Annotation created." });
      setObservation(""); setSeverity(""); setLocation(""); setConfidence(""); setComments("");
      setRegionType("whole_image_classification"); setBox({ x1: "", y1: "", x2: "", y2: "" }); setRawCoords("[]");
      onCreated();
    } catch (err) {
      setResult({ type: "error", message: err instanceof ApiError ? err.message : "Failed to create annotation." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {result && (
        <div
          role="alert"
          className={`flex items-start gap-2 rounded-lg border p-2.5 text-xs ${
            result.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          {result.type === "success" ? <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 shrink-0" /> : <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
          <p>{result.message}</p>
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <Label>Observation *</Label>
          <Select value={observation} onChange={(e) => setObservation(e.target.value)} required>
            <option value="">Select…</option>
            {OBSERVATION_TAXONOMY.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </Select>
        </div>
        <div>
          <Label>Severity</Label>
          <Input value={severity} onChange={(e) => setSeverity(e.target.value)} placeholder="e.g. minor / moderate / severe" />
        </div>
        <div>
          <Label>Location</Label>
          <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Free-text location description" />
        </div>
        <div>
          <Label>Reviewer confidence (0–1)</Label>
          <Input type="number" min={0} max={1} step={0.05} value={confidence} onChange={(e) => setConfidence(e.target.value)} />
        </div>
      </div>

      <div>
        <Label>Region type</Label>
        <Select value={regionType} onChange={(e) => setRegionType(e.target.value)}>
          {REGION_TYPES.map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </Select>
      </div>

      {regionType === "bounding_box" && (
        <div className="grid grid-cols-4 gap-2">
          {(["x1", "y1", "x2", "y2"] as const).map((k) => (
            <div key={k}>
              <Label>{k}</Label>
              <Input
                type="number" min={0} max={1} step={0.01}
                value={box[k]}
                onChange={(e) => setBox((b) => ({ ...b, [k]: e.target.value }))}
              />
            </div>
          ))}
        </div>
      )}
      {regionType !== "whole_image_classification" && regionType !== "bounding_box" && (
        <div>
          <Label>Region coordinates (JSON array, normalized 0–1)</Label>
          <Textarea value={rawCoords} onChange={(e) => setRawCoords(e.target.value)} rows={2} placeholder="[[0.1,0.2],[0.3,0.4]]" />
        </div>
      )}

      <div>
        <Label>Comments</Label>
        <Textarea value={comments} onChange={(e) => setComments(e.target.value)} rows={2} placeholder="Reviewer instructions / notes" />
      </div>

      <Button type="submit" size="sm" disabled={submitting}>
        {submitting && <Spinner className="h-4 w-4" />}
        Create Annotation
      </Button>
    </form>
  );
}
