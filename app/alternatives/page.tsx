"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Search, Pill, AlertTriangle, CheckCircle, Info, ChevronRight, IndianRupee } from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";

interface MedicineSearch {
  medicineName: string;
  unit: string;
  activeSalts: string;
  uses: string;
  sideEffects: string;
  manufacturer: string;
  price: number | null;
}

interface AlternateCandidate {
  medicineName: string;
  activeSalts: string;
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

export default function AlternativesPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MedicineSearch[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  const [selectedMed, setSelectedMed] = useState<MedicineSearch | null>(null);
  const [alternatives, setAlternatives] = useState<AlternateCandidate[]>([]);
  const [alternativesLoading, setAlternativesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Search logic
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const response = await fetch(`/api/medicines/search?q=${encodeURIComponent(searchQuery.trim())}`);
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data);
        setShowDropdown(true);
      } else {
        setError("Failed to fetch search results.");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setSearching(false);
    }
  };

  // Autocomplete triggers
  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (searchQuery.trim().length >= 2) {
        handleSearch();
      } else {
        setSearchResults([]);
        setShowDropdown(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  // Load alternatives for selected medicine
  const handleSelectMedicine = async (med: MedicineSearch) => {
    setSelectedMed(med);
    setShowDropdown(false);
    setSearchQuery(med.medicineName);
    setAlternativesLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/medicines/alternatives?name=${encodeURIComponent(med.medicineName)}`);
      if (res.ok) {
        const data = await res.json();
        setAlternatives(data);
      } else {
        setError("Failed to fetch alternatives.");
        setAlternatives([]);
      }
    } catch (err) {
      setError("Failed to retrieve alternate medicines.");
      setAlternatives([]);
    } finally {
      setAlternativesLoading(false);
    }
  };

  const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.1 } } };
  const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

  return (
    <div className="min-h-screen relative bg-background text-foreground pb-12">
      <MandalaBackground />

      <div className="relative z-10 p-6 lg:p-12 max-w-4xl mx-auto">
        {/* Navigation & Header */}
        <div className="flex items-center gap-4 mb-10">
          <button
            onClick={() => router.push("/dashboard")}
            className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center hover:bg-muted transition-colors"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="font-display text-2xl font-bold">Alternate Medicines</h1>
            <p className="text-muted-foreground text-sm">Find cheaper, active substitute drug recommendations</p>
          </div>
        </div>

        {/* Search Bar Block */}
        <div className="bg-card/75 backdrop-blur-md border border-border rounded-2xl p-6 relative mb-8 shadow-lg">
          <label className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-2 block">
            Search Medicine Name
          </label>
          <div className="flex gap-2 relative">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Enter medicine (e.g. Pantocid, Dolo, Calpol...)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearch();
                }}
                className="w-full bg-muted border border-border rounded-xl pl-10 pr-4 py-3 text-sm outline-none focus:border-primary transition-colors text-foreground"
              />
              <Search className="absolute left-3 top-3.5 text-muted-foreground" size={16} />
            </div>
            <button
              onClick={handleSearch}
              disabled={searching}
              className="px-6 py-3 bg-primary text-primary-foreground font-display font-semibold rounded-xl disabled:opacity-50 flex items-center gap-2 cursor-pointer transition-opacity"
            >
              {searching ? (
                <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
              ) : (
                "Search"
              )}
            </button>
          </div>

          {/* Autocomplete Dropdown */}
          <AnimatePresence>
            {showDropdown && searchResults.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="absolute left-6 right-6 mt-2 bg-card border border-border rounded-xl shadow-2xl z-50 max-h-60 overflow-y-auto divide-y divide-border"
              >
                {searchResults.map((med, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSelectMedicine(med)}
                    className="w-full px-4 py-3 text-left hover:bg-muted/80 transition-colors flex flex-col gap-0.5"
                  >
                    <span className="font-semibold text-sm text-foreground">{med.medicineName}</span>
                    <span className="text-xs text-muted-foreground line-clamp-1">
                      {med.activeSalts} • {med.manufacturer} {med.price != null ? ` • ₹${Number(med.price).toFixed(2)}` : ""}
                    </span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-destructive/10 border border-destructive/30 rounded-xl text-destructive text-sm">
            {error}
          </div>
        )}

        {/* Results Block */}
        {selectedMed && (
          <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-6">
            {/* Selected Medicine Profile Card */}
            <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6 shadow-md">
              <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-1">Target Medicine</p>
              <h2 className="font-display text-2xl font-bold text-foreground mb-2">{selectedMed.medicineName}</h2>
              <div className="space-y-2 mt-4 border-t border-border pt-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Active Salts:</span>
                  <span className="font-semibold text-right max-w-xs">{selectedMed.activeSalts || "Not specified"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Manufacturer:</span>
                  <span className="font-semibold text-right">{selectedMed.manufacturer || "Not specified"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Retail Price:</span>
                  <span className="font-semibold text-right text-emerald-400">
                    {selectedMed.price != null ? `₹${Number(selectedMed.price).toFixed(2)}` : "Unavailable"}
                  </span>
                </div>
              </div>
            </motion.div>

            {/* Alternates Section */}
            <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6 shadow-md space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-bold flex items-center gap-2">
                  <Pill size={20} className="text-primary" />
                  Cheaper Substitutes Found
                </h3>
                {alternativesLoading && <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />}
              </div>

              {/* Formulation Warning Banner */}
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-200 leading-relaxed flex items-start gap-2.5">
                <AlertTriangle className="text-amber-400 shrink-0 mt-0.5" size={16} />
                <span>
                  <strong>Substitution Warning:</strong> Branded formulations like Fast/Rapid/Advance may absorb differently, even when active salts and strengths match exactly. Consult a doctor or pharmacist before switching medications.
                </span>
              </div>

              {/* Candidates list */}
              {!alternativesLoading && alternatives.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground text-sm">
                  No cheaper active substitutes found in local database for this formulation.
                </div>
              ) : (
                <div className="space-y-4">
                  {alternatives.map((alt, idx) => (
                    <motion.div
                      key={idx}
                      variants={fadeUp}
                      className="border border-border/80 bg-muted/20 rounded-xl p-4 flex flex-col md:flex-row justify-between md:items-center gap-4 hover:border-primary/50 transition-colors"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2.5 flex-wrap">
                          <h4 className="font-display font-bold text-base text-foreground">{alt.medicineName}</h4>
                          <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full ${
                            alt.substitutionSafety === "doctor_curated" 
                              ? "bg-emerald-500/15 text-emerald-400" 
                              : "bg-amber-500/15 text-amber-400"
                          }`}>
                            {alt.substitutionSafety === "doctor_curated" ? "Doctor Curated" : "System Matched"}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground truncate">{alt.activeSalts}</p>
                        <p className="text-[11px] text-muted-foreground">
                          {alt.manufacturer} • {alt.unit}
                        </p>
                        {alt.matchReasons?.length > 0 && (
                          <div className="flex items-center gap-1.5 pt-1.5 flex-wrap">
                            {alt.matchReasons.map((reason, ridx) => (
                              <span key={ridx} className="text-[9px] bg-primary/10 text-primary font-semibold px-2 py-0.5 rounded">
                                {reason}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="text-right shrink-0 flex flex-col justify-center items-end">
                        {alt.price != null ? (
                          <>
                            <span className="text-xs text-muted-foreground">Substitute Price</span>
                            <span className="text-lg font-bold text-emerald-400 flex items-center gap-0.5">
                              <IndianRupee size={14} className="mt-0.5" />
                              {Number(alt.price).toFixed(2)}
                            </span>
                            {selectedMed.price != null && selectedMed.price > alt.price && (
                              <span className="text-[10px] text-emerald-400/90 font-medium">
                                Save {Math.round(((selectedMed.price - alt.price) / selectedMed.price) * 100)}%
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-xs text-muted-foreground">Price unavailable</span>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
