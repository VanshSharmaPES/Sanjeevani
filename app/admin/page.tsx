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
  { code: "en", name: "English" },
  { code: "hi", name: "Hindi" },
  { code: "ta", name: "Tamil" },
  { code: "te", name: "Telugu" },
  { code: "bn", name: "Bengali" },
  { code: "mr", name: "Marathi" },
  { code: "kn", name: "Kannada" },
  { code: "ml", name: "Malayalam" },
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
  const [dosage, setDosage] = useState("500mg");
  const [frequency, setFrequency] = useState("Twice a day (1-0-1)");
  const [timing, setTiming] = useState("After meals (PC)");
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
          setSearchResults(data);
          setShowDropdown(data.length > 0);
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
    setSearching(true);
    try {
      const res = await fetch(`/api/medicines/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setSearchResults(data);
      setShowDropdown(data.length > 0);
      if (data.length === 0) {
        alert("No medicines found matching your search. You can manually enter the details below.");
      }
    } catch (err) {
      console.error("Search error:", err);
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
        const response = await fetch("/api/translate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            text: adviceEn,
            language_code: selectedLanguage,
          }),
        });
        
        const data = await response.json();
        setGeneratedGuide({
          medicineName: medName,
          activeSalts: salts,
          dosage: dosage,
          frequency: frequency,
          timing: timing,
          language: langName,
          doctorNotes: docNotes,
          adviceText: data.translated || adviceEn,
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
        backgroundColor: "#09090b", // Dark mode aesthetic match
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

  if (!authorized) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen relative bg-background print:bg-white text-foreground print:text-black">
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
                    placeholder="e.g. 1 Tablet"
                    className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Frequency</label>
                  <AutoResizeTextarea 
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    disabled={aiGenerating}
                    placeholder="e.g. 1-0-1"
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
                  placeholder="e.g. After meals"
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
                <div id="printable-handout" className="bg-card border-2 border-border print:border-0 rounded-3xl p-6 print:p-0 space-y-4 shadow-xl print:shadow-none bg-background text-foreground">
                  
                  {/* Digital Prescription Clinic Header (Doctor Details Only, No Rx header or line below it) */}
                  <div className="flex justify-end items-start gap-4">
                    <div className="text-right space-y-0.5 text-xs text-muted-foreground">
                      <p className="font-semibold text-foreground">{doctorName}</p>
                      <p>Reg No: MCI-2026-98765</p>
                      {generationTime && <p className="text-[10px] font-medium text-emerald-500">{generationTime}</p>}
                    </div>
                  </div>

                  <div className="flex justify-between items-start pt-1">
                    <div>
                      <span className="text-[10px] px-2 py-1 rounded bg-secondary/15 text-secondary border border-secondary/20 font-semibold print:hidden">
                        BILINGUAL PATIENT HANDOUT
                      </span>
                      <h3 className="font-display text-2xl font-bold mt-1.5">{generatedGuide.medicineName}</h3>
                      <p className="text-muted-foreground text-xs mt-0.5">{generatedGuide.activeSalts}</p>
                    </div>
                    <div className="flex items-center gap-1.5 px-3 py-1 bg-muted border border-border rounded-lg text-xs print:hidden">
                      <Globe size={13} className="text-muted-foreground" />
                      <span>{generatedGuide.language}</span>
                    </div>
                  </div>

                  {/* Core schedule highlights */}
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 border-y border-border py-4">
                    <div>
                      <p className="text-[10px] text-muted-foreground font-display uppercase tracking-wider">Dosage</p>
                      <p className="font-semibold text-base">{generatedGuide.dosage}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground font-display uppercase tracking-wider">Frequency</p>
                      <p className="font-semibold text-base">{generatedGuide.frequency}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground font-display uppercase tracking-wider">Timing</p>
                      <p className="font-semibold text-base">{generatedGuide.timing}</p>
                    </div>
                  </div>

                  {/* Bilingual Advice Translation Block */}
                  <div className="space-y-3">
                    <div className="p-4 rounded-xl bg-secondary/5 border border-secondary/25">
                      <h4 className="text-[10px] font-semibold text-secondary uppercase tracking-wider mb-1">
                        Instructions in Patient's Language ({generatedGuide.language})
                      </h4>
                      <p className="text-foreground text-base leading-relaxed whitespace-pre-line">{generatedGuide.adviceText}</p>
                    </div>

                    <div className="p-4 rounded-xl bg-muted/40 border border-border">
                      <h4 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                        Instructions in English
                      </h4>
                      <p className="text-muted-foreground text-xs leading-relaxed whitespace-pre-line">{generatedGuide.adviceTextEn}</p>
                    </div>
                  </div>

                  {/* Custom Doctor Notes */}
                  {generatedGuide.doctorNotes && (
                    <div className="border-t border-border pt-4">
                      <h4 className="text-[10px] font-semibold text-foreground uppercase tracking-wider mb-1">
                        Special Notes by Practitioner
                      </h4>
                      <p className="text-foreground text-xs leading-relaxed bg-amber-500/10 border border-amber-500/20 p-3 rounded-xl">
                        {generatedGuide.doctorNotes}
                      </p>
                    </div>
                  )}

                  {/* Digital Prescription Verification Footer */}
                  <div className="border-t border-border pt-4 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="font-semibold text-foreground">Digital Prescription Verified</span>
                    </div>
                    <div className="text-center md:text-right text-[10px] italic font-medium text-muted-foreground">
                      This is a computer generated document, no physical signature required
                    </div>
                  </div>

                  {/* Print Layout Footer (Paper Only) */}
                  <div className="hidden print:block border-t border-black pt-4 mt-8 text-center text-xs">
                    <p>Generated via Sanjeevani AI Patient Assistance Assistant.</p>
                    <p className="mt-1 font-semibold">Please take medicine under supervision. Consult prescription for full details.</p>
                  </div>
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
    </div>
  );
}