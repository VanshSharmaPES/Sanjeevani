import { NextRequest, NextResponse } from "next/server";

const PYTHON_API = process.env.PYTHON_API_URL || "http://localhost:5000";

export async function POST(request: NextRequest) {
  try {
    const incoming = await request.formData();

    const imageFile = incoming.get("image") as File | null;
    if (!imageFile) {
      return NextResponse.json({ error: "No image provided" }, { status: 400 });
    }

    const language = (incoming.get("language") as string) || "en";
    const userId = (incoming.get("user_id") as string) || "";

    // Rebuild FormData explicitly so the boundary is set correctly
    const outgoing = new FormData();
    outgoing.append("image", imageFile, imageFile.name || "upload.jpg");
    outgoing.append("language", language);
    outgoing.append("user_id", userId);

    const response = await fetch(`${PYTHON_API}/api/analyze/prescription`, {
      method: "POST",
      body: outgoing,
      // No explicit timeout — prescription OCR can take 20–40 s
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || "Failed to connect to analysis server. Make sure the Python server is running (python server.py)." },
      { status: 500 }
    );
  }
}

