"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Volume2, VolumeX, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";

interface MedicineData {
  medicine_name: string;
  active_salts: string[];
  dosage_strength: string;
  is_high_dosage: boolean;
  dosage_info: string;
  conditions: string[];
  what_it_does: string;
  suitable_age_group: string;
  advice: string;
  is_medicine: boolean;
}

const MedicineResult = () => {
  const router = useRouter();
  const [medicine, setMedicine] = useState<MedicineData | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [howItWorksOpen, setHowItWorksOpen] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("scanResult");
      if (!raw) {
        router.push("/dashboard");
        return;
      }
      const parsed = JSON.parse(raw);
      const d = parsed.data || parsed;
      setMedicine(d);
      if (parsed.audio_url) setAudioUrl(parsed.audio_url);
    } catch {
      router.push("/dashboard");
    }
  }, [router]);

  const toggleAudio = () => {
    if (!audioUrl) return;
    if (!audioRef.current) {
      audioRef.current = new Audio(audioUrl);
      audioRef.current.onended = () => setPlaying(false);
    }
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
    } else {
      audioRef.current.play();
      setPlaying(true);
    }
  };

  const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.1 } } };
  const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

  if (!medicine) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <MandalaBackground />
      <div className="relative z-10 p-6 lg:p-12 max-w-2xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-8">
          <button onClick={() => router.push("/dashboard")} className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted transition-colors">
            <ArrowLeft size={18} />
          </button>
          <h1 className="font-display text-xl font-bold text-foreground">Medicine Result</h1>
          {audioUrl && (
            <button
              onClick={toggleAudio}
              className={`ml-auto w-10 h-10 rounded-xl flex items-center justify-center text-primary-foreground transition-all ${
                playing ? "bg-destructive" : "bg-primary glow-pulse-saffron"
              }`}
            >
              {playing ? <VolumeX size={18} /> : <Volume2 size={18} />}
            </button>
          )}
        </motion.div>

        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-5">
          {/* Medicine name */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-1">Medicine</p>
            <h2 className="font-display text-3xl font-bold text-foreground glow-pulse-cyan inline-block px-1">{medicine.medicine_name}</h2>
            {medicine.dosage_strength && (
              <p className="text-muted-foreground text-sm mt-1">Strength: {medicine.dosage_strength}</p>
            )}
          </motion.div>

          {/* Salts */}
          {medicine.active_salts?.length > 0 && (
            <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
              <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-3">Active Ingredients</p>
              <div className="flex flex-wrap gap-2">
                {medicine.active_salts.map((s) => (
                  <span key={s} className="px-4 py-1.5 rounded-full bg-secondary/15 text-secondary text-sm font-semibold border border-secondary/30">
                    {s}
                  </span>
                ))}
              </div>
            </motion.div>
          )}

          {/* Dosage strength */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-3">Dosage Strength</p>
            <div className="flex items-center gap-4">
              <div className={`w-16 h-16 rounded-full border-4 flex items-center justify-center ${
                medicine.is_high_dosage ? "border-red-500" : "border-green-500"
              }`}>
                {medicine.is_high_dosage ? (
                  <AlertTriangle className="text-red-500" size={28} />
                ) : (
                  <CheckCircle className="text-green-500" size={28} />
                )}
              </div>
              <div>
                <p className="font-display font-bold text-foreground text-lg">{medicine.is_high_dosage ? "High Dosage" : "Normal Dosage"}</p>
                <p className="text-muted-foreground text-sm">{medicine.dosage_info || "Standard therapeutic dose"}</p>
              </div>
            </div>
          </motion.div>

          {/* Conditions */}
          {medicine.conditions?.length > 0 && (
            <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
              <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-3">Conditions Treated</p>
              <div className="flex flex-wrap gap-2">
                {medicine.conditions.map((c) => (
                  <span key={c} className="px-3 py-1.5 rounded-lg bg-muted text-foreground text-sm">{c}</span>
                ))}
              </div>
            </motion.div>
          )}

          {/* How it works accordion */}
          {medicine.what_it_does && (
            <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl overflow-hidden">
              <button
                onClick={() => setHowItWorksOpen(!howItWorksOpen)}
                className="w-full flex items-center justify-between p-6"
              >
                <p className="text-xs text-muted-foreground font-display uppercase tracking-wider">How It Works</p>
                {howItWorksOpen ? <ChevronUp size={18} className="text-muted-foreground" /> : <ChevronDown size={18} className="text-muted-foreground" />}
              </button>
              {howItWorksOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="px-6 pb-6"
                >
                  <p className="text-foreground text-sm leading-relaxed">{medicine.what_it_does}</p>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* Age group */}
          {medicine.suitable_age_group && (
            <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
              <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-3">Suitable Age Group</p>
              <p className="font-display font-bold text-foreground">{medicine.suitable_age_group}</p>
            </motion.div>
          )}

          {/* Advice */}
          {medicine.advice && (
            <motion.div variants={fadeUp} className="bg-card border border-primary/30 rounded-2xl p-6">
              <p className="text-xs text-primary font-display uppercase tracking-wider mb-3">Advice</p>
              <p className="text-foreground text-sm leading-relaxed">{medicine.advice}</p>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default MedicineResult;
