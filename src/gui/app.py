from __future__ import annotations

import logging
import queue
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import keyboard

from src.core.logs import setup_logger
from src.core.persistence import load_settings, save_settings, save_welcome_preference
from src.core.runner import AutomationRunner
from src.gui.model import (AppState, FormValidationError, STATE_POLICIES,
                           calculate_total, repeats_last_settings,
                           validate_form)

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")
CORNER_RADIUS = 8

# Shared palette for light and dark appearance, including menus and disabled controls.
TEXT = ("#352D24", "#F0E8DA")
MUTED = ("#6C6052", "#C9BFAF")
BORDER = ("#C7B9A6", "#766957")
for widget in ("CTkLabel", "CTkEntry", "CTkComboBox", "CTkTextbox", "CTkCheckBox", "DropdownMenu"):
    ctk.ThemeManager.theme[widget]["text_color"] = TEXT
for widget in ("CTk", "CTkToplevel"):
    ctk.ThemeManager.theme[widget]["fg_color"] = ("#F3EEE6", "#211E19")
ctk.ThemeManager.theme["CTkFont"].update(family="Segoe UI", size=13)
ctk.ThemeManager.theme["CTkButton"].update(
    fg_color=("#596744", "#596744"), hover_color=("#465334", "#465334"),
    text_color="#FFFFFF", text_color_disabled=("#E5DED1", "#D1C7B7"),
    border_color=BORDER, corner_radius=CORNER_RADIUS)
for widget in ("CTkEntry", "CTkComboBox"):
    ctk.ThemeManager.theme[widget].update(fg_color=("#FAF6EF", "#363027"),
        border_color=BORDER, border_width=1, corner_radius=CORNER_RADIUS)
ctk.ThemeManager.theme["CTkEntry"]["placeholder_text_color"] = MUTED
ctk.ThemeManager.theme["CTkComboBox"].update(button_color=("#DED3C2", "#766957"),
    button_hover_color=("#CCBBA3", "#8B7A63"), text_color_disabled=MUTED)
ctk.ThemeManager.theme["DropdownMenu"].update(fg_color=("#FFFCF7", "#2D2922"),
    hover_color=("#E9DFCF", "#514536"))
ctk.ThemeManager.theme["CTkProgressBar"].update(fg_color=("#E0D7C9", "#51483B"))
ctk.ThemeManager.theme["CTkCheckBox"].update(corner_radius=CORNER_RADIUS, fg_color="#596744", hover_color="#465334", border_color=BORDER)
ctk.ThemeManager.theme["CTkScrollbar"].update(button_color=BORDER, button_hover_color=("#9B886F", "#AC977A"))
SECONDARY_BUTTON = dict(fg_color=("#EDE4D7", "#43392D"),
    hover_color=("#E0D1BD", "#574937"), text_color=TEXT,
    text_color_disabled=MUTED, border_color=BORDER, border_width=1, height=38)


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
        icon_path = Path(__file__).resolve().parents[2] / "assets" / "auto-facturas.ico"
        if icon_path.is_file():
            self.iconbitmap(str(icon_path))
            self.after(250, lambda: self.iconbitmap(str(icon_path)))
        self.geometry("1040x840")
        self.minsize(900, 780)
        self.configure(fg_color=("#F3EEE6", "#211E19"))
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
        ctk.CTkLabel(frame, text="Automatización de facturas por rangos", text_color=("#6C6052", "#C9BFAF")).grid(row=1, column=0, sticky="w")
        self.state_badge = ctk.CTkLabel(frame, text="Preparado", corner_radius=CORNER_RADIUS, width=130, height=30, text_color="white")
        self.state_badge.grid(row=0, column=1, rowspan=2, padx=(12, 14))
        self.guide_button = ctk.CTkButton(frame, text="Guía de uso", width=130, **SECONDARY_BUTTON, command=self.show_guide)
        self.guide_button.grid(row=0, column=2, rowspan=2)

    def _build_configuration(self) -> None:
        frame = ctk.CTkFrame(self, corner_radius=CORNER_RADIUS, fg_color=("#FFFCF7", "#2D2922"))
        frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        for column in range(4):
            frame.grid_columnconfigure(column, weight=1, uniform="form")
        ctk.CTkLabel(frame, text="Elige las facturas", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=4, padx=18, pady=(16, 10), sticky="w")
        for column, text in enumerate(("Caja / establecimiento", "Primera factura", "Última factura", "Facturas en total")):
            ctk.CTkLabel(frame, text=text, font=ctk.CTkFont(weight="bold")).grid(row=1, column=column, padx=14, sticky="w")
        self.caja = ctk.CTkComboBox(frame, height=40, state="readonly", values=["Hotel", "Restaurante", "Cafetería", "Albergue"])
        self.caja.set("Hotel")
        self.initial = ctk.CTkEntry(frame, height=40, placeholder_text="Ejemplo: 260002")
        self.final = ctk.CTkEntry(frame, height=40, placeholder_text="Ejemplo: 260005")
        self.total = ctk.CTkLabel(frame, text="—", anchor="w", font=ctk.CTkFont(size=26, weight="bold"), text_color=("#795438", "#DCBB94"))
        for column, widget in enumerate((self.caja, self.initial, self.final, self.total)):
            widget.grid(row=2, column=column, padx=14, pady=(5, 2), sticky="ew")
        self.caja_error = self._hint(frame, 0, "Selecciona dónde se procesarán las facturas.")
        self.initial_error = self._hint(frame, 1, "Primera factura que se procesará.")
        self.final_error = self._hint(frame, 2, "Última factura que se procesará. También está incluida.")
        self.total_hint = self._hint(frame, 3, "Se cuentan la primera y la última.")
        self.last_button = ctk.CTkButton(frame, text="Recuperar última configuración", command=self._load_last, **SECONDARY_BUTTON)
        self.last_button.grid(row=4, column=2, columnspan=2, padx=14, pady=(5, 2), sticky="ew")
        ctk.CTkLabel(frame, text="Rellena los datos anteriores. Revisa el rango antes de iniciar.", anchor="w", justify="left", wraplength=380, text_color=("#6C6052", "#C9BFAF")).grid(row=5, column=2, columnspan=2, padx=14, pady=(0, 14), sticky="w")
        self.general_error = ctk.CTkLabel(frame, text="", height=0, text_color="#A44636", anchor="w", justify="left", wraplength=800)
        self.general_error.grid(row=6, column=0, columnspan=4, padx=14, pady=(0, 6), sticky="ew")
        self.initial.bind("<KeyRelease>", self._update_total)
        self.final.bind("<KeyRelease>", self._update_total)

    @staticmethod
    def _hint(parent, column: int, text: str):
        label = ctk.CTkLabel(parent, text=text, anchor="w", text_color=MUTED, justify="left", wraplength=180)
        label.grid(row=3, column=column, padx=14, pady=(0, 4), sticky="nw")
        return label

    def _build_controls(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, padx=30, pady=8, sticky="ew")
        for column in range(3):
            frame.grid_columnconfigure(column, weight=1)
        self.start_button = ctk.CTkButton(frame, text="Iniciar proceso", height=46, font=ctk.CTkFont(size=15, weight="bold"), command=self._start, fg_color="#596744", hover_color="#465334")
        self.pause_button = ctk.CTkButton(frame, text="Pausar", height=46, fg_color="#80684F", hover_color="#69533E", command=self._pause)
        self.stop_button = ctk.CTkButton(frame, text="Detener", height=46, command=self._stop, fg_color="#A44636", hover_color="#853529")
        for column, button in enumerate((self.start_button, self.pause_button, self.stop_button)):
            button.grid(row=0, column=column, padx=6, sticky="ew")
        ctk.CTkLabel(frame, text="Al iniciar tienes 5 segundos para volver a Fortune4. Durante el proceso, no escribas ni cambies de ventana.",
                     anchor="w", justify="left", wraplength=850, text_color=("#6C6052", "#C9BFAF")).grid(row=1, column=0, columnspan=3, padx=6, pady=(8, 0), sticky="ew")

    def _build_progress(self) -> None:
        frame = ctk.CTkFrame(self, corner_radius=CORNER_RADIUS, fg_color=("#FFFCF7", "#2D2922"))
        frame.grid(row=3, column=0, padx=30, pady=10, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        self.state_label = ctk.CTkLabel(frame, text="Preparado", font=ctk.CTkFont(size=19, weight="bold"))
        self.state_label.grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")
        self.detail_label = ctk.CTkLabel(frame, text="", anchor="w", justify="left", wraplength=850)
        self.detail_label.grid(row=1, column=0, padx=18, sticky="ew")
        self.progress_label = ctk.CTkLabel(frame, text="Factura actual: —  ·  Facturas procesadas: 0 de 0")
        self.progress_label.grid(row=2, column=0, padx=18, pady=(9, 3), sticky="w")
        self.progress = ctk.CTkProgressBar(frame, corner_radius=CORNER_RADIUS, height=12, progress_color="#596744")
        self.progress.set(0)
        self.progress.grid(row=3, column=0, padx=18, pady=(3, 16), sticky="ew")

    def _build_log(self) -> None:
        frame = ctk.CTkFrame(self, corner_radius=CORNER_RADIUS, fg_color=("#FFFCF7", "#2D2922"))
        frame.grid(row=4, column=0, padx=30, pady=(10, 24), sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Registro de la sesión", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")
        self.clear_log_button = ctk.CTkButton(frame, text="Limpiar pantalla", width=130, **SECONDARY_BUTTON, command=self._clear_log)
        self.clear_log_button.grid(row=0, column=1, padx=14, pady=(8, 4), sticky="e")
        self.log_box = ctk.CTkTextbox(frame, state="disabled", font=ctk.CTkFont(family="Consolas", size=12), fg_color=("#F6F1E9", "#25221D"), corner_radius=CORNER_RADIUS)
        self.log_box.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="nsew")
        self.log_box._textbox.tag_configure("warning", foreground="#94631F")
        self.log_box._textbox.tag_configure("error", foreground="#A44636")

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
                    self.progress_label.configure(text=f"Factura actual: {data['current']}  ·  Facturas procesadas: {data['completed']} de {data['total']}")
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
        self.initial_error.configure(text="Primera factura que se procesará.", text_color=("#6C6052", "#C9BFAF"))
        self.final_error.configure(text="Última factura que se procesará. También está incluida.", text_color=("#6C6052", "#C9BFAF"))
        self.general_error.configure(text="")

    def _start(self) -> None:
        self._restore_hints()
        try:
            start, end = validate_form(self.caja.get(), self.initial.get(), self.final.get(), active=self.runner.active)
        except FormValidationError as exc:
            self._show_form_error(exc)
            return
        saved = load_settings()
        if repeats_last_settings(saved, self.caja.get(), start, end) and not messagebox.askyesno(
                "Posible repetición", "Este rango coincide con la última configuración y podría volver a procesar las mismas facturas. ¿Quieres continuar?", parent=self):
            return
        try:
            save_settings(self.caja.get(), start, end,
                          saved.get("show_welcome", True) if saved else True)
        except OSError:
            self.logger.exception("No se pudo guardar la configuración")
            self._apply_state(AppState.ERROR,
                              "No se pudo guardar la configuración. Comprueba que tienes espacio disponible e inténtalo de nuevo.")
            return
        if self.runner.start(self.caja.get(), start, end):
            self._apply_state(AppState.COUNTDOWN, "Prepárate para seleccionar Fortune4 durante la cuenta atrás.")
            self.progress.set(0)
            self.progress_label.configure(text=f"Factura actual: —  ·  Facturas procesadas: 0 de {end - start + 1}")

    def _show_form_error(self, error: FormValidationError) -> None:
        mapping = {"caja": (self.caja_error, self.caja), "initial": (self.initial_error, self.initial), "final": (self.final_error, self.final)}
        if error.field in mapping:
            label, widget = mapping[error.field]
            label.configure(text=str(error), text_color="#A44636")
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
            widget.configure(state=("readonly" if policy.editable else "disabled") if widget is self.caja else field_state)
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
        sections = (
            ("Antes de empezar", "Auto-Facturas escribe y pulsa teclas en la ventana que tengas seleccionada. Abre Fortune4, elige la caja correcta y deja preparada la pantalla desde la que sueles comenzar a introducir la factura. Si no sabes cuál es, consulta a quien realiza este trabajo habitualmente antes de iniciar."),
            ("1 - Elige la caja y el rango", "En la ventana principal, selecciona Hotel, Restaurante, Cafetería o Albergue. Escribe el número de la primera y de la última factura: se procesarán todos los números consecutivos, incluidos los dos extremos. Para una sola factura, escribe el mismo número en ambos campos."),
            ("Ejemplo - Cuatro facturas", "Primera factura: 260002    Última factura: 260005    Total: 4\nSe procesarán 260002, 260003, 260004 y 260005. Comprueba que el total coincide con lo que quieres hacer."),
            ("2 - Inicia y vuelve a Fortune4", "Pulsa Iniciar proceso. Tendrás 5 segundos para hacer clic en Fortune4 y dejar activa la pantalla preparada. Las teclas se enviarán a esa ventana. Durante el proceso no escribas, no hagas clic en otros programas ni cambies de ventana."),
            ("Pausar y continuar", "Pulsa Ñ para pausar desde Fortune4, o usa el botón Pausar. La pausa conserva el punto del proceso. Para seguir, pulsa Continuar y vuelve a Fortune4 durante los 5 segundos de cuenta atrás. Ñ también reanuda, pero lo hace inmediatamente: úsala solo cuando Fortune4 ya está activo."),
            ("Detener o resolver un problema", "Detener cancela el proceso; las pulsaciones ya enviadas no se deshacen. Como parada de emergencia, mueve el ratón a la esquina superior izquierda de la pantalla. Si algo no coincide en Fortune4, pausa o detén y revisa la última factura antes de volver a iniciar. No repitas todo el rango sin comprobar lo que ya se hizo."),
            ("3 - Revisa el resultado", "El contador indica las secuencias de teclas terminadas. Al finalizar, comprueba en Fortune4 que las facturas y referencias son correctas: Auto-Facturas no verifica el resultado contable. El detalle del proceso te ayuda a consultar por qué factura iba."),
            ("Recuperar los datos de la última vez", "Recuperar Última configuración rellena los campos, pero no inicia el proceso. Revisa la caja y el rango. Si coinciden con la última ejecución, aparecerá un aviso para evitar una repetición accidental."),
        )
        content = ctk.CTkScrollableFrame(dialog, fg_color=("#F3EEE6", "#211E19"), corner_radius=CORNER_RADIUS)
        content.grid(row=1, column=0, padx=24, pady=8, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        guide_labels = []
        for row, (title, body) in enumerate(sections):
            card = ctk.CTkFrame(content, corner_radius=CORNER_RADIUS, fg_color=("#FFFCF7", "#2D2922"))
            card.grid(row=row, column=0, pady=(0, 10), sticky="ew")
            card.grid_columnconfigure(0, weight=1)
            heading = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=16, weight="bold"), anchor="w", justify="left")
            heading.grid(row=0, column=0, padx=18, pady=(14, 4), sticky="ew")
            label = ctk.CTkLabel(card, text=body, anchor="w", justify="left", wraplength=630, font=ctk.CTkFont(size=14))
            label.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="ew")
            guide_labels.extend((heading, label))
        last_guide_width = None

        def resize_guide(event):
            nonlocal last_guide_width
            # Height changes also fire Configure; only reflow when width changes.
            if event.width == last_guide_width:
                return
            last_guide_width = event.width
            for label in guide_labels:
                label.configure(wraplength=max(280, event.width - 60))

        # Keep CTkScrollableFrame's own handler, which updates the scroll region.
        content.bind("<Configure>", resize_guide, add="+")
        current = load_settings()
        hide = ctk.BooleanVar(value=bool(current and not current.get("show_welcome", True)))
        ctk.CTkCheckBox(dialog, text="No mostrar automáticamente al iniciar", variable=hide).grid(row=2, column=0, padx=24, pady=8, sticky="w")
        ctk.CTkButton(dialog, text="Entendido - Volver a configurar", command=lambda: self._close_guide(dialog, not hide.get(), True)).grid(row=3, column=0, padx=24, pady=(6, 20), sticky="e")
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._close_guide(dialog, None, False))

    def _close_guide(self, dialog, show_automatically: bool | None, save: bool) -> None:
        if save and show_automatically is not None:
            save_welcome_preference(show_automatically)
        self.guide_required = False
        dialog.grab_release()
        dialog.destroy()
        self.guide_dialog = None
        self._apply_state(AppState.READY, "Guía cerrada. Configura las facturas cuando quieras comenzar.")

    def _close(self) -> None:
        if self.runner.active and not messagebox.askyesno("Cerrar Auto-Facturas", "Hay un proceso en marcha. ¿Quieres detenerlo y cerrar la aplicación?", parent=self):
            return
        self.runner.stop()
        self.runner.join(3)
        if self.hotkey is not None:
            keyboard.unhook(self.hotkey)
        self.destroy()
