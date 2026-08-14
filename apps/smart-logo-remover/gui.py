import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2

# Set theme colors (Sleek Dark Theme)
BG_COLOR = "#1e1e2e"
FRAME_COLOR = "#313244"
TEXT_COLOR = "#cdd6f4"
ACCENT_COLOR = "#89b4fa"  # Soft Blue
SUCCESS_COLOR = "#a6e3a1" # Soft Green
BTN_HOVER_COLOR = "#b4befe"
INPUT_BG = "#45475a"

class LogoRemoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Logo Remover")
        self.root.geometry("620x360")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)

        # Style configurations
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure frames and labels
        self.style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR)
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("Card.TFrame", background=FRAME_COLOR, relief="flat")
        self.style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background=BG_COLOR, foreground=ACCENT_COLOR, font=("Segoe UI Semibold", 16))
        self.style.configure("Sub.TLabel", background=BG_COLOR, foreground="#a6adc8", font=("Segoe UI", 9))
        self.style.configure("Card.TLabel", background=FRAME_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        
        # Configure entry and buttons
        self.style.configure("TEntry", fieldbackground=INPUT_BG, background=INPUT_BG, foreground=TEXT_COLOR, borderwidth=0)
        self.style.configure("Action.TButton", font=("Segoe UI Semibold", 11), background=ACCENT_COLOR, foreground=BG_COLOR, borderwidth=0)
        self.style.map("Action.TButton", background=[("active", BTN_HOVER_COLOR)])
        
        self.style.configure("Browse.TButton", font=("Segoe UI", 9), background="#585b70", foreground=TEXT_COLOR, borderwidth=0)
        self.style.map("Browse.TButton", background=[("active", "#6c7086")])

        # State variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready to process.")
        self.progress_val = tk.DoubleVar(value=0.0)
        self.is_processing = False

        # Create Layout
        self.create_widgets()

    def create_widgets(self):
        # 1. Header Frame
        header_frame = ttk.Frame(self.root, padding=(20, 15, 20, 10))
        header_frame.pack(fill="x")
        
        title_label = ttk.Label(header_frame, text="✨ Smart Logo Remover", style="Title.TLabel")
        title_label.pack(anchor="w")
        sub_label = ttk.Label(header_frame, text="Remove channel logos and watermarks locally with zero hardware bottleneck.", style="Sub.TLabel")
        sub_label.pack(anchor="w", pady=(2, 0))

        # 2. Main Card Frame
        card = ttk.Frame(self.root, padding=15, style="Card.TFrame")
        card.pack(fill="both", expand=True, padx=20, pady=(5, 10))

        # Input Row
        ttk.Label(card, text="Source Video:", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=5)
        self.input_entry = ttk.Entry(card, textvariable=self.input_path, width=42, font=("Segoe UI", 9))
        self.input_entry.grid(row=0, column=1, padx=8, pady=5, sticky="ew")
        
        browse_in_btn = ttk.Button(card, text="Browse...", style="Browse.TButton", command=self.browse_input)
        browse_in_btn.grid(row=0, column=2, pady=5)

        # Output Row
        ttk.Label(card, text="Save Cleaned To:", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=10)
        self.output_entry = ttk.Entry(card, textvariable=self.output_path, width=42, font=("Segoe UI", 9))
        self.output_entry.grid(row=1, column=1, padx=8, pady=10, sticky="ew")
        
        browse_out_btn = ttk.Button(card, text="Change...", style="Browse.TButton", command=self.browse_output)
        browse_out_btn.grid(row=1, column=2, pady=10)

        card.columnconfigure(1, weight=1)

        # 3. Control & Status Frame
        control_frame = ttk.Frame(self.root, padding=(20, 5, 20, 15))
        control_frame.pack(fill="x", side="bottom")

        # Progress bar
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_val, maximum=100, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 10))

        # Status & Action Row
        status_row = ttk.Frame(control_frame)
        status_row.pack(fill="x")

        self.status_label = ttk.Label(status_row, textvariable=self.status_text, font=("Segoe UI", 9), foreground="#a6adc8")
        self.status_label.pack(side="left", fill="x", expand=True)

        self.action_btn = ttk.Button(status_row, text="Select Logo & Remove", style="Action.TButton", command=self.start_workflow)
        self.action_btn.pack(side="right", ipadx=10, ipady=4)

    def browse_input(self):
        file_path = filedialog.askopenfilename(
            title="Select Source Video File",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.flv *.webm"), ("All Files", "*.*")]
        )
        if file_path:
            self.input_path.set(os.path.normpath(file_path))
            # Auto-suggest output path
            dir_name, file_name = os.path.split(file_path)
            name, ext = os.path.splitext(file_name)
            suggested_out = os.path.join(dir_name, f"{name}_nologo{ext}")
            self.output_path.set(os.path.normpath(suggested_out))
            self.status_text.set("Ready to select logo.")
            self.progress_val.set(0.0)

    def browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Cleaned Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")]
        )
        if file_path:
            self.output_path.set(os.path.normpath(file_path))

    def start_workflow(self):
        in_file = self.input_path.get().strip()
        out_file = self.output_path.get().strip()

        if not in_file or not os.path.exists(in_file):
            messagebox.showerror("Error", "Please select a valid source video file first.")
            return

        if not out_file:
            messagebox.showerror("Error", "Please specify a save destination.")
            return

        if self.is_processing:
            return

        # Phase 1: Open Video and select ROI
        self.status_text.set("Loading video frame...")
        self.root.update()

        cap = cv2.VideoCapture(in_file)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open the video file.")
            self.status_text.set("Error: Failed to open video.")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Seek 5 seconds (or 10% in) to get a clear sample frame
        seek_frame = min(int(fps * 5), max(0, total_frames // 10))
        cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)
        ret, frame = cap.read()
        
        if not ret or frame is None:
            # Try frame 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()

        cap.release()

        if not ret or frame is None:
            messagebox.showerror("Error", "Could not retrieve any frames from the video.")
            self.status_text.set("Error: Failed to read video frame.")
            return

        # Show OpenCV selection window
        window_title = "Select Logo - Drag Box + Press ENTER"
        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_title, 1100, 620)
        
        # Display window
        messagebox.showinfo("Instructions", 
                            "An interactive window will open.\n\n"
                            "1. CLICK & DRAG a rectangle over the logo.\n"
                            "2. Press ENTER or SPACE to confirm.\n"
                            "3. Press 'C' to clear/retry if you make a mistake.")
        
        roi = cv2.selectROI(window_title, frame, fromCenter=False, showCrosshair=True)
        cv2.destroyAllWindows()

        x, y, w, h = roi
        if w <= 0 or h <= 0:
            self.status_text.set("Selection cancelled.")
            return

        # Border security adjustments for delogo filter
        if x < 1:
            w = max(1, w - (1 - x))
            x = 1
        if y < 1:
            h = max(1, h - (1 - y))
            y = 1
        if x + w >= width:
            w = width - x - 1
        if y + h >= height:
            h = height - y - 1

        # Phase 2: Launch processing in background thread
        self.is_processing = True
        self.action_btn.configure(state="disabled")
        self.input_entry.configure(state="disabled")
        self.output_entry.configure(state="disabled")
        self.progress_val.set(0.0)
        self.status_text.set("Initializing FFmpeg...")

        # Resolve static FFmpeg path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
        ffmpeg_path = os.path.join(proj_root, "Libraries", "FFmpeg", "node_modules", "ffmpeg-ffprobe-static", "ffmpeg.exe")

        if not os.path.exists(ffmpeg_path):
            ffmpeg_path = "ffmpeg"  # Fallback to system

        # Start thread
        threading.Thread(
            target=self.process_video,
            args=(ffmpeg_path, in_file, out_file, x, y, w, h, total_frames),
            daemon=True
        ).start()

    def process_video(self, ffmpeg_path, in_file, out_file, x, y, w, h, total_frames):
        delogo_filter = f"delogo=x={x}:y={y}:w={w}:h={h}"
        cmd = [
            ffmpeg_path, "-y",
            "-i", in_file,
            "-vf", delogo_filter,
            "-c:a", "copy",
            out_file
        ]

        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE # Hide console popup

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=startupinfo
            )

            # Monitor progress
            for line in process.stdout:
                if "frame=" in line:
                    parts = line.strip().split()
                    frame_num = 0
                    for part in parts:
                        if part.startswith("frame="):
                            try:
                                frame_num = int(part.split("=")[1])
                            except:
                                pass
                    if frame_num > 0 and total_frames > 0:
                        pct = min(100.0, (frame_num / total_frames) * 100.0)
                        self.progress_val.set(pct)
                        self.status_text.set(f"Processing... {pct:.1f}% ({frame_num}/{total_frames} frames)")
            
            process.wait()
            
            if process.returncode == 0:
                self.progress_val.set(100.0)
                self.status_text.set("Success! Video processed successfully.")
                messagebox.showinfo("Success", f"Logo successfully removed!\n\nSaved to:\n{out_file}")
            else:
                self.status_text.set(f"Error: Process failed with code {process.returncode}")
                messagebox.showerror("Error", f"FFmpeg failed with exit code {process.returncode}")
        
        except Exception as e:
            self.status_text.set("Processing error.")
            messagebox.showerror("Error", f"Failed to run process: {str(e)}")
        
        finally:
            self.is_processing = False
            self.action_btn.configure(state="normal")
            self.input_entry.configure(state="normal")
            self.output_entry.configure(state="normal")

def main():
    root = tk.Tk()
    app = LogoRemoverApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
