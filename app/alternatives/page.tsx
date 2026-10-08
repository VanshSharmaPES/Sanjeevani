"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  Building2,
  ChevronRight,
  IndianRupee,
  Layers3,
  Loader2,
  PackageCheck,
  Pill,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";

interface MedicineSearch {
  medicineName: string;
  activeSalts?: string;
  dosageForm?: string;
  formulationVariant?: string;
  manufacturer: string;
  medicineType?: string | null;
  price: number | null;
  releaseType?: string;
  route?: string;
  sideEffects: string;
  unit: string;
  uses: string;
}

interface AlternateCandidate {
  medicineName: string;
  manufacturer: string;
  price: number | null;
  unit: string;
  substitutionSafety: string;
  confidenceScore: number;
  statusLabel: string;
  formulationMatch: boolean;
  matchReasons: string[];
  safetyWarnings: string[];
}

type LoadState = "idle" | "searching" | "loadingAlternatives" | "ready" | "empty" | "error";

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

const listMotion = {
  hidden: {},
  show: { transition: { staggerChildren: 0.055 } },
};

const MATCH_REASON_LABELS: Record<string, string> = {
  "same active ingredient composition": "Composition matched",
  "same strength": "Strength matched",
  "same dosage form": "Form matched",
  "same route": "Route matched",
  "same release type": "Release matched",
  "same formulation variant": "Variant matched",
};

function normalizeText(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function compactText(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function queryTokens(value: string) {
  return normalizeText(value)
    .split(" ")
    .filter((token) => token.length > 1);
}

function strengthTokens(value: string) {
  const matches = value.toLowerCase().match(/\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%)\b/g) || [];
  return matches.map((item) => compactText(item));
}

function formIntent(value: string) {
  const text = normalizeText(value);
  if (/\b(capsule|capsules|cap)\b/.test(text)) return "capsule";
  if (/\b(tablet|tablets|tab)\b/.test(text)) return "tablet";
  if (/\b(syrup|suspension)\b/.test(text)) return "syrup";
  if (/\b(ear|otic)\b/.test(text)) return "ear";
  if (/\b(eye|ophthalmic)\b/.test(text)) return "eye";
  if (/\b(nasal|nose)\b/.test(text)) return "nasal";
  if (/\b(inhaler|mdi)\b/.test(text)) return "inhaler";
  if (/\b(cream|ointment|gel|tube)\b/.test(text)) return "topical";
  return "";
}

function candidateFormText(medicine: MedicineSearch) {
  return normalizeText(`${medicine.medicineName} ${medicine.dosageForm || ""} ${medicine.unit || ""} ${medicine.route || ""}`);
}

function scoreSearchResult(medicine: MedicineSearch, query: string) {
  const normalizedQuery = normalizeText(query);
  const compactQuery = compactText(query);
  const normalizedName = normalizeText(medicine.medicineName);
  const compactName = compactText(medicine.medicineName);
  const metadata = normalizeText(
    `${medicine.medicineName} ${medicine.activeSalts || ""} ${medicine.dosageForm || ""} ${medicine.unit || ""} ${medicine.manufacturer || ""}`,
  );
  const tokens = queryTokens(query);
  const queryStrengths = strengthTokens(query);
  const candidateStrengths = strengthTokens(`${medicine.medicineName} ${medicine.activeSalts || ""} ${medicine.unit || ""}`);
  const requestedForm = formIntent(query);
  const candidateForm = candidateFormText(medicine);

  let score = 0;
  if (normalizedName === normalizedQuery) score += 80;
  if (compactName === compactQuery) score += 80;
  if (normalizedName.includes(normalizedQuery)) score += 36;
  if (tokens.length && tokens.every((token) => metadata.includes(token))) score += 34;
  if (queryStrengths.length && queryStrengths.every((strength) => candidateStrengths.includes(strength))) score += 45;
  if (queryStrengths.length && !queryStrengths.every((strength) => candidateStrengths.includes(strength))) score -= 35;

  if (requestedForm && candidateForm.includes(requestedForm)) score += 45;
  if (requestedForm && !candidateForm.includes(requestedForm)) score -= 45;
  if (!requestedForm && /\b(tablet|capsule|syrup|suspension|drops|inhaler|cream|ointment|gel)\b/.test(candidateForm)) score += 12;

  if (medicine.medicineType === "ai_generated") score -= 25;
  if (medicine.manufacturer) score += 5;
  if (medicine.unit) score += 5;
  return score;
}

function rankSearchResults(results: MedicineSearch[], query: string) {
  return [...results].sort((left, right) => scoreSearchResult(right, query) - scoreSearchResult(left, query));
}

function formatPrice(price: number | null) {
  return price != null ? `₹${Number(price).toFixed(2)}` : "Unavailable";
}

function displayForm(medicine: MedicineSearch) {
  const form = medicine.dosageForm || formIntent(`${medicine.medicineName} ${medicine.unit}`);
  if (!form) return "Medicine";
  return form
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function visibleMatchReasons(reasons: string[] = []) {
  const mapped = reasons
    .filter((reason) => !/salt|review/i.test(reason))
    .map((reason) => MATCH_REASON_LABELS[normalizeText(reason)] || reason.replace(/^Same /i, ""))
    .filter(Boolean);
  return Array.from(new Set(mapped)).slice(0, 5);
}

export default function AlternativesPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MedicineSearch[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);

  const [selectedMed, setSelectedMed] = useState<MedicineSearch | null>(null);
  const [alternatives, setAlternatives] = useState<AlternateCandidate[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  const isBusy = loadState === "searching" || loadState === "loadingAlternatives";

  const lowestPrice = useMemo(() => {
    const prices = alternatives
      .map((item) => item.price)
      .filter((price): price is number => typeof price === "number");
    return prices.length ? Math.min(...prices) : null;
  }, [alternatives]);

  const fetchSearchResults = async (query: string) => {
    const response = await fetch(`/api/medicines/search?q=${encodeURIComponent(query)}`, { cache: "no-store" });
    if (!response.ok) throw new Error("Search service is unavailable. Please try again.");
    const data = await response.json();
    return Array.isArray(data) ? (data as MedicineSearch[]) : [];
  };

  const fetchAlternatives = async (medicineName: string) => {
    const response = await fetch(`/api/medicines/alternatives?name=${encodeURIComponent(medicineName)}`, {
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error || "Alternative service is unavailable. Please try again.");
    return Array.isArray(data) ? (data as AlternateCandidate[]) : [];
  };

  const setSelectedWithAlternatives = async (medicine: MedicineSearch) => {
    setLoadState("loadingAlternatives");
    setError(null);
    const candidates = await fetchAlternatives(medicine.medicineName);
    setSelectedMed(medicine);
    setSearchQuery(medicine.medicineName);
    setSearchResults([]);
    setAlternatives(candidates);
    setShowDropdown(false);
    setLoadState(candidates.length ? "ready" : "empty");
    return candidates;
  };

  const handleSelectMedicine = async (medicine: MedicineSearch) => {
    try {
      await setSelectedWithAlternatives(medicine);
    } catch (err) {
      setAlternatives([]);
      setLoadState("error");
      setError(err instanceof Error ? err.message : "Failed to retrieve alternate medicines.");
    }
  };

  const handleSearch = async () => {
    const query = searchQuery.trim();
    if (!query || isBusy) return;

    setLoadState("searching");
    setError(null);
    setShowDropdown(false);

    try {
      const rankedResults = rankSearchResults(await fetchSearchResults(query), query);
      setSearchResults(rankedResults);

      if (!rankedResults.length) {
        setSelectedMed(null);
        setAlternatives([]);
        setLoadState("empty");
        setError("No medicine found for that search.");
        return;
      }

      let fallback: MedicineSearch | null = rankedResults[0];
      for (const medicine of rankedResults.slice(0, 5)) {
        const candidates = await fetchAlternatives(medicine.medicineName);
        if (candidates.length > 0) {
          setSelectedMed(medicine);
          setSearchQuery(medicine.medicineName);
          setSearchResults([]);
          setShowDropdown(false);
          setAlternatives(candidates);
          setLoadState("ready");
          return;
        }
      }

      setSelectedMed(fallback);
      setSearchQuery(fallback.medicineName);
      setSearchResults([]);
      setShowDropdown(false);
      setAlternatives([]);
      setLoadState("empty");
    } catch (err) {
      setSelectedMed(null);
      setAlternatives([]);
      setLoadState("error");
      setError(err instanceof Error ? err.message : "Network error. Please try again.");
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      const query = searchQuery.trim();
      if (query.length < 2 || query === selectedMed?.medicineName) {
        setSearchResults([]);
        setShowDropdown(false);
        return;
      }

      try {
        const results = rankSearchResults(await fetchSearchResults(query), query);
        setSearchResults(results);
        setShowDropdown(results.length > 0);
      } catch {
        setSearchResults([]);
        setShowDropdown(false);
      }
    }, 240);

    return () => window.clearTimeout(timer);
  }, [searchQuery, selectedMed?.medicineName]);

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-background pb-16 text-foreground">
      <MandalaBackground />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_10%,rgba(0,210,178,0.20),transparent_30%),radial-gradient(circle_at_82%_16%,rgba(245,158,11,0.18),transparent_28%),linear-gradient(180deg,rgba(0,0,0,0.08),transparent_30%)]" />

      <main className="relative z-10 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        <motion.header
          initial={{ opacity: 0, y: -14 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 grid gap-6 lg:grid-cols-[1fr_auto]"
        >
          <div className="flex items-start gap-4 sm:gap-5">
            <button
              onClick={() => router.push("/dashboard")}
              className="mt-2 grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-border bg-card/80 shadow-lg transition hover:border-primary/50 hover:bg-muted"
              aria-label="Back to dashboard"
            >
              <ArrowLeft size={21} />
            </button>
            <div className="min-w-0">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.28em] text-primary">
                <Sparkles size={14} /> Smart Match
              </div>
              <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
                Substitute Medicines
              </h1>
              <p className="mt-3 max-w-2xl text-base text-muted-foreground">
                Find same-composition medicine candidates with a clean clinician-facing review interface.
              </p>
            </div>
          </div>

          <div className="self-start rounded-3xl border border-primary/20 bg-card/70 px-5 py-4 shadow-xl backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-2xl bg-primary/15 text-primary">
                <ShieldCheck size={20} />
              </div>
              <div>
                <p className="font-display text-sm font-bold">Production Matching</p>
                <p className="text-xs text-muted-foreground">Strength, form, route, release, and variant are checked.</p>
              </div>
            </div>
          </div>
        </motion.header>

        <motion.section
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="relative z-40 mb-8 overflow-visible rounded-[2rem] border border-border bg-card/85 p-5 shadow-2xl backdrop-blur-md lg:p-7"
        >
          <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-primary/10 blur-2xl" />
          <label className="mb-3 block font-display text-xs uppercase tracking-[0.32em] text-muted-foreground">
            Search Medicine Name
          </label>
          <div className="flex flex-col gap-3 md:flex-row">
            <div className="relative min-w-0 flex-1">
              <input
                type="text"
                placeholder="Enter medicine (e.g. Dolo 650 Tablet, Calpol 250mg Tablet...)"
                value={searchQuery}
                onChange={(event) => {
                  setSearchQuery(event.target.value);
                  if (selectedMed && event.target.value !== selectedMed.medicineName) {
                    setSelectedMed(null);
                    setAlternatives([]);
                    setLoadState("idle");
                  }
                }}
                onFocus={() => {
                  if (!selectedMed && searchResults.length > 0) setShowDropdown(true);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void handleSearch();
                }}
                className="w-full rounded-2xl border border-border bg-muted/80 py-4 pl-12 pr-4 text-base text-foreground outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" size={20} />
            </div>
            <button
              onClick={() => void handleSearch()}
              disabled={isBusy}
              className="flex min-w-36 items-center justify-center gap-2 rounded-2xl bg-primary px-8 py-4 font-display font-bold text-primary-foreground shadow-lg shadow-primary/20 transition hover:scale-[1.01] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isBusy ? <Loader2 className="animate-spin" size={18} /> : <Search size={18} />}
              {loadState === "searching" ? "Searching" : loadState === "loadingAlternatives" ? "Matching" : "Search"}
            </button>
          </div>


          <AnimatePresence>
            {showDropdown && searchResults.length > 0 && (
              <motion.div
                data-testid="medicine-suggestion-list"
                role="listbox"
                aria-label="Medicine search suggestions"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="absolute left-5 right-5 top-full z-[100] mt-3 max-h-[min(24rem,calc(100vh-16rem))] overflow-y-auto overscroll-contain rounded-2xl border border-primary/20 bg-card/95 shadow-2xl shadow-black/35 backdrop-blur-xl lg:left-7 lg:right-7"
              >
                {searchResults.slice(0, 8).map((medicine, index) => (
                  <button
                    key={`${medicine.medicineName}-${medicine.manufacturer}-${index}`}
                    role="option"
                    onClick={() => void handleSelectMedicine(medicine)}
                    className="flex w-full items-center justify-between gap-4 border-b border-border/70 px-5 py-4 text-left transition last:border-b-0 hover:bg-muted/70"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate font-display font-semibold">{medicine.medicineName}</p>
                        {index === 0 && (
                          <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.16em] text-primary">
                            Best match
                          </span>
                        )}
                      </div>
                      <p className="mt-1 truncate text-xs text-muted-foreground">
                        {medicine.manufacturer || "Manufacturer unavailable"} • {displayForm(medicine)} • {medicine.unit || "Pack unavailable"}
                      </p>
                    </div>
                    <ChevronRight size={17} className="shrink-0 text-primary" />
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.section>

        {error && (
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="mb-8 rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"
          >
            {error}
          </motion.div>
        )}

        {!selectedMed ? (
          <EmptySearchState isBusy={isBusy} />
        ) : (
          <motion.div variants={listMotion} initial="hidden" animate="show" className="space-y-8">
            <motion.section variants={fadeUp} className="overflow-hidden rounded-[2rem] border border-border bg-card/85 shadow-xl backdrop-blur-md">
              <div className="grid gap-0 lg:grid-cols-[1.25fr_0.75fr]">
                <div className="p-6 lg:p-8">
                  <p className="mb-2 font-display text-xs uppercase tracking-[0.28em] text-muted-foreground">
                    Target Medicine
                  </p>
                  <h2 className="break-words font-display text-3xl font-bold">{selectedMed.medicineName}</h2>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <InfoPill icon={<Building2 size={16} />} label={selectedMed.manufacturer || "Manufacturer unavailable"} />
                    <InfoPill icon={<PackageCheck size={16} />} label={selectedMed.unit || "Pack unavailable"} />
                    <InfoPill icon={<Layers3 size={16} />} label={displayForm(selectedMed)} />
                    <InfoPill icon={<Target size={16} />} label="Composition profile matched" />
                  </div>
                </div>
                <div className="border-t border-border bg-muted/20 p-6 lg:border-l lg:border-t-0 lg:p-8">
                  <div className="grid grid-cols-2 gap-3">
                    <MetricCard label="Matches" value={String(alternatives.length)} />
                    <MetricCard label="Best Price" value={formatPrice(lowestPrice)} highlight />
                    <MetricCard label="Source" value="Local DB" />
                    <MetricCard label="Selection" value="Auto-ranked" />
                  </div>
                </div>
              </div>
            </motion.section>

            <motion.section variants={fadeUp} className="rounded-[2rem] border border-border bg-card/85 p-6 shadow-xl backdrop-blur-md lg:p-8">
              <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <h3 className="flex items-center gap-2 font-display text-2xl font-bold">
                    <Pill className="text-primary" size={24} />
                    Alternative Candidates
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Same-composition candidates are ranked for clinician review without exposing raw salt text in the UI.
                  </p>
                </div>
                {isBusy && (
                  <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-sm font-semibold text-primary">
                    <Loader2 className="animate-spin" size={16} />
                    Matching
                  </div>
                )}
              </div>

              {isBusy ? (
                <LoadingCards />
              ) : alternatives.length === 0 ? (
                <NoAlternativesState selectedName={selectedMed.medicineName} />
              ) : (
                <div className="grid gap-4">
                  {alternatives.map((alternate, index) => (
                    <AlternativeCard
                      key={`${alternate.medicineName}-${alternate.manufacturer}-${index}`}
                      alternate={alternate}
                      selectedPrice={selectedMed.price}
                      index={index}
                    />
                  ))}
                </div>
              )}
            </motion.section>
          </motion.div>
        )}
      </main>
    </div>
  );
}

function EmptySearchState({ isBusy }: { isBusy: boolean }) {
  return (
    <motion.section
      variants={fadeUp}
      initial="hidden"
      animate="show"
      className="grid min-h-[300px] place-items-center rounded-[2rem] border border-border bg-card/75 p-8 text-center shadow-xl backdrop-blur-md"
    >
      <div>
        <div className="mx-auto mb-5 grid h-20 w-20 place-items-center rounded-3xl border border-primary/25 bg-primary/10 text-primary shadow-lg shadow-primary/10">
          {isBusy ? <Loader2 className="animate-spin" size={34} /> : <Pill size={34} />}
        </div>
        <h2 className="font-display text-2xl font-bold">
          {isBusy ? "Finding the best medicine record" : "Search a medicine to view alternatives"}
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
          Results appear after selecting a medicine. The page avoids weak first-result matches and prefers complete branded records.
        </p>
      </div>
    </motion.section>
  );
}

function LoadingCards() {
  return (
    <div className="grid gap-4">
      {[0, 1, 2].map((item) => (
        <div key={item} className="overflow-hidden rounded-3xl border border-border bg-muted/20 p-5">
          <div className="h-5 w-56 animate-pulse rounded-full bg-muted" />
          <div className="mt-4 h-4 w-72 animate-pulse rounded-full bg-muted" />
          <div className="mt-5 flex gap-2">
            <div className="h-7 w-28 animate-pulse rounded-full bg-muted" />
            <div className="h-7 w-28 animate-pulse rounded-full bg-muted" />
            <div className="h-7 w-28 animate-pulse rounded-full bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

function NoAlternativesState({ selectedName }: { selectedName: string }) {
  return (
    <div className="rounded-3xl border border-border bg-muted/20 px-6 py-14 text-center">
      <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-primary/10 text-primary">
        <Search size={26} />
      </div>
      <h4 className="font-display text-xl font-bold">No alternatives found</h4>
      <p className="mx-auto mt-2 max-w-2xl text-sm text-muted-foreground">
        The local database did not return same-composition candidates for {selectedName}. Try a more complete brand name with form,
        such as “Tablet”, “Capsule”, “Syrup”, or “Drops”.
      </p>
    </div>
  );
}

function AlternativeCard({
  alternate,
  selectedPrice,
  index,
}: {
  alternate: AlternateCandidate;
  selectedPrice: number | null;
  index: number;
}) {
  const reasons = visibleMatchReasons(alternate.matchReasons);
  const savePercent =
    selectedPrice != null && alternate.price != null && selectedPrice > alternate.price
      ? Math.round(((selectedPrice - alternate.price) / selectedPrice) * 100)
      : null;
  const confidence = Math.max(0, Math.min(100, Number(alternate.confidenceScore || 95)));

  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: index * 0.035 }}
      className="group relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-muted/35 via-card to-card p-5 transition hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-2xl hover:shadow-primary/10"
    >
      <div className="pointer-events-none absolute right-0 top-0 h-24 w-24 rounded-bl-[4rem] bg-primary/10 transition group-hover:bg-primary/15" />
      <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-primary/15 text-primary">
              <BadgeCheck size={17} />
            </span>
            <h4 className="break-words font-display text-xl font-bold">{alternate.medicineName}</h4>
            <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-[11px] font-bold text-emerald-400">
              {confidence}% match
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            {alternate.manufacturer || "Manufacturer unavailable"} • {alternate.unit || "Pack unavailable"}
          </p>
          {reasons.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {reasons.map((reason) => (
                <span
                  key={reason}
                  className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[11px] font-semibold text-primary"
                >
                  {reason}
                </span>
              ))}
            </div>
          )}
          {alternate.safetyWarnings && alternate.safetyWarnings.length > 0 && (
            <div className="mt-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4 text-left">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                <AlertTriangle size={14} className="text-amber-400" />
                Safety Warnings
              </p>
              <ul className="mt-1.5 list-disc pl-4 space-y-1 text-xs text-muted-foreground">
                {alternate.safetyWarnings.map((warning, wIdx) => (
                  <li key={wIdx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:min-w-72">
          <div className="rounded-2xl border border-border bg-background/40 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Price</p>
            <p className="mt-1 flex items-center gap-1 text-2xl font-bold text-emerald-400">
              {alternate.price != null && <IndianRupee size={17} />}
              {alternate.price != null ? Number(alternate.price).toFixed(2) : "Unavailable"}
            </p>
            {savePercent != null && <p className="mt-1 text-xs font-semibold text-emerald-300">Save {savePercent}%</p>}
          </div>
          <div className="rounded-2xl border border-border bg-background/40 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Status</p>
            <p className={`mt-2 text-sm font-bold ${alternate.substitutionSafety === "doctor_curated" ? "text-emerald-400" : "text-amber-500"}`}>
              {alternate.statusLabel}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Confirm patient suitability before use.</p>
          </div>
        </div>
      </div>
    </motion.article>
  );
}

function InfoPill({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-2xl border border-border bg-muted/25 px-3 py-2 text-sm text-muted-foreground">
      <span className="shrink-0 text-primary">{icon}</span>
      <span className="truncate">{label}</span>
    </div>
  );
}

function MetricCard({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-2xl border border-border bg-background/35 px-4 py-3">
      <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className={`mt-1 truncate font-display text-sm font-bold ${highlight ? "text-emerald-400" : "text-foreground"}`}>
        {value}
      </p>
    </div>
  );
}
