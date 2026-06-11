import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

export const dynamic = "force-dynamic";

const PYTHON_API = getPythonApiUrl();

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
            headers: { "Cookie": cookie }
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
