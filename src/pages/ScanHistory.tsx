import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Pill, FileText, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { useNavigate } from "react-router-dom";
import MandalaBackground from "@/components/MandalaBackground";

const mockHistory = [
  { id: "1", type: "medicine", date: "22 Feb 2026, 10:45 AM", language: "Hindi", names: ["Paracetamol 500mg"], details: "Brand: Crocin Advance. Treats fever, headache, body pain." },
  { id: "2", type: "prescription", date: "20 Feb 2026, 3:30 PM", language: "English", names: ["Amoxicillin", "Pantoprazole", "Cetirizine"], details: "Prescribed by Dr. Ananya Sharma on 18 Feb 2026." },
  { id: "3", type: "medicine", date: "15 Feb 2026, 9:00 AM", language: "Tamil", names: ["Azithromycin 500mg"], details: "Brand: Azithral. Used for bacterial infections." },
];

const ScanHistory = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState(mockHistory);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = (id: string) => {
    setDeletingId(id);
    setTimeout(() => {
      setItems((prev) => prev.filter((i) => i.id !== id));
      setDeletingId(null);
    }, 500);
  };

  return (
    <div className="min-h-screen relative">
      <MandalaBackground />
      <div className="relative z-10 p-6 lg:p-12 max-w-2xl mx-auto">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4 mb-10">
          <button onClick={() => navigate("/dashboard")} className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center text-foreground hover:bg-muted transition-colors">
            <ArrowLeft size={18} />
          </button>
          <h1 className="font-display text-2xl font-bold text-foreground">Scan History</h1>
        </motion.div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
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
                {/* Timeline node */}
                <div className={`absolute left-3 top-2 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                  item.type === "medicine" ? "border-secondary bg-secondary/20" : "border-primary bg-primary/20"
                }`}>
                  {item.type === "medicine" ? <Pill size={10} className="text-secondary" /> : <FileText size={10} className="text-primary" />}
                </div>

                <div className="bg-card border border-border rounded-2xl p-5">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="text-xs text-muted-foreground">{item.date}</p>
                      <h3 className="font-display font-bold text-foreground mt-1">{item.names.join(", ")}</h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-lg">{item.language}</span>
                      <button
                        onClick={() => handleDelete(item.id)}
                        className={`w-8 h-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all ${
                          deletingId === item.id ? "animate-[shake_0.3s_ease-in-out]" : ""
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
                      {item.details}
                    </motion.p>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default ScanHistory;
