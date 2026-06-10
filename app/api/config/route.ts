import { NextResponse } from "next/server";

export async function GET() {
  const pythonApiUrl = (process.env.PYTHON_API_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
  return NextResponse.json({ python_api_url: pythonApiUrl });
}
