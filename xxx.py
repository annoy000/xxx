# To install all dependencies and run this code in PowerShell, copy and paste the following command into your terminal:
# pip install pyautogui google-generativeai pynput pyperclip ; python git.py

import tkinter as tk
import pyautogui
import google.generativeai as genai
import os
import threading
import time
import ctypes
import pyperclip
from pynput import keyboard
from pynput.keyboard import Key, Listener

# --- CONFIGURATION ---
# Add your API keys to this list. If the first one runs out of quota, it will automatically switch to the next.
API_KEYS = [
    "AIzaSyClakWCa9gHlpKAXzUbKQW92PzkFss5u3I", # Your first API key
    "AIzaSyDrFMtnvUbJ2n9HNr6xG5T-Zcj-3fHjifE",
    "AIzaSyC6r_tQo9T-isoZFS8aYHM1It6pWvIH4MY"
]

current_key_index = 0
model = None

def configure_gemini():
    global current_key_index, model
    if current_key_index < len(API_KEYS):
        try:
            genai.configure(api_key=API_KEYS[current_key_index])
            model = genai.GenerativeModel('gemini-2.5-flash')
            return True
        except Exception as e:
            return False
    return False

# Note: We are NOT using Tesseract OCR anymore
# The application now sends screenshots directly to Gemini AI for analysis
# This provides better accuracy and handles all question types

# Initialize the first API key
if not configure_gemini():
    exit()

# Global variables for storing answers and controlling the app
stored_answer = None
answer_window = None
answer_label = None

# --- STEALTH FUNCTIONS ---
def hide_from_taskbar():
    """Hide the application from taskbar and make it stealth."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.ShowWindow(hwnd, 0)
        ctypes.windll.user32.SetWindowLongW(hwnd, -8, 0)
    except Exception as e:
        pass

def minimize_to_system_tray():
    """Minimize to system tray (if available)."""
    try:
        root.withdraw()
    except Exception as e:
        pass

def disable_console_window():
    """Hide the console window on Windows."""
    try:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception as e:
        pass


# --- CORE FUNCTIONS ---

def set_status_async(text, color):
    """Thread-safe status label update scheduled on Tk main loop."""
    try:
        def _apply():
            try:
                status_label.config(text=text, fg=color)
            except Exception:
                pass
        root.after(0, _apply)
    except Exception:
        pass

def process_screen_and_get_answer():
    """
    Main logic: Capture screen, send to Gemini with image, and get MCQ answer.
    """
    global stored_answer
    
    try:
        # Update status
        set_status_async("📸 Capturing screen...", "yellow")
        
        # 1. Capture the entire screen
        screenshot = pyautogui.screenshot()
        
        # Update status
        set_status_async("🤖 Analyzing with AI...", "yellow")
        
        # 2. Send the screenshot directly to Gemini for analysis
        
        # Create a comprehensive prompt for both MCQs and coding questions
        prompt = """Look at this screenshot carefully. This could be a multiple choice question (MCQ) or a coding question.

Your task:
1. Identify if this is an MCQ or coding question
2. For MCQs: Return the correct option letter (A, B, C, D, etc.)
3. For coding questions: Return the complete code solution in nodejs or java language

For MCQ questions:
- Read the question and all answer options (A, B, C, D, etc.)
- Use logical reasoning to determine the correct answer
- Return ONLY the correct option letter

For coding questions:
- Analyze the code problem, error, or requirement
- Provide the complete, working code solution
- Include proper formatting and indentation
- Analyze the question if its a a coding question of nodejs or moongoes  the code should be in the language of the question


Response format:
- MCQ: Just the letter (A, B, C, D, etc.)
- Coding: Complete code solution

Examples:
- MCQ: B
- Coding: 
class Solution {
    public int add(int a, int b) {
        return a + b;
    }
}

If you cannot see the question clearly, respond: Cannot determine"""

        # Send both image and text prompt to Gemini
        global current_key_index
        max_retries = len(API_KEYS)
        retry_count = 0
        response = None
        
        while retry_count < max_retries:
            try:
                response = model.generate_content([prompt, screenshot])
                break # Success
            except Exception as e:
                error_msg = str(e).lower()
                # Check if it's a quota/rate limit error (429) or other API error
                if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg or "api key" in error_msg:
                    print(f"API Key {current_key_index + 1} failed/exhausted. Switching to next key...")
                    current_key_index += 1
                    if configure_gemini():
                        retry_count += 1
                        continue
                    else:
                        raise Exception("All API keys exhausted or invalid.")
                else:
                    raise e
                    
        if not response:
            raise Exception("Failed to get response from Gemini.")

        answer = response.text.strip()
        
        # Clean up the answer - remove any prefixes
        if "Answer:" in answer:
            answer = answer.split("Answer:")[-1].strip()
        if "answer:" in answer:
            answer = answer.split("answer:")[-1].strip()
        
        # Store the answer globally and copy to clipboard
        stored_answer = answer
        print(f"Answer stored: {stored_answer}")
        
        # Copy answer to clipboard for easy pasting
        try:
            pyperclip.copy(answer)
            print("Answer copied to clipboard")
        except Exception as e:
            print(f"Clipboard error: {e}")
        
        # If overlay already exists, refresh its text with the latest answer
        try:
            if answer_window and answer_window.winfo_exists():
                def _update_existing_label():
                    try:
                        if answer_label:
                            answer_label.config(text=stored_answer)
                    except Exception:
                        pass
                root.after(0, _update_existing_label)
        except Exception:
            pass

        set_status_async("✅ Answer ready! Press . to show answer", "green")
        
    except Exception as e:
        stored_answer = f"Error: {e}"
        set_status_async(f"❌ Error: {str(e)[:50]}...", "red")


def start_processing_thread():
    """Starts the processing in a separate thread to keep the GUI responsive."""
    threading.Thread(target=process_screen_and_get_answer).start()

def show_answer_while_holding():
    """Shows the answer window while the period key is held down."""
    global answer_window
    global answer_label
    
    if not stored_answer:
        return
    
    # Copy answer to clipboard when showing
    try:
        pyperclip.copy(stored_answer)
    except Exception as e:
        pass
    
    # If window already exists, refresh text and make it visible
    if answer_window and answer_window.winfo_exists():
        try:
            if answer_label:
                answer_label.config(text=stored_answer)
        except Exception:
            pass
        answer_window.deiconify()
        answer_window.lift()
        answer_window.focus_force()
        return
    
    # Get screen dimensions for center positioning
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Determine window size based on answer length
    if len(stored_answer) <= 5:  # MCQ answer (short)
        window_width = 200
        window_height = 100
        font_size = 48
        font_family = "Arial"
    else:  # Coding answer (long)
        window_width = min(800, screen_width - 100)
        window_height = min(600, screen_height - 100)
        font_size = 12
        font_family = "Consolas"
    
    # Create a new window for the answer - positioned at center
    answer_window = tk.Toplevel()
    answer_window.title("")
    answer_window.geometry("{}x{}+{}+{}".format(
        window_width,
        window_height,
        (screen_width - window_width) // 2,  # Center horizontally
        (screen_height - window_height) // 2  # Center vertically
    ))
    answer_window.attributes("-topmost", True)
    answer_window.configure(bg='white')  # White background for better visibility
    answer_window.overrideredirect(True)  # Remove title bar
    answer_window.attributes("-alpha", 0.99)  # Slight transparency
    
    # Create label for the answer
    answer_label = tk.Label(
        answer_window,
        text=stored_answer,
        font=(font_family, font_size, "bold"),
        fg="#000000",  # Black color for better visibility
        bg='white',  # White background
        justify="left" if len(stored_answer) > 5 else "center",
        wraplength=window_width - 20
    )
    answer_label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    
    # Make sure the window is visible
    answer_window.deiconify()
    answer_window.lift()
    answer_window.focus_force()

def hide_answer_on_release():
    """Hides the answer window when the period key is released."""
    global answer_window
    
    if answer_window and answer_window.winfo_exists():
        try:
            answer_window.withdraw()  # Hide the window instead of destroying it
        except Exception as e:
            pass




# --- HOTKEY SETUP ---
def setup_global_hotkeys():
    """Setup global hotkeys using pynput."""
    try:
        from pynput import keyboard
        
        
        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char == ',':
                    print("Comma pressed - Starting scan...")
                    # Schedule on main thread to avoid Tk from non-main threads
                    root.after(0, start_processing_thread)
                elif hasattr(key, 'char') and key.char == '.':
                    print("Period pressed - Showing answer...")
                    # Schedule UI on main thread
                    root.after(0, show_answer_while_holding)
                elif key == keyboard.Key.esc:
                    print("ESC pressed - Exiting...")
                    return False
            except Exception as e:
                print(f"Key press error: {e}")
                pass
        
        def on_release(key):
            try:
                if hasattr(key, 'char') and key.char == '.':
                    # Schedule UI on main thread
                    root.after(0, hide_answer_on_release)
            except Exception as e:
                pass
        
        # Start the listener
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        return listener
    except Exception as e:
        return None

# --- STEALTH GUI SETUP ---
root = tk.Tk()
root.title("")
root.geometry("1x1+0+0")
root.attributes("-topmost", True)
root.attributes("-alpha", 0.0)
root.overrideredirect(True)
root.withdraw()
root.attributes("-toolwindow", True)
root.attributes("-disabled", True)
root.attributes("-transparentcolor", "black")

# Minimal invisible elements for functionality
button = tk.Button(root, text="", command=start_processing_thread, font=("Arial", 1), bg="black", fg="black", bd=0, height=1, width=1)
button.pack()
status_label = tk.Label(root, text="", font=("Arial", 1), fg="black", bg="black")
status_label.pack()

# --- START THE APP ---
# Setup global hotkeys
listener = setup_global_hotkeys()

# Enable stealth mode
hide_from_taskbar()
minimize_to_system_tray()

# Hide console window after a delay
def hide_console_delayed():
    time.sleep(2)
    disable_console_window()

threading.Thread(target=hide_console_delayed, daemon=True).start()

try:
    root.mainloop()
except KeyboardInterrupt:
    pass
except Exception as e:
    pass
finally:
    if listener:
        listener.stop()

      