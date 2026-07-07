"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Printer, Share2, Search, PlusCircle, FileText, CheckCircle, 
  ArrowLeft, Globe, Send, User, ChevronRight, UserCheck, ShieldAlert, BadgeCheck, Save, Video, RotateCcw
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
  alternates: AlternateCandidate[];
}

interface AlternateCandidate {
  medicineName: string;
  activeSalts: string;
  manufacturer: string;
  price: number | null;
  unit: string;
  source: "local_database" | "doctor_curated";
  substitutionSafety: "review_required" | "doctor_curated";
  statusLabel: string;
  formulationMatch: boolean;
  matchReasons: string[];
  safetyWarnings: string[];
}

interface VideoGuideResult {
  success: boolean;
  medicineName: string;
  videoUrl: string;
  videoPath: string;
  subtitlePath: string;
  durationSeconds: number;
  warnings: string[];
  error?: string;
}

interface VideoAssetFailure {
  medicineName?: string;
  routeTemplate?: string;
  assetType?: string;
  stage?: string;
  reason?: string;
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

const VIDEO_COPY_EN = {
  pageSubtitle: "Split-screen patient instruction video",
  approvedDemo: "Approved human demonstration template video",
  packageImage: "Medicine package image",
  productImage: "Dosage form / strip image",
  caption: "Caption",
  medicine: "Medicine",
  activeIngredients: "Active ingredients",
  dose: "Dose",
  timing: "Timing",
  frequency: "Frequency",
  duration: "Duration",
  doctorNote: "Doctor note",
  followPrescription: "Follow your doctor's prescription.",
  noDoseChange: "Do not change dosage without medical advice.",
  professionalAdministration: "Administer only by a qualified healthcare professional.",
  asPrescribed: "As prescribed",
  templateProfessionalOnly: "Healthcare professional administration",
  templateEyeDrops: "Human demonstration: applying eye drops",
  templateEarDrops: "Human demonstration: applying ear drops",
  templateNasalSpray: "Human demonstration: using nasal medicine",
  templateInhaler: "Human demonstration: using an inhaler",
  templateOintmentTopical: "Human demonstration: applying topical medicine",
  templateSyrupOral: "Human demonstration: drinking measured syrup",
  templateCapsuleOral: "Human demonstration: taking capsule with water",
  templateTabletOral: "Human demonstration: taking tablet with water",
  exactPackageMatch: "Exact package match",
  likelyDosageFormImage: "Likely dosage form image",
  genericDosageForm: "Generic dosage form",
  imageReviewRequired: "Image review required",
};

const VIDEO_COPY_LOCAL_FALLBACKS: Record<string, Partial<Record<keyof typeof VIDEO_COPY_EN, string>>> = {
  hi: {
    pageSubtitle: "रोगी निर्देश वीडियो",
    approvedDemo: "स्वीकृत मानव प्रदर्शन टेम्पलेट वीडियो",
    packageImage: "दवा पैकेज छवि",
    productImage: "खुराक रूप / स्ट्रिप छवि",
    caption: "कैप्शन",
    medicine: "दवा",
    activeIngredients: "सक्रिय घटक",
    dose: "खुराक",
    timing: "समय",
    frequency: "आवृत्ति",
    duration: "अवधि",
    doctorNote: "डॉक्टर का नोट",
    followPrescription: "अपने डॉक्टर के प्रिस्क्रिप्शन का पालन करें।",
    noDoseChange: "चिकित्सकीय सलाह के बिना खुराक न बदलें।",
    professionalAdministration: "केवल योग्य स्वास्थ्यकर्मी द्वारा दें।",
    asPrescribed: "जैसा निर्धारित हो",
    templateProfessionalOnly: "स्वास्थ्यकर्मी द्वारा प्रशासन",
    templateEyeDrops: "मानव प्रदर्शन: आंखों की बूंदें डालना",
    templateEarDrops: "मानव प्रदर्शन: कान की बूंदें डालना",
    templateNasalSpray: "मानव प्रदर्शन: नाक की दवा का उपयोग",
    templateInhaler: "मानव प्रदर्शन: इनहेलर का उपयोग",
    templateOintmentTopical: "मानव प्रदर्शन: त्वचा पर दवा लगाना",
    templateSyrupOral: "मानव प्रदर्शन: मापी हुई सिरप पीना",
    templateCapsuleOral: "मानव प्रदर्शन: पानी के साथ कैप्सूल लेना",
    templateTabletOral: "मानव प्रदर्शन: पानी के साथ टैबलेट लेना",
    exactPackageMatch: "सटीक पैकेज मिलान",
    likelyDosageFormImage: "संभावित खुराक रूप छवि",
    genericDosageForm: "सामान्य खुराक रूप",
    imageReviewRequired: "छवि समीक्षा आवश्यक",
  },
  te: {
    pageSubtitle: "రోగి సూచనల వీడియో",
    approvedDemo: "ఆమోదించబడిన మానవ ప్రదర్శన టెంప్లేట్ వీడియో",
    packageImage: "ఔషధ ప్యాకేజ్ చిత్రం",
    productImage: "మోతాదు రూపం / స్ట్రిప్ చిత్రం",
    caption: "క్యాప్షన్",
    medicine: "ఔషధం",
    activeIngredients: "సక్రియ పదార్థాలు",
    dose: "మోతాదు",
    timing: "సమయం",
    frequency: "తరచుదనం",
    duration: "వ్యవధి",
    doctorNote: "డాక్టర్ గమనిక",
    followPrescription: "మీ డాక్టర్ ప్రిస్క్రిప్షన్‌ను పాటించండి.",
    noDoseChange: "వైద్య సలహా లేకుండా మోతాదును మార్చవద్దు.",
    professionalAdministration: "అర్హత కలిగిన ఆరోగ్య సిబ్బంది మాత్రమే ఇవ్వాలి.",
    asPrescribed: "సూచించినట్లు",
    templateProfessionalOnly: "ఆరోగ్య సిబ్బంది ద్వారా ఇవ్వడం",
    templateEyeDrops: "మానవ ప్రదర్శన: కంటి చుక్కలు వేయడం",
    templateEarDrops: "మానవ ప్రదర్శన: చెవి చుక్కలు వేయడం",
    templateNasalSpray: "మానవ ప్రదర్శన: ముక్కు ఔషధం ఉపయోగించడం",
    templateInhaler: "మానవ ప్రదర్శన: ఇన్హేలర్ ఉపయోగించడం",
    templateOintmentTopical: "మానవ ప్రదర్శన: చర్మంపై ఔషధం రాయడం",
    templateSyrupOral: "మానవ ప్రదర్శన: కొలిచిన సిరప్ తాగడం",
    templateCapsuleOral: "మానవ ప్రదర్శన: నీటితో క్యాప్సూల్ తీసుకోవడం",
    templateTabletOral: "మానవ ప్రదర్శన: నీటితో టాబ్లెట్ తీసుకోవడం",
    exactPackageMatch: "ఖచ్చితమైన ప్యాకేజ్ సరిపోలిక",
    likelyDosageFormImage: "సంభావ్య మోతాదు రూప చిత్రం",
    genericDosageForm: "సాధారణ మోతాదు రూపం",
    imageReviewRequired: "చిత్ర సమీక్ష అవసరం",
  },
};

const COMMON_VIDEO_FIELD_FALLBACKS: Record<string, Record<string, string>> = {
  hi: {
    "1 Tablet": "1 टैबलेट",
    "1 tablet": "1 टैबलेट",
    "1 Capsule": "1 कैप्सूल",
    "1 Drop": "1 बूंद",
    "2 Drops": "2 बूंदें",
    "1 Puff": "1 पफ",
    "5 ml": "5 मि.ली.",
    "Twice a day (1-0-1)": "दिन में दो बार (1-0-1)",
    "After meals (PC)": "भोजन के बाद",
    "As prescribed": "जैसा निर्धारित हो",
    "As directed": "निर्देशानुसार",
    "As directed by doctor": "डॉक्टर के निर्देशानुसार",
    "As prescribed by doctor.": "डॉक्टर के निर्देशानुसार।",
    "Apply a thin layer": "पतली परत लगाएं",
    "Apply to affected area": "प्रभावित स्थान पर लगाएं",
    "Consult prescription details for specific instructions.": "विशिष्ट निर्देशों के लिए प्रिस्क्रिप्शन विवरण देखें।",
    "No special warnings. Take as directed by practitioner.": "कोई विशेष चेतावनी नहीं। चिकित्सक के निर्देशानुसार लें।",
  },
  te: {
    "1 Tablet": "1 టాబ్లెట్",
    "1 tablet": "1 టాబ్లెట్",
    "1 Capsule": "1 క్యాప్సూల్",
    "1 Drop": "1 చుక్క",
    "2 Drops": "2 చుక్కలు",
    "1 Puff": "1 పఫ్",
    "5 ml": "5 మి.లీ.",
    "Twice a day (1-0-1)": "రోజుకు రెండుసార్లు (1-0-1)",
    "After meals (PC)": "భోజనం తర్వాత",
    "As prescribed": "సూచించినట్లు",
    "As directed": "నిర్దేశించినట్లు",
    "As directed by doctor": "డాక్టర్ సూచించినట్లు",
    "As prescribed by doctor.": "డాక్టర్ సూచించినట్లు.",
    "Apply a thin layer": "పలుచని పొరగా రాయండి",
    "Apply to affected area": "ప్రభావిత ప్రాంతంపై రాయండి",
    "Consult prescription details for specific instructions.": "ప్రత్యేక సూచనల కోసం ప్రిస్క్రిప్షన్ వివరాలను చూడండి.",
    "No special warnings. Take as directed by practitioner.": "ప్రత్యేక హెచ్చరికలు లేవు. వైద్యుని సూచనల ప్రకారం తీసుకోండి.",
  },
};

const applyLocalVideoFallback = (items: Record<string, string>, languageCode: string): Record<string, string> => {
  const copyFallback = VIDEO_COPY_LOCAL_FALLBACKS[languageCode] || {};
  const fieldFallback = COMMON_VIDEO_FIELD_FALLBACKS[languageCode] || {};
  return Object.fromEntries(
    Object.entries(items).map(([key, value]) => [
      key,
      copyFallback[key as keyof typeof VIDEO_COPY_EN] || fieldFallback[value] || value,
    ])
  );
};

const translateBulk = async (items: Record<string, string>, languageCode: string): Promise<Record<string, string>> => {
  if (languageCode === "en") return items;
  const localFallback = applyLocalVideoFallback(items, languageCode);
  try {
    const response = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, language_code: languageCode }),
    });
    if (!response.ok) return localFallback;
    const data = await response.json();
    return { ...localFallback, ...(data.translations || {}) };
  } catch (error) {
    console.error("Bulk translation failed:", error);
    return localFallback;
  }
};

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

const missingProviderKeys = (failures: VideoAssetFailure[]): string[] => {
  const keys = new Set<string>();
  failures.forEach((failure) => {
    const reason = failure.reason || "";
    if (reason.includes("PEXELS_API_KEY")) keys.add("PEXELS_API_KEY");
    if (reason.includes("SERPAPI_API_KEY")) keys.add("SERPAPI_API_KEY");
    if (reason.includes("BRAVE_SEARCH_API_KEY")) keys.add("BRAVE_SEARCH_API_KEY");
    if (reason.includes("GOOGLE_CSE_API_KEY")) keys.add("GOOGLE_CSE_API_KEY");
    if (reason.includes("GOOGLE_CSE_ID")) keys.add("GOOGLE_CSE_ID");
  });
  return Array.from(keys);
};

const formatAssetFailure = (failure: VideoAssetFailure): string => {
  const target = failure.medicineName || failure.routeTemplate || "Video asset";
  const asset = failure.assetType || "asset";
  const stage = failure.stage === "provider_config" ? "setup required" : failure.stage || "resolution";
  return `${target} • ${asset} • ${stage}: ${failure.reason || "No high-confidence result found"}`;
};

const medicationDescriptor = (medicine: any): string =>
  [
    medicine?.medicineName,
    medicine?.activeSalts,
    medicine?.unit,
    medicine?.form,
    medicine?.dosageForm,
    medicine?.route,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

const routeDefaultsForMedicine = (medicine: any) => {
  const text = medicationDescriptor(medicine);
  if (/(ointment|cream|gel|lotion|topical|external)/i.test(text)) {
    return {
      dosage: "Apply a thin layer",
      frequency: "As directed by doctor",
      timing: "Apply to affected area",
      doctorNotes: "For external use only. Do not ingest. Apply only to the affected area as prescribed.",
      route: "topical",
      form: text.includes("cream") ? "cream" : text.includes("gel") ? "gel" : text.includes("lotion") ? "lotion" : "ointment",
      replaceGenericOral: true,
    };
  }
  if (/(eye|ophthalmic)/i.test(text)) {
    return { dosage: "1 Drop", frequency: "As directed", timing: "As directed", doctorNotes: "", route: "ophthalmic", form: "eye drops", replaceGenericOral: true };
  }
  if (/(ear|otic)/i.test(text)) {
    return { dosage: "2 Drops", frequency: "As directed", timing: "As directed", doctorNotes: "", route: "otic", form: "ear drops", replaceGenericOral: true };
  }
  if (/(nasal|nose)/i.test(text)) {
    return { dosage: "2 Drops", frequency: "As directed", timing: "As directed", doctorNotes: "", route: "nasal", form: "nasal drops", replaceGenericOral: true };
  }
  if (/(inhaler|respule|inhalation)/i.test(text)) {
    return { dosage: "1 Puff", frequency: "As prescribed", timing: "As directed", doctorNotes: "", route: "inhalation", form: "inhaler", replaceGenericOral: true };
  }
  if (/(syrup|suspension|oral solution)/i.test(text)) {
    return { dosage: "5 ml", frequency: "As prescribed", timing: "After meals (PC)", doctorNotes: "", route: "oral", form: "syrup", replaceGenericOral: true };
  }
  if (/capsule/i.test(text)) {
    return { dosage: "1 Capsule", frequency: "As prescribed", timing: "As directed", doctorNotes: "", route: "oral", form: "capsule", replaceGenericOral: true };
  }
  return { dosage: "1 Tablet", frequency: "Twice a day (1-0-1)", timing: "After meals (PC)", doctorNotes: "", route: "oral", form: "tablet", replaceGenericOral: false };
};

const applyRouteDefaultIfNeeded = (value: string | undefined, fallback: string, replaceGenericOral: boolean): string => {
  const trimmed = (value || "").trim();
  if (!trimmed) return fallback;
  if (!replaceGenericOral) return trimmed;
  const normalized = trimmed.toLowerCase();
  const genericOralValues = new Set([
    "1 tablet",
    "one tablet",
    "1 tab",
    "twice a day (1-0-1)",
    "after meals (pc)",
  ]);
  return genericOralValues.has(normalized) ? fallback : trimmed;
};

const isSupportedLanguage = (code: string | null): code is string =>
  Boolean(code && languages.some((language) => language.code === code));

export default function AdminDashboard() {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState("en");
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
  const [alternatives, setAlternatives] = useState<AlternateCandidate[]>([]);
  const [alternativesLoading, setAlternativesLoading] = useState(false);
  const [curationSaving, setCurationSaving] = useState(false);
  const [curationMessage, setCurationMessage] = useState("");
  const [curationForm, setCurationForm] = useState({
    alternateName: "", alternateComposition: "", manufacturer: "", price: "", reason: "",
  });

  // Generated Guide state
  const [generatedGuide, setGeneratedGuide] = useState<GuideData | null>(null);
  const [videoGenerating, setVideoGenerating] = useState(false);
  const [videoResults, setVideoResults] = useState<VideoGuideResult[]>([]);
  const [videoError, setVideoError] = useState("");
  const [assetFailures, setAssetFailures] = useState<VideoAssetFailure[]>([]);
  const videoRefs = useRef<Record<string, HTMLVideoElement | null>>({});

  const clearVideoState = () => {
    setVideoResults([]);
    setVideoError("");
    setAssetFailures([]);
  };

  const clearGeneratedOutput = () => {
    setGeneratedGuide(null);
    clearVideoState();
  };

  // Role Guard
  useEffect(() => {
    const savedRole = localStorage.getItem("sanjeevani_role");
    const savedUser = localStorage.getItem("sanjeevani_user") || "Doctor";
    const savedLanguage = localStorage.getItem("sanjeevani_language");
    if (isSupportedLanguage(savedLanguage)) {
      setSelectedLanguage(savedLanguage);
    }
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
    const routeDefaults = routeDefaultsForMedicine(med);
    setMedName(med.medicineName);
    setSalts(med.activeSalts);
    setCurationMessage("");
    clearGeneratedOutput();
    void loadAlternatives(med.medicineName);
    
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
      
      setDosage(applyRouteDefaultIfNeeded(data.dosage, routeDefaults.dosage, routeDefaults.replaceGenericOral));
      setFrequency(applyRouteDefaultIfNeeded(data.frequency, routeDefaults.frequency, routeDefaults.replaceGenericOral));
      setTiming(applyRouteDefaultIfNeeded(data.timing, routeDefaults.timing, routeDefaults.replaceGenericOral));
      setDocNotes(data.doctorNotes || routeDefaults.doctorNotes || "");
    } catch (err) {
      console.error("AI prefill error:", err);
      // Fallback parsing if backend or API fails
      let defaultDosage = routeDefaults.dosage;
      if (!routeDefaults.replaceGenericOral && med.unit && med.unit.toLowerCase() !== "tablet") {
        defaultDosage = med.unit.charAt(0).toUpperCase() + med.unit.slice(1);
      }
      setDosage(defaultDosage);
      setFrequency(routeDefaults.frequency);
      setTiming(routeDefaults.timing);
      
      let notes = routeDefaults.doctorNotes;
      if (med.uses) notes += `Uses: ${med.uses}. `;
      if (med.sideEffects) notes += `Side Effects: ${med.sideEffects}. `;
      setDocNotes(notes.trim());
    } finally {
      setAiGenerating(false);
    }
  };

  const loadAlternatives = async (name: string) => {
    setAlternativesLoading(true);
    try {
      const response = await fetch(`/api/medicines/alternatives?name=${encodeURIComponent(name)}`, { cache: "no-store" });
      const data = await response.json();
      setAlternatives(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Alternate lookup failed:", error);
      setAlternatives([]);
    } finally {
      setAlternativesLoading(false);
    }
  };

  const handleUseAlternateMedicine = async (alternate: AlternateCandidate) => {
    await handleSelectMedicine({
      medicineName: alternate.medicineName,
      activeSalts: alternate.activeSalts,
      unit: alternate.unit,
      manufacturer: alternate.manufacturer,
    });
  };

  const saveCuratedAlternate = async () => {
    if (!medName || !curationForm.alternateName.trim() || !curationForm.reason.trim()) {
      setCurationMessage("Selected medicine, alternate name, and clinical reason are required.");
      return;
    }
    setCurationSaving(true);
    setCurationMessage("");
    try {
      const response = await fetch("/api/medicines/alternatives", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          medicineName: medName,
          medicineComposition: salts,
          alternateName: curationForm.alternateName.trim(),
          alternateComposition: curationForm.alternateComposition.trim(),
          manufacturer: curationForm.manufacturer.trim(),
          price: Number(curationForm.price) || 0,
          reason: curationForm.reason.trim(),
          createdBy: doctorName,
        }),
      });
      const data = await response.json();
      setCurationMessage(data.message || (response.ok ? "Curated alternate saved." : "Unable to save alternate."));
      if (response.ok) {
        setCurationForm({ alternateName: "", alternateComposition: "", manufacturer: "", price: "", reason: "" });
        await loadAlternatives(medName);
      }
    } catch {
      setCurationMessage("Unable to connect to the curation service.");
    } finally {
      setCurationSaving(false);
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
    clearVideoState();
    
    const now = new Date().toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "medium",
    });
    setGenerationTime(now);
    
    const langName = languages.find(l => l.code === selectedLanguage)?.name || "English";
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
          adviceTextEn: adviceEn,
          alternates: [],
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
          adviceTextEn: adviceEn,
          alternates: [],
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
        adviceTextEn: adviceEn,
        alternates: [],
      });
    } finally {
      setLoading(false);
    }
  };

  const [copied, setCopied] = useState(false);
  const [sharingLoading, setSharingLoading] = useState(false);

  const handleGenerateVideoGuide = async () => {
    if (!generatedGuide) return;
    const routeDefaults = routeDefaultsForMedicine({
      medicineName: generatedGuide.medicineName,
      activeSalts: generatedGuide.activeSalts,
    });
    setVideoGenerating(true);
    setVideoError("");
    setAssetFailures([]);
    setVideoResults([]);
    const videoText = await translateBulk(
      {
        ...VIDEO_COPY_EN,
        dosageValue: generatedGuide.dosage,
        frequencyValue: generatedGuide.frequency,
        timingValue: generatedGuide.timing,
        durationValue: "As prescribed",
        doctorNotesValue: generatedGuide.doctorNotes,
      },
      selectedLanguage
    );
    const payload = {
      patientName: "Patient",
      language: selectedLanguage,
      medicines: [
        {
          medicineName: generatedGuide.medicineName,
          activeSalts: generatedGuide.activeSalts,
          dosage: videoText.dosageValue || generatedGuide.dosage,
          frequency: videoText.frequencyValue || generatedGuide.frequency,
          timing: videoText.timingValue || generatedGuide.timing,
          duration: videoText.durationValue || "As prescribed",
          route: routeDefaults.route,
          form: routeDefaults.form,
          doctorNotes: videoText.doctorNotesValue || generatedGuide.doctorNotes,
          warnings: [
            videoText.followPrescription || VIDEO_COPY_EN.followPrescription,
            videoText.noDoseChange || VIDEO_COPY_EN.noDoseChange,
          ],
          videoCopy: videoText,
        },
      ],
    };
    try {
      const response = await fetch("/api/video-guides/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      const videos = Array.isArray(data.videos) ? data.videos : [];
      const failures = Array.isArray(data.failures) ? data.failures : [];
      setVideoResults(videos);
      setAssetFailures(failures);
      if (!response.ok || !data.success) {
        setVideoError(failures.length > 0 ? "" : data.error || videos[0]?.error || "Video guide generation failed.");
      }
    } catch {
      setVideoError("Unable to connect to the video generation service.");
    } finally {
      setVideoGenerating(false);
    }
  };

  const handleRetryAssetFetch = async () => {
    if (!generatedGuide) return;
    const routeDefaults = routeDefaultsForMedicine({
      medicineName: generatedGuide.medicineName,
      activeSalts: generatedGuide.activeSalts,
    });
    setVideoGenerating(true);
    setVideoError("");
    setAssetFailures([]);
    try {
      const response = await fetch("/api/video-assets/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patientName: "Patient",
          language: selectedLanguage,
          medicines: [
            {
              medicineName: generatedGuide.medicineName,
              activeSalts: generatedGuide.activeSalts,
              dosage: generatedGuide.dosage,
              frequency: generatedGuide.frequency,
              timing: generatedGuide.timing,
              duration: "As prescribed",
              route: routeDefaults.route,
              form: routeDefaults.form,
            },
          ],
        }),
      });
      const data = await response.json();
      const failures = Array.isArray(data.failures) ? data.failures : [];
      setAssetFailures(failures);
      if (!response.ok || !data.success) {
        setVideoError(failures.length > 0 ? "" : data.error || "Asset fetch failed. Check provider API keys and approved domains.");
        return;
      }
      await handleGenerateVideoGuide();
    } catch {
      setVideoError("Unable to connect to the video asset resolver.");
    } finally {
      setVideoGenerating(false);
    }
  };

  const handleReplayVideo = async (videoUrl: string) => {
    const video = videoRefs.current[videoUrl];
    if (!video) return;
    video.currentTime = 0;
    try {
      await video.play();
    } catch {
      // Browser autoplay policy may require the patient/doctor to press play manually.
    }
  };

  const getShareText = () => {
    if (!generatedGuide) return "";
    const alternateText = generatedGuide.alternates.length > 0
      ? `\n*Alternate candidates for professional review:*\n${generatedGuide.alternates.map((item) => `• ${item.medicineName} — ${item.activeSalts} (${item.statusLabel})`).join("\n")}\n\n*Warning:* Alternate medicines are shown for doctor/pharmacist review only. Do not substitute medicines without professional approval.\n`
      : "";
    return `⚕️ *Sanjeevani AI - Medication Handout* ⚕️\n\n` +
      `*Medicine:* ${generatedGuide.medicineName}\n` +
      `*Composition:* ${generatedGuide.activeSalts}\n` +
      `*Dosage:* ${generatedGuide.dosage}\n` +
      `*Frequency:* ${generatedGuide.frequency}\n` +
      `*Timing:* ${generatedGuide.timing}\n\n` +
      `*Instructions (${generatedGuide.language}):*\n${generatedGuide.adviceText}\n\n` +
      `*Instructions (English):*\n${generatedGuide.adviceTextEn}\n\n` +
      alternateText +
      (generatedGuide.doctorNotes ? `*Practitioner Notes:*\n${generatedGuide.doctorNotes}\n\n` : "") +
      `_Generated via Sanjeevani AI Patient Assistant_`;
  };

  // Strips invisible Unicode used in clipboard-hijack attacks:
  // RTL override (\u202A-\u202E), zero-width chars (\u200B-\u200F),
  // BOM (\uFEFF), and C0 control chars except \n and \t.
  const sanitiseForClipboard = (text: string): string =>
    text.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u200B-\u200F\u202A-\u202E\uFEFF]/g, "");

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

  const handleCopyClipboard = async () => {
    if (!isSecureContext) {
      console.warn("Clipboard API requires a secure context (HTTPS).");
      return;
    }
    try {
      await navigator.clipboard.writeText(sanitiseForClipboard(getShareText()));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Clipboard write failed:", err);
    }
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
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    clearGeneratedOutput();
                  }}
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
                        <span className="text-xs text-muted-foreground line-clamp-1">
                          {med.activeSalts} • {med.manufacturer}{med.price != null ? ` • ₹${Number(med.price).toFixed(2)}` : ""}
                        </span>
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
                  onChange={(e) => {
                    setMedName(e.target.value);
                    clearGeneratedOutput();
                  }}
                  placeholder="e.g. Dolo 650"
                  className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1">Active Salts / Ingredients</label>
                <AutoResizeTextarea 
                  value={salts}
                  onChange={(e) => {
                    setSalts(e.target.value);
                    clearGeneratedOutput();
                  }}
                  placeholder="e.g. Paracetamol IP 650mg"
                  className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Dosage</label>
                  <AutoResizeTextarea 
                    value={dosage}
                    onChange={(e) => {
                      setDosage(e.target.value);
                      clearGeneratedOutput();
                    }}
                    disabled={aiGenerating}
                    placeholder="e.g. 500mg"
                    className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Frequency</label>
                  <AutoResizeTextarea 
                    value={frequency}
                    onChange={(e) => {
                      setFrequency(e.target.value);
                      clearGeneratedOutput();
                    }}
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
                  onChange={(e) => {
                    setTiming(e.target.value);
                    clearGeneratedOutput();
                  }}
                  disabled={aiGenerating}
                  placeholder="e.g. After meals (PC)"
                  className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1">Target Handout Language</label>
                <select 
                  value={selectedLanguage}
                  onChange={(e) => {
                    const nextLanguage = e.target.value;
                    setSelectedLanguage(nextLanguage);
                    localStorage.setItem("sanjeevani_language", nextLanguage);
                    clearGeneratedOutput();
                  }}
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
                  onChange={(e) => {
                    setDocNotes(e.target.value);
                    clearGeneratedOutput();
                  }}
                  disabled={aiGenerating}
                  placeholder="Add custom warnings or instructions..."
                  className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                />
              </div>

              {medName && (
                <div className="border-t border-border pt-4 space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-display font-bold text-base flex items-center gap-2">
                        <ShieldAlert size={17} className="text-amber-500" />
                        Alternate Medicines
                      </h3>
                      <p className="text-xs text-muted-foreground mt-1">
                        Optional handout candidates with the same active ingredient composition and strength.
                      </p>
                    </div>
                    {alternativesLoading && <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />}
                  </div>

                  {!alternativesLoading && alternatives.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No same-composition medicines found for this medicine.</p>
                  ) : (
                    <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
                      {alternatives.map((alternate) => {
                        return (
                          <button
                            type="button"
                            key={alternate.medicineName}
                            onClick={() => handleUseAlternateMedicine(alternate)}
                            className={`block w-full select-none rounded-xl border p-3 text-left cursor-pointer hover:border-primary/60 hover:bg-primary/10 transition-colors ${
                              alternate.formulationMatch === false ? "border-amber-500/40 bg-muted/30" : "border-border bg-muted/30"
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <ChevronRight size={16} className="mt-0.5 text-primary flex-shrink-0" />
                              <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="text-sm font-semibold">{alternate.medicineName}</span>
                                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                    alternate.substitutionSafety === "doctor_curated"
                                      ? "bg-emerald-500/15 text-emerald-400"
                                      : "bg-amber-500/15 text-amber-400"
                                  }`}>
                                    {alternate.substitutionSafety === "doctor_curated" ? "Doctor/pharmacist curated" : "Review required"}
                                  </span>
                                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-primary/15 text-primary">
                                    Use this medicine
                                  </span>
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">{alternate.activeSalts}</p>
                                <p className="text-[11px] text-muted-foreground mt-1">
                                  {alternate.manufacturer || "Manufacturer unavailable"} • {alternate.unit || "Pack unavailable"}
                                  {alternate.price != null ? ` • ₹${Number(alternate.price).toFixed(2)}` : ""}
                                </p>
                                <p className="text-[11px] text-amber-300 mt-2">{alternate.statusLabel}</p>
                                <p className="text-[11px] text-emerald-400/80 mt-1">{alternate.matchReasons.join(" • ")}</p>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  <details className="border-t border-border pt-4">
                    <summary className="cursor-pointer text-sm font-semibold flex items-center gap-2">
                      <BadgeCheck size={16} className="text-primary" /> Save clinician-curated alternate
                    </summary>
                    <div className="grid grid-cols-2 gap-3 mt-4">
                      <input value={curationForm.alternateName} onChange={(e) => setCurationForm({...curationForm, alternateName: e.target.value})} placeholder="Exact alternate name *" className="col-span-2 bg-muted border border-border rounded-lg px-3 py-2 text-xs" />
                      <input value={curationForm.alternateComposition} onChange={(e) => setCurationForm({...curationForm, alternateComposition: e.target.value})} placeholder="Composition" className="col-span-2 bg-muted border border-border rounded-lg px-3 py-2 text-xs" />
                      <input value={curationForm.manufacturer} onChange={(e) => setCurationForm({...curationForm, manufacturer: e.target.value})} placeholder="Manufacturer" className="bg-muted border border-border rounded-lg px-3 py-2 text-xs" />
                      <input value={curationForm.price} onChange={(e) => setCurationForm({...curationForm, price: e.target.value})} placeholder="Price" inputMode="decimal" className="bg-muted border border-border rounded-lg px-3 py-2 text-xs" />
                      <textarea value={curationForm.reason} onChange={(e) => setCurationForm({...curationForm, reason: e.target.value})} placeholder="Clinical review reason *" rows={3} className="col-span-2 bg-muted border border-border rounded-lg px-3 py-2 text-xs resize-none" />
                      <button onClick={saveCuratedAlternate} disabled={curationSaving} className="col-span-2 py-2 bg-primary text-primary-foreground rounded-lg text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-50">
                        <Save size={14} /> {curationSaving ? "Validating..." : "Validate and save as doctor-curated"}
                      </button>
                      {curationMessage && <p className="col-span-2 text-xs text-muted-foreground">{curationMessage}</p>}
                    </div>
                  </details>
                </div>
              )}

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
                  <button 
                    onClick={handleGenerateVideoGuide}
                    disabled={videoGenerating}
                    className="px-5 py-2.5 bg-secondary text-secondary-foreground font-semibold rounded-xl flex items-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    <Video size={16} />
                    {videoGenerating ? "Generating Video..." : "Generate Video Guide"}
                  </button>
                </div>

                {(videoResults.length > 0 || videoError) && (
                  <div className="print:hidden bg-card border border-border rounded-2xl p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <Video size={18} className="text-primary" />
                      <h3 className="font-display font-semibold">Prescription Video Guide</h3>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      This video is generated from prescription instructions. Follow your doctor's prescription.
                    </p>
                    {videoError && <p className="text-xs text-destructive">{videoError}</p>}
                    {assetFailures.length > 0 && (
                      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-100 space-y-3">
                        <div>
                          <p className="font-semibold text-amber-200">
                            {missingProviderKeys(assetFailures).length > 0 ? "Asset provider setup required" : "Verified medicine image not found"}
                          </p>
                            <p className="text-muted-foreground mt-1">
                              {missingProviderKeys(assetFailures).length > 0
                                ? "Strict mode needs the configured provider keys before it can fetch real medicine assets."
                                : "SerpAPI is working, but the returned images did not pass medicine identity checks. Generic fallback images are not used; unrelated or low-confidence results are rejected."}
                            </p>
                        </div>
                        {missingProviderKeys(assetFailures).length > 0 && (
                          <div>
                            <p className="font-semibold text-amber-200">Missing configuration</p>
                            <p className="text-muted-foreground">
                              Add {missingProviderKeys(assetFailures).map((key) => <code key={key} className="mx-1 text-amber-100">{key}</code>)} in your environment, then restart the backend.
                            </p>
                          </div>
                        )}
                        <div className="space-y-1">
                          <p className="font-semibold text-amber-200">Resolver details</p>
                          {assetFailures.map((failure, index) => (
                            <p key={`${failure.assetType || "asset"}-${index}`} className="text-muted-foreground">
                              {formatAssetFailure(failure)}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                    {(videoError || assetFailures.length > 0) && (
                      <button
                        onClick={handleRetryAssetFetch}
                        disabled={videoGenerating}
                        className="px-4 py-2 rounded-xl bg-secondary text-secondary-foreground text-xs font-semibold disabled:opacity-50"
                      >
                        {videoGenerating ? "Fetching assets..." : "Retry asset fetch"}
                      </button>
                    )}
                    {videoResults.filter((item) => item.success && item.videoUrl).map((item) => (
                      <div key={item.videoUrl} className="space-y-2">
                        <video
                          ref={(node) => {
                            videoRefs.current[item.videoUrl] = node;
                          }}
                          src={item.videoUrl}
                          controls
                          loop={false}
                          className="w-full rounded-xl border border-border bg-black"
                        />
                        <div className="text-xs text-muted-foreground space-y-1">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p>{item.medicineName} • {item.durationSeconds}s</p>
                            <button
                              type="button"
                              onClick={() => handleReplayVideo(item.videoUrl)}
                              className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1 text-xs font-semibold text-foreground hover:bg-muted transition-colors"
                            >
                              <RotateCcw size={13} />
                              Replay Video
                            </button>
                          </div>
                          {item.warnings?.map((warning) => (
                            <p key={warning}>Warning: {warning}</p>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

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

                  {generatedGuide.alternates.length > 0 && (
                    <section className="py-4 border-b-2 border-zinc-200 print:border-zinc-300 print:break-inside-avoid">
                      <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-medium mb-2">Alternate candidates for professional review</p>
                      <div className="space-y-2">
                        {generatedGuide.alternates.map((alternate) => (
                          <div key={alternate.medicineName} className="border border-zinc-200 rounded px-3 py-2">
                            <p className="text-[12px] font-semibold text-zinc-800">{alternate.medicineName}</p>
                            <p className="text-[10px] text-zinc-500">{alternate.activeSalts} • {alternate.manufacturer}</p>
                            <p className="text-[10px] font-medium text-amber-700 mt-1">{alternate.statusLabel}</p>
                          </div>
                        ))}
                      </div>
                      <p className="mt-3 text-[10px] font-semibold text-amber-700 leading-relaxed">
                        Alternate medicines are shown for doctor/pharmacist review only. Do not substitute medicines without professional approval.
                      </p>
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
