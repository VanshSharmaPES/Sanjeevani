"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff } from "lucide-react";
import ParticleField from "@/components/ParticleField";
import MandalaBackground from "@/components/MandalaBackground";
import SanjeevaniLogo from "@/components/SanjeevaniLogo";
import { useRouter } from "next/navigation";

const Login = () => {
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("patient");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  // Remember Me & OTP States
  const [rememberMe, setRememberMe] = useState(true);
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");

  // Redirect to dashboard if already logged in (checking both localStorage and sessionStorage)
  useEffect(() => {
    const user = localStorage.getItem("sanjeevani_user") || sessionStorage.getItem("sanjeevani_user");
    const token = localStorage.getItem("sanjeevani_token") || sessionStorage.getItem("sanjeevani_token");
    if (user && token) {
      router.push("/dashboard");
    } else {
      setCheckingAuth(false);
    }
  }, [router]);

  // Reset Password State
  const [showReset, setShowReset] = useState(false);
  const [resetUsername, setResetUsername] = useState("");
  const [resetPasswordVal, setResetPasswordVal] = useState("");
  const [resetError, setResetError] = useState("");
  const [resetSuccess, setResetSuccess] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [resetOtpSent, setResetOtpSent] = useState(false);
  const [resetOtpCode, setResetOtpCode] = useState("");
  const [otpTimer, setOtpTimer] = useState(0);

  // OTP Countdown Timer
  useEffect(() => {
    if (otpTimer <= 0) return;
    const interval = setInterval(() => {
      setOtpTimer((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [otpTimer]);

  const handleResendRegisterOtp = async () => {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const username = name.trim();
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "request", username, password, role, email: registerEmail.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setSuccess("A new verification code (OTP) has been sent to your Email.");
        setOtpTimer(60);
      } else {
        setError(data.message || "Failed to resend registration OTP.");
      }
    } catch {
      setError("Could not connect to server.");
    } finally {
      setLoading(false);
    }
  };

  const handleResendResetOtp = async () => {
    setResetError("");
    setResetSuccess("");
    setResetLoading(true);
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "request", username: resetUsername.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setResetSuccess("A new verification code (OTP) has been sent to your registered Email.");
        setOtpTimer(60);
      } else {
        setResetError(data.message || "Failed to resend reset OTP.");
      }
    } catch {
      setResetError("Failed to connect to authentication server.");
    } finally {
      setResetLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetError("");
    setResetSuccess("");
    
    const u = resetUsername.trim();
    if (!u) {
      setResetError("Username is required.");
      return;
    }

    if (!resetOtpSent) {
      setResetLoading(true);
      try {
        const res = await fetch("/api/auth/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "request", username: u }),
        });
        const data = await res.json();
        if (data.success) {
          setResetOtpSent(true);
          setResetSuccess("Verification code (OTP) sent to your registered Email address.");
          setOtpTimer(60);
        } else {
          setResetError(data.message || "Failed to request password reset.");
        }
      } catch {
        setResetError("Failed to connect to authentication server.");
      } finally {
        setResetLoading(false);
      }
    } else {
      const p = resetPasswordVal;
      const o = resetOtpCode.trim();
      
      if (!p || !o) {
        setResetError("New password and 6-digit OTP code are required.");
        return;
      }
      if (p.length < 4) {
        setResetError("Password must be at least 4 characters.");
        return;
      }
      if (p.length > 128) {
        setResetError("Password must be at most 128 characters.");
        return;
      }
      if (o.length !== 6) {
        setResetError("OTP must be exactly 6 digits.");
        return;
      }

      setResetLoading(true);
      try {
        const res = await fetch("/api/auth/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "verify", username: u, otp: o, new_password: p }),
        });
        const data = await res.json();
        if (data.success) {
          setResetSuccess("Password reset successfully! You can now log in.");
          setResetUsername("");
          setResetPasswordVal("");
          setResetOtpCode("");
          setResetOtpSent(false);
          setTimeout(() => {
            setShowReset(false);
            setResetSuccess("");
          }, 2200);
        } else {
          setResetError(data.message || "Invalid or expired OTP.");
        }
      } catch {
        setResetError("Failed to connect to authentication server.");
      } finally {
        setResetLoading(false);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (isLogin) {
      if (password.length > 128) {
        setError("Password must be at most 128 characters.");
        return;
      }
      setLoading(true);
      try {
        // Login: `email` state holds the username the user typed
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ username: email.trim(), password }),
        });
        const data = await res.json();
        if (data.success) {
          const storage = rememberMe ? localStorage : sessionStorage;
          storage.setItem("sanjeevani_user", data.username || email.trim());
          storage.setItem("sanjeevani_role", data.role || "patient");
          if (data.token) {
            storage.setItem("sanjeevani_token", data.token);
          }
          router.push("/dashboard");
        } else {
          setError(data.message || "Invalid credentials");
        }
      } catch {
        setError("Could not connect to server. Make sure the Python backend is running.");
      } finally {
        setLoading(false);
      }
    } else {
      // Register
      const username = name.trim();
      if (!username) {
        setError("Please enter a username.");
        return;
      }
      
      if (!otpSent) {
        if (!password || !registerEmail.trim()) {
          setError("Password and Email address are required.");
          return;
        }
        if (password.length < 4) {
          setError("Password must be at least 4 characters.");
          return;
        }
        if (password.length > 128) {
          setError("Password must be at most 128 characters.");
          return;
        }
        setLoading(true);
        try {
          const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "request", username, password, role, email: registerEmail.trim() }),
          });
          const data = await res.json();
          if (data.success) {
            setOtpSent(true);
            setSuccess("Verification code (OTP) sent to your Email address.");
            setOtpTimer(60);
          } else {
            setError(data.message || "Registration request failed.");
          }
        } catch {
          setError("Could not connect to server.");
        } finally {
          setLoading(false);
        }
      } else {
        // Verify OTP code
        const o = otpCode.trim();
        if (!o) {
          setError("Please enter the 6-digit verification code.");
          return;
        }
        if (o.length !== 6) {
          setError("OTP must be exactly 6 digits.");
          return;
        }
        setLoading(true);
        try {
          const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "verify", username, otp: o }),
          });
          const data = await res.json();
          if (data.success) {
            setSuccess(`Account created! Log in with username "${username}".`);
            setName("");
            setPassword("");
            setRegisterEmail("");
            setOtpCode("");
            setOtpSent(false);
            setTimeout(() => {
              setSuccess("");
              setIsLogin(true);
            }, 2500);
          } else {
            setError(data.message || "Invalid or expired verification code.");
          }
        } catch {
          setError("Could not connect to server.");
        } finally {
          setLoading(false);
        }
      }
    }
  };

  if (checkingAuth) {
    return (
      <div className="relative min-h-screen flex items-center justify-center overflow-hidden">
        <ParticleField />
        <MandalaBackground />
      </div>
    );
  }

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
              onClick={() => { setIsLogin(true); setError(""); setSuccess(""); setOtpSent(false); }}
              className={`relative z-10 flex-1 py-2 text-sm font-display font-semibold rounded-full transition-colors ${isLogin ? "text-primary-foreground" : "text-muted-foreground"
                }`}
            >
              Login
            </button>
            <button
              onClick={() => { setIsLogin(false); setError(""); setSuccess(""); setOtpSent(false); }}
              className={`relative z-10 flex-1 py-2 text-sm font-display font-semibold rounded-full transition-colors ${!isLogin ? "text-primary-foreground" : "text-muted-foreground"
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
            {success && (
              <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-xl text-green-400 text-sm text-center">
                {success}
              </div>
            )}
            <AnimatePresence mode="wait">
              {isLogin ? (
                /* Login Form */
                <motion.div
                  key="login-fields"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-6"
                >
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Username"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="username"
                      className="w-full bg-transparent border-b-2 border-border focus:border-primary py-3 px-1 text-foreground placeholder:text-muted-foreground outline-none transition-colors font-body"
                    />
                  </div>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      maxLength={128}
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

                  <div className="flex items-center gap-2 pt-2">
                    <input
                      type="checkbox"
                      id="rememberMe"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="h-4 w-4 rounded border-border bg-muted accent-primary text-primary focus:ring-primary focus:ring-offset-background"
                    />
                    <label htmlFor="rememberMe" className="text-xs text-muted-foreground cursor-pointer select-none font-display">
                      Save login info (Keep me logged in)
                    </label>
                  </div>
                </motion.div>
              ) : otpSent ? (
                /* Register: OTP Verification */
                <motion.div
                  key="register-otp-fields"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-4"
                >
                  <div className="text-center text-xs text-muted-foreground leading-relaxed">
                    We sent a 6-digit OTP code to <strong className="text-foreground">{registerEmail}</strong>. 
                    Please check your Email inbox (or server console) and enter it below.
                  </div>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Enter 6-digit OTP"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value)}
                      maxLength={6}
                      className="w-full bg-transparent border-b-2 border-border focus:border-primary py-3 px-1 text-foreground placeholder:text-muted-foreground outline-none transition-colors font-body text-center font-bold tracking-widest text-lg"
                    />
                  </div>
                  <div className="text-center text-xs flex flex-col gap-2.5">
                    <span 
                      onClick={() => setOtpSent(false)} 
                      className="text-primary hover:underline cursor-pointer font-semibold"
                    >
                      &larr; Go back and edit details
                    </span>
                    <div className="text-xs font-display">
                      {otpTimer > 0 ? (
                        <span className="text-muted-foreground select-none">
                          Resend code in <strong className="text-foreground">{otpTimer}s</strong>
                        </span>
                      ) : (
                        <span 
                          onClick={handleResendRegisterOtp} 
                          className="text-secondary hover:underline cursor-pointer font-bold"
                        >
                          Resend OTP
                        </span>
                      )}
                    </div>
                  </div>
                </motion.div>
              ) : (
                /* Register Form fields */
                <motion.div
                  key="register-fields"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-6"
                >
                  <div className="relative">
                    <input
                      type="email"
                      placeholder="Email Address"
                      value={registerEmail}
                      onChange={(e) => setRegisterEmail(e.target.value)}
                      className="w-full bg-transparent border-b-2 border-border focus:border-primary py-3 px-1 text-foreground placeholder:text-muted-foreground outline-none transition-colors font-body"
                    />
                  </div>

                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Choose a Username"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      autoComplete="username"
                      className="w-full bg-transparent border-b-2 border-border focus:border-primary py-3 px-1 text-foreground placeholder:text-muted-foreground outline-none transition-colors font-body"
                    />
                  </div>

                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder="Choose a Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      maxLength={128}
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
                  
                  <div className="relative pt-2">
                    <label className="text-[10px] text-muted-foreground block mb-2 font-display uppercase tracking-wider">I am registering as a:</label>
                    <div className="flex bg-muted rounded-xl p-1 border border-border">
                      <button
                        type="button"
                        onClick={() => setRole("patient")}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-colors ${role === "patient" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground"}`}
                      >
                        Patient
                      </button>
                      <button
                        type="button"
                        onClick={() => setRole("doctor")}
                        className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-colors ${role === "doctor" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground"}`}
                      >
                        Doctor / Pharmacist
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full py-3.5 bg-primary text-primary-foreground font-display font-bold rounded-xl glow-pulse-saffron transition-all text-lg tracking-wide disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? "Please wait..." : isLogin ? "Enter Sanjeevani" : otpSent ? "Verify & Register" : "Send Registration OTP"}
            </motion.button>
          </form>

          {isLogin && (
            <p className="text-center text-muted-foreground text-xs mt-6">
              Forgot your password?{" "}
              <span 
                onClick={() => { setShowReset(true); setResetOtpSent(false); setResetError(""); setResetSuccess(""); }}
                className="text-secondary cursor-pointer hover:underline"
              >
                Reset here
              </span>
            </p>
          )}
        </div>
      </motion.div>

      {/* Reset Password Modal */}
      <AnimatePresence>
        {showReset && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setShowReset(false);
                setResetError("");
                setResetSuccess("");
                setResetOtpSent(false);
              }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative bg-card/95 border border-border w-full max-w-sm rounded-2xl p-6 shadow-2xl z-10"
            >
              <h3 className="font-display font-bold text-lg mb-4 text-foreground">
                Reset Password
              </h3>
              
              <form onSubmit={handleResetPassword} className="space-y-4">
                {resetError && (
                  <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-xl">
                    {resetError}
                  </div>
                )}
                {resetSuccess && (
                  <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs rounded-xl">
                    {resetSuccess}
                  </div>
                )}
                
                {!resetOtpSent ? (
                  /* Reset Step 1: Username */
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Username</label>
                    <input
                      type="text"
                      value={resetUsername}
                      onChange={(e) => setResetUsername(e.target.value)}
                      placeholder="Enter your username"
                      className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm outline-none focus:border-primary text-foreground"
                    />
                  </div>
                ) : (
                  /* Reset Step 2: OTP & New Password */
                  <div className="space-y-4">
                    <div className="text-xs text-muted-foreground leading-relaxed text-center">
                      We sent a 6-digit OTP code to the email address associated with <strong className="text-foreground">{resetUsername}</strong>.
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground block mb-1">6-Digit OTP</label>
                      <input
                        type="text"
                        value={resetOtpCode}
                        onChange={(e) => setResetOtpCode(e.target.value)}
                        placeholder="Enter 6-digit OTP code"
                        maxLength={6}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm outline-none focus:border-primary text-foreground text-center font-bold tracking-wider"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground block mb-1">New Password</label>
                      <input
                        type="password"
                        value={resetPasswordVal}
                        onChange={(e) => setResetPasswordVal(e.target.value)}
                        placeholder="Enter new password"
                        maxLength={128}
                        className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm outline-none focus:border-primary text-foreground"
                      />
                    </div>
                    <div className="text-center text-xs flex justify-between px-2 font-display">
                      <span 
                        onClick={() => setResetOtpSent(false)} 
                        className="text-primary hover:underline cursor-pointer font-semibold"
                      >
                        &larr; Go back
                      </span>
                      {otpTimer > 0 ? (
                        <span className="text-muted-foreground select-none">
                          Resend in <strong className="text-foreground">{otpTimer}s</strong>
                        </span>
                      ) : (
                        <span 
                          onClick={handleResendResetOtp} 
                          className="text-secondary hover:underline cursor-pointer font-bold"
                        >
                          Resend OTP
                        </span>
                      )}
                    </div>
                  </div>
                )}
                
                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowReset(false);
                      setResetError("");
                      setResetSuccess("");
                      setResetOtpSent(false);
                    }}
                    className="flex-1 py-2.5 bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-xl text-xs transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={resetLoading}
                    className="flex-1 py-2.5 bg-primary text-primary-foreground font-semibold rounded-xl text-xs disabled:opacity-50 transition-opacity"
                  >
                    {resetLoading ? "Processing..." : resetOtpSent ? "Verify & Reset" : "Send Reset OTP"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Login;
