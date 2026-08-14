import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np

# Add parent directory to path to make sure packages load if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import char_render

# Set theme colors (Sleek Dark Theme)
BG_COLOR = "#1e1e2e"
FRAME_COLOR = "#313244"
TEXT_COLOR = "#cdd6f4"
ACCENT_COLOR = "#89b4fa"      # Soft Blue
SUCCESS_COLOR = "#a6e3a1"     # Soft Green
BTN_HOVER_COLOR = "#b4befe"
INPUT_BG = "#45475a"
TEXT_MUTED = "#a6adc8"

class CharArtApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart CharArt Stylizer")
        self.root.geometry("920x540")
        self.root.resizable(True, True)
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
        self.style.configure("Sub.TLabel", background=BG_COLOR, foreground=TEXT_MUTED, font=("Segoe UI", 9))
        self.style.configure("Card.TLabel", background=FRAME_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        
        # Configure entries and buttons
        self.style.configure("TEntry", fieldbackground=INPUT_BG, background=INPUT_BG, foreground=TEXT_COLOR, borderwidth=0)
        self.style.configure("Action.TButton", font=("Segoe UI Semibold", 11), background=ACCENT_COLOR, foreground=BG_COLOR, borderwidth=0)
        self.style.map("Action.TButton", background=[("active", BTN_HOVER_COLOR)])
        
        self.style.configure("Browse.TButton", font=("Segoe UI", 9), background="#585b70", foreground=TEXT_COLOR, borderwidth=0)
        self.style.map("Browse.TButton", background=[("active", "#6c7086")])

        self.style.configure("TCheckbutton", background=FRAME_COLOR, foreground=TEXT_COLOR)
        self.style.map("TCheckbutton", background=[("active", FRAME_COLOR)], foreground=[("active", TEXT_COLOR)])

        self.style.configure("TRadiobutton", background=FRAME_COLOR, foreground=TEXT_COLOR)

        # State variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.style_var = tk.StringVar(value="ascii")
        self.fill_var = tk.StringVar(value="image")
        self.char_var = tk.StringVar(value=".:-+*#%@")
        self.cell_var = tk.IntVar(value=10)
        self.normalize_var = tk.BooleanVar(value=True)
        
        self.status_text = tk.StringVar(value="Select an image to start.")
        self.preview_image = None
        self.source_image = None
        
        # Setup trace callbacks for live preview updates
        self.input_path.trace_add("write", self.queue_preview_update)
        self.style_var.trace_add("write", self.on_style_changed)
        self.fill_var.trace_add("write", self.queue_preview_update)
        self.char_var.trace_add("write", self.queue_preview_update)
        self.normalize_var.trace_add("write", self.queue_preview_update)

        # UI Layout
        self.create_widgets()
        
        # Idle render timer for slider debouncing
        self.debounce_timer = None

    def create_widgets(self):
        # Master PanedWindow for Left Controls and Right Preview
        paned = ttk.Panedwindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=15, pady=15)

        # ------------------- LEFT PANEL: CONTROLS -------------------
        left_panel = ttk.Frame(paned, padding=(0, 0, 10, 0))
        paned.add(left_panel, weight=1)

        # Title Block
        header_frame = ttk.Frame(left_panel)
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="✨ Smart CharArt Stylizer", style="Title.TLabel")
        title_label.pack(anchor="w")
        sub_label = ttk.Label(header_frame, text="Convert images into stylized text characters in real time.", style="Sub.TLabel")
        sub_label.pack(anchor="w", pady=(2, 0))

        # Main Control Card
        card = ttk.Frame(left_panel, padding=12, style="Card.TFrame")
        card.pack(fill="both", expand=True)

        # Source File Row
        ttk.Label(card, text="Source Image:", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.input_entry = ttk.Entry(card, textvariable=self.input_path, font=("Segoe UI", 9))
        self.input_entry.grid(row=0, column=1, padx=6, pady=4, sticky="ew")
        
        browse_in_btn = ttk.Button(card, text="Browse...", style="Browse.TButton", command=self.browse_input)
        browse_in_btn.grid(row=0, column=2, pady=4, padx=(2, 0))

        # Save Path Row
        ttk.Label(card, text="Output Path:", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        self.output_entry = ttk.Entry(card, textvariable=self.output_path, font=("Segoe UI", 9))
        self.output_entry.grid(row=1, column=1, padx=6, pady=4, sticky="ew")
        
        browse_out_btn = ttk.Button(card, text="Change...", style="Browse.TButton", command=self.browse_output)
        browse_out_btn.grid(row=1, column=2, pady=4, padx=(2, 0))

        # Divider
        ttk.Separator(card, orient="horizontal").grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")

        # Style Dropdown Row
        ttk.Label(card, text="Render Style:", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=4)
        self.style_combo = ttk.Combobox(card, textvariable=self.style_var, values=["ascii", "mono", "hatch", "custom"], state="readonly", width=18)
        self.style_combo.grid(row=3, column=1, sticky="w", padx=6, pady=4)

        # Character / Custom Ramp Row
        self.char_label = ttk.Label(card, text="Custom Ramp:", style="Card.TLabel")
        self.char_label.grid(row=4, column=0, sticky="w", pady=4)
        self.char_entry = ttk.Entry(card, textvariable=self.char_var, font=("Segoe UI", 9))
        self.char_entry.grid(row=4, column=1, columnspan=2, padx=6, pady=4, sticky="ew")

        # Background Fill Row
        ttk.Label(card, text="Background Fill:", style="Card.TLabel").grid(row=5, column=0, sticky="w", pady=4)
        self.fill_combo = ttk.Combobox(card, textvariable=self.fill_var, values=["none", "tint", "image"], state="readonly", width=18)
        self.fill_combo.grid(row=5, column=1, sticky="w", padx=6, pady=4)

        # Cell Size Slider Row
        ttk.Label(card, text="Cell Grid Size:", style="Card.TLabel").grid(row=6, column=0, sticky="w", pady=6)
        
        slider_frame = ttk.Frame(card)
        slider_frame.configure(style="Card.TFrame")
        slider_frame.grid(row=6, column=1, columnspan=2, padx=6, pady=6, sticky="ew")
        
        self.cell_scale = ttk.Scale(slider_frame, from_=4, to=32, variable=self.cell_var, orient="horizontal", command=self.on_slider_scroll)
        self.cell_scale.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self.cell_val_label = ttk.Label(slider_frame, text="10 px", width=5, style="Card.TLabel")
        self.cell_val_label.pack(side="right")

        # Contrast Normalize Row
        self.norm_check = ttk.Checkbutton(card, text="Auto-Normalize Contrast (helps dark images)", variable=self.normalize_var)
        self.norm_check.grid(row=7, column=1, columnspan=2, sticky="w", padx=6, pady=6)

        card.columnconfigure(1, weight=1)

        # Status Block (Bottom left)
        status_frame = ttk.Frame(left_panel, padding=(5, 10, 5, 0))
        status_frame.pack(fill="x", side="bottom")
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_text, font=("Segoe UI", 9), foreground=TEXT_MUTED)
        self.status_label.pack(side="left", fill="x", expand=True)

        self.action_btn = ttk.Button(status_frame, text="Render & Save Full Art", style="Action.TButton", command=self.save_full_art)
        self.action_btn.pack(side="right", ipadx=12, ipady=4)

        # ------------------- RIGHT PANEL: PREVIEW -------------------
        right_panel = ttk.Frame(paned, padding=(10, 0, 0, 0))
        paned.add(right_panel, weight=1)

        preview_card = ttk.Frame(right_panel, padding=12, style="Card.TFrame")
        preview_card.pack(fill="both", expand=True)
        
        ttk.Label(preview_card, text="Live Render Preview", font=("Segoe UI Semibold", 11), style="Card.TLabel").pack(anchor="w", pady=(0, 8))

        # Styled canvas container for the preview image
        self.preview_canvas_frame = ttk.Frame(preview_card, style="Card.TFrame")
        self.preview_canvas_frame.pack(fill="both", expand=True)

        self.preview_lbl = tk.Label(
            self.preview_canvas_frame,
            text="No source image loaded.\nUse 'Browse' to select a photo and view live renders.",
            bg=BG_COLOR,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
            relief="sunken",
            bd=1
        )
        self.preview_lbl.pack(fill="both", expand=True)

        # Trigger initial field configuration
        self.on_style_changed()

    def browse_input(self):
        file_path = filedialog.askopenfilename(
            title="Select Source Image File",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"), ("All Files", "*.*")]
        )
        if file_path:
            self.input_path.set(os.path.normpath(file_path))
            
            # Suggest output file path in the workspace Output directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            proj_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
            output_dir = os.path.join(proj_root, "Output")
            
            _, file_name = os.path.split(file_path)
            name, _ = os.path.splitext(file_name)
            suggested_out = os.path.join(output_dir, f"{name}_charart.png")
            self.output_path.set(os.path.normpath(suggested_out))
            
            self.status_text.set("Image loaded successfully.")
            self.load_source_image()

    def browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Rendered Artwork As",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All Files", "*.*")]
        )
        if file_path:
            self.output_path.set(os.path.normpath(file_path))

    def load_source_image(self):
        in_file = self.input_path.get().strip()
        if in_file and os.path.exists(in_file):
            # Load full image
            self.source_image = cv2.imread(in_file, cv2.IMREAD_COLOR)
            if self.source_image is not None:
                self.queue_preview_update()
            else:
                self.status_text.set("Error: Failed to read image file.")

    def on_style_changed(self, *args):
        style = self.style_var.get()
        if style == "mono":
            self.char_label.configure(text="Stipple Character:")
            self.char_entry.configure(state="normal")
            if self.char_var.get() == ".:-+*#%@" or not self.char_var.get():
                self.char_var.set("+")
        elif style == "custom":
            self.char_label.configure(text="Custom Ramp:")
            self.char_entry.configure(state="normal")
            if self.char_var.get() == "+" or not self.char_var.get():
                self.char_var.set(".:-+*#%@")
        else:
            # ascii or hatch style ignores custom character ramps
            self.char_label.configure(text="Custom Ramp (N/A):")
            self.char_entry.configure(state="disabled")
            
        self.queue_preview_update()

    def on_slider_scroll(self, val):
        # Update numerical label immediately
        cell = int(float(val))
        self.cell_var.set(cell)
        self.cell_val_label.configure(text=f"{cell} px")
        
        # Debounce the preview rendering update by 150ms to keep dragging fluid
        if self.debounce_timer:
            self.root.after_cancel(self.debounce_timer)
        self.debounce_timer = self.root.after(150, self.queue_preview_update)

    def queue_preview_update(self, *args):
        if self.source_image is None:
            return
        
        # Trigger rendering in the idle loop to keep UI thread responsive
        self.root.after_idle(self.render_preview)

    def render_preview(self):
        if self.source_image is None:
            return

        try:
            # Obtain parameters
            style = self.style_var.get()
            cell = self.cell_var.get()
            char = self.char_var.get()
            fill = self.fill_var.get()
            normalize = self.normalize_var.get()

            # Sizing for rapid preview: Downscale the source image to fits into a max 380px bounding box.
            # This makes preview renders almost instantaneous and highly fluid!
            h, w = self.source_image.shape[:2]
            max_preview_dim = 360
            scale = min(max_preview_dim / w, max_preview_dim / h)
            
            # Ensure cell size matches the downscaled preview space proportionally.
            # E.g., if real image is 1920px with cell 10, then a 380px preview image uses a cell of 2.
            preview_w = int(w * scale)
            preview_h = int(h * scale)
            
            # Floor limit cell size to 3 in downscaled preview so glyphs remain readable
            preview_cell = max(3, int(cell * scale))
            
            # Resize source to preview scale
            preview_source = cv2.resize(self.source_image, (preview_w, preview_h), interpolation=cv2.INTER_AREA)

            # Draw using CharArt core engine
            # Standard Font Scale is adjusted proportionally to preview cell sizes
            fontscale = max(0.2, 0.5 * (preview_cell / 12))
            
            canvas = char_render.render(
                img=preview_source,
                style=style,
                cell=preview_cell,
                ink=(220, 220, 220), # Flat ink
                bg=(12, 12, 12),      # Flat background
                fontscale=fontscale,
                mono_char=char,
                fill=fill,
                normalize=normalize
            )

            # Convert BGR array to Tkinter PhotoImage using standard library
            success, encoded_img = cv2.imencode('.png', canvas)
            if success:
                self.preview_image = tk.PhotoImage(data=encoded_img.tobytes())
                self.preview_lbl.configure(image=self.preview_image, text="")
                self.status_text.set(f"Preview updated. Render grid size: {preview_w//preview_cell}x{preview_h//preview_cell}.")
        
        except Exception as e:
            self.status_text.set(f"Render Error: {str(e)}")

    def save_full_art(self):
        in_file = self.input_path.get().strip()
        out_file = self.output_path.get().strip()

        if not in_file or self.source_image is None:
            messagebox.showerror("Error", "Please select a valid source image first.")
            return

        if not out_file:
            messagebox.showerror("Error", "Please specify a save destination.")
            return

        # Ensure output directory exists
        parent_dir = os.path.dirname(out_file)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        self.status_text.set("Rendering full-resolution artwork...")
        self.action_btn.configure(state="disabled")
        self.root.update()

        # Run full-scale render in a background thread to keep Tkinter responsive
        threading.Thread(target=self.process_full_scale, args=(out_file,), daemon=True).start()

    def process_full_scale(self, out_file):
        try:
            style = self.style_var.get()
            cell = self.cell_var.get()
            char = self.char_var.get()
            fill = self.fill_var.get()
            normalize = self.normalize_var.get()

            # Dynamic fontscale based on cell size (Standard matches 0.5 for 12px cell size)
            fontscale = max(0.15, 0.5 * (cell / 12))

            # Full-scale high resolution render
            canvas = char_render.render(
                img=self.source_image,
                style=style,
                cell=cell,
                ink=(220, 220, 220),
                bg=(12, 12, 12),
                fontscale=fontscale,
                mono_char=char,
                fill=fill,
                normalize=normalize
            )

            # Write file using OpenCV
            success = cv2.imwrite(out_file, canvas)
            
            if success:
                self.root.after(0, lambda: self.finish_full_scale(True, out_file))
            else:
                self.root.after(0, lambda: self.finish_full_scale(False, "Failed to write output image."))
        
        except Exception as e:
            self.root.after(0, lambda: self.finish_full_scale(False, str(e)))

    def finish_full_scale(self, success, details):
        self.action_btn.configure(state="normal")
        if success:
            self.status_text.set("Render completed successfully!")
            messagebox.showinfo("Success", f"Full-resolution CharArt saved successfully!\n\nDestination:\n{details}")
        else:
            self.status_text.set(f"Render failed: {details}")
            messagebox.showerror("Error", f"Rendering failed!\n\nDetails: {details}")

def main():
    root = tk.Tk()
    app = CharArtApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
