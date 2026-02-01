import tkinter as tk
import os
import sys

# Add master to path to import utils
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    import fc.utils as us
except ImportError:
    # Mock utils if not found easily
    class us:
        WINDOWS = 'WIN'
        @staticmethod
        def platform():
            import platform
            return 'WIN' if platform.system() == 'Windows' else 'UNK'

def verify():
    print("--- Starting Icon Verification ---")
    
    # This script is in master/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Script dir: {script_dir}")
    
    # Files are in master/resources/icons
    icon_dir = os.path.join(script_dir, "resources", "icons")
    png_path = os.path.join(icon_dir, "fan_icon.png")
    ico_path = os.path.join(icon_dir, "fan_icon.ico")
    
    print(f"Checking PNG: {png_path} -> {os.path.exists(png_path)}")
    print(f"Checking ICO: {ico_path} -> {os.path.exists(ico_path)}")
    
    root = tk.Tk()
    root.title("Icon Verification")
    root.geometry("300x100")
    
    # 1. Try PNG
    try:
        if os.path.exists(png_path):
            icon = tk.PhotoImage(file=png_path)
            root.iconphoto(True, icon)
            print("SUCCESS: Loaded PNG icon via iconphoto")
        else:
            print("FAILURE: PNG file not found")
    except Exception as e:
        print(f"FAILURE: Could not load PNG icon: {e}")
        
    # 2. Try ICO
    try:
        if os.path.exists(ico_path):
            root.iconbitmap(ico_path)
            print("SUCCESS: Loaded ICO icon via iconbitmap")
        else:
            print("FAILURE: ICO file not found")
    except Exception as e:
        print(f"FAILURE: Could not load ICO icon: {e}")
        
    print("Window is open. Please check the taskbar and window icon.")
    print("Closing in 3 seconds...")
    root.after(3000, root.destroy)
    root.mainloop()
    print("--- Verification Finished ---")

if __name__ == "__main__":
    verify()
