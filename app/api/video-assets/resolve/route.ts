import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

export const dynamic = "force-dynamic";

const PYTHON_API = getPythonApiUrl();

export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${PYTHON_API}/api/video-assets/resolve`, {
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
      { success: false, assets: { medicines: [] }, failures: [], error: "Failed to connect to video asset resolver" },
      { status: 502 },
    );
  }
}
