import platform
import subprocess
try:
    import sounddevice as sd
    print("✅ sounddevice imported")
except ImportError:
    print("❌ sounddevice NOT found. Please run: pip install sounddevice")

def test_mic():
    if platform.system() != "Darwin":
        print("Not macOS")
        return
    
    print("\n[PERM] Testing Microphone Access...")
    try:
        def callback(indata, frames, time, status):
            if status:
                print(f"Status: {status}")
        
        print(">>> Attempting to open input stream. This SHOULD trigger a macOS dialog if not yet granted.")
        with sd.InputStream(callback=callback, channels=1, samplerate=16000):
            print("✅ Successfully opened input stream! (If you didn't see a dialog, it means access was already granted or the system blocked it silently.)")
    except Exception as e:
        print(f"❌ FAILED to open stream: {e}")
        print("\nPossible solutions:")
        print("1. Run: xattr -cr /path/to/app")
        print("2. Check 'System Settings' -> 'Privacy & Security' -> 'Microphone'")

if __name__ == "__main__":
    test_mic()
