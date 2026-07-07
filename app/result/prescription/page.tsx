"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft, ChevronDown, ChevronUp,
  Sun, Sunset, Moon, Loader2, AlertTriangle, Info, Clock, Pill,
  Play, Pause, Volume2, Video, RotateCcw
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
  audio_b64?: string;
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
  ocr_hash?: string;
}

interface VideoGuideResult {
  success: boolean;
  medicineName: string;
  videoUrl: string;
  durationSeconds: number;
  warnings?: string[];
  error?: string;
}

interface VideoAssetFailure {
  medicineName?: string;
  routeTemplate?: string;
  assetType?: string;
  stage?: string;
  reason?: string;
}

const VIDEO_COPY_EN = {
  pageSubtitle: "Split-screen patient instruction video",
  approvedDemo: "Approved human demonstration template video",
  packageImage: "Medicine package image",
  productImage: "Dosage form / strip image",
  caption: "Caption",
  medicine: "Medicine",
  activeIngredients: "Active ingredients",
  dose: "Dose",
  timing: "Timing",
  frequency: "Frequency",
  duration: "Duration",
  doctorNote: "Doctor note",
  followPrescription: "Follow your doctor's prescription.",
  noDoseChange: "Do not change dosage without medical advice.",
  professionalAdministration: "Administer only by a qualified healthcare professional.",
  asPrescribed: "As prescribed",
  templateProfessionalOnly: "Healthcare professional administration",
  templateEyeDrops: "Human demonstration: applying eye drops",
  templateEarDrops: "Human demonstration: applying ear drops",
  templateNasalSpray: "Human demonstration: using nasal medicine",
  templateInhaler: "Human demonstration: using an inhaler",
  templateOintmentTopical: "Human demonstration: applying topical medicine",
  templateSyrupOral: "Human demonstration: drinking measured syrup",
  templateCapsuleOral: "Human demonstration: taking capsule with water",
  templateTabletOral: "Human demonstration: taking tablet with water",
  exactPackageMatch: "Exact package match",
  likelyDosageFormImage: "Likely dosage form image",
  genericDosageForm: "Generic dosage form",
  imageReviewRequired: "Image review required",
};

const translateVideoItems = async (items: Record<string, string>, languageCode: string): Promise<Record<string, string>> => {
  if (!languageCode || languageCode === "en") return items;
  try {
    const response = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, language_code: languageCode }),
    });
    if (!response.ok) return items;
    const data = await response.json();
    return { ...items, ...(data.translations || {}) };
  } catch (error) {
    console.error("Video copy translation failed:", error);
    return items;
  }
};

const missingProviderKeys = (failures: VideoAssetFailure[]): string[] => {
  const keys = new Set<string>();
  failures.forEach((failure) => {
    const reason = failure.reason || "";
    if (reason.includes("PEXELS_API_KEY")) keys.add("PEXELS_API_KEY");
    if (reason.includes("SERPAPI_API_KEY")) keys.add("SERPAPI_API_KEY");
    if (reason.includes("BRAVE_SEARCH_API_KEY")) keys.add("BRAVE_SEARCH_API_KEY");
    if (reason.includes("GOOGLE_CSE_API_KEY")) keys.add("GOOGLE_CSE_API_KEY");
    if (reason.includes("GOOGLE_CSE_ID")) keys.add("GOOGLE_CSE_ID");
  });
  return Array.from(keys);
};

const formatAssetFailure = (failure: VideoAssetFailure): string => {
  const target = failure.medicineName || failure.routeTemplate || "Video asset";
  const asset = failure.assetType || "asset";
  const stage = failure.stage === "provider_config" ? "setup required" : failure.stage || "resolution";
  return `${target} • ${asset} • ${stage}: ${failure.reason || "No high-confidence result found"}`;
};

const activeSaltsText = (salts?: string[] | string): string => {
  if (Array.isArray(salts)) return salts.filter(Boolean).join(" + ");
  return String(salts || "");
};

const medicationDescriptor = (medicine: Medicine): string =>
  [
    medicine.name,
    activeSaltsText(medicine.active_salts),
    medicine.form,
    medicine.dosage,
    medicine.purpose,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

const routeDefaultsForMedicine = (medicine: Medicine) => {
  const text = medicationDescriptor(medicine);
  if (/(injection|injectable|vial|ampoule|infusion|iv\b|intravenous)/i.test(text)) {
    return { dosage: "As prescribed", frequency: "As prescribed", timing: "As directed", route: "professional", form: "injection", replaceGenericOral: true };
  }
  if (/(ointment|cream|gel|lotion|topical|external)/i.test(text)) {
    return { dosage: "Apply a thin layer", frequency: "As directed by doctor", timing: "Apply to affected area", route: "topical", form: text.includes("cream") ? "cream" : text.includes("gel") ? "gel" : "ointment", replaceGenericOral: true };
  }
  if (/(eye|ophthalmic)/i.test(text)) {
    return { dosage: "1 Drop", frequency: "As directed", timing: "As directed", route: "ophthalmic", form: "eye drops", replaceGenericOral: true };
  }
  if (/(ear|otic)/i.test(text)) {
    return { dosage: "2 Drops", frequency: "As directed", timing: "As directed", route: "otic", form: "ear drops", replaceGenericOral: true };
  }
  if (/(nasal|nose)/i.test(text)) {
    return { dosage: "2 Drops", frequency: "As directed", timing: "As directed", route: "nasal", form: "nasal drops", replaceGenericOral: true };
  }
  if (/(inhaler|respule|inhalation)/i.test(text)) {
    return { dosage: "1 Puff", frequency: "As prescribed", timing: "As directed", route: "inhalation", form: "inhaler", replaceGenericOral: true };
  }
  if (/(syrup|suspension|oral solution|solution)/i.test(text)) {
    return { dosage: "5 ml", frequency: "As prescribed", timing: "After meals (PC)", route: "oral", form: "syrup", replaceGenericOral: true };
  }
  if (/capsule/i.test(text)) {
    return { dosage: "1 Capsule", frequency: "As prescribed", timing: "As directed", route: "oral", form: "capsule", replaceGenericOral: true };
  }
  return { dosage: "1 Tablet", frequency: "As prescribed", timing: "As directed", route: "oral", form: "tablet", replaceGenericOral: false };
};

const applyRouteDefaultIfNeeded = (value: string | undefined, fallback: string, replaceGenericOral: boolean): string => {
  const trimmed = (value || "").trim();
  if (!trimmed) return fallback;
  if (!replaceGenericOral) return trimmed;
  const genericOralValues = new Set(["1 tablet", "one tablet", "1 tab", "twice a day (1-0-1)", "after meals (pc)"]);
  return genericOralValues.has(trimmed.toLowerCase()) ? fallback : trimmed;
};

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

const base64ToBlobUrl = (b64: string): string => {
  try {
    const binary = atob(b64);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: "audio/mpeg" });
    return URL.createObjectURL(blob);
  } catch (err) {
    console.error("Failed to convert base64 to audio blob:", err);
    return "";
  }
};

const PrescriptionResult = () => {
  const router = useRouter();
  const [prescription, setPrescription] = useState<PrescriptionData | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [guideLanguage, setGuideLanguage] = useState("en");
  const [videoGenerating, setVideoGenerating] = useState(false);
  const [videoResults, setVideoResults] = useState<VideoGuideResult[]>([]);
  const [videoError, setVideoError] = useState("");
  const [assetFailures, setAssetFailures] = useState<VideoAssetFailure[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const videoRefs = useRef<Record<string, HTMLVideoElement | null>>({});
  const rafRef = useRef<number | null>(null);

  // Per-medicine audio state
  const [playingIdx, setPlayingIdx] = useState<number | null>(null);
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);

  // Embedded SDK state
  const [isEmbedded, setIsEmbedded] = useState(false);

  useEffect(() => {
    setIsEmbedded(window.self !== window.top);
  }, []);

  const handleImport = () => {
    if (window.parent) {
      window.parent.postMessage(
        { type: "SANJEEVANI_RESULT", payload: prescription },
        "*"
      );
    }
  };



  useEffect(() => {
    let cancelled = false;

    const attachSummaryAudio = (src: string | null) => {
      if (!src || cancelled) return;
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setAudioUrl(src);
      const audio = new Audio(src);
      audioRef.current = audio;
      audio.onloadedmetadata = () => {
        if (!cancelled) setDuration(audio.duration);
      };
      audio.onended = () => {
        if (cancelled) return;
        setPlaying(false);
        setCurrentTime(0);
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
      };
    };

    const rebuildHistoryAudio = async (data: PrescriptionData, lang: string) => {
      try {
        const token = localStorage.getItem("sanjeevani_token");
        const response = await fetch("/api/prescription/audio-summary", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ prescription: data, language: lang }),
        });
        const rebuilt = await response.json();
        if (cancelled || !response.ok || !rebuilt.success) return;

        const rebuiltData = rebuilt.data || data;
        setPrescription(rebuiltData);
        sessionStorage.setItem("scanResult", JSON.stringify({
          success: true,
          data: rebuiltData,
          audio_b64: rebuilt.audio_b64,
        }));
        if (rebuilt.audio_b64) {
          attachSummaryAudio(base64ToBlobUrl(rebuilt.audio_b64));
        }
      } catch (error) {
        console.error("Failed to rebuild prescription audio summary:", error);
      }
    };

    try {
      const raw = sessionStorage.getItem("scanResult");
      if (!raw) { router.push("/dashboard"); return; }
      const parsed = JSON.parse(raw);
      const d = parsed.data || parsed;
      const lang = sessionStorage.getItem("scanLanguage") || localStorage.getItem("sanjeevani_language") || "en";
      setGuideLanguage(lang);
      setPrescription(d);

      let src: string | null = null;
      if (parsed.audio_b64) {
        src = base64ToBlobUrl(parsed.audio_b64);
      } else if (parsed.audio_url) {
        src = parsed.audio_url;
      }

      if (src) {
        attachSummaryAudio(src);
      } else if (d?.medicines?.length) {
        rebuildHistoryAudio(d, lang);
      }
    } catch { router.push("/dashboard"); }

    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    return () => {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
      if (activeAudioRef.current) { activeAudioRef.current.pause(); activeAudioRef.current = null; }
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

    // Stop active medicine audio if playing
    if (playingIdx !== null && activeAudioRef.current) {
      activeAudioRef.current.pause();
      setPlayingIdx(null);
    }

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
      audioRef.current.play()
        .then(() => {
          setPlaying(true);
          rafRef.current = requestAnimationFrame(tickProgress);
        })
        .catch((err) => {
          console.error("Global playback failed:", err);
          setPlaying(false);
        });
    }
  };

  const toggleMedAudio = (idx: number, b64: string) => {
    if (!b64) return;

    // Stop the global audio if it's playing
    if (playing && audioRef.current) {
      audioRef.current.pause();
      setPlaying(false);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    }

    if (playingIdx === idx) {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause();
      }
      setPlayingIdx(null);
      return;
    }

    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }

    const url = base64ToBlobUrl(b64);
    if (!url) return;

    const audio = new Audio(url);
    activeAudioRef.current = audio;
    setPlayingIdx(idx);

    audio.play()
      .then(() => {
        audio.onended = () => {
          setPlayingIdx(null);
          activeAudioRef.current = null;
        };
      })
      .catch((err) => {
        console.error("Medicine playback failed:", err);
        setPlayingIdx(null);
        activeAudioRef.current = null;
      });
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const t = parseFloat(e.target.value);
    if (audioRef.current) audioRef.current.currentTime = t;
    setCurrentTime(t);
  };

  const buildVideoPayload = async () => {
    const videoCopy = await translateVideoItems(VIDEO_COPY_EN, guideLanguage);
    const patientName = prescription?.patient_info?.name || "Patient";
    return {
      patientName,
      language: guideLanguage,
      medicines: medicines.map((med) => {
        const routeDefaults = routeDefaultsForMedicine(med);
        const dosage = applyRouteDefaultIfNeeded(med.dosage, routeDefaults.dosage, routeDefaults.replaceGenericOral);
        const frequency = applyRouteDefaultIfNeeded(med.frequency, routeDefaults.frequency, routeDefaults.replaceGenericOral);
        const timing = applyRouteDefaultIfNeeded(med.meal_relation || med.timing, routeDefaults.timing, routeDefaults.replaceGenericOral);
        return {
          medicineName: med.name,
          activeSalts: activeSaltsText(med.active_salts),
          dosage,
          frequency,
          timing,
          duration: med.duration || videoCopy.asPrescribed || "As prescribed",
          route: routeDefaults.route,
          form: med.form || routeDefaults.form,
          doctorNotes: med.special_instructions || med.warnings || med.food_interaction || "",
          warnings: [
            videoCopy.followPrescription || VIDEO_COPY_EN.followPrescription,
            videoCopy.noDoseChange || VIDEO_COPY_EN.noDoseChange,
          ],
          videoCopy,
        };
      }),
    };
  };

  const handleGenerateVideoGuide = async (forceRefresh = false) => {
    if (!prescription || medicines.length === 0) return;
    setVideoGenerating(true);
    setVideoError("");
    setAssetFailures([]);
    setVideoResults([]);
    try {
      const payload = await buildVideoPayload();
      if (forceRefresh) {
        const refreshResponse = await fetch("/api/video-assets/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const refreshData = await refreshResponse.json().catch(() => ({}));
        if (!refreshResponse.ok || !refreshData.success) {
          setAssetFailures(Array.isArray(refreshData.failures) ? refreshData.failures : []);
          setVideoError(refreshData.error || "Unable to refresh verified video assets.");
          return;
        }
      }
      const response = await fetch("/api/video-guides/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      const videos = Array.isArray(data.videos) ? data.videos : [];
      const failures = Array.isArray(data.failures) ? data.failures : [];
      setVideoResults(videos);
      setAssetFailures(failures);
      if (!response.ok || !data.success) {
        setVideoError(failures.length > 0 ? "" : data.error || videos[0]?.error || "Video guide generation failed.");
      }
    } catch (error) {
      console.error("Prescription video generation failed:", error);
      setVideoError("Unable to connect to the video generation service.");
    } finally {
      setVideoGenerating(false);
    }
  };

  const handleReplayVideo = async (videoUrl: string) => {
    const video = videoRefs.current[videoUrl];
    if (!video) return;
    video.currentTime = 0;
    try {
      await video.play();
    } catch (error) {
      console.error("Video replay failed:", error);
    }
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

        </motion.div>        {/* Audio Player Bar */}
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

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="mb-6 bg-card border border-border rounded-2xl p-4 space-y-3"
        >
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <Video size={17} className="text-primary" />
              <div>
                <h2 className="font-display font-bold text-foreground text-sm">Video Guide</h2>
                <p className="text-xs text-muted-foreground">Generated from the same prescription fields as the audio guide.</p>
              </div>
            </div>
            <button
              onClick={() => handleGenerateVideoGuide(false)}
              disabled={videoGenerating || medicines.length === 0}
              className="px-4 py-2 rounded-xl bg-secondary text-secondary-foreground text-xs font-display font-bold hover:bg-secondary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {videoGenerating ? "Generating..." : "Generate Video Guide"}
            </button>
          </div>

          {videoError && <p className="text-xs text-destructive">{videoError}</p>}

          {assetFailures.length > 0 && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs space-y-2">
              <div>
                <p className="font-semibold text-amber-200">
                  {missingProviderKeys(assetFailures).length > 0 ? "Asset provider setup required" : "Verified medicine image not found"}
                </p>
                <p className="text-muted-foreground mt-1">
                  {missingProviderKeys(assetFailures).length > 0
                    ? "Add the missing provider keys and restart the backend before generating prescription videos."
                    : "The image resolver rejected unrelated or low-confidence internet results so the patient video is not built with wrong medicine images."}
                </p>
              </div>
              {missingProviderKeys(assetFailures).length > 0 && (
                <p className="text-muted-foreground">
                  Missing: {missingProviderKeys(assetFailures).map((key) => <code key={key} className="mx-1 text-amber-100">{key}</code>)}
                </p>
              )}
              <div className="space-y-1">
                {assetFailures.map((failure, index) => (
                  <p key={`${failure.assetType || "asset"}-${index}`} className="text-muted-foreground">
                    {formatAssetFailure(failure)}
                  </p>
                ))}
              </div>
              <button
                onClick={() => handleGenerateVideoGuide(true)}
                disabled={videoGenerating}
                className="px-3 py-2 rounded-lg bg-secondary text-secondary-foreground text-xs font-semibold disabled:opacity-50"
              >
                {videoGenerating ? "Retrying..." : "Retry asset fetch"}
              </button>
            </div>
          )}

          {videoResults.filter((item) => item.success && item.videoUrl).map((item) => (
            <div key={item.videoUrl} className="space-y-2">
              <video
                ref={(node) => {
                  videoRefs.current[item.videoUrl] = node;
                }}
                src={item.videoUrl}
                controls
                loop={false}
                className="w-full rounded-xl border border-border bg-black"
              />
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                <p>{item.medicineName} • {item.durationSeconds}s</p>
                <button
                  type="button"
                  onClick={() => handleReplayVideo(item.videoUrl)}
                  className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1 text-xs font-semibold text-foreground hover:bg-muted transition-colors"
                >
                  <RotateCcw size={13} />
                  Replay Video
                </button>
              </div>
              {item.warnings?.map((warning) => (
                <p key={warning} className="text-xs text-muted-foreground">Warning: {warning}</p>
              ))}
            </div>
          ))}
        </motion.div>

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
                      {med.audio_b64 && (
                        <button
                          onClick={() => toggleMedAudio(idx, med.audio_b64!)}
                          className={`w-6 h-6 rounded-md flex items-center justify-center transition-all shrink-0 ml-1.5 ${playingIdx === idx ? "bg-primary text-primary-foreground animate-pulse" : "bg-primary/10 text-primary hover:bg-primary/20"}`}
                          title="Listen to instruction"
                        >
                          {playingIdx === idx ? <Pause size={10} /> : <Volume2 size={10} />}
                        </button>
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

          {isEmbedded && (
            <motion.button
              variants={fadeUp}
              onClick={handleImport}
              className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 text-white font-display font-bold text-lg rounded-xl transition-all shadow-lg flex items-center justify-center gap-2"
            >
              Import Guide to Portal
            </motion.button>
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
