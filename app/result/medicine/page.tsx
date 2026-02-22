"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Volume2, ChevronDown, ChevronUp, AlertTriangle, CheckCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";

const mockMedicine = {
  name: "Paracetamol 500mg",
  brand: "Crocin Advance",
  salts: ["Paracetamol IP 500mg"],
  dosageStrength: "normal" as const,
  conditions: ["Fever", "Headache", "Body Pain", "Toothache", "Cold & Flu"],
  howItWorks:
    "Paracetamol works by blocking the production of prostaglandins, chemicals in the body that cause inflammation, pain, and fever. It acts on the brain's heat-regulating center to reduce fever.",
  ageGroups: { children: "6+", adults: "12+", elderly: "Use with caution" },
  sideEffects: ["Nausea", "Allergic reactions (rare)", "Liver damage (overdose)"],
};

const MedicineResult = () => {
  const router = useRouter();
  const [howItWorksOpen, setHowItWorksOpen] = useState(false);

  const stagger = {
    hidden: {},
    show: { transition: { staggerChildren: 0.1 } },
  };
  const fadeUp = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  };

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
          <button className="ml-auto w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-primary-foreground glow-pulse-saffron">
            <Volume2 size={18} />
          </button>
        </motion.div>

        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-5">
          {/* Medicine name */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-1">Brand</p>
            <h2 className="font-display text-3xl font-bold text-foreground glow-pulse-cyan inline-block px-1">{mockMedicine.brand}</h2>
            <p className="text-muted-foreground text-sm mt-1">{mockMedicine.name}</p>
          </motion.div>

          {/* Salts */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-3">Active Ingredients</p>
            <div className="flex flex-wrap gap-2">
              {mockMedicine.salts.map((s) => (
                <span key={s} className="px-4 py-1.5 rounded-full bg-secondary/15 text-secondary text-sm font-semibold border border-secondary/30">
                  {s}
                </span>
              ))}
            </div>
          </motion.div>

          {/* Dosage strength */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-3">Dosage Strength</p>
            <div className="flex items-center gap-4">
              <div className={`w-16 h-16 rounded-full border-4 flex items-center justify-center ${
                mockMedicine.dosageStrength === "normal" ? "border-green-500" : "border-red-500"
              }`}>
                {mockMedicine.dosageStrength === "normal" ? (
                  <CheckCircle className="text-green-500" size={28} />
                ) : (
                  <AlertTriangle className="text-red-500" size={28} />
                )}
              </div>
              <div>
                <p className="font-display font-bold text-foreground text-lg capitalize">{mockMedicine.dosageStrength}</p>
                <p className="text-muted-foreground text-sm">Standard therapeutic dose</p>
              </div>
            </div>
          </motion.div>

          {/* Conditions */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-3">Conditions Treated</p>
            <div className="flex flex-wrap gap-2">
              {mockMedicine.conditions.map((c) => (
                <span key={c} className="px-3 py-1.5 rounded-lg bg-muted text-foreground text-sm">{c}</span>
              ))}
            </div>
          </motion.div>

          {/* How it works accordion */}
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
                <p className="text-foreground text-sm leading-relaxed">{mockMedicine.howItWorks}</p>
              </motion.div>
            )}
          </motion.div>

          {/* Age groups */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-4">Age Groups</p>
            <div className="flex gap-3">
              {Object.entries(mockMedicine.ageGroups).map(([group, age]) => (
                <div key={group} className="flex-1 bg-muted rounded-xl p-3 text-center">
                  <p className="font-display font-bold text-foreground text-sm capitalize">{group}</p>
                  <p className="text-muted-foreground text-xs mt-1">{age}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export default MedicineResult;
