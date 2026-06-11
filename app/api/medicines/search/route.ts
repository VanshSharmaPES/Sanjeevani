import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

const PYTHON_API = getPythonApiUrl();

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const q = searchParams.get("q") || "";

    const response = await fetch(`${PYTHON_API}/api/medicines/search?q=${encodeURIComponent(q)}`, {
      method: "GET",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, message: "Failed to connect to server" },
      { status: 500 }
    );
  }
}
