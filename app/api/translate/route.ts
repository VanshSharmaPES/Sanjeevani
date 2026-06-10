import { NextRequest, NextResponse } from "next/server";

const ANALYSIS_MODEL = "llama-3.3-70b-versatile";

const getApiKeys = (): string[] => {
  const keys: string[] = [];
  for (let i = 1; i <= 10; i++) {
    const k = process.env[`API_KEY_${i}`] || process.env[`GROQ_API_KEY_${i}`];
    if (k && k.trim()) keys.push(k.trim());
  }
  const mainKey = process.env.API_KEY || process.env.GROQ_API_KEY;
  if (mainKey && mainKey.trim() && !keys.includes(mainKey.trim())) {
    keys.push(mainKey.trim());
  }
  return keys;
};

const LANG_CODE_MAP: Record<string, string> = {
  "en": "English",
  "hi": "Hindi",
  "ta": "Tamil",
  "te": "Telugu",
  "bn": "Bengali",
  "mr": "Marathi",
  "kn": "Kannada",
  "ml": "Malayalam",
};

export async function POST(request: NextRequest) {
  try {
    const { text, language_code } = await request.json();
    const targetLanguage = LANG_CODE_MAP[language_code] || "English";

    if (!text) {
      return NextResponse.json({ error: "Missing text to translate" }, { status: 400 });
    }

    if (targetLanguage === "English") {
      return NextResponse.json({ translated: text });
    }

    const keys = getApiKeys();
    if (keys.length === 0) {
      console.error("No Groq API keys configured in environment variables.");
      return NextResponse.json({ error: "Translation API key not configured" }, { status: 500 });
    }

    let response: Response | null = null;
    let lastError: any = null;

    for (let i = 0; i < keys.length; i++) {
      const activeKey = keys[i];
      try {
        response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${activeKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: ANALYSIS_MODEL,
            messages: [
              {
                role: "system",
                content: `You are a certified medical translator. Translate the following medical text to ${targetLanguage}. Keep all medicine names, dosages, and medical terms accurate. Return ONLY the translated text — no explanations, no English labels.`,
              },
              {
                role: "user",
                content: text,
              },
            ],
            temperature: 0.1,
            max_tokens: 1200,
          }),
        });

        if (response.ok) {
          break; // Success!
        } else {
          const errText = await response.text();
          console.warn(`Translation key index ${i} failed with status ${response.status}: ${errText}`);
          lastError = new Error(`Backend returned status ${response.status}`);
        }
      } catch (err: any) {
        console.warn(`Translation fetch error with key index ${i}:`, err.message);
        lastError = err;
      }
    }

    if (!response || !response.ok) {
      return NextResponse.json({ error: lastError?.message || "Failed to get translation from Groq" }, { status: 500 });
    }

    const data = await response.json();
    const translated = data.choices?.[0]?.message?.content?.trim() || text;

    return NextResponse.json({ translated });
  } catch (error: any) {
    console.error("Translation error in Next.js:", error);
    return NextResponse.json(
      { success: false, message: "Failed to translate using Groq API" },
      { status: 500 }
    );
  }
}
