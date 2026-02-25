"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft, ChevronDown, ChevronUp,
  Sun, Sunset, Moon, Loader2, AlertTriangle, Info, Clock, Pill,
  Play, Pause, Volume2
} from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";

interface Medicine {
  name: string;
  dosage: string;
  form?: string;
  frequency: string;
  timing: string;
  duration?: string;
  meal_relation: string;
  active_salts: string[];
  alternatives: string[];
  purpose: string;
  side_effects?: string[];
  food_interaction?: string;
  warnings?: string;
  is_antibiotic?: boolean;
  special_instructions?: string;
  order?: number;
}

interface PrescriptionData {
  medicines: Medicine[];
  interactions?: string[];
  overall_advice?: string;
  overall_advice_en?: string;  // English version for bilingual display
  patient_info?: { name?: string; age?: string; date?: string };
  doctor_info?: { name?: string; qualification?: string };
  diagnosis?: string | null;
  diet_advice?: string;
  follow_up?: string;
}

const timingToSlots = (timing: string): string[] => {
  const t = timing?.toLowerCase() || "";
  const slots: string[] = [];
  if (t.includes("morning") || t.includes("breakfast") || t.includes("bd") || t.includes("twice") || t.includes("tds") || t.includes("thrice") || t.includes("three")) slots.push("Morning");
  if (t.includes("afternoon") || t.includes("lunch") || t.includes("tds") || t.includes("thrice") || t.includes("three")) slots.push("Afternoon");
  if (t.includes("night") || t.includes("dinner") || t.includes("bedtime") || t.includes("bd") || t.includes("twice") || t.includes("tds") || t.includes("thrice") || t.includes("three")) slots.push("Night");
  if (t.includes("needed") || t.includes("sos") || t.includes("required")) slots.push("As Needed");
  if (slots.length === 0) slots.push("As directed");
  return slots;
};

const timingIcons: Record<string, React.ReactNode> = {
  Morning: <Sun size={12} />,
  Afternoon: <Sunset size={12} />,
  Night: <Moon size={12} />,
  "As Needed": <Clock size={12} />,
  "As directed": null,
};

/** Format seconds → m:ss */
const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

const PrescriptionResult = () => {
  const router = useRouter();
  const [prescription, setPrescription] = useState<PrescriptionData | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("scanResult");
      if (!raw) { router.push("/dashboard"); return; }
      const parsed = JSON.parse(raw);
      const d = parsed.data || parsed;
      setPrescription(d);

      let src: string | null = null;
      if (parsed.audio_b64) src = `data:audio/mpeg;base64,${parsed.audio_b64}`;
      else if (parsed.audio_url) src = parsed.audio_url;

      if (src) {
        setAudioUrl(src);
        const audio = new Audio(src);
        audioRef.current = audio;
        audio.onloadedmetadata = () => setDuration(audio.duration);
        audio.onended = () => {
          setPlaying(false);
          setCurrentTime(0);
          if (rafRef.current) cancelAnimationFrame(rafRef.current);
        };
        // Auto-play TTS on result load
        audio.play()
          .then(() => {
            setPlaying(true);
            rafRef.current = requestAnimationFrame(tickProgress);
          })
          .catch((e) => console.log("Autoplay blocked/failed:", e));
      }
    } catch { router.push("/dashboard"); }
  }, [router]);

  useEffect(() => {
    return () => {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const tickProgress = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      rafRef.current = requestAnimationFrame(tickProgress);
    }
  };

  const toggleAudio = () => {
    if (!audioUrl) return;
    if (!audioRef.current) {
      audioRef.current = new Audio(audioUrl);
      audioRef.current.onloadedmetadata = () => setDuration(audioRef.current!.duration);
      audioRef.current.onended = () => {
        setPlaying(false);
        setCurrentTime(0);
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
      };
    }
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    } else {
      audioRef.current.play().catch(() => { });
      setPlaying(true);
      rafRef.current = requestAnimationFrame(tickProgress);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const t = parseFloat(e.target.value);
    if (audioRef.current) audioRef.current.currentTime = t;
    setCurrentTime(t);
  };

  const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } };
  const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.35 } } };

  if (!prescription) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const medicines = prescription.medicines || [];
  const pi = prescription.patient_info || {};
  const di = prescription.doctor_info || {};

  return (
    <div className="min-h-screen relative">
      <MandalaBackground />
      <div className="relative z-10 p-6 lg:p-12 max-w-2xl mx-auto">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-6">
          <button onClick={() => router.push("/dashboard")} className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted transition-colors">
            <ArrowLeft size={18} />
          </button>
          <div className="flex-1">
            <h1 className="font-display text-xl font-bold text-foreground">Prescription Result</h1>
            {(pi.name || pi.date) && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {pi.name && `For ${pi.name}`}{pi.name && pi.date && " · "}{pi.date}
              </p>
            )}
          </div>
        </motion.div>

        {/* Audio Player Bar */}
        {audioUrl && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="mb-6 bg-card border border-border rounded-2xl px-4 py-3 flex items-center gap-3"
          >
            <button
              onClick={toggleAudio}
              className={`w-10 h-10 rounded-xl flex items-center justify-center text-primary-foreground shrink-0 transition-all ${playing ? "bg-primary" : "bg-primary glow-pulse-saffron"}`}
            >
              {playing ? <Pause size={16} /> : <Play size={16} />}
            </button>
            <Volume2 size={14} className="text-muted-foreground shrink-0" />
            <div className="flex-1 flex flex-col gap-1">
              <input
                type="range"
                min={0}
                max={duration || 100}
                step={0.1}
                value={currentTime}
                onChange={handleSeek}
                className="w-full h-1.5 rounded-full accent-primary cursor-pointer"
                style={{ background: `linear-gradient(to right, var(--primary) ${duration ? (currentTime / duration) * 100 : 0}%, var(--muted) 0%)` }}
              />
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>{fmt(currentTime)}</span>
                <span className="text-xs text-muted-foreground font-display font-medium">Audio Summary</span>
                <span>{fmt(duration)}</span>
              </div>
            </div>
          </motion.div>
        )}

        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-4">

          {/* Summary card */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-5">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-1">Prescription Summary</p>
                <h2 className="font-display text-xl font-bold text-foreground">
                  {medicines.length} Medicine{medicines.length !== 1 ? "s" : ""} Found
                </h2>
                {prescription.diagnosis && (
                  <p className="text-sm text-muted-foreground mt-1">Diagnosis: <span className="text-foreground font-medium">{prescription.diagnosis}</span></p>
                )}
              </div>
              {(di.name || di.qualification) && (
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Prescribed by</p>
                  {di.name && <p className="text-sm font-semibold text-foreground">{di.name}</p>}
                  {di.qualification && <p className="text-xs text-muted-foreground">{di.qualification}</p>}
                </div>
              )}
            </div>
          </motion.div>

          {/* Drug Interactions */}
          {prescription.interactions && prescription.interactions.length > 0 && (
            <motion.div variants={fadeUp} className="bg-destructive/10 border border-destructive/20 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={18} className="text-destructive shrink-0" />
                <h3 className="font-display font-bold text-destructive text-sm uppercase tracking-wider">Drug Interactions Warning</h3>
              </div>
              <ul className="list-disc list-outside ml-5 space-y-1 text-destructive/90 text-sm">
                {prescription.interactions.map((interaction, idx) => (
                  <li key={idx} className="leading-relaxed">{interaction}</li>
                ))}
              </ul>
            </motion.div>
          )}

          {/* Medicine cards */}
          {medicines.map((med, idx) => {
            const slots = timingToSlots(med.timing || med.frequency || "");
            const isOpen = expandedIdx === idx;
            return (
              <motion.div key={idx} variants={fadeUp} className="bg-card border border-border rounded-2xl overflow-hidden">
                <div className="p-5">
                  {/* Name + antibiotic badge + dosage */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Pill size={15} className="text-primary shrink-0" />
                      <h3 className="font-display font-bold text-foreground">{med.name}</h3>
                      {med.is_antibiotic && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-500 border border-amber-500/30 font-semibold">ANTIBIOTIC</span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {med.dosage && <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-lg">{med.dosage}</span>}
                      {med.form && <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-lg">{med.form}</span>}
                    </div>
                  </div>

                  {/* Time chips */}
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
                    {med.duration && (
                      <span className="flex items-center gap-1 px-3 py-1 rounded-full bg-muted text-muted-foreground text-xs font-semibold">
                        <Clock size={11} />
                        {med.duration}
                      </span>
                    )}
                  </div>

                  <p className="text-muted-foreground text-sm mb-1">{med.frequency}</p>
                  <p className="text-foreground/80 text-sm leading-relaxed">{med.purpose}</p>

                  {/* Active salts */}
                  {med.active_salts?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {med.active_salts.map((s) => (
                        <span key={s} className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">{s}</span>
                      ))}
                    </div>
                  )}

                  {/* Antibiotic warning */}
                  {med.is_antibiotic && (
                    <div className="mt-3 flex items-start gap-2 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
                      <AlertTriangle size={13} className="text-amber-500 mt-0.5 shrink-0" />
                      <p className="text-xs text-amber-600 dark:text-amber-400">Complete the full course even if you feel better. Do not stop early.</p>
                    </div>
                  )}

                  {/* Expand toggle */}
                  <button
                    onClick={() => setExpandedIdx(isOpen ? null : idx)}
                    className="flex items-center gap-1 mt-3 text-secondary text-xs font-display font-semibold hover:underline"
                  >
                    {isOpen ? "Show less" : "Side effects & details"}
                    {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>

                {/* Expanded section */}
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    className="px-5 pb-5 border-t border-border pt-4 space-y-4"
                  >
                    {/* Side effects */}
                    {med.side_effects && med.side_effects.length > 0 && (
                      <div>
                        <p className="text-xs font-display font-semibold text-muted-foreground uppercase tracking-wider mb-2">Common Side Effects</p>
                        <div className="flex flex-wrap gap-1.5">
                          {med.side_effects.map((s) => (
                            <span key={s} className="text-xs px-2.5 py-1 rounded-full bg-destructive/10 text-destructive border border-destructive/20">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Food interaction */}
                    {med.food_interaction && (
                      <div className="flex items-start gap-2 p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20">
                        <Info size={13} className="text-blue-500 mt-0.5 shrink-0" />
                        <p className="text-xs text-blue-600 dark:text-blue-400">{med.food_interaction}</p>
                      </div>
                    )}

                    {/* Warnings */}
                    {med.warnings && (
                      <div className="flex items-start gap-2 p-2.5 rounded-xl bg-orange-500/10 border border-orange-500/20">
                        <AlertTriangle size={13} className="text-orange-500 mt-0.5 shrink-0" />
                        <p className="text-xs text-orange-600 dark:text-orange-400">{med.warnings}</p>
                      </div>
                    )}

                    {/* Special instructions */}
                    {med.special_instructions && (
                      <p className="text-xs text-muted-foreground italic">{med.special_instructions}</p>
                    )}

                    {/* Alternatives */}
                    {med.alternatives?.length > 0 && (
                      <div>
                        <p className="text-xs font-display font-semibold text-muted-foreground uppercase tracking-wider mb-2">Alternatives</p>
                        <div className="flex flex-wrap gap-2">
                          {med.alternatives.map((a) => (
                            <span key={a} className="px-3 py-1.5 rounded-lg bg-secondary/10 text-secondary text-sm border border-secondary/20">{a}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </motion.div>
            );
          })}

          {/* Daily schedule — translated text matches audio exactly */}
          {prescription.overall_advice && (
            <motion.div variants={fadeUp} className="bg-card border border-primary/30 rounded-2xl p-5 space-y-3">
              <p className="text-xs text-primary font-display uppercase tracking-wider">Daily Schedule</p>
              <p className="text-foreground text-sm leading-relaxed whitespace-pre-line">{prescription.overall_advice}</p>
              {prescription.overall_advice_en && prescription.overall_advice_en !== prescription.overall_advice && (
                <div className="border-t border-border/50 pt-3">
                  <p className="text-[10px] text-muted-foreground font-display uppercase tracking-wider mb-1">In English</p>
                  <p className="text-foreground/70 text-sm leading-relaxed whitespace-pre-line">{prescription.overall_advice_en}</p>
                </div>
              )}
            </motion.div>
          )}

          {/* Diet advice */}
          {prescription.diet_advice && (
            <motion.div variants={fadeUp} className="bg-card border border-secondary/30 rounded-2xl p-5">
              <p className="text-xs text-secondary font-display uppercase tracking-wider mb-2">Diet Advice</p>
              <p className="text-foreground/80 text-sm leading-relaxed">{prescription.diet_advice}</p>
            </motion.div>
          )}

          {/* Follow up */}
          {prescription.follow_up && (
            <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-5">
              <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-2">Follow Up</p>
              <p className="text-foreground/80 text-sm leading-relaxed">{prescription.follow_up}</p>
            </motion.div>
          )}

          {/* Disclaimer */}
          <motion.div variants={fadeUp} className="p-4 rounded-xl bg-muted/50 border border-border">
            <p className="text-xs text-muted-foreground text-center leading-relaxed">
              ⚕️ This is AI-generated information for reference only. Always follow your doctor&apos;s instructions. Consult your physician before making any changes to your medication.
            </p>
          </motion.div>

        </motion.div>
      </div>
    </div>
  );
};

export default PrescriptionResult;
