import os
import subprocess
import shutil
import sys

def run_command(command, cwd=None, check=True):
    """Run a shell command with error handling."""
    print(f"--- 🏃 Running: {command} in {cwd or '.'} ---")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=False,
            text=True
        )
        if result.returncode != 0 and check:
            print(f"❌ Command failed with exit code {result.returncode}")
            sys.exit(1)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {e}")
        if check:
            sys.exit(1)
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if check:
            sys.exit(1)
        return None

def main():
    print("--- 🚀 STARTING PYTHON BUILD SCRIPT FOR RENDER ---")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    # Check if we're in the right directory
    if not os.path.exists("frontend") or not os.path.exists("backend"):
        print("❌ Error: frontend/ or backend/ directory not found!")
        print("Current directory contents:", os.listdir("."))
        sys.exit(1)
    
    # 0. Check/Install ffmpeg (for Render deployment)
    # Note: On Render, ffmpeg should be installed in buildCommand before this runs
    # This is just a verification step
    print("--- 🔍 Checking for ffmpeg ---")
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ ffmpeg is available")
        else:
            print("⚠️  ffmpeg check returned non-zero exit code")
    except FileNotFoundError:
        print("⚠️  WARNING: ffmpeg not found. Video upload features will not work.")
        print("⚠️  On Render: Ensure buildCommand installs ffmpeg (see render.yaml)")
        print("⚠️  On localhost: Install ffmpeg and add to PATH (see LOCALHOST_SETUP.md)")
    except Exception as e:
        print(f"⚠️  Could not check ffmpeg: {e}")
    
    # 1. Build Frontend
    print("\n--- 📦 Building Frontend ---")
    if not os.path.exists("frontend/package.json"):
        print("❌ frontend/package.json not found!")
        sys.exit(1)
    
    print("Installing frontend dependencies...")
    run_command("npm install", cwd="frontend")
    
    print("Building frontend...")
    run_command("npm run build", cwd="frontend")
    
    # Verify Frontend Build
    frontend_dist = os.path.join("frontend", "dist")
    if not os.path.exists(frontend_dist):
        print("❌ Frontend build directory not created!")
        sys.exit(1)
    
    dist_contents = os.listdir(frontend_dist)
    if not dist_contents:
        print("❌ Frontend build directory is empty!")
        sys.exit(1)
    
    print(f"✅ Frontend build successful. Contents: {dist_contents}")

    # 2. Build Backend
    print("\n--- 🐍 Installing Backend Dependencies ---")
    if not os.path.exists("backend/requirements.txt"):
        print("❌ backend/requirements.txt not found!")
        sys.exit(1)
    
    run_command("pip install -r requirements.txt", cwd="backend")
    
    # 3. Copy Static Files
    print("\n--- 📂 Moving Static Files ---")
    backend_dist = os.path.join("backend", "dist_build")
    
    # Clean old build
    if os.path.exists(backend_dist):
        print(f"Cleaning old build at {backend_dist}...")
        shutil.rmtree(backend_dist)
    
    os.makedirs(backend_dist, exist_ok=True)
    
    # Copy frontend dist to backend/dist_build
    print(f"Copying files from {frontend_dist} to {backend_dist}...")
    copied_count = 0
    for item in os.listdir(frontend_dist):
        src = os.path.join(frontend_dist, item)
        dst = os.path.join(backend_dist, item)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            copied_count += 1
        except Exception as e:
            print(f"⚠️ Warning: Failed to copy {item}: {e}")
    
    if copied_count == 0:
        print("❌ No files were copied!")
        sys.exit(1)
    
    print(f"✅ Copied {copied_count} items to {backend_dist}")
    
    # Verify copy
    if not os.path.exists(backend_dist) or not os.listdir(backend_dist):
        print("❌ Backend dist_build is empty after copy!")
        sys.exit(1)
    
    print(f"✅ Build verification: {os.listdir(backend_dist)}")
    
    print("\n--- 🎉 BUILD COMPLETE ---")
    print("Ready for deployment on Render!")

if __name__ == "__main__":
    main()
