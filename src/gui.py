"""
gui.py — Asistente de configuración gráfico (tkinter).
Funciona en cualquier plataforma con Python (tkinter viene incluido).
"""

import os
import sys
import webbrowser
from pathlib import Path

from .config import FIELDS, get_creds, save_creds, validate_creds, has_minimum


def run_gui_setup():
    """Lanza ventana de configuración gráfica con tkinter."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("tkinter no está disponible en este sistema.", file=sys.stderr)
        return False

    root = tk.Tk()
    root.title("YouTube Summarizer — Configuración")
    root.geometry("520x480")
    root.resizable(False, False)

    if os.name != "nt":
        try:
            root.iconify()
        except Exception:
            pass

    frame = ttk.Frame(root, padding="20")
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="YouTube Summarizer — Configuración",
              font=("", 14, "bold")).pack(anchor="w", pady=(0, 5))
    ttk.Label(frame, text="Completa las credenciales necesarias para el bot.",
              font=("", 9)).pack(anchor="w", pady=(0, 15))

    creds = get_creds()
    entries = {}
    show_var = tk.BooleanVar(value=False)
    status_labels = {}

    canvas = tk.Canvas(frame, highlightthickness=0)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=480)
    canvas.configure(yscrollcommand=scrollbar.set)

    for key in FIELDS:
        info = FIELDS[key]
        row = ttk.Frame(scroll_frame)
        row.pack(fill="x", pady=4)

        label_frame = ttk.Frame(row)
        label_frame.pack(fill="x")

        ttk.Label(label_frame, text=f"{info['label']}", font=("", 9, "bold")).pack(side="left")
        req_text = " *" if info["required"] else " (opcional)"
        ttk.Label(label_frame, text=req_text,
                  foreground="red" if info["required"] else "gray").pack(side="left")

        help_btn = ttk.Label(label_frame, text=" [?]", foreground="blue", cursor="hand2")
        help_btn.pack(side="right")
        url = info["help"]
        if url.startswith("http"):
            help_btn.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

        entry_frame = ttk.Frame(row)
        entry_frame.pack(fill="x", pady=(2, 0))

        entry = ttk.Entry(entry_frame, show="*" if info["secret"] else "")
        entry.pack(side="left", fill="x", expand=True, ipady=2)
        if key in creds:
            entry.insert(0, creds[key])

        status_lbl = ttk.Label(entry_frame, text="", width=4)
        status_lbl.pack(side="right", padx=(4, 0))

        entries[key] = entry
        status_labels[key] = status_lbl

    def toggle_show():
        show = show_var.get()
        for key in FIELDS:
            if FIELDS[key]["secret"]:
                entries[key].configure(show="" if show else "*")

    ttk.Checkbutton(frame, text="Mostrar contraseñas", variable=show_var,
                    command=toggle_show).pack(anchor="w", pady=(5, 0))

    def validate():
        creds = {}
        for key in FIELDS:
            val = entries[key].get().strip()
            if val:
                creds[key] = val
        results = validate_creds(creds)
        for key, ok in results.items():
            if ok is True:
                status_labels[key].configure(text="✓", foreground="green")
            elif ok is False:
                status_labels[key].configure(text="✗", foreground="red")
            else:
                status_labels[key].configure(text="–", foreground="gray")

    def save():
        creds = {}
        for key in FIELDS:
            val = entries[key].get().strip()
            if val:
                creds[key] = val
        results = validate_creds(creds)
        missing = [k for k, v in results.items() if v is False]
        if missing:
            msg = "Faltan campos obligatorios:\n" + "\n".join(f"  • {FIELDS[k]['label']}" for k in missing)
            messagebox.showerror("Error", msg)
            return
        save_creds(creds)
        messagebox.showinfo("Guardado", "Configuración guardada correctamente.")
        root.destroy()

    def cancel():
        root.destroy()

    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill="x", pady=(10, 0))
    ttk.Button(btn_frame, text="Validar", command=validate).pack(side="left", padx=(0, 5))
    ttk.Button(btn_frame, text="Guardar y salir", command=save).pack(side="right", padx=(5, 0))
    ttk.Button(btn_frame, text="Cancelar", command=cancel).pack(side="right")

    canvas.pack(side="left", fill="both", expand=True, pady=(0, 5))
    scrollbar.pack(side="right", fill="y", pady=(0, 5))

    validate()
    root.mainloop()
    return True
