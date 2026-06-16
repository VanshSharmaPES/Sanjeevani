"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Printer, Share2, Search, PlusCircle, FileText, CheckCircle, 
  ArrowLeft, Globe, Send, User, ChevronRight, UserCheck 
} from "lucide-react";
import { useRouter } from "next/navigation";
import MandalaBackground from "@/components/MandalaBackground";

interface GuideData {
  medicineName: string;
  activeSalts: string;
  dosage: string;
  frequency: string;
  timing: string;
  language: string;
  doctorNotes: string;
  adviceText: string;
  adviceTextEn: string;
}

const languages = [
  { code: "en",  name: "English" },
  { code: "hi",  name: "Hindi" },
  { code: "ta",  name: "Tamil" },
  { code: "te",  name: "Telugu" },
  { code: "bn",  name: "Bengali" },
  { code: "mr",  name: "Marathi" },
  { code: "kn",  name: "Kannada" },
  { code: "ml",  name: "Malayalam" },
  { code: "gu",  name: "Gujarati" },
  { code: "pa",  name: "Punjabi" },
  { code: "or",  name: "Odia" },
  { code: "as",  name: "Assamese" },
  { code: "ur",  name: "Urdu" },
  { code: "sa",  name: "Sanskrit" },
  { code: "kok", name: "Konkani" },
  { code: "mni", name: "Manipuri" },
  { code: "ne",  name: "Nepali" },
  { code: "sd",  name: "Sindhi" },
  { code: "mai", name: "Maithili" },
  { code: "doi", name: "Dogri" },
  { code: "ks",  name: "Kashmiri" },
  { code: "sat", name: "Santali" },
];

interface AutoResizeTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  value: string;
}

const AutoResizeTextarea = ({ value, className = "", ...props }: AutoResizeTextareaProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, [value]);

  return (
    <textarea
      ref={textareaRef}
      value={value}
      className={`${className} resize-none overflow-hidden`}
      rows={1}
      {...props}
    />
  );
};

const containsTemplatePayload = (value: string): boolean => {
  if (!value) return false;
  const pattern = /(\{\{|\}\}|\{%|%\}|\$\{|\<%|%\>|\#\{|`|__|\b(eval|exec|import|globals|locals|subclasses|constructor|prototype|function)\b)/i;
  const redosPattern = /\([^)]+[*+]\)[*+]/;
  return pattern.test(value) || redosPattern.test(value);
};

export default function AdminDashboard() {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState("hi");
  const [loading, setLoading] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [shareSuccess, setShareSuccess] = useState(false);

  // Form Fields
  const [medName, setMedName] = useState("");
  const [salts, setSalts] = useState("");
  const [dosage, setDosage] = useState("");
  const [frequency, setFrequency] = useState("");
  const [timing, setTiming] = useState("");
  const [docNotes, setDocNotes] = useState("");
  const [doctorName, setDoctorName] = useState("Dr. Sanjeevani AI");
  const [generationTime, setGenerationTime] = useState("");

  // Generated Guide state
  const [generatedGuide, setGeneratedGuide] = useState<GuideData | null>(null);

  // Role Guard
  useEffect(() => {
    const savedRole = localStorage.getItem("sanjeevani_role");
    const savedUser = localStorage.getItem("sanjeevani_user") || "Doctor";
    if (savedRole !== "doctor") {
      router.push("/dashboard");
    } else {
      setAuthorized(true);
      setDoctorName(`Dr. ${savedUser}`);
    }
  }, [router]);

  // Debounced Keystroke Search Autocomplete
  useEffect(() => {
    const query = searchQuery.trim();
    if (query.length < 3) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    const delayDebounceFn = setTimeout(() => {
      const performSearch = async () => {
        setSearching(true);
        try {
          const res = await fetch(`/api/medicines/search?q=${encodeURIComponent(query)}`);
          const data = await res.json();
          const results = Array.isArray(data) ? data : [];
          setSearchResults(results);
          setShowDropdown(results.length > 0);
        } catch (err) {
          console.error("Auto search error:", err);
        } finally {
          setSearching(false);
        }
      };
      performSearch();
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  const handleSearch = async () => {
    const query = searchQuery.trim();
    if (!query) return;
    if (containsTemplatePayload(query)) {
      alert("Search query contains disallowed template patterns or unsafe code payloads.");
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(`/api/medicines/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      const results = Array.isArray(data) ? data : [];
      setSearchResults(results);
      setShowDropdown(results.length > 0);
      if (!Array.isArray(data)) {
        alert(data.message || "Search failed. Backend API server error.");
      } else if (results.length === 0) {
        alert("No medicines found matching your search. You can manually enter the details below.");
      }
    } catch (err) {
      console.error("Search error:", err);
      alert("Failed to search medicines. Connection to the API failed.");
    } finally {
      setSearching(false);
    }
  };

  const handleSelectMedicine = async (med: any) => {
    setMedName(med.medicineName);
    setSalts(med.activeSalts);
    
    // Clear dropdown list immediately
    setShowDropdown(false);
    setSearchResults([]);

    // Loading states for baseline fields
    setDosage("Generating..");
    setFrequency("Generating..");
    setTiming("Generating..");
    setDocNotes("Generating..");
    setAiGenerating(true);

    try {
      const res = await fetch(
        `/api/medicines/dosage-info?name=${encodeURIComponent(med.medicineName)}&composition=${encodeURIComponent(med.activeSalts)}`
      );
      const data = await res.json();
      
      setDosage(data.dosage || "1 Tablet");
      setFrequency(data.frequency || "Twice a day (1-0-1)");
      setTiming(data.timing || "After meals (PC)");
      setDocNotes(data.doctorNotes || "");
    } catch (err) {
      console.error("AI prefill error:", err);
      // Fallback parsing if backend or API fails
      let defaultDosage = "1 Tablet";
      if (med.unit && med.unit.toLowerCase() !== "tablet") {
        defaultDosage = med.unit.charAt(0).toUpperCase() + med.unit.slice(1);
      }
      setDosage(defaultDosage);
      setFrequency("Twice a day (1-0-1)");
      setTiming("After meals (PC)");
      
      let notes = "";
      if (med.uses) notes += `Uses: ${med.uses}. `;
      if (med.sideEffects) notes += `Side Effects: ${med.sideEffects}. `;
      setDocNotes(notes.trim());
    } finally {
      setAiGenerating(false);
    }
  };

  const handleGenerate = async () => {
    if (!medName) return;
    if (
      containsTemplatePayload(medName) ||
      containsTemplatePayload(salts) ||
      containsTemplatePayload(dosage) ||
      containsTemplatePayload(frequency) ||
      containsTemplatePayload(timing) ||
      containsTemplatePayload(docNotes)
    ) {
      alert("Error: Input contains disallowed template patterns or unsafe code payloads.");
      return;
    }
    setLoading(true);
    
    const now = new Date().toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "medium",
    });
    setGenerationTime(now);
    
    const langName = languages.find(l => l.code === selectedLanguage)?.name || "Hindi";
    const adviceEn = `PRESCRIPTION & MEDICATION GUIDE
---------------------------------
• Medicine Name: ${medName}
• Composition: ${salts}
• Dosage: ${dosage}
• Frequency: ${frequency}
• Food Relation: ${timing}
• Special Warnings: ${docNotes || "No special warnings. Take as directed by practitioner."}`;

    try {
      if (selectedLanguage === "en") {
        setGeneratedGuide({
          medicineName: medName,
          activeSalts: salts,
          dosage: dosage,
          frequency: frequency,
          timing: timing,
          language: langName,
          doctorNotes: docNotes,
          adviceText: adviceEn,
          adviceTextEn: adviceEn
        });
      } else {
        // Translate advice text and doctor notes in parallel
        const translateAdvicePromise = fetch("/api/translate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: adviceEn,
            language_code: selectedLanguage,
          }),
        }).then(r => r.json());

        const translateNotesPromise = docNotes ? fetch("/api/translate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: docNotes,
            language_code: selectedLanguage,
          }),
        }).then(r => r.json()) : Promise.resolve({ translated: "" });

        const [adviceData, notesData] = await Promise.all([translateAdvicePromise, translateNotesPromise]);

        setGeneratedGuide({
          medicineName: medName,
          activeSalts: salts,
          dosage: dosage,
          frequency: frequency,
          timing: timing,
          language: langName,
          doctorNotes: notesData.translated || docNotes,
          adviceText: adviceData.translated || adviceEn,
          adviceTextEn: adviceEn
        });
      }
    } catch (err) {
      console.error("Translation error:", err);
      setGeneratedGuide({
        medicineName: medName,
        activeSalts: salts,
        dosage: dosage,
        frequency: frequency,
        timing: timing,
        language: langName,
        doctorNotes: docNotes,
        adviceText: adviceEn,
        adviceTextEn: adviceEn
      });
    } finally {
      setLoading(false);
    }
  };

  const [copied, setCopied] = useState(false);
  const [sharingLoading, setSharingLoading] = useState(false);

  const getShareText = () => {
    if (!generatedGuide) return "";
    return `⚕️ *Sanjeevani AI - Medication Handout* ⚕️\n\n` +
      `*Medicine:* ${generatedGuide.medicineName}\n` +
      `*Composition:* ${generatedGuide.activeSalts}\n` +
      `*Dosage:* ${generatedGuide.dosage}\n` +
      `*Frequency:* ${generatedGuide.frequency}\n` +
      `*Timing:* ${generatedGuide.timing}\n\n` +
      `*Instructions (${generatedGuide.language}):*\n${generatedGuide.adviceText}\n\n` +
      `*Instructions (English):*\n${generatedGuide.adviceTextEn}\n\n` +
      (generatedGuide.doctorNotes ? `*Practitioner Notes:*\n${generatedGuide.doctorNotes}\n\n` : "") +
      `_Generated via Sanjeevani AI Patient Assistant_`;
  };

  const triggerPrint = () => {
    window.print();
  };

  const generatePDFBlob = async (): Promise<Blob | null> => {
    const element = document.getElementById("printable-handout");
    if (!element) return null;

    try {
      // Dynamically import client-only packages to prevent SSR build issues
      const html2canvas = (await import("html2canvas")).default;
      const { jsPDF } = await import("jspdf");

      const canvas = await html2canvas(element, {
        scale: 2, // High resolution
        useCORS: true,
        backgroundColor: "#ffffff", // Minimalistic white design
      });

      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a4",
      });

      const imgWidth = 210; // A4 page width
      const pageHeight = 297; // A4 page height
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      while (heightLeft >= 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      return pdf.output("blob");
    } catch (error) {
      console.error("Failed to generate PDF:", error);
      return null;
    }
  };

  const handleSharePDF = async () => {
    setSharingLoading(true);
    try {
      const blob = await generatePDFBlob();
      if (!blob) {
        alert("Failed to generate PDF guide. Please try again.");
        setSharingLoading(false);
        return;
      }
      const fileName = `${generatedGuide?.medicineName.replace(/\s+/g, "_") || "Medication"}_Guide.pdf`;
      const file = new File([blob], fileName, { type: "application/pdf" });

      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: "Sanjeevani AI Medication Handout",
          text: `Here is the personalized bilingual medication guide for ${generatedGuide?.medicineName}.`
        });
        setShareSuccess(true);
        setTimeout(() => {
          setShareSuccess(false);
          setShowShareModal(false);
        }, 2000);
      } else {
        // Fallback: download locally
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = fileName;
        a.click();
        URL.revokeObjectURL(url);
        
        alert("Native PDF sharing is not supported by your current browser/device. We have downloaded the PDF file to your system instead so you can attach and send it manually.");
        setShowShareModal(false);
      }
    } catch (err) {
      console.error("Error sharing PDF:", err);
    } finally {
      setSharingLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    setSharingLoading(true);
    try {
      const blob = await generatePDFBlob();
      if (!blob) {
        alert("Failed to generate PDF.");
        setSharingLoading(false);
        return;
      }
      const fileName = `${generatedGuide?.medicineName.replace(/\s+/g, "_") || "Medication"}_Guide.pdf`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(url);
      
      setShareSuccess(true);
      setTimeout(() => {
        setShareSuccess(false);
        setShowShareModal(false);
      }, 1500);
    } catch (err) {
      console.error("Download error:", err);
    } finally {
      setSharingLoading(false);
    }
  };

  const handleCopyClipboard = () => {
    navigator.clipboard.writeText(getShareText());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence mode="wait">
      {!authorized ? (
        <motion.div
          key="loading"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="min-h-screen bg-background flex items-center justify-center"
        >
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </motion.div>
      ) : (
        <motion.div
          key="admin-content"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="min-h-screen relative bg-background print:bg-white text-foreground print:text-black print:!opacity-100 print:!transform-none"
        >
      <div className="print:hidden">
        <MandalaBackground />
      </div>

      {/* Main Container */}
      <div className="relative z-10 p-6 lg:p-12 max-w-6xl mx-auto print:p-0">
        
        {/* Navigation & Header */}
        <div className="flex items-center justify-between mb-8 print:hidden">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => router.push("/dashboard")}
              className="w-10 h-10 rounded-xl bg-card border border-border flex items-center justify-center hover:bg-muted transition-colors"
            >
              <ArrowLeft size={18} />
            </button>
            <div>
              <h1 className="font-display text-2xl font-bold">Admin Guide Creator</h1>
              <p className="text-muted-foreground text-sm">For Doctors &amp; Pharmacists</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
            <UserCheck size={16} className="text-emerald-500" />
            <span className="text-xs font-semibold text-emerald-500">Dispensing Authorized</span>
          </div>
        </div>

        {/* Print Layout Header (Hidden on screen, shown on paper) */}
        <div className="hidden print:block border-b-2 border-black pb-3 mb-4">
          <div className="flex justify-between items-end">
            <div>
              <h1 className="text-2xl font-bold">SANJEEVANI</h1>
              <p className="text-sm">Personalized Medication Guide</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold">Date: {new Date().toLocaleDateString("en-IN")}</p>
              <p className="text-xs">Digital Dispensing System</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 print:block">
          
          {/* Left Panel: Creation Form (Hidden during printing) */}
          <div className="lg:col-span-5 space-y-6 print:hidden">
            <div className="bg-card border border-border rounded-2xl p-6 relative">
              <h2 className="font-display font-bold text-lg mb-4 flex items-center gap-2">
                <Search size={18} className="text-primary" />
                Search Indian Medicines
              </h2>
              <div className="flex gap-2">
                <input 
                  type="text"
                  placeholder="e.g. Dolo, Augmentin, Pantocid..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
                  className="flex-1 bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary"
                />
                <button 
                  onClick={handleSearch}
                  disabled={searching}
                  className="px-4 py-2 bg-primary text-primary-foreground text-sm font-semibold rounded-xl disabled:opacity-50 flex items-center gap-1.5"
                >
                  {searching ? (
                    <div className="w-3.5 h-3.5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                  ) : "Find"}
                </button>
              </div>

              {/* Suggestions Dropdown */}
              <AnimatePresence>
                {showDropdown && searchResults.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute left-6 right-6 mt-2 bg-card border border-border rounded-xl shadow-2xl z-25 max-h-60 overflow-y-auto divide-y divide-border"
                  >
                    {searchResults.map((med, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSelectMedicine(med)}
                        className="w-full px-4 py-3 text-left hover:bg-muted/60 transition-colors flex flex-col gap-0.5"
                      >
                        <span className="font-semibold text-sm text-foreground">{med.medicineName}</span>
                        <span className="text-xs text-muted-foreground line-clamp-1">{med.activeSalts} • {med.manufacturer}</span>
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
              <h2 className="font-display font-bold text-lg flex items-center gap-2">
                <PlusCircle size={18} className="text-secondary" />
                Create Medication Handout
              </h2>
              
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Medicine Name</label>
                <AutoResizeTextarea 
                  value={medName}
                  onChange={(e) => setMedName(e.target.value)}
                  placeholder="e.g. Dolo 650"
                  className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1">Active Salts / Ingredients</label>
                <AutoResizeTextarea 
                  value={salts}
                  onChange={(e) => setSalts(e.target.value)}
                  placeholder="e.g. Paracetamol IP 650mg"
                  className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Dosage</label>
                  <AutoResizeTextarea 
                    value={dosage}
                    onChange={(e) => setDosage(e.target.value)}
                    disabled={aiGenerating}
                    placeholder="e.g. 500mg"
                    className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Frequency</label>
                  <AutoResizeTextarea 
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    disabled={aiGenerating}
                    placeholder="e.g. Twice a day (1-0-1)"
                    className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1">Timing / Meal Relation</label>
                <AutoResizeTextarea 
                  value={timing}
                  onChange={(e) => setTiming(e.target.value)}
                  disabled={aiGenerating}
                  placeholder="e.g. After meals (PC)"
                  className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1">Target Handout Language</label>
                <select 
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  disabled={aiGenerating}
                  className="w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm outline-none focus:border-primary disabled:opacity-60"
                >
                  {languages.map(l => (
                    <option key={l.code} value={l.code}>{l.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1">Doctor Specific Advice (Optional)</label>
                <AutoResizeTextarea 
                  value={docNotes}
                  onChange={(e) => setDocNotes(e.target.value)}
                  disabled={aiGenerating}
                  placeholder="Add custom warnings or instructions..."
                  className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                />
              </div>

              <button 
                onClick={handleGenerate}
                disabled={loading || !medName || aiGenerating}
                className="w-full py-3 bg-secondary text-secondary-foreground font-display font-semibold rounded-xl hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              >
                {aiGenerating ? "AI Baseline Generating..." : loading ? "Generating Guide..." : "Create Guide & Handout"}
              </button>
            </div>
          </div>

          {/* Right Panel: Handout Preview (Printed on paper) */}
          <div className="lg:col-span-7 print:block">
            {generatedGuide ? (
              <div className="space-y-6">
                
                {/* Print and Share Action Panel (Hidden on print) */}
                <div className="flex justify-end gap-3 print:hidden">
                  <button 
                    onClick={triggerPrint}
                    className="px-5 py-2.5 bg-primary text-primary-foreground font-semibold rounded-xl flex items-center gap-2 hover:opacity-90 transition-opacity"
                  >
                    <Printer size={16} />
                    Print Handout
                  </button>
                  <button 
                    onClick={() => setShowShareModal(true)}
                    className="px-5 py-2.5 bg-card border border-border text-foreground font-semibold rounded-xl flex items-center gap-2 hover:bg-muted transition-colors"
                  >
                    <Share2 size={16} />
                    Share Digitally
                  </button>
                </div>

                {/* Printable Handout Content */}
                <div id="printable-handout" className="w-full bg-white text-zinc-800 p-8 shadow-sm border border-zinc-100 rounded-3xl space-y-5 print:shadow-none print:border-0 print:p-0">
                  <style dangerouslySetInnerHTML={{__html: `
                    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
                    #printable-handout * { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
                    @media print {
                      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                      #printable-handout { margin: 0; padding: 32px 40px; max-width: 100%; background: white !important; color: black !important; }
                      @page { size: A4 portrait; margin: 0; }
                    }
                  `}} />

                  {/* ── HEADER ──────────────────────────────────────────────── */}
                  <header className="pb-5 border-b-2 border-zinc-200 print:border-zinc-300">
                    {/* Brand mark */}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-600 text-lg">✦</span>
                        <span className="text-[13px] font-semibold tracking-[0.18em] text-zinc-800 uppercase print:text-black">
                          Sanjeevani
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-400 mt-0.5 ml-6 tracking-wide">
                        AI-Powered Medication Guide
                      </p>
                    </div>
                  </header>

                  {/* ── MEDICINE ITEM ───────────────────────────────────────────── */}
                  <section className="py-4 print:break-inside-avoid border-b-2 border-zinc-200 print:border-zinc-300">
                    <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-medium pb-2">
                      Prescribed Medicine
                    </p>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3.5">
                        {/* Index number */}
                        <span className="mt-0.5 text-xs font-semibold text-zinc-300 tabular-nums w-4 shrink-0 print:text-zinc-400">
                          01
                        </span>
                        <div>
                          <div className="flex flex-wrap items-baseline gap-2">
                            <span className="text-[15px] font-semibold text-zinc-900 print:text-black">
                              {generatedGuide.medicineName}
                            </span>
                            {/* Antibiotic indicator if name/notes mention it */}
                            {(generatedGuide.medicineName.toLowerCase().includes("antibiotic") || (generatedGuide.doctorNotes && generatedGuide.doctorNotes.toLowerCase().includes("antibiotic"))) && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium tracking-wide uppercase bg-amber-50 text-amber-700 print:bg-transparent print:border print:border-amber-300">
                                Antibiotic
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-zinc-400 mt-0.5 font-normal">
                            {generatedGuide.activeSalts}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Core Instructions */}
                    <div className="mt-4 ml-7 grid grid-cols-4 divide-x-2 divide-zinc-200 print:divide-zinc-300">
                      {[
                        { label: "Dose", value: dosage },
                        { label: "Frequency", value: frequency },
                        { label: "Timing", value: timing },
                        { label: "Duration", value: "As directed" },
                      ].map(({ label, value }) => (
                        <div key={label} className="px-4 first:pl-0 last:pr-0">
                          <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-medium">
                            {label}
                          </p>
                          <p className="text-[12px] text-zinc-700 mt-0.5 leading-snug print:text-black">
                            {value}
                          </p>
                        </div>
                      ))}
                    </div>

                    {/* Active Salts tags */}
                    {generatedGuide.activeSalts && (
                      <div className="mt-4 ml-7">
                        <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-medium mb-1.5">
                          Active Salts
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {generatedGuide.activeSalts.split('+').map(s => s.trim()).filter(Boolean).map((salt) => (
                            <span
                              key={salt}
                              className="text-[10px] text-zinc-500 bg-zinc-50 border border-zinc-100 px-2 py-0.5 rounded print:bg-transparent print:border-zinc-200 print:text-zinc-600"
                            >
                              {salt}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </section>

                  {/* ── BILINGUAL INSTRUCTIONS ──────────────────────────────── */}
                  <section className="py-4 border-b-2 border-zinc-200 print:border-zinc-300">
                    <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-medium mb-2">
                      Handout Instructions ({generatedGuide.language})
                    </p>
                    <p className="text-[12px] text-zinc-600 leading-relaxed whitespace-pre-line print:text-black">
                      {generatedGuide.adviceText}
                    </p>
                  </section>

                  {/* ── CLINICAL NOTES ────────────────────────────────────────── */}
                  {generatedGuide.doctorNotes && (
                    <section className="py-4 border-b-2 border-zinc-200 print:border-zinc-300 print:break-inside-avoid">
                      <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-medium mb-2">
                        Clinical Notes
                      </p>
                      <div className="border-2 border-zinc-200 rounded-sm px-4 py-3.5 print:border-zinc-300">
                        <p className="text-[12px] text-zinc-600 leading-relaxed print:text-black">
                          {generatedGuide.doctorNotes}
                        </p>
                      </div>
                    </section>
                  )}

                  {/* ── FOOTER ──────────────────────────────────────────────── */}
                  <footer className="pt-4 flex items-center justify-between print:break-inside-avoid">
                    <div className="flex items-center gap-1.5">
                      <span className="text-emerald-500 text-sm">✓</span>
                      <span className="text-[11px] text-emerald-600 font-bold print:text-zinc-600">
                        Digitally verified via Sanjeevani AI
                      </span>
                    </div>
                    <p className="text-[10px] text-zinc-500 font-bold text-right max-w-[280px] leading-snug print:text-zinc-700">
                      For informational use only. Always consult a qualified healthcare professional before taking or changing medication.
                    </p>
                  </footer>
                </div>
              </div>
            ) : (
              <div className="bg-card/40 border-2 border-dashed border-border rounded-3xl p-12 text-center flex flex-col items-center justify-center min-h-[400px]">
                <FileText size={48} className="text-muted-foreground opacity-30 mb-4" />
                <h3 className="font-display font-semibold text-lg mb-2">No Handout Active</h3>
                <p className="text-muted-foreground text-sm max-w-sm">
                  Fill in the details on the left, or use the Quick Search cache, to generate a printable medication guide.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Share Modal Dialog */}
      <AnimatePresence>
        {showShareModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowShareModal(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative bg-card border border-border w-full max-w-md rounded-2xl p-6 shadow-2xl z-10"
            >
              <h3 className="font-display font-bold text-lg mb-4 flex items-center gap-2">
                <Share2 size={18} className="text-primary" />
                Digital Sharing
              </h3>
              
              {shareSuccess ? (
                <div className="py-8 text-center space-y-3">
                  <CheckCircle size={48} className="text-emerald-500 mx-auto animate-pulse" />
                  <p className="font-semibold text-foreground text-lg">Action Completed!</p>
                  <p className="text-muted-foreground text-xs">Personalized PDF medication guide has been shared or saved.</p>
                </div>
              ) : (
                <div className="space-y-5">
                  <p className="text-muted-foreground text-xs">
                    Generate a high-fidelity PDF copy of the patient handout and share it digitally via WhatsApp, SMS, Email, or download it directly.
                  </p>

                  <div className="flex flex-col gap-3">
                    <button
                      onClick={handleSharePDF}
                      disabled={sharingLoading}
                      className="w-full py-4 bg-primary text-primary-foreground font-display font-bold text-sm rounded-xl hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2 glow-pulse-cyan"
                    >
                      {sharingLoading ? (
                        <>
                          <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                          <span>Generating PDF...</span>
                        </>
                      ) : (
                        <>
                          <Share2 size={16} />
                          <span>Share PDF Guide (WhatsApp / Apps)</span>
                        </>
                      )}
                    </button>

                    <button
                      onClick={handleDownloadPDF}
                      disabled={sharingLoading}
                      className="w-full py-3 bg-muted hover:bg-muted/80 text-foreground font-display font-semibold text-sm rounded-xl disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                    >
                      <Printer size={15} />
                      <span>Download PDF File</span>
                    </button>
                  </div>

                  <div className="border-t border-border pt-4 space-y-2">
                    <p className="text-[10px] text-muted-foreground font-display uppercase tracking-wider">Alternative Text Copy</p>
                    <button 
                      onClick={handleCopyClipboard}
                      className="w-full py-2.5 bg-secondary/15 hover:bg-secondary/20 text-secondary border border-secondary/20 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <FileText size={13} />
                      {copied ? "Copied to Clipboard!" : "Copy Handout Text"}
                    </button>
                  </div>

                  <div className="flex justify-end gap-2 pt-3 border-t border-border/50">
                    <button 
                      onClick={() => setShowShareModal(false)}
                      className="px-4 py-2 bg-card border border-border rounded-xl text-xs font-semibold hover:bg-muted transition-colors"
                    >
                      Close
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
}