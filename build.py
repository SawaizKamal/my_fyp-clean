import os
import subprocess
import shutil
import sys

def run_command(command, cwd=None):
    print(f"--- 🏃 Running: {command} in {cwd or '.'} ---")
    try:
        subprocess.check_call(command, shell=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {e}")
        sys.exit(1)

def main():
    print("--- 🚀 STARTING PYTHON BUILD SCRIPT ---")
    
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
    print("--- 📦 Building Frontend ---")
    run_command("npm install", cwd="frontend")
    run_command("npm run build", cwd="frontend")
    
    # Verify Frontend Build
    frontend_dist = os.path.join("frontend", "dist")
    if os.path.exists(frontend_dist) and os.listdir(frontend_dist):
        print(f"✅ Frontend build successful. Contents: {os.listdir(frontend_dist)}")
    else:
        print("❌ Frontend build creation failed!")
        sys.exit(1)

    # 2. Build Backend
    print("--- 🐍 Installing Backend Dependencies ---")
    run_command("pip install -r requirements.txt", cwd="backend")
    
    # 3. Copy Static Files
    print("--- 📂 Moving Static Files ---")
    backend_dist = os.path.join("backend", "dist_build")
    
    # Clean old
    if os.path.exists(backend_dist):
        shutil.rmtree(backend_dist)
    os.makedirs(backend_dist)
    
    # Copy
    # shutil.copytree requires destination to NOT exist usually, but we made it.
    # So iterating or using distutils is easier, or just copytree to a temp and rename.
    # Actually, let's just use cp command or shutil properly
    
    # Simpler: copy tree content
    for item in os.listdir(frontend_dist):
        s = os.path.join(frontend_dist, item)
        d = os.path.join(backend_dist, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
            
    print(f"✅ Copied files to {backend_dist}")
    print("Files in dist_build:", os.listdir(backend_dist))
    
    print("--- 🎉 BUILD COMPLETE ---")

if __name__ == "__main__":
    main()
