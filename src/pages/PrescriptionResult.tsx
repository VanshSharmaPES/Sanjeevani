import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Printer, Share2, ChevronDown, ChevronUp, Sun, Sunset, Moon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import MandalaBackground from "@/components/MandalaBackground";

const mockPrescription = {
  doctorName: "Dr. Ananya Sharma",
  date: "18 Feb 2026",
  medicines: [
    {
      name: "Amoxicillin 500mg",
      timing: ["Morning", "Night"],
      dosage: "1 tablet",
      purpose: "Bacterial infection",
      alternatives: ["Augmentin 625mg", "Cefixime 200mg"],
    },
    {
      name: "Pantoprazole 40mg",
      timing: ["Morning"],
      dosage: "1 tablet before food",
      purpose: "Acid reflux / stomach protection",
      alternatives: ["Omeprazole 20mg", "Rabeprazole 20mg"],
    },
    {
      name: "Cetirizine 10mg",
      timing: ["Night"],
      dosage: "1 tablet",
      purpose: "Allergic symptoms",
      alternatives: ["Levocetirizine 5mg", "Fexofenadine 120mg"],
    },
  ],
};

const timingIcons: Record<string, React.ReactNode> = {
  Morning: <Sun size={12} />,
  Afternoon: <Sunset size={12} />,
  Night: <Moon size={12} />,
};

const PrescriptionResult = () => {
  const navigate = useNavigate();
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.1 } } };
  const fadeUp = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

  return (
    <div className="min-h-screen relative">
      <MandalaBackground />
      <div className="relative z-10 p-6 lg:p-12 max-w-2xl mx-auto">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate("/dashboard")} className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted transition-colors">
            <ArrowLeft size={18} />
          </button>
          <h1 className="font-display text-xl font-bold text-foreground">Prescription Result</h1>
          <div className="ml-auto flex gap-2">
            <button className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted">
              <Printer size={16} />
            </button>
            <button className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted">
              <Share2 size={16} />
            </button>
          </div>
        </motion.div>

        <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-5">
          {/* Doctor info */}
          <motion.div variants={fadeUp} className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-1">Prescribed By</p>
                <h2 className="font-display text-xl font-bold text-foreground">{mockPrescription.doctorName}</h2>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-1">Date</p>
                <p className="text-foreground text-sm font-semibold">{mockPrescription.date}</p>
              </div>
            </div>
          </motion.div>

          {/* Medicine rows */}
          {mockPrescription.medicines.map((med, idx) => (
            <motion.div key={idx} variants={fadeUp} className="bg-card border border-border rounded-2xl overflow-hidden">
              <div className="p-6">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-display font-bold text-foreground">{med.name}</h3>
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-lg">{med.dosage}</span>
                </div>

                {/* Timing chips */}
                <div className="flex gap-2 mb-3">
                  {med.timing.map((t) => (
                    <span key={t} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/15 text-primary text-xs font-semibold border border-primary/30">
                      {timingIcons[t]}
                      {t}
                    </span>
                  ))}
                </div>

                <p className="text-muted-foreground text-sm">{med.purpose}</p>

                {/* Alternatives toggle */}
                <button
                  onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                  className="flex items-center gap-1 mt-3 text-secondary text-xs font-display font-semibold hover:underline"
                >
                  Alternatives
                  {expandedIdx === idx ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
              </div>

              {expandedIdx === idx && (
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
          ))}
        </motion.div>
      </div>
    </div>
  );
};

export default PrescriptionResult;
