import { NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

export async function GET() {
  const pythonApiUrl = getPythonApiUrl();
  return NextResponse.json({ python_api_url: pythonApiUrl });
}
