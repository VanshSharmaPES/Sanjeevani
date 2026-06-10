import { NextRequest, NextResponse } from "next/server";

const PYTHON_API = (process.env.PYTHON_API_URL || "http://127.0.0.1:5000").replace(/\/$/, "");

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${PYTHON_API}/api/health`, {
      method: "GET",
      // Bypass Next.js fetch caching
      cache: "no-store",
    });

    if (!response.ok) {
      const text = await response.text();
      return NextResponse.json({
        success: false,
        python_api_url: PYTHON_API,
        status: response.status,
        error: text || `Backend returned status ${response.status}`,
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json({
      success: true,
      python_api_url: PYTHON_API,
      backend_status: data,
    });
  } catch (error: any) {
    return NextResponse.json({
      success: false,
      python_api_url: PYTHON_API,
      error: error.message || "Failed to connect to backend",
    }, { status: 500 });
  }
}
