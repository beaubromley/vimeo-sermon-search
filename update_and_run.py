import subprocess
import sys
from pathlib import Path
import time
import os

def run_script(script_path, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Running: {script_path}")
    
    try:
        # Run the script from the current directory (vimeo_project root)
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=False, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully!")
            return True
        else:
            print(f"❌ {description} failed with return code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running {script_path}: {e}")
        return False

def run_interactive_script(script_path, description):
    """Run an interactive script (like search interface) without capturing output"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Starting: {script_path}")
    
    try:
        # Run interactively without capturing output
        subprocess.run([
            sys.executable, script_path
        ], cwd=Path.cwd())
        return True
    except Exception as e:
        print(f"❌ Error running {script_path}: {e}")
        return False

def check_directory_structure():
    """Verify we're in the right directory"""
    current_dir = Path.cwd()
    required_folders = ['data', 'scripts', 'src']
    
    print(f"📁 Current directory: {current_dir}")
    print(f"📂 Checking for required folders...")
    
    missing_folders = []
    for folder in required_folders:
        folder_path = current_dir / folder
        if folder_path.exists():
            print(f"  ✅ {folder}/ found")
        else:
            print(f"  ❌ {folder}/ NOT found")
            missing_folders.append(folder)
    
    if missing_folders:
        print(f"\n❌ ERROR: Missing required folders: {missing_folders}")
        print(f"📍 Make sure you're running this from the vimeo_project root directory")
        print(f"📁 Your current directory should contain: data/, scripts/, src/")
        return False
    
    return True

def main():
    print("🎥 Vimeo Transcript Manager - Full Update Process")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not check_directory_structure():
        input("\nPress Enter to exit...")
        return
    
    print("\nThis will run the complete 4-step process:")
    print("1. 📥 Download new videos and transcripts")
    print("2. 💾 Update the searchable database") 
    print("3. 📊 Show updated KPIs and statistics")
    print("4. 🔍 Launch search interface")
    print()
       
    start_time = time.time()
    
    # Step 1: Download videos (using incremental for speed)
    if not run_script("scripts/download_videos_incremental.py", "STEP 1: Downloading Videos & Transcripts"):
        print("\n❌ Process stopped due to download error.")
        print("💡 You can try running scripts/download_videos.py instead for a full refresh.")
        
        # Ask if user wants to continue anyway
        continue_response = input("\nDo you want to continue with database update anyway? (y/n): ").lower().strip()
        if continue_response not in ['y', 'yes']:
            input("Press Enter to exit...")
            return
    
    print("\n⏳ Waiting 3 seconds before next step...")
    time.sleep(3)
    
    # Step 2: Update database  
    if not run_script("scripts/update_database.py", "STEP 2: Updating Database"):
        print("\n❌ Process stopped due to database error.")
        print("💡 Check that transcript files were downloaded correctly.")
        
        # Ask if user wants to see stats and search anyway
        continue_response = input("\nDo you want to continue to view stats and search? (y/n): ").lower().strip()
        if continue_response not in ['y', 'yes']:
            input("Press Enter to exit...")
            return
    
    print("\n⏳ Waiting 2 seconds before showing results...")
    time.sleep(2)
    
    # Step 3: Show KPIs
    run_script("scripts/show_kpis.py", "STEP 3: Updated Statistics")
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n🎉 UPDATE PROCESS COMPLETED!")
    print(f"⏱️  Total time: {duration:.1f} seconds")
    
    # Ask if user wants to start searching
    print("\n🚀 Launching search interface...")
    print("💡 Remember: You can search both video titles and transcript content!")
    print("💡 Type 'quit' to exit the search interface when you're done")
    
    time.sleep(2)  # Brief pause before launching
    
    run_interactive_script("scripts/search_interface.py", "STEP 4: Search Interface")
    
    print(f"\n👋 Search interface closed. Thanks for using Vimeo Transcript Manager!")
    
if __name__ == "__main__":
    main()
