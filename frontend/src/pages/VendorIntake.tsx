import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2, AlertTriangle, ScanLine, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { BarcodeScanner } from "@/components/ui/barcode-scanner";
import { useAuth, API_BASE } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

const schema = z.object({
  facility_name: z.string().min(2, "Facility name is required"),
  department_name: z.string().min(2, "Department is required"),
  vendor_name: z.string().min(2, "Vendor name is required"),
  instrument_name: z.string().min(2, "Instrument name is required"),
  instrument_category: z.enum(["lumened instrument", "non-lumened instrument", "rigid scope", "flexible scope", "other"]),
  barcode_value: z.string().optional(),
  qr_code_value: z.string().optional(),
  key_dot_value: z.string().optional(),
  finding_category: z.enum([
    "bioburden / retained debris",
    "blood / retained blood residue",
    "bone / bone fragment",
    "tissue / retained tissue",
    "debris / retained debris",
    "corrosion / surface rust",
    "crack / hairline fracture",
    "insulation damage",
    "mechanical damage",
    "discoloration",
    "lumen blockage",
    "seal integrity failure",
    "other",
  ]),
  finding_description: z.string().min(10, "Description must be at least 10 characters"),
  severity: z.enum(["low", "medium", "high", "critical"]),
  confidence_score: z.coerce.number().min(0).max(1),
  recommended_action: z.string().min(5, "Recommended action is required"),
});

type FormValues = z.infer<typeof schema>;

const SEVERITY_COLORS: Record<string, string> = {
  low: "success",
  medium: "warning",
  high: "warning",
  critical: "destructive",
};

type ScanTarget = "barcode_value" | "qr_code_value" | "key_dot_value" | null;

export default function VendorIntake() {
  const { headers } = useAuth();
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [apiError, setApiError] = useState("");
  const [scanTarget, setScanTarget] = useState<ScanTarget>(null);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      facility_name: "St. Mary's Hospital",
      department_name: "Sterile Processing",
      vendor_name: "",
      instrument_name: "",
      instrument_category: "lumened instrument",
      barcode_value: "",
      qr_code_value: "",
      key_dot_value: "",
      finding_category: "bioburden / retained debris",
      finding_description: "",
      severity: "high",
      confidence_score: 0.85,
      recommended_action: "Quarantine + reclean + second inspection",
    },
  });

  const severity = watch("severity");

  function handleScanResult(value: string) {
    if (scanTarget) setValue(scanTarget, value);
    setScanTarget(null);
  }

  async function onSubmit(values: FormValues) {
    setApiError("");
    setResult(null);
    const hdrs = headers();
    const res = await apiFetch(`/api/enterprise/intake`, { raw: true,
      method: "POST",
      headers: { ...hdrs, "X-Tenant-Id": "bonsecours", "X-Tenant-Name": "Bon Secours", "X-LumenAI-Role": "operator" },
      body: JSON.stringify(values),
    });
    const data = await res.json();
    if (!res.ok) {
      setApiError(data?.detail || `Request failed (${res.status})`);
      return;
    }
    setResult(data);
  }

  if (result) {
    return (
      <div className="max-w-2xl space-y-4">
        <nav className="flex items-center gap-1.5 text-xs text-slate-400">
          <Link to="/" className="hover:text-slate-600">Dashboard</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-slate-600 font-medium">Vendor Intake</span>
        </nav>

        <Alert variant="success">
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>Inspection intake submitted successfully</AlertTitle>
          <AlertDescription>The finding has been captured and routed for workflow processing.</AlertDescription>
        </Alert>
        <Card>
          <CardHeader><CardTitle>Intake Record Created</CardTitle></CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              {(["finding_id", "risk_score_id", "disposition_id", "evidence_id", "workflow_status"] as const).map((k) =>
                result[k] != null ? (
                  <div key={k}>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{k.replace(/_/g, " ")}</dt>
                    <dd className="mt-0.5 font-semibold text-slate-900">{String(result[k])}</dd>
                  </div>
                ) : null
              )}
            </dl>
          </CardContent>
        </Card>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => { setResult(null); reset(); }}>
            Submit another intake
          </Button>
          <Link to="/intake-history">
            <Button variant="ghost">View intake history →</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/" className="hover:text-slate-600">Dashboard</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-600 font-medium">Vendor Intake</span>
      </nav>

      <div>
        <h2 className="text-xl font-semibold text-slate-900">New Inspection Finding</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Submit an inspection finding from sterile processing triage. All fields are validated before submission.
        </p>
      </div>

      {apiError && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        {/* Facility */}
        <Card>
          <CardHeader><CardTitle>Facility & Department</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="facility_name">Facility Name *</Label>
              <Input id="facility_name" {...register("facility_name")} placeholder="St. Mary's Hospital" />
              {errors.facility_name && <p className="text-xs text-red-600">{errors.facility_name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="department_name">Department *</Label>
              <Input id="department_name" {...register("department_name")} placeholder="Sterile Processing" />
              {errors.department_name && <p className="text-xs text-red-600">{errors.department_name.message}</p>}
            </div>
          </CardContent>
        </Card>

        {/* Instrument + identifiers */}
        <Card>
          <CardHeader><CardTitle>Instrument Identification</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="vendor_name">Vendor / Manufacturer *</Label>
                <Input id="vendor_name" {...register("vendor_name")} placeholder="e.g. Medtronic" />
                {errors.vendor_name && <p className="text-xs text-red-600">{errors.vendor_name.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="instrument_name">Instrument Name *</Label>
                <Input id="instrument_name" {...register("instrument_name")} placeholder="e.g. Frazier Suction 8Fr" />
                {errors.instrument_name && <p className="text-xs text-red-600">{errors.instrument_name.message}</p>}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="instrument_category">Instrument Category *</Label>
              <Select id="instrument_category" {...register("instrument_category")}>
                <option value="lumened instrument">Lumened Instrument</option>
                <option value="non-lumened instrument">Non-Lumened Instrument</option>
                <option value="rigid scope">Rigid Scope</option>
                <option value="flexible scope">Flexible Scope</option>
                <option value="other">Other</option>
              </Select>
            </div>

            {/* Identifier fields with scan buttons */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Instrument Identifiers (scan or type)
              </Label>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {(
                  [
                    { field: "barcode_value" as const, label: "Barcode" },
                    { field: "qr_code_value" as const, label: "QR Code / UDI" },
                    { field: "key_dot_value" as const, label: "KeyDot" },
                  ] as const
                ).map(({ field, label }) => (
                  <div key={field} className="space-y-1">
                    <Label htmlFor={field} className="text-xs">{label}</Label>
                    <div className="flex gap-1.5">
                      <Input
                        id={field}
                        {...register(field)}
                        placeholder={`Scan or type…`}
                        className="text-xs"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="shrink-0"
                        title={`Scan ${label}`}
                        onClick={() => setScanTarget(field)}
                      >
                        <ScanLine className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-400">
                Click the scan icon to use your device camera. Requires Chrome 83+ or Edge.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Finding */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Finding Details
              {severity && (
                <Badge variant={(SEVERITY_COLORS[severity] as "success" | "warning" | "destructive") || "secondary"} className="capitalize">
                  {severity}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="finding_category">Finding Category *</Label>
                <Select id="finding_category" {...register("finding_category")}>
                  <optgroup label="Biological Residue">
                    <option value="blood / retained blood residue">Blood / Retained Blood Residue</option>
                    <option value="bone / bone fragment">Bone / Bone Fragment</option>
                    <option value="tissue / retained tissue">Tissue / Retained Tissue</option>
                    <option value="bioburden / retained debris">Bioburden / Retained Debris</option>
                  </optgroup>
                  <optgroup label="Physical / Mechanical">
                    <option value="debris / retained debris">Debris / Retained Debris</option>
                    <option value="corrosion / surface rust">Corrosion / Surface Rust</option>
                    <option value="crack / hairline fracture">Crack / Hairline Fracture</option>
                    <option value="insulation damage">Insulation Damage</option>
                    <option value="mechanical damage">Mechanical Damage</option>
                    <option value="discoloration">Discoloration</option>
                    <option value="lumen blockage">Lumen Blockage</option>
                    <option value="seal integrity failure">Seal Integrity Failure</option>
                  </optgroup>
                  <optgroup label="Other">
                    <option value="other">Other</option>
                  </optgroup>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="severity">Severity *</Label>
                <Select id="severity" {...register("severity")}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </Select>
                {errors.severity && <p className="text-xs text-red-600">{errors.severity.message}</p>}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="finding_description">Finding Description *</Label>
              <Textarea
                id="finding_description"
                {...register("finding_description")}
                placeholder="Describe the finding observed during borescope inspection — location, appearance, extent…"
                rows={3}
              />
              {errors.finding_description && <p className="text-xs text-red-600">{errors.finding_description.message}</p>}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="confidence_score">AI Confidence Score (0–1) *</Label>
                <Input id="confidence_score" type="number" step="0.01" min="0" max="1" {...register("confidence_score")} />
                {errors.confidence_score && <p className="text-xs text-red-600">{errors.confidence_score.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="recommended_action">Recommended Action *</Label>
                <Input id="recommended_action" {...register("recommended_action")} placeholder="e.g. Quarantine + reclean" />
                {errors.recommended_action && <p className="text-xs text-red-600">{errors.recommended_action.message}</p>}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={isSubmitting} className="min-w-[180px]">
            {isSubmitting ? <><Spinner className="h-4 w-4" />Submitting…</> : "Submit Inspection Finding"}
          </Button>
          <Button type="button" variant="outline" onClick={() => reset()}>
            Reset Form
          </Button>
        </div>
      </form>

      {/* Barcode scanner modal */}
      {scanTarget && (
        <BarcodeScanner
          onDetected={handleScanResult}
          onClose={() => setScanTarget(null)}
        />
      )}
    </div>
  );
}
