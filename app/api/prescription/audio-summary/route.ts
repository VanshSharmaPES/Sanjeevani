import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

export const dynamic = "force-dynamic";

const PYTHON_API = getPythonApiUrl();

export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${PYTHON_API}/api/prescription/audio-summary`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: request.headers.get("cookie") || "",
        Authorization: request.headers.get("authorization") || "",
      },
      body: JSON.stringify(await request.json()),
    });
    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "Failed to rebuild prescription audio summary" },
      { status: 502 },
    );
  }
}
