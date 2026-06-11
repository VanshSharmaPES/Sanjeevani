import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

const PYTHON_API = getPythonApiUrl();

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ filename: string }> }
) {
  try {
    const { filename } = await params;
    const response = await fetch(`${PYTHON_API}/api/audio/${filename}`);

    if (!response.ok) {
      return NextResponse.json({ error: "Audio not found" }, { status: 404 });
    }

    const buffer = await response.arrayBuffer();
    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": "audio/mpeg",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ error: "Failed to fetch audio" }, { status: 500 });
  }
}
