import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const PYTHON_API = process.env.PYTHON_API_URL || "http://127.0.0.1:5000";

export async function DELETE(
    request: NextRequest,
    { params }: { params: Promise<{ scanId: string }> }
) {
    try {
        const { scanId } = await params;
        const cookie = request.headers.get("cookie") || "";
        console.log(`[DELETE] Requesting proxy deletion for scan_id: ${scanId}`);

        const response = await fetch(`${PYTHON_API}/api/history/${scanId}`, {
            method: "DELETE",
            headers: { cookie }
        });

        const data = await response.json();
        return NextResponse.json(data, { status: response.status });
    } catch (error: any) {
        console.error(`[DELETE] Proxy error:`, error);
        return NextResponse.json(
            { success: false, message: "Failed to connect to server" },
            { status: 500 }
        );
    }
}
