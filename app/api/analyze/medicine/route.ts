import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const image = formData.get("image") as File | null;
    const language = formData.get("language") as string || "en";

    if (!image) {
      return NextResponse.json({ error: "No image provided" }, { status: 400 });
    }

    // Convert image to base64
    const bytes = await image.arrayBuffer();
    const base64 = Buffer.from(bytes).toString("base64");
    const mimeType = image.type || "image/jpeg";
    const dataUrl = `data:${mimeType};base64,${base64}`;

    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: "GROQ_API_KEY not configured" }, { status: 500 });
    }

    // Stage 1: Vision model for OCR
    const visionResponse = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "meta-llama/llama-4-scout-17b-16e-instruct",
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: "Read the medicine strip/box in this image. Extract: medicine name, brand name, all active salts/ingredients with strengths, dosage form, manufacturer. Return ONLY the raw extracted text, no analysis.",
              },
              {
                type: "image_url",
                image_url: { url: dataUrl },
              },
            ],
          },
        ],
        max_tokens: 1024,
      }),
    });

    const visionData = await visionResponse.json();
    const extractedText = visionData.choices?.[0]?.message?.content || "";

    // Stage 2: Analysis model
    const analysisResponse = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [
          {
            role: "system",
            content: `You are a medical analysis AI. Respond ONLY in ${language}. Analyze the extracted medicine data and respond in valid JSON with this exact structure:
{
  "medicine_name": "string",
  "brand": "string",
  "active_salts": ["string"],
  "dosage_strength": "normal | high",
  "conditions": ["string"],
  "what_it_does": "string (2-3 sentence explanation)",
  "age_groups": {"children": "string", "adults": "string", "elderly": "string"},
  "side_effects": ["string"],
  "similar_medicines": [{"name": "string", "same_salt": true}]
}`,
          },
          {
            role: "user",
            content: `Analyze this extracted medicine data:\n\n${extractedText}`,
          },
        ],
        max_tokens: 2048,
      }),
    });

    const analysisData = await analysisResponse.json();
    const resultText = analysisData.choices?.[0]?.message?.content || "{}";

    // Parse JSON from response
    let result;
    try {
      const jsonMatch = resultText.match(/\{[\s\S]*\}/);
      result = jsonMatch ? JSON.parse(jsonMatch[0]) : {};
    } catch {
      result = { raw: resultText };
    }

    return NextResponse.json({ success: true, data: result });
  } catch (error: any) {
    return NextResponse.json({ error: error.message || "Analysis failed" }, { status: 500 });
  }
}
