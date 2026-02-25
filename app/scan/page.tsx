"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { Camera, Upload, ArrowLeft, Scan, X, RotateCcw, Image as ImageIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";
import DNASpinner from "@/components/DNASpinner";
import { Suspense } from "react";

function ScanUploadContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const type = searchParams.get("type") || "medicine";
  const [mode, setMode] = useState<"camera" | "upload">("upload");
  const [analyzing, setAnalyzing] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Camera state
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cleanup camera stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  }, []);

  const startCamera = useCallback(async () => {
    setError(null);
    setCapturedImage(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Camera is not available. This feature requires HTTPS or localhost. Try the Upload tab instead.");
      return;
    }

    try {
      // No resolution constraints — negotiating a specific resolution is the primary delay source
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
      });
      streamRef.current = stream;

      // videoRef is always mounted (just hidden when not active), so this is always safe
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        // autoPlay attribute on the <video> handles play() automatically.
        // We only call play() manually as a safety net if autoPlay doesn't fire.
        if (videoRef.current.readyState < 2) {
          await new Promise<void>((resolve) => {
            if (!videoRef.current) { resolve(); return; }
            videoRef.current.oncanplay = () => resolve();
          });
        }
        try { await videoRef.current.play(); } catch { /* AbortError is harmless */ }
      }
      setCameraActive(true);
    } catch (err: any) {
      const msg =
        err?.name === "NotAllowedError"
          ? "Camera permission denied. Please click the camera icon in your browser address bar and allow access, then click Enable Camera."
          : err?.name === "NotFoundError"
            ? "No camera detected on this device. Please use the Upload tab instead."
            : `Camera error: ${err?.message || "unknown"}. Try the Upload tab instead.`;
      setError(msg);
    }
  }, []);

  // Start/stop camera when mode changes
  useEffect(() => {
    if (mode === "camera") {
      startCamera();
    } else {
      stopCamera();
      setCapturedImage(null);
    }
  }, [mode, startCamera, stopCamera]);

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    setCapturedImage(dataUrl);
    stopCamera();

    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], "camera-capture.jpg", { type: "image/jpeg" });
          setSelectedFile(file);
          setPreview(dataUrl);
        }
      },
      "image/jpeg",
      0.9
    );
  }, [stopCamera]);

  const retakePhoto = useCallback(() => {
    setCapturedImage(null);
    setSelectedFile(null);
    setPreview(null);
    startCamera();
  }, [startCamera]);

  const handleFileSelect = (file: File) => {
    if (!file.type.startsWith("image/")) {
      setError("Please select an image file (JPG, PNG, HEIC).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File size must be under 10MB.");
      return;
    }
    setError(null);
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreview(url);
  };

  const clearFile = () => {
    setSelectedFile(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError("Please select or capture an image first.");
      return;
    }

    setAnalyzing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("image", selectedFile);

      const lang = localStorage.getItem("sanjeevani_language") || "en";
      formData.append("language", lang);

      const endpoint = type === "prescription" ? "/api/analyze/prescription" : "/api/analyze/medicine";
      const res = await fetch(endpoint, { method: "POST", credentials: "include", body: formData });
      const data = await res.json();

      if (!res.ok || data.error) {
        setError(data.error || "Analysis failed. Make sure the Python server is running.");
        setAnalyzing(false);
        return;
      }

      sessionStorage.setItem("scanResult", JSON.stringify(data));
      sessionStorage.setItem("scanType", type);

      if (type === "prescription") {
        router.push("/result/prescription");
      } else {
        router.push("/result/medicine");
      }
    } catch (err: any) {
      setError(err.message || "Network error. Is the Python server running?");
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen relative">
      <MandalaBackground />
      {/* Canvas is always hidden — used only for snapshot capture */}
      <canvas ref={canvasRef} className="hidden" />

      {/*
        The <video> element MUST be always present in the DOM so that videoRef.current
        is non-null when startCamera() assigns stream.srcObject.
        Visibility is controlled with CSS (block/hidden), NOT with conditional rendering.
      */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="hidden"   // startCamera will switch this to block via cameraActive state
      />

      <div className="relative z-10 p-6 lg:p-12 max-w-2xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4 mb-10"
        >
          <button
            onClick={() => router.push("/dashboard")}
            className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted transition-colors"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">
              {type === "prescription" ? "Read Prescription" : "Scan Medicine Strip"}
            </h1>
            <p className="text-muted-foreground text-sm">Upload or capture an image to analyze</p>
          </div>
        </motion.div>

        {/* Mode toggle */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex bg-card border border-border rounded-xl p-1 mb-8"
        >
          {[
            { id: "camera" as const, icon: Camera, label: "Camera" },
            { id: "upload" as const, icon: Upload, label: "Upload" },
          ].map((m) => (
            <button
              key={m.id}
              onClick={() => { setMode(m.id); clearFile(); }}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-display font-semibold transition-all ${mode === m.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <m.icon size={16} />
              {m.label}
            </button>
          ))}
        </motion.div>

        {/* Error message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded-xl text-destructive text-sm"
          >
            {error}
          </motion.div>
        )}

        {/* Content — camera section or upload zone */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          {mode === "camera" ? (
            /* ── Camera viewfinder ── */
            <div className="relative aspect-[4/3] bg-forest-deep rounded-2xl border-2 border-border overflow-hidden flex items-center justify-center">
              {/* Captured photo overlay */}
              {capturedImage && (
                <>
                  <img src={capturedImage} alt="Captured" className="absolute inset-0 w-full h-full object-contain" />
                  <button
                    onClick={retakePhoto}
                    className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-5 py-2.5 bg-card/90 backdrop-blur border border-border rounded-xl text-foreground text-sm font-display font-semibold hover:bg-muted transition-colors"
                  >
                    <RotateCcw size={16} />
                    Retake
                  </button>
                </>
              )}

              {/* Live video feed — shown once camera is active */}
              {cameraActive && !capturedImage && (
                <>
                  {/* Mirror the global video element into this viewfinder via a cloned display */}
                  <video
                    ref={(el) => {
                      if (el && streamRef.current) {
                        el.srcObject = streamRef.current;
                        el.play().catch(() => { });
                      }
                    }}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                  {/* Scan corner overlays */}
                  <div className="absolute top-4 left-4 w-12 h-12 border-t-2 border-l-2 border-secondary rounded-tl-lg" style={{ animation: "scanPulse 1.5s ease-in-out infinite" }} />
                  <div className="absolute top-4 right-4 w-12 h-12 border-t-2 border-r-2 border-secondary rounded-tr-lg" style={{ animation: "scanPulse 1.5s ease-in-out infinite 0.2s" }} />
                  <div className="absolute bottom-16 left-4 w-12 h-12 border-b-2 border-l-2 border-secondary rounded-bl-lg" style={{ animation: "scanPulse 1.5s ease-in-out infinite 0.4s" }} />
                  <div className="absolute bottom-16 right-4 w-12 h-12 border-b-2 border-r-2 border-secondary rounded-br-lg" style={{ animation: "scanPulse 1.5s ease-in-out infinite 0.6s" }} />
                  {/* Capture button */}
                  <button
                    onClick={capturePhoto}
                    className="absolute bottom-4 left-1/2 -translate-x-1/2 w-16 h-16 rounded-full border-4 border-white bg-white/20 backdrop-blur hover:bg-white/40 transition-all active:scale-90"
                  >
                    <div className="w-12 h-12 rounded-full bg-white mx-auto" />
                  </button>
                </>
              )}

              {/* Loading/permission state */}
              {!cameraActive && !capturedImage && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
                  <Camera size={48} className="mb-3 opacity-40" />
                  <p className="text-sm">{error ? "Camera unavailable" : "Starting camera..."}</p>
                  <button
                    onClick={startCamera}
                    className="mt-3 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-lg font-display font-semibold"
                  >
                    Enable Camera
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* ── Upload zone ── */
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFileSelect(f);
                }}
              />

              {preview ? (
                <div className="relative aspect-[4/3] rounded-2xl border-2 border-secondary overflow-hidden bg-card">
                  <img src={preview} alt="Selected" className="w-full h-full object-contain" />
                  <button
                    onClick={clearFile}
                    className="absolute top-3 right-3 w-9 h-9 bg-card/90 backdrop-blur border border-border rounded-xl flex items-center justify-center text-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <X size={16} />
                  </button>
                  <div className="absolute bottom-3 left-3 flex items-center gap-2 px-3 py-1.5 bg-card/90 backdrop-blur border border-border rounded-lg">
                    <ImageIcon size={14} className="text-muted-foreground" />
                    <span className="text-xs text-muted-foreground truncate max-w-[200px]">{selectedFile?.name}</span>
                  </div>
                </div>
              ) : (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    const f = e.dataTransfer.files?.[0];
                    if (f) handleFileSelect(f);
                  }}
                  className={`aspect-[4/3] border-2 border-dashed rounded-2xl flex flex-col items-center justify-center transition-all cursor-pointer ${dragOver
                    ? "border-secondary bg-secondary/5"
                    : "border-border hover:border-primary/50 bg-card/50"
                    }`}
                >
                  <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center mb-4">
                    <Upload size={28} className="text-muted-foreground" />
                  </div>
                  <p className="font-display font-semibold text-foreground mb-1">
                    Drag &amp; drop your image here
                  </p>
                  <p className="text-muted-foreground text-sm mb-4">or click to browse files</p>
                  <span className="text-xs text-muted-foreground">
                    Supports JPG, PNG, HEIC &bull; Max 10MB
                  </span>
                </div>
              )}
            </>
          )}
        </motion.div>

        {/* Analyze button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-8"
        >
          <motion.button
            onClick={handleAnalyze}
            disabled={analyzing || !selectedFile}
            whileHover={!analyzing && selectedFile ? { scale: 1.02 } : {}}
            whileTap={!analyzing && selectedFile ? { scale: 0.98 } : {}}
            className="w-full py-4 bg-primary text-primary-foreground font-display font-bold text-lg rounded-xl glow-pulse-saffron disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-3 transition-all"
          >
            {analyzing ? (
              <>
                <DNASpinner />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Scan size={22} />
                <span>Analyze Now</span>
              </>
            )}
          </motion.button>
        </motion.div>
      </div>
    </div>
  );
}

export default function ScanUploadPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <ScanUploadContent />
    </Suspense>
  );
}
