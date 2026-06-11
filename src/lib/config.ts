export function getPythonApiUrl(): string {
  return (
    process.env.PYTHON_API_URL || 
    (process.env.NODE_ENV === "production" 
      ? "https://sanjeevani-py8t.onrender.com" 
      : "http://127.0.0.1:5000")
  ).replace(/\/$/, "");
}
