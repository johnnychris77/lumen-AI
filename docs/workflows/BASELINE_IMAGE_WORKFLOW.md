# Baseline Image Workflow

How a vendor or manufacturer attaches a baseline image — borescope capture is now
an inline source, and **baseline approval governance is unchanged**.

## Flow

```
Baseline submission / Create-or-update baseline
  → Add Baseline Image
      ├─ Capture from Borescope   (live capture, inline)
      ├─ Upload Existing Image
      └─ Drag & Drop
  → image attaches to the baseline record
  → Continue submission
  → Verification / Review → Approval per existing governance
```

Attaching or capturing a baseline image does **not** approve a baseline. The
existing states are preserved:

```
draft → submitted → pending_review → approved | rejected
```

Only an authorized reviewer moves a baseline to `approved`. Image acquisition
never sets or shortcuts approval status.

## Component

`components/ui/baseline-image-upload.tsx` (`BaselineImageUpload`) gained a
source picker in its empty state: **Capture from Borescope** / **Upload Existing
Image** / **Drag & Drop**. A borescope capture is handed to the component's
existing `handleFile()` — the **same** upload call to the same baseline image
endpoint. No new or alternate upload path is introduced, so tenant isolation,
authorization, validation, metadata, and audit behavior are identical to the
previous upload-only flow.

`BaselineImageUpload` is reused by:

- `BaselineImageUploadPage.tsx` ("Upload Baseline Image" — vendor / manufacturer),
- `Dashboard.tsx`, `InstrumentPassportPage.tsx`, `TrainingCenterPage.tsx`.

Because the borescope was added inside the shared component, every one of these
surfaces gains live capture with no per-page changes.

## Authorization

Server-side authorization on the baseline image endpoint is authoritative and
unchanged. The component never trusts client-supplied tenant or role values; a
hidden button is never treated as authorization. Vendors can only modify their
allowed submissions; manufacturers only authorized records; reviewers retain
their permissions.

## Legacy manufacturer panel

`ManufacturerBaselinePanel.tsx` is a separate, older inline-styled surface that
uploads arbitrary baseline **files** (not only images) and carries its own
pre-existing auth handling. It is intentionally **left unchanged** in this sprint
to avoid touching that auth path and to keep scope to the image-acquisition UX.
The modern, image-based baseline flow (`BaselineImageUpload`) is where borescope
capture is embedded.
