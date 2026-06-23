"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Pill, FileText, LogOut, History, Globe, User, Menu, X, ChevronDown, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";
import SanjeevaniLogo from "@/components/SanjeevaniLogo";

const languages = [
  { code: "en",  name: "English",   native: "English" },
  { code: "hi",  name: "Hindi",     native: "हिन्दी" },
  { code: "ta",  name: "Tamil",     native: "தமிழ்" },
  { code: "te",  name: "Telugu",    native: "తెలుగు" },
  { code: "bn",  name: "Bengali",   native: "বাংলা" },
  { code: "mr",  name: "Marathi",   native: "मराठी" },
  { code: "kn",  name: "Kannada",   native: "ಕನ್ನಡ" },
  { code: "ml",  name: "Malayalam", native: "മലയാളം" },
  { code: "gu",  name: "Gujarati",  native: "ગુજરાતી" },
  { code: "pa",  name: "Punjabi",   native: "ਪੰਜਾਬੀ" },
  { code: "or",  name: "Odia",      native: "ଓଡ଼ିଆ" },
  { code: "as",  name: "Assamese",  native: "অসমীয়া" },
  { code: "ur",  name: "Urdu",      native: "اردو" },
  { code: "sa",  name: "Sanskrit",  native: "संस्कृतम्" },
  { code: "kok", name: "Konkani",   native: "कोंकणी" },
  { code: "mni", name: "Manipuri",  native: "মৈতৈলোন্" },
  { code: "ne",  name: "Nepali",    native: "नेपाली" },
  { code: "sd",  name: "Sindhi",    native: "سنڌي" },
  { code: "mai", name: "Maithili",  native: "मैथिली" },
  { code: "doi", name: "Dogri",     native: "डोगरी" },
  { code: "ks",  name: "Kashmiri",  native: "کٲشُر" },
  { code: "sat", name: "Santali",   native: "ᱥᱟᱱᱛᱟᱲᱤ" },
];

interface HistoryItem {
  id: number;
  scan_type: string;
  language: string;
  result: any;
  created_at: string;
}

const Dashboard = () => {
  const router = useRouter();
  const [userName, setUserName] = useState("User");
  const [role, setRole] = useState("patient");
  const [language, setLanguage] = useState("en");
  const [langOpen, setLangOpen] = useState(false);
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0, width: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    const name = localStorage.getItem("sanjeevani_user") || "User";
    setUserName(name);

    const savedRole = localStorage.getItem("sanjeevani_role") || "patient";
    setRole(savedRole);

    const savedLang = localStorage.getItem("sanjeevani_language") || "en";
    setLanguage(savedLang);

    // Fetch history
    fetch(`/api/history`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        if (data.success) {
          const hist = data.history || [];
          setHistoryItems(hist);
          setHistoryCount(hist.length);
        }
      })
      .catch(() => { })
      .finally(() => setHistoryLoading(false));
  }, []);

  const getDisplayName = (item: HistoryItem) => {
    const r = item.result;
    if (item.scan_type === "medicine") {
      return r?.medicine_name || "Unknown Medicine";
    }
    const meds = r?.medicines || [];
    if (meds.length > 0) return meds.map((m: any) => m.name).join(", ");
    return "Prescription";
  };

  const formatDate = (iso: string) => {
    try {
      // If the ISO string doesn't have a timezone offset or Z suffix, assume it is in UTC
      let dateStr = iso;
      if (iso && !iso.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(iso)) {
        dateStr = iso + "Z";
      }
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      return iso;
    }
  };

  const handleViewDetails = (item: HistoryItem) => {
    sessionStorage.setItem("scanResult", JSON.stringify(item.result));
    sessionStorage.setItem("scanType", item.scan_type);
    if (item.scan_type === "prescription") {
      router.push("/result/prescription");
    } else {
      router.push("/result/medicine");
    }
  };

  const handleLanguageChange = (code: string) => {
    setLanguage(code);
    setLangOpen(false);
    localStorage.setItem("sanjeevani_language", code);
  };

  const openDropdown = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setDropdownPos({ top: rect.bottom + 4, left: rect.left, width: rect.width });
    }
    setLangOpen((o) => !o);
  };

  // Close on outside click
  useEffect(() => {
    if (!langOpen) return;
    const handler = (e: MouseEvent) => {
      if (triggerRef.current && !triggerRef.current.contains(e.target as Node)) {
        setLangOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [langOpen]);

  const handleLogout = () => {
    localStorage.removeItem("sanjeevani_user");
    localStorage.removeItem("sanjeevani_role");
    localStorage.removeItem("sanjeevani_language");
    localStorage.removeItem("sanjeevani_token");
    
    // Clear cookie in background (best-effort)
    fetch("/api/auth/logout", { method: "POST", credentials: "include" }).catch(() => {});
    
    // Force a hard redirect to clear router cache and state
    window.location.href = "/";
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



      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 left-0 h-[100dvh] w-64 bg-sidebar border-r border-sidebar-border z-40 flex flex-col transition-transform duration-300 ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
          }`}
      >
        <div className="p-6 border-b border-sidebar-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
              <User size={20} className="text-primary" />
            </div>
            <div>
              <p className="font-display font-semibold text-sidebar-foreground text-sm">{userName}</p>
              <p className="text-xs text-muted-foreground capitalize">{role === "doctor" ? "Doctor / Pharmacist" : "Patient"}</p>
            </div>
          </div>
        </div>

        <div className="p-4 flex-1 overflow-y-auto">
          {/* Language selector — custom fixed-position dropdown (escapes sidebar transform stacking context) */}
          <div className="mb-6">
            <label className="text-xs text-muted-foreground font-display uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Globe size={12} /> Language
            </label>
            <button
              ref={triggerRef}
              onClick={openDropdown}
              className="w-full flex items-center justify-between bg-sidebar-accent border border-sidebar-border rounded-lg px-3 py-2 text-sm text-sidebar-foreground outline-none focus:border-primary transition-colors cursor-pointer hover:bg-sidebar-accent/80"
            >
              <span>
                {(() => { const l = languages.find(x => x.code === language); return l ? `${l.native} (${l.name})` : "English"; })()}
              </span>
              <ChevronDown size={14} className={`transition-transform duration-200 ${langOpen ? "rotate-180" : ""}`} />
            </button>
          </div>

          {/* Fixed-position dropdown panel — rendered outside sidebar's stacking context via inline fixed styles */}
          {langOpen && (
            <div
              style={{
                position: "fixed",
                top: dropdownPos.top,
                left: dropdownPos.left,
                width: dropdownPos.width,
                zIndex: 99999,
              }}
              className="bg-card border border-border rounded-lg shadow-2xl overflow-hidden"
            >
              <div className="max-h-64 overflow-y-auto">
                {languages.map((l) => (
                  <button
                    key={l.code}
                    onMouseDown={(e) => { e.preventDefault(); handleLanguageChange(l.code); }}
                    className={`w-full flex items-center justify-between text-left px-3 py-2 text-sm transition-colors ${
                      language === l.code
                        ? "bg-primary/15 text-primary font-semibold"
                        : "text-foreground hover:bg-muted"
                    }`}
                  >
                    <span>{l.native} <span className="text-xs text-muted-foreground">({l.name})</span></span>
                    {language === l.code && <Check size={12} className="text-primary shrink-0" />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Nav items */}
          <nav className="space-y-1">
            {role === "doctor" && (
              <button
                onClick={() => router.push("/admin")}
                className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent transition-colors text-sm"
              >
                <FileText size={18} />
                <span>Admin Dashboard</span>
              </button>
            )}

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

          {/* Symmetrical Layout for Dashboard Actions & Recent Scans */}
          <motion.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* Left side: Action Card */}
            <div className="lg:col-span-5 flex flex-col">
              <ActionCard
                title="Read Prescription"
                description="Decode handwritten prescriptions into clear, structured daily schedules."
                icon={<FileText size={32} />}
                variant="amber"
                onClick={() => router.push("/scan?type=prescription")}
              />
            </div>

            {/* Right side: C (Recent Scans Box) */}
            <div className="lg:col-span-7 flex flex-col">
              <div className="bg-card/60 backdrop-blur border border-border rounded-2xl p-6 shadow-lg flex flex-col h-full justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-display text-xl font-bold text-foreground flex items-center gap-2">
                      <History size={20} className="text-primary" />
                      Recent Scans
                    </h2>
                    {historyItems.length > 0 && (
                      <button
                        onClick={() => router.push("/history")}
                        className="text-primary hover:text-primary/80 hover:underline text-sm font-semibold transition-colors"
                      >
                        View All
                      </button>
                    )}
                  </div>

                  {historyLoading ? (
                    <div className="text-center py-16">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                      <p className="text-muted-foreground text-xs font-display">Loading scans...</p>
                    </div>
                  ) : historyItems.length === 0 ? (
                    <div className="text-center py-16 text-muted-foreground text-sm font-display">
                      No recent scans. Your analyzed medicines and prescriptions will appear here.
                    </div>
                  ) : (
                    <div className="space-y-2.5 max-h-[290px] overflow-y-auto pr-1">
                      {historyItems.slice(0, 5).map((item) => (
                        <div
                          key={item.id}
                          onClick={() => handleViewDetails(item)}
                          className="flex items-center justify-between p-4 bg-muted/20 hover:bg-muted/50 border border-border/40 rounded-xl cursor-pointer transition-all group hover:scale-[1.005] hover:shadow-sm"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                              item.scan_type === "medicine" ? "bg-secondary/15 text-secondary" : "bg-primary/15 text-primary"
                            }`}>
                              {item.scan_type === "medicine" ? <Pill size={16} /> : <FileText size={16} />}
                            </div>
                            <div className="min-w-0">
                              <h4 className="font-display font-bold text-sm text-foreground group-hover:text-primary transition-colors truncate">
                                {getDisplayName(item)}
                              </h4>
                              <p className="text-[10px] text-muted-foreground mt-0.5 font-display">
                                {formatDate(item.created_at)} &bull; {languages.find(l => l.code === item.language)?.name || item.language}
                              </p>
                            </div>
                          </div>
                          <span className="text-xs text-secondary group-hover:text-secondary/80 group-hover:underline font-bold font-display shrink-0 ml-4 flex items-center gap-1">
                            View &rarr;
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
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
      whileHover={{ scale: 1.02, rotateY: 2, rotateX: -1 }}
      whileTap={{ scale: 0.98 }}
      className={`${bgClass} border border-border ${borderHover} rounded-2xl p-6 md:p-7 text-left transition-all group cursor-pointer w-full flex-1 flex flex-col`}
      style={{ perspective: 800 }}
    >
      <div className={`w-12 h-12 rounded-xl bg-background/20 flex items-center justify-center mb-4 text-foreground group-hover:${glowClass} transition-all`}>
        {icon}
      </div>
      <h3 className="font-display text-lg font-bold text-foreground mb-1">{title}</h3>
      <p className="text-muted-foreground text-xs md:text-sm leading-relaxed flex-1">{description}</p>
    </motion.button>
  );
};

export default Dashboard;
