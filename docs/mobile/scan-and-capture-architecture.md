# Scan & Capture Architecture — P18

## Barcode / QR / UDI Scanning

### Client-Side Decode (@zxing/browser)

```javascript
import { BrowserMultiFormatReader } from '@zxing/browser';

const codeReader = new BrowserMultiFormatReader();
const result = await codeReader.decodeOnceFromVideoDevice(undefined, videoElement);
console.log(result.getText());  // decoded barcode/QR value
```

Supported formats: Code 128, Code 39, EAN-13, UPC-A, QR Code, Data Matrix, PDF417 (UDI).

### Server Fallback

When client-side decode fails (low-end device, motion blur, unusual symbology):

```
POST /api/mobile/scan/decode
Body: { image_base64, scan_type, session_id, facility_id }
```

Server uses seeded mock decode in dev/test. Production integration would use a commercial OCR/barcode SDK.

---

## UDI Parsing (GS1 Application Identifiers)

UDI barcodes follow GS1-128 or GS1 DataMatrix encoding:

| AI Code | Field          | Example value        |
|---------|----------------|----------------------|
| 01      | GTIN-14        | 00123456789012       |
| 21      | Serial Number  | SN-A4829B            |
| 17      | Expiration     | 260101 (YYMMDD)      |
| 10      | Lot/Batch      | LOT-2024-001         |

Parsing logic:
```javascript
function parseUDI(rawValue) {
  const groups = {};
  const AI_REGEX = /(\d{2,4})([^(]+)/g;
  const cleaned = rawValue.replace(/[()]/g, match => match === '(' ? '' : '\x1D');
  let match;
  while ((match = AI_REGEX.exec(cleaned)) !== null) {
    groups[match[1]] = match[2].trim();
  }
  return {
    gtin: groups['01'],
    serial: groups['21'],
    expiration: groups['17'],
    lot: groups['10'],
  };
}
```

---

## KeyDot

KeyDot barcodes are proprietary image-based identifiers. Capture and decode:

1. Camera captures image of the KeyDot mark.
2. Image is compressed to < 2MB via `canvas.toBlob(cb, 'image/jpeg', 0.85)`.
3. Base64-encoded and POSTed to `POST /api/mobile/scan/decode` with `scan_type=keydot`.
4. Server returns `decoded_value` (instrument ID) and `confidence_score`.
5. Client uses returned `instrument_id_resolved` to pre-fill inspection form.

---

## Camera Constraints

```javascript
const constraints = {
  video: {
    facingMode: "environment",        // rear camera preferred
    width: { ideal: 1920, min: 1280 },
    height: { ideal: 1080, min: 720 },
    focusMode: "continuous",          // auto-focus for barcodes
  }
};
const stream = await navigator.mediaDevices.getUserMedia(constraints);
```

If rear camera unavailable (tablet/desktop), falls back to `facingMode: "user"` with a warning.

---

## Borescope Integration

### Current (Phase 1)
USB borescopes that enumerate as a standard camera device appear via `MediaDevices.enumerateDevices()`. Users select the borescope from a device picker:

```javascript
const devices = await navigator.mediaDevices.enumerateDevices();
const videoInputs = devices.filter(d => d.kind === 'videoinput');
// Display picker for user to select borescope vs. built-in camera
```

### Future (Phase 2)
- **WebUSB**: `navigator.usb.requestDevice({ filters: [...] })` for proprietary USB borescopes.
- **WebBluetooth**: `navigator.bluetooth.requestDevice(...)` for wireless borescopes.
- Available only in Chromium-based browsers (Chrome, Edge). iOS Safari not supported.
- React Native wrapper would use `react-native-usb` or manufacturer SDK for full native support.
