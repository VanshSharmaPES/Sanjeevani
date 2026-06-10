import { NextRequest, NextResponse } from "next/server";

const API_KEY = process.env.API_KEY || "";
const ANALYSIS_MODEL = "llama-3.3-70b-versatile";

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

    if (!API_KEY) {
      console.error("API_KEY environment variable is not defined on the server.");
      return NextResponse.json({ error: "Translation API key not configured" }, { status: 500 });
    }

    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${API_KEY}`,
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

    if (!response.ok) {
      const errText = await response.text();
      console.error("Groq translation error response:", errText);
      return NextResponse.json({ error: "Failed to get translation from Groq" }, { status: response.status });
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
