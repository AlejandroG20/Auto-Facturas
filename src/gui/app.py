from __future__ import annotations

import logging
import queue
from tkinter import messagebox

import customtkinter as ctk
import keyboard

from src.core.logs import setup_logger
from src.core.persistence import load_settings, save_settings, save_welcome_preference, validate_range
from src.core.runner import AutomationRunner

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class QueueLogHandler(logging.Handler):
    def __init__(self, events: queue.Queue) -> None:
        super().__init__(); self.events = events
    def emit(self, record: logging.LogRecord) -> None:
        self.events.put(("log", {"message": self.format(record)}))


class AutoFacturasApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Auto-Facturas"); self.geometry("940x720"); self.minsize(760, 620)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.events: queue.Queue = queue.Queue()
        self.logger, self.log_path = setup_logger()
        handler = QueueLogHandler(self.events)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"))
        self.logger.addHandler(handler)
        self.runner = AutomationRunner(self._emit, self.logger)
        self.hotkey = None; self.resume_job = None
        self._build(); self._register_hotkey(); self.after(50, self._drain_events)
        saved = load_settings()
        if not saved or saved.get("show_welcome", True): self.after(100, self.show_guide)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(4, weight=1)
        top = ctk.CTkFrame(self, fg_color="transparent"); top.grid(row=0, column=0, padx=28, pady=(24, 10), sticky="ew"); top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text="Auto-Facturas", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(top, text="Ayuda → Guía de uso", width=170, fg_color="transparent", border_width=1, command=self.show_guide).grid(row=0, column=1)
        form = ctk.CTkFrame(self); form.grid(row=1, column=0, padx=28, pady=10, sticky="ew")
        for column in range(4): form.grid_columnconfigure(column, weight=1)
        for column, title in enumerate(("Caja", "Factura inicial", "Factura final", "Total")): ctk.CTkLabel(form, text=title).grid(row=0, column=column, padx=14, pady=(14, 4), sticky="w")
        self.caja = ctk.CTkComboBox(form, values=["Hotel", "Restaurante", "Cafetería", "Albergue"]); self.caja.set("Hotel")
        self.initial = ctk.CTkEntry(form, placeholder_text="260002"); self.final = ctk.CTkEntry(form, placeholder_text="260005")
        self.total = ctk.CTkLabel(form, text="—", font=ctk.CTkFont(size=18, weight="bold"))
        for column, widget in enumerate((self.caja, self.initial, self.final, self.total)): widget.grid(row=1, column=column, padx=14, pady=(0, 16), sticky="ew")
        self.initial.bind("<KeyRelease>", self._update_total); self.final.bind("<KeyRelease>", self._update_total)
        buttons = ctk.CTkFrame(self, fg_color="transparent"); buttons.grid(row=2, column=0, padx=28, pady=8, sticky="ew")
        for column in range(4): buttons.grid_columnconfigure(column, weight=1)
        self.last_button = ctk.CTkButton(buttons, text="Última configuración", command=self._load_last)
        self.start_button = ctk.CTkButton(buttons, text="Iniciar", command=self._start)
        self.pause_button = ctk.CTkButton(buttons, text="Pausar", command=self._pause, state="disabled")
        self.stop_button = ctk.CTkButton(buttons, text="Detener", command=self._stop, state="disabled", fg_color="#B83232")
        for index, button in enumerate((self.last_button, self.start_button, self.pause_button, self.stop_button)): button.grid(row=0, column=index, padx=6, sticky="ew")
        status = ctk.CTkFrame(self); status.grid(row=3, column=0, padx=28, pady=10, sticky="ew"); status.grid_columnconfigure(0, weight=1)
        self.state_label = ctk.CTkLabel(status, text="PREPARADO", font=ctk.CTkFont(size=20, weight="bold")); self.state_label.grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")
        self.detail_label = ctk.CTkLabel(status, text="Configura un rango para comenzar"); self.detail_label.grid(row=1, column=0, padx=18, sticky="w")
        self.progress_label = ctk.CTkLabel(status, text="Factura actual: —  ·  Procesadas: 0 de 0"); self.progress_label.grid(row=2, column=0, padx=18, pady=(8, 3), sticky="w")
        self.progress = ctk.CTkProgressBar(status); self.progress.set(0); self.progress.grid(row=3, column=0, padx=18, pady=(3, 16), sticky="ew")
        frame = ctk.CTkFrame(self); frame.grid(row=4, column=0, padx=28, pady=(10, 24), sticky="nsew"); frame.grid_rowconfigure(1, weight=1); frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Registro", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")
        self.log_box = ctk.CTkTextbox(frame, state="disabled"); self.log_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

    def _emit(self, kind: str, **data) -> None: self.events.put((kind, data))
    def _drain_events(self) -> None:
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "log":
                    self.log_box.configure(state="normal"); self.log_box.insert("end", data["message"] + "\n"); self.log_box.see("end"); self.log_box.configure(state="disabled")
                elif kind == "state": self._set_state(data["state"], data["message"])
                elif kind == "countdown": self.detail_label.configure(text=f"Cambia de ventana · Inicio en {data['remaining']} s")
                elif kind == "progress":
                    self.progress_label.configure(text=f"Factura actual: {data['current']}  ·  Procesadas: {data['completed']} de {data['total']}"); self.progress.set(data["completed"] / data["total"])
                elif kind == "hotkey": self.pause_button.configure(text="Continuar" if data["paused"] else "Pausar")
                elif kind == "finished": self._set_state(data["state"], data["message"]); self._set_running(False)
        except queue.Empty: pass
        self.after(50, self._drain_events)

    def _update_total(self, _event=None) -> None:
        try:
            start, end = validate_range(self.initial.get(), self.final.get()); self.total.configure(text=str(end - start + 1))
        except ValueError: self.total.configure(text="—")

    def _start(self) -> None:
        try:
            start, end = validate_range(self.initial.get(), self.final.get()); saved = load_settings()
            save_settings(self.caja.get(), start, end, saved.get("show_welcome", True) if saved else True)
        except ValueError as exc: messagebox.showerror("Rango no válido", str(exc), parent=self); return
        if self.runner.start(self.caja.get(), start, end):
            self._set_running(True); self.progress.set(0); self.progress_label.configure(text=f"Factura actual: —  ·  Procesadas: 0 de {end-start+1}")

    def _pause(self) -> None:
        if not self.runner.active: return
        if not self.runner.control.pause_event.is_set(): self.runner.toggle_pause(); self.pause_button.configure(text="Continuar")
        elif self.resume_job is None: self._resume_countdown(5)

    def _resume_countdown(self, remaining: int) -> None:
        if not self.runner.active or not self.runner.control.pause_event.is_set(): self.resume_job = None; return
        if remaining:
            self._set_state("cuenta atrás", f"Vuelve al programa · Continuación en {remaining} s"); self.resume_job = self.after(1000, self._resume_countdown, remaining - 1)
        else: self.resume_job = None; self.runner.toggle_pause(); self.pause_button.configure(text="Pausar")

    def _stop(self) -> None:
        if self.resume_job: self.after_cancel(self.resume_job); self.resume_job = None
        self.runner.stop(); self.detail_label.configure(text="Deteniendo de forma ordenada…")

    def _hotkey_toggle(self, _event=None) -> None:
        paused = self.runner.toggle_pause(); self._emit("hotkey", paused=paused)
    def _register_hotkey(self) -> None:
        try: self.hotkey = keyboard.on_release_key("ñ", self._hotkey_toggle, suppress=True)
        except Exception as exc: self.logger.warning("No se pudo registrar el atajo Ñ: %s", exc)
    def _set_state(self, state: str, message: str) -> None: self.state_label.configure(text=state.upper()); self.detail_label.configure(text=message)
    def _set_running(self, active: bool) -> None:
        state = "disabled" if active else "normal"
        for widget in (self.caja, self.initial, self.final, self.last_button, self.start_button): widget.configure(state=state)
        self.pause_button.configure(state="normal" if active else "disabled", text="Pausar"); self.stop_button.configure(state="normal" if active else "disabled")

    def _load_last(self) -> None:
        saved = load_settings()
        if not saved: messagebox.showinfo("Última configuración", "No hay una configuración válida guardada.", parent=self); return
        self.caja.set(saved["caja"])
        for entry, value in ((self.initial, saved["inicial"]), (self.final, saved["final"])): entry.delete(0, "end"); entry.insert(0, str(value))
        self._update_total(); messagebox.showinfo("Última configuración", "Valores recuperados. Revísalos antes de iniciar; esto no reanuda una ejecución interrumpida.", parent=self)

    def show_guide(self) -> None:
        dialog = ctk.CTkToplevel(self); dialog.title("Guía de uso"); dialog.geometry("700x610"); dialog.minsize(600, 500); dialog.transient(self); dialog.grab_set(); dialog.grid_rowconfigure(0, weight=1); dialog.grid_columnconfigure(0, weight=1)
        text = ("Antes de comenzar, abre el programa de facturación y déjalo correctamente preparado en su pantalla inicial habitual.\n\n1. Selecciona la caja.\n2. Introduce la factura inicial y final.\n3. Revisa el total.\n4. Pulsa «Iniciar».\n5. Usa los 5 segundos para seleccionar la ventana del programa de facturación.\n6. No escribas ni cambies de ventana durante la ejecución.\n7. Pulsa Ñ para pausar o continuar sin cambiar el foco.\n8. Usa «Detener» para cancelar definitivamente.\n9. «Última configuración» recupera los valores para revisarlos; no reanuda una ejecución y puede repetir facturas ya procesadas.\n\nEjemplo\nCaja: Hotel · Factura inicial: 260002 · Factura final: 260005.\nSe procesarán cuatro facturas: 260002, 260003, 260004 y 260005.\n\nEl progreso indica secuencias de teclado completadas, no facturas verificadas en el programa externo. Al pausar se conserva el paso y la espera pendientes, pero una tecla ya enviada no puede deshacerse.")
        box = ctk.CTkTextbox(dialog, wrap="word"); box.insert("1.0", text); box.configure(state="disabled"); box.grid(row=0, column=0, padx=22, pady=(22, 10), sticky="nsew")
        hide = ctk.BooleanVar(value=False); ctk.CTkCheckBox(dialog, text="No mostrar al iniciar", variable=hide).grid(row=1, column=0, padx=22, pady=8, sticky="w")
        ctk.CTkButton(dialog, text="Entendido, comenzar", command=lambda: (save_welcome_preference(not hide.get()), dialog.destroy())).grid(row=2, column=0, padx=22, pady=(6, 20), sticky="e")

    def _close(self) -> None:
        if self.runner.active and not messagebox.askyesno("Cerrar Auto-Facturas", "Hay una ejecución activa. ¿Quieres detenerla y cerrar?", parent=self): return
        self.runner.stop(); self.runner.join(3)
        if self.hotkey is not None: keyboard.unhook(self.hotkey)
        self.destroy()
