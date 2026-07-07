import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

export const dynamic = "force-dynamic";

const PYTHON_API = getPythonApiUrl();

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ filename: string }> },
) {
  try {
    const { filename } = await params;
    const response = await fetch(`${PYTHON_API}/api/video-guides/file/${encodeURIComponent(filename)}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return NextResponse.json({ error: "Video not found" }, { status: response.status });
    }
    const buffer = await response.arrayBuffer();
    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": "video/mp4",
        "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
      },
    });
  } catch {
    return NextResponse.json({ error: "Failed to fetch generated video" }, { status: 500 });
  }
}
