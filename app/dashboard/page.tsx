"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Pill, FileText, LogOut, History, Globe, User, Menu, X } from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";
import SanjeevaniLogo from "@/components/SanjeevaniLogo";

const languages = [
  { code: "en", name: "English", native: "English" },
  { code: "hi", name: "Hindi", native: "हिन्दी" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
  { code: "bn", name: "Bengali", native: "বাংলা" },
  { code: "mr", name: "Marathi", native: "मराठी" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ" },
  { code: "ml", name: "Malayalam", native: "മലയാളം" },
];

const Dashboard = () => {
  const router = useRouter();
  const [userName, setUserName] = useState("User");
  const [language, setLanguage] = useState("en");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);

  useEffect(() => {
    const name = localStorage.getItem("sanjeevani_user") || "User";
    setUserName(name);

    const savedLang = localStorage.getItem("sanjeevani_language") || "en";
    setLanguage(savedLang);

    // Fetch history count
    const userId = localStorage.getItem("sanjeevani_user_id");
    if (userId) {
      fetch(`/api/history/${userId}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.success) setHistoryCount((data.history || []).length);
        })
        .catch(() => {});
    }
  }, []);

  const handleLanguageChange = (code: string) => {
    setLanguage(code);
    localStorage.setItem("sanjeevani_language", code);
  };

  const handleLogout = () => {
    localStorage.removeItem("sanjeevani_user");
    localStorage.removeItem("sanjeevani_user_id");
    localStorage.removeItem("sanjeevani_language");
    router.push("/");
  };

  const stagger = {
    hidden: {},
    show: { transition: { staggerChildren: 0.1 } },
  };

  const fadeUp = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
  };

  return (
    <div className="min-h-screen flex relative">
      <MandalaBackground />

      {/* Mobile menu toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden bg-card/90 backdrop-blur border border-border rounded-lg p-2 text-foreground"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 left-0 h-screen w-64 bg-sidebar border-r border-sidebar-border z-40 flex flex-col transition-transform duration-300 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="p-6 border-b border-sidebar-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
              <User size={20} className="text-primary" />
            </div>
            <div>
              <p className="font-display font-semibold text-sidebar-foreground text-sm">{userName}</p>
              <p className="text-xs text-muted-foreground">Patient</p>
            </div>
          </div>
        </div>

        <div className="p-4 flex-1">
          {/* Language selector */}
          <div className="mb-6">
            <label className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Globe size={12} /> Language
            </label>
            <select
              value={language}
              onChange={(e) => handleLanguageChange(e.target.value)}
              className="w-full bg-sidebar-accent border border-sidebar-border rounded-lg px-3 py-2 text-sm text-sidebar-foreground outline-none focus:border-primary transition-colors"
            >
              {languages.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native} ({l.name})
                </option>
              ))}
            </select>
          </div>

          {/* Nav items */}
          <nav className="space-y-1">
            <button
              onClick={() => router.push("/history")}
              className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors text-sm"
            >
              <History size={18} />
              <span>Scan History</span>
              {historyCount > 0 && (
                <span className="ml-auto text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full font-semibold">{historyCount}</span>
              )}
            </button>
          </nav>
        </div>

        <div className="p-4 border-t border-sidebar-border">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors text-sm"
          >
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 relative z-10 p-6 lg:p-12">
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="show"
          className="max-w-4xl mx-auto"
        >
          {/* Hero greeting */}
          <motion.div variants={fadeUp} className="text-center mb-16 pt-8">
            <div className="flex justify-center mb-6">
              <SanjeevaniLogo size={72} breathing />
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-bold text-foreground mb-3">
              Namaste, <span className="text-primary">{userName}</span>
            </h1>
            <p className="text-muted-foreground text-lg">
              How can Sanjeevani help you today?
            </p>
          </motion.div>

          {/* Action cards */}
          <motion.div variants={fadeUp} className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ActionCard
              title="Scan Medicine Strip"
              description="Identify medicines, ingredients, dosage & more using AI vision"
              icon={<Pill size={36} />}
              variant="teal"
              onClick={() => router.push("/scan?type=medicine")}
            />
            <ActionCard
              title="Read Prescription"
              description="Decode handwritten prescriptions into clear, structured results"
              icon={<FileText size={36} />}
              variant="amber"
              onClick={() => router.push("/scan?type=prescription")}
            />
          </motion.div>
        </motion.div>
      </main>
    </div>
  );
};

const ActionCard = ({
  title,
  description,
  icon,
  variant,
  onClick,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  variant: "teal" | "amber";
  onClick: () => void;
}) => {
  const bgClass = variant === "teal" ? "bg-teal" : "bg-amber";
  const borderHover = variant === "teal" ? "hover:border-secondary" : "hover:border-primary";
  const glowClass = variant === "teal" ? "glow-pulse-cyan" : "glow-pulse-saffron";

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.03, rotateY: 3, rotateX: -2 }}
      whileTap={{ scale: 0.98 }}
      className={`${bgClass} border border-border ${borderHover} rounded-2xl p-8 text-left transition-all group cursor-pointer`}
      style={{ perspective: 800 }}
    >
      <div className={`w-16 h-16 rounded-xl bg-background/20 flex items-center justify-center mb-5 text-foreground group-hover:${glowClass} transition-all`}>
        {icon}
      </div>
      <h3 className="font-display text-xl font-bold text-foreground mb-2">{title}</h3>
      <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>
    </motion.button>
  );
};

export default Dashboard;
