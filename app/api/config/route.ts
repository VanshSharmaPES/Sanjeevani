import { NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

export const dynamic = "force-dynamic";

export async function GET() {
  const pythonApiUrl = getPythonApiUrl();
  return NextResponse.json({ python_api_url: pythonApiUrl });
}
