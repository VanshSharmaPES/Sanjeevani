"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Pill, FileText, Trash2, ChevronDown, ChevronUp, Inbox } from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";

interface HistoryItem {
  id: number;
  scan_type: string;
  language: string;
  result: any;
  created_at: string;
}

const ScanHistory = () => {
  const router = useRouter();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    fetch(`/api/history`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        if (data.success) setItems(data.history || []);
      })
      .catch(() => { })
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = (id: number) => {
    setDeletingId(id);
    fetch(`/api/history/${id}`, { method: "DELETE", credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        if (data.success) {
          setTimeout(() => {
            setItems((prev) => prev.filter((i) => i.id !== id));
            setDeletingId(null);
          }, 400);
        } else {
          setDeletingId(null);
        }
      })
      .catch(() => setDeletingId(null));
  };

  const getDisplayName = (item: HistoryItem) => {
    const r = item.result;
    if (item.scan_type === "medicine") {
      return r?.medicine_name || "Unknown Medicine";
    }
    const meds = r?.medicines || [];
    if (meds.length > 0) return meds.map((m: any) => m.name).join(", ");
    return "Prescription";
  };

  const getDetails = (item: HistoryItem) => {
    const r = item.result;
    if (item.scan_type === "medicine") {
      const parts = [];
      if (r?.active_salts?.length) parts.push(`Salts: ${r.active_salts.join(", ")}`);
      if (r?.conditions?.length) parts.push(`Treats: ${r.conditions.join(", ")}`);
      if (r?.what_it_does) parts.push(r.what_it_does);
      return parts.join(". ") || "No details available.";
    }
    const meds = r?.medicines || [];
    return meds.map((m: any) => `${m.name} — ${m.frequency || ""} ${m.timing || ""}`).join("; ") || "No details.";
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      return iso;
    }
  };

  return (
    <div className="min-h-screen relative">
      <MandalaBackground />
      <div className="relative z-10 p-6 lg:p-12 max-w-2xl mx-auto">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-10">
          <button onClick={() => router.push("/dashboard")} className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted transition-colors">
            <ArrowLeft size={18} />
          </button>
          <h1 className="font-display text-2xl font-bold text-foreground">Scan History</h1>
        </motion.div>

        {loading ? (
          <div className="text-center py-20">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground text-sm">Loading history...</p>
          </div>
        ) : items.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <Inbox size={48} className="mx-auto mb-4 text-muted-foreground opacity-40" />
            <h3 className="font-display text-lg font-semibold text-foreground mb-2">No scans yet</h3>
            <p className="text-muted-foreground text-sm mb-6">Your scan history will appear here after you analyze a medicine or prescription.</p>
            <button
              onClick={() => router.push("/dashboard")}
              className="px-6 py-2.5 bg-primary text-primary-foreground font-display font-semibold rounded-xl text-sm"
            >
              Start Scanning
            </button>
          </motion.div>
        ) : (
          <div className="relative">
            <div className="absolute left-5 top-0 bottom-0 w-px bg-border" />

            <AnimatePresence>
              {items.map((item, idx) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{
                    opacity: deletingId === item.id ? 0 : 1,
                    x: deletingId === item.id ? 40 : 0,
                    scale: deletingId === item.id ? 0.9 : 1,
                  }}
                  exit={{ opacity: 0, x: 40 }}
                  transition={{ duration: 0.4, delay: idx * 0.08 }}
                  className="relative pl-14 pb-8"
                >
                  <div className={`absolute left-3 top-2 w-5 h-5 rounded-full border-2 flex items-center justify-center ${item.scan_type === "medicine" ? "border-secondary bg-secondary/20" : "border-primary bg-primary/20"
                    }`}>
                    {item.scan_type === "medicine" ? <Pill size={10} className="text-secondary" /> : <FileText size={10} className="text-primary" />}
                  </div>

                  <div className="bg-card border border-border rounded-2xl p-5">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-xs text-muted-foreground">{formatDate(item.created_at)}</p>
                        <h3 className="font-display font-bold text-foreground mt-1">{getDisplayName(item)}</h3>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-lg">{item.language}</span>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className={`w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all ${deletingId === item.id ? "animate-[shake_0.3s_ease-in-out]" : ""
                            }`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    <button
                      onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                      className="flex items-center gap-1 text-secondary text-xs font-display font-semibold hover:underline"
                    >
                      Details
                      {expandedId === item.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>

                    {expandedId === item.id && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="text-muted-foreground text-sm mt-3 leading-relaxed"
                      >
                        {getDetails(item)}
                      </motion.p>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
};

export default ScanHistory;
