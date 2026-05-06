import React, { useEffect, useState } from "react";
import {
  uploadEvidence,
  fetchEvidence,
  buildEvidenceFileUrl,
  linkEvidenceToVisualReview,
  linkEvidenceToInspection,
  linkEvidenceToCapa,
  classifyEvidence,
  humanReviewEvidence,
  fetchEvidenceClassificationSummary,
} from "../api/evidenceApi.js";

const initialForm = {
  evidence_type: "borescope_image",
  facility: "St. Mary’s Hospital",
  instrument_name: "Frazier suction",
  vendor: "Medtronic",
  finding_category: "bioburden suspected",
};

export default function EvidenceUploadPanel() {
  const [form, setForm] = useState(initialForm);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const [evidenceItems, setEvidenceItems] = useState([]);
  const [linkTargets, setLinkTargets] = useState({
    visualReviewId: "",
    inspectionId: "",
    capaId: "",
  });
  const [uploading, setUploading] = useState(false);
  const [linking, setLinking] = useState("");
  const [classifying, setClassifying] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [classificationSummary, setClassificationSummary] = useState(null);
  const [classificationForm, setClassificationForm] = useState({
    suspected_debris_type: "Suspected blood residue",
    suspected_material_type: "Possible organic material",
    quality_issue_type: "Bioburden / retained debris",
    image_quality_score: 88,
    human_confirmed_classification: "Bioburden / retained debris",
    human_override_reason: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadEvidence() {
    const data = await fetchEvidence();
    setEvidenceItems(data.items || []);
  }

  async function loadClassificationSummary() {
    const data = await fetchEvidenceClassificationSummary();
    setClassificationSummary(data);
  }

  useEffect(() => {
    loadEvidence().catch((err) => setError(err.message));
    loadClassificationSummary().catch((err) => setError(err.message));
  }, []);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateLinkTarget(field, value) {
    setLinkTargets((current) => ({ ...current, [field]: value }));
  }

  function updateClassificationField(field, value) {
    setClassificationForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function handleFileChange(event) {
    const selected = event.target.files?.[0] || null;
    setFile(selected);
    setSelectedEvidence(null);
    setMessage("");
    setError("");

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(selected ? URL.createObjectURL(selected) : "");
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (!file) {
      setError("Please choose an image or evidence file before uploading.");
      return;
    }

    try {
      setUploading(true);
      setError("");
      setMessage("");

      const result = await uploadEvidence({ file, ...form });
      setSelectedEvidence(result.evidence);
      setMessage(`Evidence uploaded: ${result.evidence.evidence_id}`);
      await loadEvidence();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleLinkEvidence(type) {
    if (!selectedEvidence?.evidence_id) {
      setError("Select or upload evidence before linking.");
      return;
    }

    try {
      setLinking(type);
      setError("");
      setMessage("");

      let result;

      if (type === "visual_review") {
        if (!linkTargets.visualReviewId) throw new Error("Visual Review ID is required.");
        result = await linkEvidenceToVisualReview(selectedEvidence.evidence_id, linkTargets.visualReviewId);
      }

      if (type === "inspection") {
        if (!linkTargets.inspectionId) throw new Error("Inspection ID is required.");
        result = await linkEvidenceToInspection(selectedEvidence.evidence_id, linkTargets.inspectionId);
      }

      if (type === "capa") {
        if (!linkTargets.capaId) throw new Error("CAPA ID is required.");
        result = await linkEvidenceToCapa(selectedEvidence.evidence_id, linkTargets.capaId);
      }

      setSelectedEvidence(result.evidence);
      setMessage(result.message || "Evidence linked successfully.");
      await loadEvidence();
    } catch (err) {
      setError(err.message);
    } finally {
      setLinking("");
    }
  }


  async function handleClassifyEvidence() {
    if (!selectedEvidence?.evidence_id) {
      setError("Select or upload evidence before classification.");
      return;
    }

    try {
      setClassifying(true);
      setError("");
      setMessage("");

      const result = await classifyEvidence(selectedEvidence.evidence_id, {
        suspected_debris_type: classificationForm.suspected_debris_type,
        suspected_material_type: classificationForm.suspected_material_type,
        quality_issue_type: classificationForm.quality_issue_type,
        image_quality_score: Number(classificationForm.image_quality_score),
      });

      setSelectedEvidence(result.evidence);
      setMessage("Evidence classified and ready for human confirmation.");
      await loadEvidence();
      await loadClassificationSummary();
    } catch (err) {
      setError(err.message);
    } finally {
      setClassifying(false);
    }
  }

  async function handleHumanReviewEvidence() {
    if (!selectedEvidence?.evidence_id) {
      setError("Select or upload evidence before human review.");
      return;
    }

    try {
      setReviewing(true);
      setError("");
      setMessage("");

      const result = await humanReviewEvidence(selectedEvidence.evidence_id, {
        human_confirmed_classification: classificationForm.human_confirmed_classification,
        human_override_reason: classificationForm.human_override_reason,
        reviewer: "Dashboard User",
      });

      setSelectedEvidence(result.evidence);
      setMessage("Human evidence review completed.");
      await loadEvidence();
      await loadClassificationSummary();
    } catch (err) {
      setError(err.message);
    } finally {
      setReviewing(false);
    }
  }

  return (
    <section style={sectionWrapper}>
      <div style={{ marginBottom: "18px" }}>
        <h2 style={titleStyle}>Evidence & Image Upload Module</h2>
        <p style={subtitleStyle}>
          Upload borescope images, inspection photos, and quality evidence for inspection intelligence, CAPA review, and vendor escalation.
        </p>
      </div>

      {message && <div style={successStyle}>{message}</div>}
      {error && <div style={errorStyle}>{error}</div>}

      <ClassificationSummaryCard summary={classificationSummary} />

      <div style={layoutStyle}>
        <form onSubmit={handleUpload} style={cardStyle}>
          <h3 style={cardTitleStyle}>Upload Evidence</h3>

          <div style={uploadBoxStyle}>
            <div style={{ fontSize: "15px", fontWeight: 950, color: "#0c4a6e" }}>
              Choose an Image File
            </div>
            <p style={{ color: "#0369a1", fontSize: "13px", marginTop: "6px" }}>
              Upload a borescope image, inspection photo, vendor tray photo, PDF, or audit evidence.
            </p>
            <input
              type="file"
              accept="image/*,.pdf"
              onChange={handleFileChange}
              style={fileInputStyle}
            />
          </div>

          <div style={gridStyle}>
            <Select
              label="Evidence Type"
              value={form.evidence_type}
              onChange={(value) => updateField("evidence_type", value)}
              options={[
                "borescope_image",
                "inspection_photo",
                "vendor_tray_photo",
                "audit_evidence",
                "ip_review_evidence",
                "other",
              ]}
            />
            <Input label="Facility" value={form.facility} onChange={(value) => updateField("facility", value)} />
            <Input label="Instrument Name" value={form.instrument_name} onChange={(value) => updateField("instrument_name", value)} />
            <Input label="Vendor" value={form.vendor} onChange={(value) => updateField("vendor", value)} />
            <Input label="Finding Category" value={form.finding_category} onChange={(value) => updateField("finding_category", value)} />
          </div>

          <button type="submit" disabled={uploading} style={primaryButtonStyle}>
            {uploading ? "Uploading..." : "Upload Evidence"}
          </button>
        </form>

        <EvidencePreviewCard
          previewUrl={previewUrl}
          file={file}
          evidence={selectedEvidence}
          linkTargets={linkTargets}
          updateLinkTarget={updateLinkTarget}
          onLinkEvidence={handleLinkEvidence}
          linking={linking}
          classificationForm={classificationForm}
          updateClassificationField={updateClassificationField}
          onClassifyEvidence={handleClassifyEvidence}
          onHumanReviewEvidence={handleHumanReviewEvidence}
          classifying={classifying}
          reviewing={reviewing}
        />
      </div>

      <EvidenceGallery
        items={evidenceItems}
        selectedEvidenceId={selectedEvidence?.evidence_id}
        onSelect={(item) => {
          setSelectedEvidence(item);
          setPreviewUrl("");
          setFile(null);
        }}
      />
    </section>
  );
}

function EvidencePreviewCard({
  previewUrl,
  file,
  evidence,
  linkTargets,
  updateLinkTarget,
  onLinkEvidence,
  linking,
  classificationForm,
  updateClassificationField,
  onClassifyEvidence,
  onHumanReviewEvidence,
  classifying,
  reviewing,
}) {
  const evidenceFileUrl = evidence?.file_url ? buildEvidenceFileUrl(evidence.file_url) : "";
  const displayUrl = previewUrl || evidenceFileUrl;

  return (
    <div style={cardStyle}>
      <h3 style={cardTitleStyle}>Image Preview</h3>

      {!displayUrl ? (
        <p style={subtitleStyle}>Choose or select evidence to preview it here.</p>
      ) : (
        <div>
          <div style={imageFrameStyle}>
            {displayUrl.match(/\.pdf($|\?)/i) ? (
              <div style={filePlaceholderStyle}>PDF Evidence</div>
            ) : (
              <img
                src={displayUrl}
                alt="Evidence preview"
                style={{ maxWidth: "100%", maxHeight: "320px", objectFit: "contain", borderRadius: "12px" }}
              />
            )}
          </div>

          {file && (
            <div style={metaBoxStyle}>
              <strong>Selected file:</strong> {file.name}<br />
              <strong>Type:</strong> {file.type || "Unknown"}<br />
              <strong>Size:</strong> {formatBytes(file.size)}
            </div>
          )}

          {evidence && (
            <>
              <div style={metaBoxStyle}>
                <strong>Evidence ID:</strong> {evidence.evidence_id}<br />
                <strong>Stored File:</strong> {evidence.stored_filename}<br />
                <strong>Type:</strong> {evidence.evidence_type}<br />
                <strong>AI Review:</strong> {evidence.ai_review_status}<br />
                <strong>Human Review:</strong> {evidence.human_review_status}<br />
                <strong>Linked Visual Review:</strong> {evidence.linked_visual_review_id || "None"}<br />
                <strong>Linked Inspection:</strong> {evidence.linked_inspection_id || "None"}<br />
                <strong>Linked CAPA:</strong> {evidence.linked_capa_id || "None"}<br />
                <strong>File URL:</strong> {evidence.file_url}
              </div>

              <EvidenceLinkControls
                linkTargets={linkTargets}
                updateLinkTarget={updateLinkTarget}
                onLinkEvidence={onLinkEvidence}
                linking={linking}
              />

              <EvidenceClassificationPanel
                evidence={evidence}
                classificationForm={classificationForm}
                updateClassificationField={updateClassificationField}
                onClassifyEvidence={onClassifyEvidence}
                onHumanReviewEvidence={onHumanReviewEvidence}
                classifying={classifying}
                reviewing={reviewing}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}


function ClassificationSummaryCard({ summary }) {
  if (!summary) return null;

  return (
    <div style={summaryGridStyle}>
      <SummaryTile label="Total Evidence" value={summary.total_evidence} />
      <SummaryTile label="AI Reviewed" value={summary.ai_reviewed} />
      <SummaryTile label="Human Confirmed" value={summary.human_confirmed} />
      <SummaryTile label="High Severity" value={summary.high_severity} />
    </div>
  );
}

function SummaryTile({ label, value }) {
  return (
    <div style={summaryTileStyle}>
      <div style={{ color: "#6b7280", fontSize: "12px", fontWeight: 900 }}>
        {label}
      </div>
      <div style={{ color: "#111827", fontSize: "28px", fontWeight: 950 }}>
        {value ?? 0}
      </div>
    </div>
  );
}

function EvidenceClassificationPanel({
  evidence,
  classificationForm,
  updateClassificationField,
  onClassifyEvidence,
  onHumanReviewEvidence,
  classifying,
  reviewing,
}) {
  return (
    <div style={classificationBoxStyle}>
      <h4 style={{ marginTop: 0, fontSize: "16px", fontWeight: 900 }}>
        AI-Ready Evidence Classification
      </h4>

      <div style={statusGridStyle}>
        <StatusPill label="AI Review" value={evidence.ai_review_status || "Not Reviewed"} />
        <StatusPill label="Human Review" value={evidence.human_review_status || "Pending Review"} />
      </div>

      <Input
        label="Suspected Debris Type"
        value={classificationForm.suspected_debris_type}
        onChange={(value) => updateClassificationField("suspected_debris_type", value)}
      />

      <Input
        label="Suspected Material Type"
        value={classificationForm.suspected_material_type}
        onChange={(value) => updateClassificationField("suspected_material_type", value)}
      />

      <Input
        label="Quality Issue Type"
        value={classificationForm.quality_issue_type}
        onChange={(value) => updateClassificationField("quality_issue_type", value)}
      />

      <Input
        label="Image Quality Score"
        value={classificationForm.image_quality_score}
        onChange={(value) => updateClassificationField("image_quality_score", value)}
      />

      <button
        type="button"
        onClick={onClassifyEvidence}
        disabled={classifying}
        style={{ ...smallActionButtonStyle, background: "#2563eb", borderColor: "#2563eb" }}
      >
        {classifying ? "Classifying..." : "Classify Evidence"}
      </button>

      <div style={metaBoxStyle}>
        <strong>AI Classification:</strong> {evidence.final_classification || "Not classified"}
        <br />
        <strong>Debris:</strong> {evidence.suspected_debris_type || "Not classified"}
        <br />
        <strong>Material:</strong> {evidence.suspected_material_type || "Not classified"}
        <br />
        <strong>Issue:</strong> {evidence.quality_issue_type || "Not classified"}
        <br />
        <strong>Image Quality:</strong> {evidence.image_quality_score ?? "N/A"}
        <br />
        <strong>AI Confidence:</strong> {evidence.ai_confidence_score ?? "N/A"}
        <br />
        <strong>Severity:</strong> {evidence.severity_score ?? "N/A"}
        <br />
        <strong>Recommended Action:</strong> {evidence.recommended_action || "N/A"}
      </div>

      <Input
        label="Human Confirmed Classification"
        value={classificationForm.human_confirmed_classification}
        onChange={(value) => updateClassificationField("human_confirmed_classification", value)}
      />

      <Input
        label="Human Override Reason"
        value={classificationForm.human_override_reason}
        onChange={(value) => updateClassificationField("human_override_reason", value)}
      />

      <button
        type="button"
        onClick={onHumanReviewEvidence}
        disabled={reviewing}
        style={{ ...smallActionButtonStyle, background: "#0f766e", borderColor: "#0f766e" }}
      >
        {reviewing ? "Saving Review..." : "Confirm Human Review"}
      </button>
    </div>
  );
}

function StatusPill({ label, value }) {
  return (
    <div style={statusPillStyle}>
      <div style={{ fontSize: "11px", color: "#6b7280", fontWeight: 900 }}>
        {label}
      </div>
      <div style={{ fontSize: "13px", color: "#111827", fontWeight: 900 }}>
        {value}
      </div>
    </div>
  );
}

function EvidenceLinkControls({ linkTargets, updateLinkTarget, onLinkEvidence, linking }) {
  return (
    <div style={linkBoxStyle}>
      <h4 style={{ marginTop: 0, fontSize: "16px", fontWeight: 900 }}>
        Link Evidence to Workflow
      </h4>

      <Input
        label="Visual Review ID"
        value={linkTargets.visualReviewId}
        onChange={(value) => updateLinkTarget("visualReviewId", value)}
      />
      <button
        type="button"
        onClick={() => onLinkEvidence("visual_review")}
        disabled={linking === "visual_review"}
        style={{ ...smallActionButtonStyle, background: "#4f46e5", borderColor: "#4f46e5" }}
      >
        {linking === "visual_review" ? "Linking..." : "Attach to Visual Review"}
      </button>

      <Input
        label="Inspection ID"
        value={linkTargets.inspectionId}
        onChange={(value) => updateLinkTarget("inspectionId", value)}
      />
      <button
        type="button"
        onClick={() => onLinkEvidence("inspection")}
        disabled={linking === "inspection"}
        style={{ ...smallActionButtonStyle, background: "#0f766e", borderColor: "#0f766e" }}
      >
        {linking === "inspection" ? "Linking..." : "Attach to Inspection"}
      </button>

      <Input
        label="CAPA ID"
        value={linkTargets.capaId}
        onChange={(value) => updateLinkTarget("capaId", value)}
      />
      <button
        type="button"
        onClick={() => onLinkEvidence("capa")}
        disabled={linking === "capa"}
        style={{ ...smallActionButtonStyle, background: "#7c3aed", borderColor: "#7c3aed" }}
      >
        {linking === "capa" ? "Linking..." : "Attach to CAPA"}
      </button>
    </div>
  );
}

function EvidenceGallery({ items, selectedEvidenceId, onSelect }) {
  return (
    <div style={{ ...cardStyle, marginTop: "20px" }}>
      <h3 style={cardTitleStyle}>Evidence Gallery</h3>

      {!items.length ? (
        <p style={subtitleStyle}>No evidence uploaded yet.</p>
      ) : (
        <div style={galleryGridStyle}>
          {items.map((item) => {
            const imageUrl = buildEvidenceFileUrl(item.file_url);
            const selected = item.evidence_id === selectedEvidenceId;

            return (
              <button
                key={item.evidence_id}
                type="button"
                onClick={() => onSelect(item)}
                style={{
                  ...galleryCardStyle,
                  borderColor: selected ? "#2563eb" : "#e5e7eb",
                  background: selected ? "#eff6ff" : "#ffffff",
                }}
              >
                <div style={thumbnailFrameStyle}>
                  {item.mime_type?.startsWith("image/") ? (
                    <img
                      src={imageUrl}
                      alt={item.original_filename}
                      style={{ width: "100%", height: "130px", objectFit: "cover", borderRadius: "10px" }}
                    />
                  ) : (
                    <div style={filePlaceholderStyle}>File</div>
                  )}
                </div>

                <div style={{ marginTop: "10px" }}>
                  <div style={{ fontWeight: 900, color: "#111827" }}>
                    {item.instrument_name || "Unknown instrument"}
                  </div>
                  <div style={smallMutedStyle}>{item.original_filename}</div>
                  <div style={smallMutedStyle}>{item.facility}</div>
                  <div style={smallMutedStyle}>{item.finding_category}</div>
                  <div style={smallMutedStyle}>VR: {item.linked_visual_review_id || "None"}</div>
                  <div style={smallMutedStyle}>INS: {item.linked_inspection_id || "None"}</div>
                  <div style={smallMutedStyle}>CAPA: {item.linked_capa_id || "None"}</div>
                  <div style={{ ...smallMutedStyle, fontFamily: "monospace" }}>{shortenId(item.evidence_id)}</div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Input({ label, value, onChange }) {
  return (
    <label style={labelWrapperStyle}>
      <span style={labelStyle}>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle} />
    </label>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label style={labelWrapperStyle}>
      <span style={labelStyle}>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle}>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function shortenId(id = "") {
  if (id.length <= 18) return id;
  return `${id.slice(0, 10)}...${id.slice(-6)}`;
}

function formatBytes(bytes = 0) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

const sectionWrapper = { marginTop: "28px", border: "1px solid #bae6fd", background: "#f0f9ff", borderRadius: "22px", padding: "22px" };
const titleStyle = { fontSize: "26px", fontWeight: 950, color: "#111827", margin: 0 };
const subtitleStyle = { color: "#6b7280", marginTop: "6px" };
const layoutStyle = { display: "grid", gridTemplateColumns: "minmax(0, 1.1fr) minmax(320px, 0.9fr)", gap: "18px", alignItems: "start" };
const cardStyle = { border: "1px solid #e5e7eb", background: "#ffffff", borderRadius: "18px", padding: "18px", boxShadow: "0 8px 24px rgba(15, 23, 42, 0.06)" };
const cardTitleStyle = { marginTop: 0, fontSize: "20px", fontWeight: 900, color: "#111827" };
const gridStyle = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" };
const uploadBoxStyle = { border: "2px dashed #0284c7", background: "#f0f9ff", borderRadius: "16px", padding: "16px", marginBottom: "16px" };
const fileInputStyle = { marginTop: "10px", width: "100%", border: "1px solid #7dd3fc", borderRadius: "12px", padding: "12px", background: "#ffffff", fontWeight: 800 };
const labelWrapperStyle = { display: "block", marginBottom: "12px" };
const labelStyle = { display: "block", fontSize: "13px", color: "#374151", fontWeight: 900 };
const inputStyle = { marginTop: "6px", width: "100%", border: "1px solid #d1d5db", borderRadius: "12px", padding: "10px", fontSize: "14px", fontFamily: "inherit", boxSizing: "border-box", background: "#ffffff" };
const primaryButtonStyle = { marginTop: "14px", border: "1px solid #0284c7", background: "#0284c7", color: "#ffffff", borderRadius: "12px", padding: "11px 14px", fontWeight: 900, cursor: "pointer" };
const successStyle = { border: "1px solid #86efac", background: "#ecfdf5", color: "#166534", borderRadius: "12px", padding: "12px", fontWeight: 800, marginBottom: "14px" };
const errorStyle = { border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", borderRadius: "12px", padding: "12px", fontWeight: 800, marginBottom: "14px" };
const imageFrameStyle = { minHeight: "260px", border: "1px dashed #93c5fd", background: "#f8fafc", borderRadius: "16px", padding: "12px", display: "flex", alignItems: "center", justifyContent: "center" };
const metaBoxStyle = { marginTop: "12px", border: "1px solid #e5e7eb", background: "#f9fafb", borderRadius: "12px", padding: "12px", color: "#374151", fontSize: "13px", lineHeight: 1.6 };
const linkBoxStyle = { marginTop: "14px", border: "1px solid #bae6fd", background: "#f0f9ff", borderRadius: "14px", padding: "14px" };
const smallActionButtonStyle = { marginBottom: "12px", border: "1px solid #0284c7", background: "#0284c7", color: "#ffffff", borderRadius: "10px", padding: "9px 12px", fontWeight: 900, cursor: "pointer" };
const galleryGridStyle = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" };
const galleryCardStyle = { border: "2px solid #e5e7eb", borderRadius: "16px", padding: "12px", cursor: "pointer", textAlign: "left" };
const thumbnailFrameStyle = { background: "#f8fafc", borderRadius: "12px", overflow: "hidden" };
const filePlaceholderStyle = { height: "130px", display: "flex", alignItems: "center", justifyContent: "center", background: "#f3f4f6", color: "#6b7280", fontWeight: 900 };

const summaryGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "12px",
  marginBottom: "16px",
};

const summaryTileStyle = {
  border: "1px solid #bae6fd",
  background: "#ffffff",
  borderRadius: "14px",
  padding: "14px",
  boxShadow: "0 6px 18px rgba(15, 23, 42, 0.05)",
};

const classificationBoxStyle = {
  marginTop: "14px",
  border: "1px solid #bfdbfe",
  background: "#eff6ff",
  borderRadius: "14px",
  padding: "14px",
};

const statusGridStyle = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "10px",
  marginBottom: "12px",
};

const statusPillStyle = {
  border: "1px solid #dbeafe",
  background: "#ffffff",
  borderRadius: "12px",
  padding: "10px",
};

const smallMutedStyle = { color: "#6b7280", fontSize: "12px", marginTop: "4px" };
