from __future__ import annotations

import logging
import queue
from tkinter import messagebox

import customtkinter as ctk
import keyboard

from src.core.logs import setup_logger
from src.core.notice import DEFAULT_NOTICE_MODE, MODE_LABELS, NoticeMode
from src.core.persistence import load_settings, save_settings, save_welcome_preference
from src.core.runner import AutomationRunner
from src.gui.model import (AppState, FormValidationError, STATE_POLICIES,
                           calculate_total, repeats_last_settings, shows_notice_mode,
                           validate_form)

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")
MODE_BY_LABEL = {label: mode for mode, label in MODE_LABELS.items()}
HELP_TEXTS = {
    NoticeMode.OLD: "Normalmente muestran el aviso de factura contabilizada.",
    NoticeMode.MODERN: "Normalmente no muestran el aviso.",
    NoticeMode.AUTO: "Comprueba cada factura y decide si debe aceptar el aviso.",
}


class QueueLogHandler(logging.Handler):
    def __init__(self, events: queue.Queue) -> None:
        super().__init__()
        self.events = events

    def emit(self, record: logging.LogRecord) -> None:
        self.events.put(("log", {"message": self.format(record), "level": record.levelno}))


class AutoFacturasApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Auto-Facturas")
        self.geometry("980x780")
        self.minsize(800, 680)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.events: queue.Queue = queue.Queue()
        self.logger, self.log_path = setup_logger()
        handler = QueueLogHandler(self.events)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"))
        self.logger.addHandler(handler)
        self.runner = AutomationRunner(self._emit, self.logger)
        self.hotkey = None
        self.resume_job = None
        self.guide_dialog = None
        saved = load_settings()
        self.guide_required = not saved or saved.get("show_welcome", True)
        self._build()
        self._register_hotkey()
        self._apply_state(AppState.READY, "Configura las facturas que quieres procesar.")
        self.after(50, self._drain_events)
        if self.guide_required:
            self.after(100, self.show_guide)

    def _build(self) -> None:
        self._build_header()
        self._build_configuration()
        self._build_controls()
        self._build_progress()
        self._build_log()

    def _build_header(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, padx=30, pady=(24, 8), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Auto-Facturas", font=ctk.CTkFont(size=30, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(frame, text="Automatización de facturas por rangos", text_color=("#555555", "#B8B8B8")).grid(row=1, column=0, sticky="w")
        self.state_badge = ctk.CTkLabel(frame, text="Preparado", corner_radius=14, width=130, height=30, text_color="white")
        self.state_badge.grid(row=0, column=1, rowspan=2, padx=(12, 14))
        self.guide_button = ctk.CTkButton(frame, text="Guía de uso", width=130, fg_color="transparent", border_width=1, command=self.show_guide)
        self.guide_button.grid(row=0, column=2, rowspan=2)

    def _build_configuration(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        for column in range(4):
            frame.grid_columnconfigure(column, weight=1, uniform="form")
        ctk.CTkLabel(frame, text="Configuración", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=4, padx=18, pady=(16, 10), sticky="w")
        for column, text in enumerate(("Caja", "Factura inicial", "Factura final", "Total")):
            ctk.CTkLabel(frame, text=text, font=ctk.CTkFont(weight="bold")).grid(row=1, column=column, padx=14, sticky="w")
        self.caja = ctk.CTkComboBox(frame, values=["Hotel", "Restaurante", "Cafetería", "Albergue"], command=self._on_caja_changed)
        self.caja.set("Hotel")
        self.initial = ctk.CTkEntry(frame, placeholder_text="Ejemplo: 260002")
        self.final = ctk.CTkEntry(frame, placeholder_text="Ejemplo: 260005")
        self.total = ctk.CTkLabel(frame, text="—", anchor="w", font=ctk.CTkFont(size=20, weight="bold"))
        for column, widget in enumerate((self.caja, self.initial, self.final, self.total)):
            widget.grid(row=2, column=column, padx=14, pady=(5, 2), sticky="ew")
        self.caja_error = self._hint(frame, 0, "Selecciona dónde se procesarán las facturas.")
        self.initial_error = self._hint(frame, 1, "Primera factura que se procesará.")
        self.final_error = self._hint(frame, 2, "Última factura que se procesará. También está incluida.")
        self.total_hint = self._hint(frame, 3, "Se cuentan la primera y la última.")
        self.notice_mode_label = ctk.CTkLabel(frame, text="Tipo de facturas", font=ctk.CTkFont(weight="bold"))
        self.notice_mode_label.grid(row=4, column=0, padx=14, pady=(12, 0), sticky="w")
        self.notice_mode = ctk.CTkComboBox(frame, values=list(MODE_BY_LABEL), command=self._on_mode_changed)
        self.notice_mode.set(MODE_LABELS[DEFAULT_NOTICE_MODE])
        self.notice_mode.grid(row=5, column=0, columnspan=2, padx=14, pady=(5, 2), sticky="ew")
        self.mode_error = ctk.CTkLabel(frame, text=HELP_TEXTS[DEFAULT_NOTICE_MODE], anchor="w", text_color=("#555555", "#B8B8B8"))
        self.mode_error.grid(row=6, column=0, columnspan=2, padx=14, pady=(0, 14), sticky="w")
        self.last_button = ctk.CTkButton(frame, text="Recuperar última configuración", command=self._load_last, fg_color="transparent", border_width=1)
        self.last_button.grid(row=5, column=2, columnspan=2, padx=14, pady=(5, 2), sticky="ew")
        ctk.CTkLabel(frame, text="Recupera los últimos valores utilizados, pero no inicia el proceso.", anchor="w", text_color=("#555555", "#B8B8B8")).grid(row=6, column=2, columnspan=2, padx=14, pady=(0, 14), sticky="w")
        self.general_error = ctk.CTkLabel(frame, text="", text_color="#B83232", anchor="w")
        self.general_error.grid(row=7, column=0, columnspan=4, padx=14, pady=(0, 12), sticky="ew")
        self.initial.bind("<KeyRelease>", self._update_total)
        self.final.bind("<KeyRelease>", self._update_total)

    @staticmethod
    def _hint(parent, column: int, text: str):
        label = ctk.CTkLabel(parent, text=text, anchor="w", text_color=("#555555", "#B8B8B8"), wraplength=210)
        label.grid(row=3, column=column, padx=14, pady=(0, 4), sticky="nw")
        return label

    def _build_controls(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, padx=30, pady=8, sticky="ew")
        for column in range(3):
            frame.grid_columnconfigure(column, weight=1)
        self.start_button = ctk.CTkButton(frame, text="Iniciar", height=42, command=self._start)
        self.pause_button = ctk.CTkButton(frame, text="Pausar", height=42, command=self._pause)
        self.stop_button = ctk.CTkButton(frame, text="Detener", height=42, command=self._stop, fg_color="#B83232", hover_color="#922626")
        for column, button in enumerate((self.start_button, self.pause_button, self.stop_button)):
            button.grid(row=0, column=column, padx=6, sticky="ew")

    def _build_progress(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=3, column=0, padx=30, pady=10, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        self.state_label = ctk.CTkLabel(frame, text="Preparado", font=ctk.CTkFont(size=19, weight="bold"))
        self.state_label.grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")
        self.detail_label = ctk.CTkLabel(frame, text="", anchor="w", wraplength=850)
        self.detail_label.grid(row=1, column=0, padx=18, sticky="ew")
        self.progress_label = ctk.CTkLabel(frame, text="Factura actual: —  ·  Secuencias completadas: 0 de 0")
        self.progress_label.grid(row=2, column=0, padx=18, pady=(9, 3), sticky="w")
        self.progress = ctk.CTkProgressBar(frame)
        self.progress.set(0)
        self.progress.grid(row=3, column=0, padx=18, pady=(3, 16), sticky="ew")

    def _build_log(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=4, column=0, padx=30, pady=(10, 24), sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Registro de la sesión", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")
        self.clear_log_button = ctk.CTkButton(frame, text="Limpiar pantalla", width=130, fg_color="transparent", border_width=1, command=self._clear_log)
        self.clear_log_button.grid(row=0, column=1, padx=14, pady=(8, 4), sticky="e")
        self.log_box = ctk.CTkTextbox(frame, state="disabled")
        self.log_box.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="nsew")
        self.log_box._textbox.tag_configure("warning", foreground="#B7791F")
        self.log_box._textbox.tag_configure("error", foreground="#B83232")

    def _emit(self, kind: str, **data) -> None:
        self.events.put((kind, data))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "log":
                    self._append_log(data["message"], data.get("level", logging.INFO))
                elif kind == "state":
                    self._apply_state(AppState(data["state"]), data["message"])
                elif kind == "countdown":
                    self._apply_state(AppState.COUNTDOWN, f"Selecciona Fortune4. El proceso comenzará en {data['remaining']} segundos.")
                elif kind == "progress":
                    self.progress_label.configure(text=f"Factura actual: {data['current']}  ·  Secuencias completadas: {data['completed']} de {data['total']}")
                    self.progress.set(data["completed"] / data["total"])
                elif kind == "hotkey":
                    state = AppState.PAUSED if data["paused"] else AppState.RUNNING
                    message = "Proceso en pausa. Pulsa Continuar cuando estés preparado." if data["paused"] else "El proceso continúa."
                    self._apply_state(state, message)
                elif kind == "finished":
                    self._apply_state(AppState(data["state"]), data["message"])
        except queue.Empty:
            pass
        self.after(50, self._drain_events)

    def _append_log(self, message: str, level: int) -> None:
        tag = "error" if level >= logging.ERROR else "warning" if level >= logging.WARNING else None
        self.log_box.configure(state="normal")
        if tag:
            self.log_box._textbox.insert("end", message + "\n", tag)
        else:
            self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.detail_label.configure(text="La pantalla del registro se ha limpiado. El archivo de log se conserva.")

    def _update_total(self, _event=None) -> None:
        total = calculate_total(self.initial.get(), self.final.get())
        self.total.configure(text=str(total) if total is not None else "—")
        self._restore_hints()

    def _restore_hints(self) -> None:
        self.initial_error.configure(text="Primera factura que se procesará.", text_color=("#555555", "#B8B8B8"))
        self.final_error.configure(text="Última factura que se procesará. También está incluida.", text_color=("#555555", "#B8B8B8"))
        self.general_error.configure(text="")

    def _start(self) -> None:
        self._restore_hints()
        try:
            start, end, mode = validate_form(self.caja.get(), self.initial.get(), self.final.get(), self.notice_mode.get(), active=self.runner.active)
        except FormValidationError as exc:
            self._show_form_error(exc)
            return
        saved = load_settings()
        if repeats_last_settings(saved, self.caja.get(), start, end, mode) and not messagebox.askyesno(
                "Posible repetición", "Este rango coincide con la última configuración y podría volver a procesar las mismas facturas. ¿Quieres continuar?", parent=self):
            return
        try:
            save_settings(self.caja.get(), start, end,
                          saved.get("show_welcome", True) if saved else True,
                          notice_mode=mode)
        except OSError:
            self.logger.exception("No se pudo guardar la configuración")
            self._apply_state(AppState.ERROR,
                              "No se pudo guardar la configuración. Comprueba que tienes espacio disponible e inténtalo de nuevo.")
            return
        if self.runner.start(self.caja.get(), start, end, mode):
            self._apply_state(AppState.COUNTDOWN, "Prepárate para seleccionar Fortune4 durante la cuenta atrás.")
            self.progress.set(0)
            self.progress_label.configure(text=f"Factura actual: —  ·  Secuencias completadas: 0 de {end - start + 1}")

    def _show_form_error(self, error: FormValidationError) -> None:
        mapping = {"caja": (self.caja_error, self.caja), "initial": (self.initial_error, self.initial), "final": (self.final_error, self.final), "mode": (self.mode_error, self.notice_mode)}
        if error.field in mapping:
            label, widget = mapping[error.field]
            label.configure(text=str(error), text_color="#B83232")
            widget.focus_set()
        else:
            self.general_error.configure(text=str(error))
        self._apply_state(AppState.ERROR, f"Revisa los datos indicados: {error}")

    def _pause(self) -> None:
        if not self.runner.active:
            return
        if not self.runner.control.pause_event.is_set():
            self.runner.toggle_pause()
        elif self.resume_job is None:
            self._resume_countdown(5)

    def _resume_countdown(self, remaining: int) -> None:
        if not self.runner.active or not self.runner.control.pause_event.is_set():
            self.resume_job = None
        elif remaining:
            self._apply_state(AppState.COUNTDOWN, f"Vuelve a Fortune4. El proceso continuará en {remaining} segundos.")
            self.resume_job = self.after(1000, self._resume_countdown, remaining - 1)
        else:
            self.resume_job = None
            self.runner.toggle_pause()

    def _stop(self) -> None:
        if self.resume_job:
            self.after_cancel(self.resume_job)
            self.resume_job = None
        self.runner.stop()
        self._apply_state(AppState.STOPPING, "Deteniendo el proceso de forma segura…")

    def _hotkey_toggle(self, _event=None) -> None:
        paused = self.runner.toggle_pause()
        if self.runner.active:
            self._emit("hotkey", paused=paused)

    def _register_hotkey(self) -> None:
        try:
            self.hotkey = keyboard.on_release_key("ñ", self._hotkey_toggle, suppress=True)
        except Exception as exc:
            self.logger.warning("No se pudo registrar el atajo Ñ: %s", exc)

    def _apply_state(self, state: AppState, message: str) -> None:
        policy = STATE_POLICIES[state]
        self.state_badge.configure(text=policy.title, fg_color=policy.color)
        self.state_label.configure(text=policy.title)
        self.detail_label.configure(text=message)
        field_state = "normal" if policy.editable else "disabled"
        for widget in (self.caja, self.initial, self.final, self.last_button):
            widget.configure(state=field_state)
        if shows_notice_mode(self.caja.get()):
            self.notice_mode.configure(state=field_state)
        self.start_button.configure(state="normal" if policy.can_start and not self.guide_required else "disabled")
        self.pause_button.configure(state="normal" if policy.can_pause else "disabled", text=policy.pause_text)
        self.stop_button.configure(state="normal" if policy.can_stop else "disabled")
        self.guide_button.configure(state="normal" if policy.editable else "disabled")

    def _load_last(self) -> None:
        saved = load_settings()
        if not saved:
            messagebox.showinfo("Última configuración", "Todavía no hay una configuración guardada.", parent=self)
            return
        self.caja.set(saved["caja"])
        self.notice_mode.set(MODE_LABELS[NoticeMode(saved.get("notice_mode", DEFAULT_NOTICE_MODE.value))])
        self._on_caja_changed(saved["caja"])
        for entry, value in ((self.initial, saved["inicial"]), (self.final, saved["final"])):
            entry.delete(0, "end")
            entry.insert(0, str(value))
        self._update_total()
        self.detail_label.configure(text="Configuración recuperada. Revísala antes de iniciar; no se ha enviado ninguna pulsación.")

    def show_guide(self) -> None:
        if self.guide_dialog and self.guide_dialog.winfo_exists():
            self.guide_dialog.focus_force()
            return
        dialog = ctk.CTkToplevel(self)
        self.guide_dialog = dialog
        dialog.title("Guía de uso")
        dialog.geometry("760x680")
        dialog.minsize(620, 520)
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_rowconfigure(1, weight=1)
        dialog.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(dialog, text="Guía de uso", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=24, pady=(22, 8), sticky="w")
        guide = ("ANTES DE COMENZAR\n• Abre Fortune4 y prepara la pantalla habitual desde la que comienza el proceso.\n• No utilices el teclado ni cambies de ventana mientras se envían las pulsaciones.\n• Auto-Facturas envía pulsaciones, pero no comprueba el resultado contable final.\n\nPASOS DE USO\n1. Selecciona la caja.\n2. Escribe la primera factura.\n3. Escribe la última factura.\n4. Revisa el total. La primera y la última también se incluyen.\n5. En Hotel o Albergue, selecciona el tipo de facturas.\n6. Pulsa Iniciar.\n7. Durante los cinco segundos de cuenta atrás, selecciona Fortune4.\n8. No toques el teclado ni cambies de ventana durante el proceso.\n9. Pulsa Ñ o el botón Pausar cuando lo necesites.\n10. Pulsa Detener para cancelar definitivamente.\n\nEJEMPLO\nCaja: Hotel\nFactura inicial: 260002\nFactura final: 260005\nTotal: 4 facturas\nSe procesarán 260002, 260003, 260004 y 260005. Ambos extremos están incluidos.\n\nÚLTIMA CONFIGURACIÓN\nRecupera la caja, el rango y las opciones utilizadas anteriormente. No inicia ni reanuda el proceso. Si utilizas el mismo rango, podrías repetir facturas.\n\nPuedes cerrar esta guía sin iniciar ninguna factura y volver a abrirla con Guía de uso.")
        box = ctk.CTkTextbox(dialog, wrap="word")
        box.insert("1.0", guide)
        box.configure(state="disabled")
        box.grid(row=1, column=0, padx=24, pady=8, sticky="nsew")
        current = load_settings()
        hide = ctk.BooleanVar(value=bool(current and not current.get("show_welcome", True)))
        ctk.CTkCheckBox(dialog, text="No mostrar automáticamente al iniciar", variable=hide).grid(row=2, column=0, padx=24, pady=8, sticky="w")
        ctk.CTkButton(dialog, text="Entendido, comenzar", command=lambda: self._close_guide(dialog, not hide.get(), True)).grid(row=3, column=0, padx=24, pady=(6, 20), sticky="e")
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._close_guide(dialog, None, False))

    def _close_guide(self, dialog, show_automatically: bool | None, save: bool) -> None:
        if save and show_automatically is not None:
            save_welcome_preference(show_automatically)
        self.guide_required = False
        dialog.grab_release()
        dialog.destroy()
        self.guide_dialog = None
        self._apply_state(AppState.READY, "Guía cerrada. Configura las facturas cuando quieras comenzar.")

    def _on_caja_changed(self, caja: str) -> None:
        if shows_notice_mode(caja):
            self.notice_mode_label.grid()
            self.notice_mode.grid()
            self.mode_error.grid()
            self._on_mode_changed(self.notice_mode.get())
        else:
            self.notice_mode_label.grid_remove()
            self.notice_mode.grid_remove()
            self.mode_error.grid_remove()

    def _on_mode_changed(self, label: str) -> None:
        mode = MODE_BY_LABEL.get(label)
        if mode:
            self.mode_error.configure(text=HELP_TEXTS[mode], text_color=("#555555", "#B8B8B8"))

    def _close(self) -> None:
        if self.runner.active and not messagebox.askyesno("Cerrar Auto-Facturas", "Hay un proceso en marcha. ¿Quieres detenerlo y cerrar la aplicación?", parent=self):
            return
        self.runner.stop()
        self.runner.join(3)
        if self.hotkey is not None:
            keyboard.unhook(self.hotkey)
        self.destroy()
