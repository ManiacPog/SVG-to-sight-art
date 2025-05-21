import math
from xml.dom import minidom
from svg.path import parse_path
from svg.path.path import Line, Move, CubicBezier, QuadraticBezier
import tkinter as tk
from tkinter import filedialog, messagebox
import webbrowser

DEFAULT_LINE_THICKNESS = 0.002

def extract_number(value, default=1000):
    try:
        return float(''.join(c for c in value if c.isdigit() or c == '.'))
    except ValueError:
        return default

def normalize_point(x, y, width, height, scale_factor=1.0, x_offset=0.0, y_offset=0.0):
    normalized_x = (x - width / 2) / (width / 2)
    normalized_y = (y - height / 2) / (height / 2)
    scaled_x = normalized_x * scale_factor
    scaled_y = normalized_y * scale_factor
    return scaled_x + x_offset, scaled_y + y_offset

def edge_to_quad(x1, y1, x2, y2, width_norm):
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return [(x1, y1)] * 4
    px = -(dy / length) * width_norm / 2
    py = (dx / length) * width_norm / 2
    return [
        (x1 + px, y1 + py),
        (x2 + px, y2 + py),
        (x2 - px, y2 - py),
        (x1 - px, y1 - py)
    ]

def parse_svg_filled(svg_path, scale_factor=1.0, x_offset=0.0, y_offset=0.0, thickness_multiplier=1.0):
    doc = minidom.parse(svg_path)
    svg_tag = doc.getElementsByTagName('svg')[0]
    width = extract_number(svg_tag.getAttribute('width'))
    height = extract_number(svg_tag.getAttribute('height'))

    quads = []
    actual_thickness = DEFAULT_LINE_THICKNESS * thickness_multiplier

    def add_outline_quad(x1, y1, x2, y2):
        x1n, y1n = normalize_point(x1, y1, width, height, scale_factor, x_offset, y_offset)
        x2n, y2n = normalize_point(x2, y2, width, height, scale_factor, x_offset, y_offset)
        quad_pts = edge_to_quad(x1n, y1n, x2n, y2n, width_norm=actual_thickness)
        tl, tr, br, bl = quad_pts
        quads.append(
            f"""    quad {{
        tl:p2 = {tl[0]:.6f}, {tl[1]:.6f};
        tr:p2 = {tr[0]:.6f}, {tr[1]:.6f};
        br:p2 = {br[0]:.6f}, {br[1]:.6f};
        bl:p2 = {bl[0]:.6f}, {bl[1]:.6f};
    }}"""
        )

    for tag in ['polygon', 'polyline']:
        for node in doc.getElementsByTagName(tag):
            pts = node.getAttribute('points').strip().split()
            coords = [tuple(map(float, pt.split(','))) for pt in pts]
            for i in range(len(coords) - 1):
                add_outline_quad(*coords[i], *coords[i + 1])
            if tag == 'polygon' and len(coords) > 2:
                add_outline_quad(*coords[-1], *coords[0])

    for node in doc.getElementsByTagName('path'):
        try:
            parsed = parse_path(node.getAttribute('d'))
            for segment in parsed:
                if isinstance(segment, (Line, Move)):
                    start = segment.start
                    end = segment.end
                    add_outline_quad(start.real, start.imag, end.real, end.imag)
                elif isinstance(segment, (CubicBezier, QuadraticBezier)):
                    start = segment.start
                    end = segment.end
                    add_outline_quad(start.real, start.imag, end.real, end.imag)
        except Exception as e:
            print(f"Error parsing path: {e}")
            continue

    doc.unlink()
    return quads

def convert_svg_to_wt(svg_file, output_file="output.txt", scale_factor=1.0, x_offset=0.0, y_offset=0.0, thickness_multiplier=1.0):
    quads = parse_svg_filled(svg_file, scale_factor=scale_factor, x_offset=x_offset, y_offset=y_offset, thickness_multiplier=thickness_multiplier)
    with open(output_file, "w") as f:
        f.write("drawQuads {\n")
        for quad in quads:
            f.write(quad + "\n")
        f.write("}\n")
    return output_file

# GUI
def launch_gui():
    def browse_file():
        path = filedialog.askopenfilename(filetypes=[("SVG Files", "*.svg")])
        if path:
            file_entry.delete(0, tk.END)
            file_entry.insert(0, path)

    def get_inputs():
        svg_path = file_entry.get()
        try:
            scale = float(scale_entry.get())
            x_off = float(x_offset_entry.get())
            y_off = float(y_offset_entry.get())
            thickness_mult = float(thickness_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid number you retard")
            return None
        if not svg_path:
            messagebox.showerror("Missing File", "Pick a file idiot")
            return None
        return svg_path, scale, x_off, y_off, thickness_mult

    def run_conversion_to_file():
        inputs = get_inputs()
        if not inputs:
            return
        svg_path, scale, x_off, y_off, thickness_mult = inputs

        output_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not output_path:
            status_label.config(text="⚠️ Save cancelled.", fg="orange")
            return

        try:
            convert_svg_to_wt(svg_path, output_path, scale, x_off, y_off, thickness_mult)
            status_label.config(text=f"✅ Success! Saved to: {output_path}", fg="green")
        except Exception as e:
            status_label.config(text=f"❌ Error: {str(e)}", fg="red")

    def run_conversion_to_clipboard():
        inputs = get_inputs()
        if not inputs:
            return
        svg_path, scale, x_off, y_off, thickness_mult = inputs
        try:
            quads = parse_svg_filled(svg_path, scale, x_off, y_off, thickness_mult)
            full_text = "drawQuads {\n" + "\n".join(quads) + "\n}"
            root.clipboard_clear()
            root.clipboard_append(full_text)
            status_label.config(text="📋 Copied to clipboard!", fg="green")
        except Exception as e:
            status_label.config(text=f"❌ Error: {str(e)}", fg="red")

    def open_github():
        webbrowser.open("https://github.com/ManiacPog/SVG-to-sight-art")

    root = tk.Tk()
    root.title("🦊 SVG to Sight 🦊")
    root.resizable(False, False)

    padding = {'padx': 8, 'pady': 4}

    tk.Label(root, text="SVG File:").grid(row=0, column=0, sticky="e", **padding)
    file_entry = tk.Entry(root, width=40)
    file_entry.grid(row=0, column=1, **padding)
    tk.Button(root, text="Browse", command=browse_file).grid(row=0, column=2, **padding)

    tk.Label(root, text="Scale Factor:").grid(row=1, column=0, sticky="e", **padding)
    scale_entry = tk.Entry(root)
    scale_entry.insert(0, "1.0")
    scale_entry.grid(row=1, column=1, **padding)

    tk.Label(root, text="X Offset:").grid(row=2, column=0, sticky="e", **padding)
    x_offset_entry = tk.Entry(root)
    x_offset_entry.insert(0, "0.0")
    x_offset_entry.grid(row=2, column=1, **padding)

    tk.Label(root, text="Y Offset:").grid(row=3, column=0, sticky="e", **padding)
    y_offset_entry = tk.Entry(root)
    y_offset_entry.insert(0, "0.0")
    y_offset_entry.grid(row=3, column=1, **padding)

    tk.Label(root, text="Thickness Multiplier:").grid(row=4, column=0, sticky="e", **padding)
    thickness_entry = tk.Entry(root)
    thickness_entry.insert(0, "1.0")
    thickness_entry.grid(row=4, column=1, **padding)

    # Buttons
    btn_frame = tk.Frame(root)
    btn_frame.grid(row=5, column=0, columnspan=3, pady=10)
    tk.Button(btn_frame, text="Convert & Save", command=run_conversion_to_file).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Copy to Clipboard", command=run_conversion_to_clipboard).pack(side="left", padx=5)
    tk.Button(btn_frame, text="View on GitHub", command=open_github).pack(side="left", padx=5)

    # Status
    status_label = tk.Label(root, text="", fg="green")
    status_label.grid(row=6, column=0, columnspan=3, **padding)

    root.mainloop()

if __name__ == "__main__":
    launch_gui()
