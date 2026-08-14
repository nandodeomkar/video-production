import os
import sys
import subprocess
import cv2

def main():
    if len(sys.argv) < 3:
        print("Usage: python remove_logo.py <input_video> <output_video>")
        sys.exit(1)

    input_video = sys.argv[1]
    output_video = sys.argv[2]

    if not os.path.exists(input_video):
        print(f"Error: Input video '{input_video}' does not exist.")
        sys.exit(1)

    print(f"Opening video: {input_video}")
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print("Error: Could not open the video file.")
        sys.exit(1)

    # Get total frames and FPS to seek past any initial black screens
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video Info: {width}x{height} @ {fps:.2f} fps, {total_frames} total frames")

    # Seek to 5 seconds (or 10% of the video if it's very short) to get a good frame for logo selection
    seek_frame = min(int(fps * 5), max(0, total_frames // 10))
    cap.set(cv2.CAP_PROP_POS_FRAMES, seek_frame)

    ret, frame = cap.read()
    if not ret or frame is None:
        # Fallback: try to read the very first frame if seeking failed
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Error: Could not read any frames from the video.")
            sys.exit(1)

    cap.release()

    # Create a friendly window instructions banner
    instruction_text = "DRAG A BOX OVER THE LOGO, THEN PRESS ENTER OR SPACE. PRESS 'C' TO CLEAR, OR 'Q' TO QUIT."
    print("\n" + "=" * len(instruction_text))
    print(instruction_text)
    print("=" * len(instruction_text) + "\n")

    # Let user select ROI (Region of Interest)
    # cv2.selectROI opens a window and blocks until ENTER/SPACE or 'c' or 'q' is pressed
    window_title = "Select Logo - Press ENTER/SPACE to Confirm"
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_title, 1280, 720) # Resize window to fit screen nicely
    roi = cv2.selectROI(window_title, frame, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    x, y, w, h = roi

    if w <= 0 or h <= 0:
        print("No region selected. Exiting without processing.")
        sys.exit(0)

    # Adjust coordinates so they don't touch the exact borders (FFmpeg delogo needs adjacent pixels for interpolation)
    # delogo uses a default band of 1 pixel around the selected box.
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

    print(f"\nSelected logo boundaries: x={x}, y={y}, w={w}, h={h}")

    # Resolve FFmpeg location relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proj_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    ffmpeg_path = os.path.join(proj_root, "Libraries", "FFmpeg", "node_modules", "ffmpeg-ffprobe-static", "ffmpeg.exe")

    if not os.path.exists(ffmpeg_path):
        # Fallback to system ffmpeg if static one is missing
        ffmpeg_path = "ffmpeg"
        print("Warning: Static FFmpeg not found in Libraries. Falling back to system path 'ffmpeg'.")

    # Build the FFmpeg command
    # -vf "delogo=x=...:y=...:w=...:h=..."
    # -c:a copy copies audio without re-encoding, saving time/CPU
    delogo_filter = f"delogo=x={x}:y={y}:w={w}:h={h}"
    
    cmd = [
        ffmpeg_path,
        "-y",               # Overwrite output
        "-i", input_video,
        "-vf", delogo_filter,
        "-c:a", "copy",     # Fast audio copy
        output_video
    ]

    print(f"\nRunning FFmpeg command:\n{' '.join(cmd)}\n")
    
    try:
        # Run FFmpeg and stream output
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout:
            # Print FFmpeg progress (only the carriage return lines to keep it clean)
            if "frame=" in line or "size=" in line or "time=" in line:
                sys.stdout.write(f"\r{line.strip()}")
                sys.stdout.flush()
            else:
                if line.strip():
                    print(line.strip())
        
        process.wait()
        print("\n")
        if process.returncode == 0:
            print(f"Success! Logo removed. Output saved to: {output_video}")
        else:
            print(f"Error: FFmpeg process failed with exit code {process.returncode}")
    except Exception as e:
        print(f"Failed to execute FFmpeg: {e}")

if __name__ == "__main__":
    main()
