import { useEffect, useRef, useState, useCallback } from "react";
import { Camera, CameraOff, X } from "lucide-react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

interface BarcodeScannerProps {
  onDetected: (value: string, format: string) => void;
  onClose: () => void;
}

declare global {
  interface Window {
    BarcodeDetector?: new (opts?: { formats: string[] }) => {
      detect(source: ImageBitmapSource): Promise<{ rawValue: string; format: string }[]>;
    };
  }
}

const SUPPORTED_FORMATS = [
  "qr_code",
  "code_128",
  "code_39",
  "ean_13",
  "ean_8",
  "data_matrix",
  "pdf417",
];

export function BarcodeScanner({ onDetected, onClose }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const [error, setError] = useState<string>("");
  const [scanning, setScanning] = useState(false);
  const [detectorSupported, setDetectorSupported] = useState<boolean | null>(null);

  const stopStream = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    setDetectorSupported(typeof window.BarcodeDetector !== "undefined");
    return stopStream;
  }, [stopStream]);

  const startCamera = useCallback(async () => {
    setError("");
    setScanning(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      if (!window.BarcodeDetector) {
        setError("BarcodeDetector API not available in this browser. Use Chrome 83+ or Edge 83+. You can also type the value manually below.");
        return;
      }

      const detector = new window.BarcodeDetector({ formats: SUPPORTED_FORMATS });
      setScanning(true);

      const scan = async () => {
        if (!videoRef.current || videoRef.current.readyState < 2) {
          rafRef.current = requestAnimationFrame(scan);
          return;
        }
        try {
          const results = await detector.detect(videoRef.current);
          if (results.length > 0) {
            const { rawValue, format } = results[0];
            stopStream();
            setScanning(false);
            onDetected(rawValue, format);
            return;
          }
        } catch {
          // frame not ready, continue
        }
        rafRef.current = requestAnimationFrame(scan);
      };
      rafRef.current = requestAnimationFrame(scan);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Camera access denied. Please allow camera permission and try again.");
    }
  }, [onDetected, stopStream]);

  const handleStop = () => {
    stopStream();
    setScanning(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Scan Barcode / QR / UDI</h3>
            <p className="text-xs text-slate-500 mt-0.5">Point camera at the instrument identifier</p>
          </div>
          <button
            onClick={() => { stopStream(); onClose(); }}
            className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Camera viewport */}
        <div className="relative bg-black aspect-video">
          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            muted
            playsInline
          />
          {scanning && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-48 h-48 border-2 border-white rounded-lg opacity-70" />
              <div className="absolute bottom-4 left-0 right-0 text-center">
                <span className="text-xs text-white bg-black/50 px-3 py-1 rounded-full">
                  Scanning…
                </span>
              </div>
            </div>
          )}
          {!scanning && !error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Camera className="h-12 w-12 text-white/40" />
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="p-4 space-y-3">
          {error && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {detectorSupported === false && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              BarcodeDetector API is not supported in this browser. Use Chrome 83+ or Edge. You can type the value manually.
            </p>
          )}

          <div className="flex gap-2">
            {!scanning ? (
              <Button onClick={startCamera} className="flex-1 gap-2">
                <Camera className="h-4 w-4" /> Start Camera
              </Button>
            ) : (
              <Button variant="outline" onClick={handleStop} className="flex-1 gap-2">
                <CameraOff className="h-4 w-4" /> Stop
              </Button>
            )}
            <Button variant="outline" onClick={() => { stopStream(); onClose(); }}>
              Cancel
            </Button>
          </div>

          <p className="text-xs text-slate-400 text-center">
            Supports QR code, Code 128, EAN-13, Data Matrix, PDF417
          </p>
        </div>
      </div>
    </div>
  );
}
