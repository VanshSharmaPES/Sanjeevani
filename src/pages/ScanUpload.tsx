import { useState } from "react";
import { motion } from "framer-motion";
import { Camera, Upload, ArrowLeft, Scan } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import MandalaBackground from "@/components/MandalaBackground";
import DNASpinner from "@/components/DNASpinner";

const ScanUpload = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const type = searchParams.get("type") || "medicine";
  const [mode, setMode] = useState<"camera" | "upload">("upload");
  const [analyzing, setAnalyzing] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleAnalyze = () => {
    setAnalyzing(true);
    setTimeout(() => {
      if (type === "prescription") {
        navigate("/result/prescription");
      } else {
        navigate("/result/medicine");
      }
    }, 2500);
  };

  return (
    <div className="min-h-screen relative">
      <MandalaBackground />

      <div className="relative z-10 p-6 lg:p-12 max-w-2xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4 mb-10"
        >
          <button
            onClick={() => navigate("/dashboard")}
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
              onClick={() => setMode(m.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-display font-semibold transition-all ${
                mode === m.id
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <m.icon size={16} />
              {m.label}
            </button>
          ))}
        </motion.div>

        {/* Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          {mode === "camera" ? (
            /* Camera viewfinder */
            <div className="relative aspect-[4/3] bg-forest-deep rounded-2xl border-2 border-border overflow-hidden flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <Camera size={48} className="mx-auto mb-3 opacity-40" />
                <p className="text-sm">Camera access required</p>
                <p className="text-xs mt-1">Tap to enable camera</p>
              </div>

              {/* Scan corners */}
              <div className="absolute top-4 left-4 w-12 h-12 border-t-2 border-l-2 border-secondary rounded-tl-lg" style={{ animation: "scanPulse 1.5s ease-in-out infinite" }} />
              <div className="absolute top-4 right-4 w-12 h-12 border-t-2 border-r-2 border-secondary rounded-tr-lg" style={{ animation: "scanPulse 1.5s ease-in-out infinite 0.2s" }} />
              <div className="absolute bottom-4 left-4 w-12 h-12 border-b-2 border-l-2 border-secondary rounded-bl-lg" style={{ animation: "scanPulse 1.5s ease-in-out infinite 0.4s" }} />
              <div className="absolute bottom-4 right-4 w-12 h-12 border-b-2 border-r-2 border-secondary rounded-br-lg" style={{ animation: "scanPulse 1.5s ease-in-out infinite 0.6s" }} />
            </div>
          ) : (
            /* Upload zone */
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); }}
              className={`aspect-[4/3] border-2 border-dashed rounded-2xl flex flex-col items-center justify-center transition-all cursor-pointer ${
                dragOver
                  ? "border-secondary bg-secondary/5"
                  : "border-border hover:border-primary/50 bg-card/50"
              }`}
            >
              <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center mb-4">
                <Upload size={28} className="text-muted-foreground" />
              </div>
              <p className="font-display font-semibold text-foreground mb-1">
                Drag & drop your image here
              </p>
              <p className="text-muted-foreground text-sm mb-4">or click to browse files</p>
              <span className="text-xs text-muted-foreground">
                Supports JPG, PNG, HEIC • Max 10MB
              </span>
            </div>
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
            disabled={analyzing}
            whileHover={!analyzing ? { scale: 1.02 } : {}}
            whileTap={!analyzing ? { scale: 0.98 } : {}}
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
};

export default ScanUpload;
