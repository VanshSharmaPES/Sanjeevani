"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff } from "lucide-react";
import ParticleField from "@/components/ParticleField";
import MandalaBackground from "@/components/MandalaBackground";
import SanjeevaniLogo from "@/components/SanjeevaniLogo";
import { useRouter } from "next/navigation";

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        // Login flow
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: email, password }),
        });
        const data = await res.json();
        if (data.success) {
          localStorage.setItem("sanjeevani_user", data.username || email.split("@")[0]);
          localStorage.setItem("sanjeevani_user_id", String(data.user_id));
          router.push("/dashboard");
        } else {
          setError(data.message || "Invalid credentials");
        }
      } else {
        // Register flow
        const username = name || email.split("@")[0];
        const res = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (data.success) {
          localStorage.setItem("sanjeevani_user", username);
          localStorage.setItem("sanjeevani_user_id", String(data.user_id));
          router.push("/dashboard");
        } else {
          setError(data.message || "Registration failed");
        }
      }
    } catch {
      setError("Could not connect to server. Make sure the Python backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden">
      <ParticleField />
      <MandalaBackground />

      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md mx-4"
      >
        <div className="bg-card/80 backdrop-blur-xl border border-border rounded-2xl p-8 shadow-2xl">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="glow-pulse-cyan rounded-full p-3 mb-4">
              <SanjeevaniLogo size={56} />
            </div>
            <h1 className="font-display text-2xl font-bold text-foreground tracking-tight">
              Sanjeevani AI
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Your intelligent medical companion
            </p>
          </div>

          {/* Toggle Login / Register */}
          <div className="relative flex bg-muted rounded-full p-1 mb-8">
            <motion.div
              className="absolute top-1 bottom-1 rounded-full bg-primary"
              animate={{ x: isLogin ? 0 : "100%" }}
              style={{ width: "calc(50% - 4px)" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            />
            <button
              onClick={() => setIsLogin(true)}
              className={`relative z-10 flex-1 py-2 text-sm font-display font-semibold rounded-full transition-colors ${
                isLogin ? "text-primary-foreground" : "text-muted-foreground"
              }`}
            >
              Login
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`relative z-10 flex-1 py-2 text-sm font-display font-semibold rounded-full transition-colors ${
                !isLogin ? "text-primary-foreground" : "text-muted-foreground"
              }`}
            >
              Register
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-xl text-destructive text-sm text-center">
                {error}
              </div>
            )}
            <AnimatePresence mode="wait">
              {!isLogin && (
                <motion.div
                  key="name"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Full Name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full bg-transparent border-b-2 border-border focus:border-primary py-3 px-1 text-foreground placeholder:text-muted-foreground outline-none transition-colors font-body"
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="relative">
              <input
                type="email"
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-transparent border-b-2 border-border focus:border-primary py-3 px-1 text-foreground placeholder:text-muted-foreground outline-none transition-colors font-body"
              />
            </div>

            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-transparent border-b-2 border-border focus:border-primary py-3 px-1 text-foreground placeholder:text-muted-foreground outline-none transition-colors font-body pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-3 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full py-3.5 bg-primary text-primary-foreground font-display font-bold rounded-xl glow-pulse-saffron transition-all text-lg tracking-wide disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? "Please wait..." : "Enter Sanjeevani"}
            </motion.button>
          </form>

          {isLogin && (
            <p className="text-center text-muted-foreground text-xs mt-6">
              Forgot your password?{" "}
              <span className="text-secondary cursor-pointer hover:underline">Reset here</span>
            </p>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default Login;
