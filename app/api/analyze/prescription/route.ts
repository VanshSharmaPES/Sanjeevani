import { NextRequest, NextResponse } from "next/server";

const PYTHON_API = process.env.PYTHON_API_URL || "http://localhost:5000";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();

    // Forward the formData directly to the Python backend
    const response = await fetch(`${PYTHON_API}/api/analyze/prescription`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message || "Failed to connect to analysis server. Make sure the Python server is running (python server.py)." },
      { status: 500 }
    );
  }
}
