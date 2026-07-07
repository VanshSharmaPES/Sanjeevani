import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

export const dynamic = "force-dynamic";

const PYTHON_API = getPythonApiUrl();

export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${PYTHON_API}/api/video-guides/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: request.headers.get("cookie") || "",
      },
      body: JSON.stringify(await request.json()),
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json(
      { success: false, videos: [], error: "Failed to connect to video generation server" },
      { status: 502 },
    );
  }
}
