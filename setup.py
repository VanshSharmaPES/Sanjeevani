#!/usr/bin/env python3
"""
setup.py - Quick setup script for Sanjeevani AI
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ is required!")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")


def install_dependencies():
    """Install required packages"""
    print_header("📦 Installing Dependencies")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"]
        )
        print("✅ All dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)


def setup_env_file():
    """Setup .env file if not exists"""
    print_header("🔑 Setting up Environment Variables")
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    env_example = Path(".env.example")
    if env_example.exists():
        env_file.write_text(env_example.read_text())
        print("✅ Created .env from .env.example")
    else:
        env_file.write_text("API_KEY=your_groq_api_key_here\n")
        print("✅ Created basic .env file")
    
    print("\n⚠️  IMPORTANT: Update .env with your Groq API key")
    print("   Get it from: https://console.groq.com/keys\n")


def verify_imports():
    """Verify critical imports"""
    print_header("🔍 Verifying Imports")
    
    required_modules = [
        ("streamlit", "Streamlit"),
        ("pandas", "Pandas"),
        ("groq", "Groq"),
        ("gtts", "Google Text-to-Speech"),
        ("PIL", "Pillow"),
    ]
    
    all_ok = True
    for module, name in required_modules:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - Not installed")
            all_ok = False
    
    if not all_ok:
        print("\n⚠️  Some modules are missing. Run: pip install -r requirements.txt")
        sys.exit(1)


def main():
    """Main setup flow"""
    print("\n")
    print("  " + "=" * 56)
    print("  " + "💊 SANJEEVANI AI v4.0 - SETUP WIZARD".center(56))
    print("  " + "=" * 56)
    
    check_python_version()
    install_dependencies()
    setup_env_file()
    verify_imports()
    
    print_header("✨ Setup Complete!")
    print("Next steps:")
    print("  1. Edit .env and add your Groq API key")
    print("  2. Run: streamlit run app.py")
    print("  3. Open http://localhost:8501 in your browser\n")
    print("  🏥 Happy healing with Sanjeevani AI!\n")


if __name__ == "__main__":
    main()
