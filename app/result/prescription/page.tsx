"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Volume2, VolumeX, ChevronDown, ChevronUp, Sun, Sunset, Moon, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";

interface Medicine {
  name: string;
  dosage: string;
  frequency: string;
  timing: string;
  meal_relation: string;
  active_salts: string[];
  alternatives: string[];
  purpose: string;
  order?: number;
}

interface PrescriptionData {
  medicines: Medicine[];
  overall_advice?: string;
}

const timingToSlots = (timing: string): string[] => {
  const t = timing?.toLowerCase() || "";
  const slots: string[] = [];
  if (t.includes("morning") || t.includes("breakfast") || t.includes("bd") || t.includes("twice") || t.includes("tds") || t.includes("thrice")) slots.push("Morning");
  if (t.includes("afternoon") || t.includes("lunch") || t.includes("tds") || t.includes("thrice")) slots.push("Afternoon");
  if (t.includes("night") || t.includes("dinner") || t.includes("bedtime") || t.includes("bd") || t.includes("twice") || t.includes("tds") || t.includes("thrice")) slots.push("Night");
  if (slots.length === 0) slots.push("As directed");
  return slots;
};

const timingIcons: Record<string, React.ReactNode> = {
  Morning: <Sun size={12} />,
  Afternoon: <Sunset size={12} />,
  Night: <Moon size={12} />,
  "As directed": null,
};

const PrescriptionResult = () => {
  const router = useRouter();
  const [prescription, setPrescription] = useState<PrescriptionData | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
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
      setPrescription(d);

      // Build audio source: prefer embedded base64, fall back to URL
      let src: string | null = null;
      if (parsed.audio_b64) {
        src = `data:audio/mpeg;base64,${parsed.audio_b64}`;
      } else if (parsed.audio_url) {
        src = parsed.audio_url;
      }
      if (src) {
        setAudioUrl(src);
        const audio = new Audio(src);
        audioRef.current = audio;
        audio.onended = () => setPlaying(false);
        setTimeout(() => {
          audio.play().catch(() => {
            // Autoplay may be blocked by browser policy — user can still click the button
          });
          setPlaying(true);
        }, 800);
      }
    } catch {
      router.push("/dashboard");
    }
  }, [router]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

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
      // Reset to start so the user can replay from the beginning
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(() => { });
      setPlaying(true);
    }
  };

  const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.1 } } };
  const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

  if (!prescription) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const medicines = prescription.medicines || [];

  return (
    <div className="min-h-screen relative">
      <MandalaBackground />
      <div className="relative z-10 p-6 lg:p-12 max-w-2xl mx-auto">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-8">
          <button onClick={() => router.push("/dashboard")} className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted transition-colors">
            <ArrowLeft size={18} />
          </button>
          <h1 className="font-display text-xl font-bold text-foreground">Prescription Result</h1>
          {audioUrl && (
            <button
              onClick={toggleAudio}
              className={`ml-auto w-10 h-10 rounded-xl flex items-center justify-center text-primary-foreground transition-all ${playing ? "bg-destructive" : "bg-primary glow-pulse-saffron"
                }`}
            >
              {playing ? <VolumeX size={18} /> : <Volume2 size={18} />}
            </button>
          )}
        </motion.div>

        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-5">
          {/* Summary card */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-1">Prescription Summary</p>
            <h2 className="font-display text-xl font-bold text-foreground">
              {medicines.length} Medicine{medicines.length !== 1 ? "s" : ""} Found
            </h2>
          </motion.div>

          {/* Medicine rows */}
          {medicines.map((med, idx) => {
            const slots = timingToSlots(med.timing || med.frequency || "");
            return (
              <motion.div key={idx} variants={fadeUp} className="bg-card border border-border rounded-2xl overflow-hidden">
                <div className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-display font-bold text-foreground">{med.name}</h3>
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-lg whitespace-nowrap ml-2">{med.dosage}</span>
                  </div>

                  {/* Timing chips */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    {slots.map((t) => (
                      <span key={t} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/15 text-primary text-xs font-semibold border border-primary/30">
                        {timingIcons[t]}
                        {t}
                      </span>
                    ))}
                    {med.meal_relation && (
                      <span className="px-3 py-1 rounded-full bg-secondary/15 text-secondary text-xs font-semibold border border-secondary/30">
                        {med.meal_relation}
                      </span>
                    )}
                  </div>

                  <p className="text-muted-foreground text-sm mb-1">{med.frequency}</p>
                  <p className="text-muted-foreground text-sm">{med.purpose}</p>

                  {/* Active salts */}
                  {med.active_salts?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {med.active_salts.map((s) => (
                        <span key={s} className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">{s}</span>
                      ))}
                    </div>
                  )}

                  {/* Alternatives toggle */}
                  {med.alternatives?.length > 0 && (
                    <button
                      onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                      className="flex items-center gap-1 mt-3 text-secondary text-xs font-display font-semibold hover:underline"
                    >
                      Alternatives
                      {expandedIdx === idx ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                  )}
                </div>

                {expandedIdx === idx && med.alternatives?.length > 0 && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    className="px-6 pb-5 border-t border-border pt-4"
                  >
                    <div className="flex flex-wrap gap-2">
                      {med.alternatives.map((a) => (
                        <span key={a} className="px-3 py-1.5 rounded-lg bg-secondary/10 text-secondary text-sm border border-secondary/20">{a}</span>
                      ))}
                    </div>
                  </motion.div>
                )}
              </motion.div>
            );
          })}

          {/* Overall advice */}
          {prescription.overall_advice && (
            <motion.div variants={fadeUp} className="bg-card border border-primary/30 rounded-2xl p-6">
              <p className="text-xs text-primary font-display uppercase tracking-wider mb-3">Advice</p>
              <p className="text-foreground text-sm leading-relaxed">{prescription.overall_advice}</p>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default PrescriptionResult;
