import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import calendar
import queue
from datetime import datetime
from oslo.db import init_db
from oslo import inventario, compras, ventas, finanzas, agenda
from local_service import ScanService

# Sistemas de Temas (Oscuro Corporativo & Claro Ejecutivo)
THEMES = {
    "dark": {
        "name": "dark",
        "bg_main": "#0F172A",       # Slate 900
        "bg_sidebar": "#1E293B",    # Slate 800
        "bg_card": "#1E293B",       # Slate 800
        "bg_input": "#334155",      # Slate 700
        "table_head": "#0F172A",
        "accent": "#38BDF8",        # Sky 400
        "accent_fg": "#0F172A",
        "success": "#10B981",       # Emerald 500
        "danger": "#EF4444",        # Red 500
        "warning": "#F59E0B",       # Amber 500
        "text_primary": "#F8FAFC",  # Slate 50
        "text_muted": "#94A3B8",    # Slate 400
        "border": "#334155"
    },
    "light": {
        "name": "light",
        "bg_main": "#F1F5F9",       # Slate 100
        "bg_sidebar": "#FFFFFF",    # Pure White
        "bg_card": "#FFFFFF",       # Pure White
        "bg_input": "#E2E8F0",      # Slate 200
        "table_head": "#E2E8F0",
        "accent": "#0284C7",        # Sky 600
        "accent_fg": "#FFFFFF",
        "success": "#059669",       # Emerald 600
        "danger": "#DC2626",        # Red 600
        "warning": "#D97706",       # Amber 600
        "text_primary": "#0F172A",  # Slate 900
        "text_muted": "#475569",    # Slate 600
        "border": "#CBD5E1"
    }
}

class OsloERP:
    def __init__(self, root):
        self.root = root
        self.root.title("Oslo — Sistema de ventas")
        self.root.geometry("1220x750")
        self.root.minsize(1060, 660)

        self.theme_mode = "dark"
        self.colors = THEMES[self.theme_mode]
        self.vista_actual = "dashboard"
        self.scan_queue = queue.Queue()
        self.scan_service = None
        self._buscar_codigo_venta = None

        # Estado de calendario interactivo
        hoy = datetime.now()
        self.cal_year = hoy.year
        self.cal_month = hoy.month
        self.selected_date = hoy.strftime("%Y-%m-%d")

        init_db()
        try:
            self.scan_service = ScanService(self.scan_queue, inventario.buscar_por_codigo_barras)
            self.scan_service.start()
        except OSError as exc:
            self.scan_service = None
            messagebox.showwarning(
                "Lector móvil no disponible",
                f"No se pudo iniciar el servicio local del lector. La caja seguirá funcionando.\n\n{exc}",
                parent=self.root
            )
        self.root.after(200, self._procesar_lecturas_movil)
        self._aplicar_tema_global()

    def _procesar_lecturas_movil(self):
        if not self.root.winfo_exists():
            return
        try:
            while True:
                lectura = self.scan_queue.get_nowait()
                self._resolver_codigo_escaneado(lectura["barcode"])
        except queue.Empty:
            pass
        self.root.after(200, self._procesar_lecturas_movil)

    def _resolver_codigo_escaneado(self, codigo):
        self.mostrar_vista("ventas")
        if self._buscar_codigo_venta:
            self._buscar_codigo_venta(codigo)

    def _mostrar_vinculacion_lector(self):
        c = self.colors
        if not self.scan_service:
            messagebox.showerror("Lector no disponible", "Reinicia la aplicación para intentar iniciar el servicio local.", parent=self.root)
            return

        modal = tk.Toplevel(self.root)
        modal.title("Conectar lector móvil")
        modal.geometry("460x590")
        modal.resizable(False, False)
        modal.configure(bg=c["bg_card"])
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text="Conecta tu teléfono", bg=c["bg_card"], fg=c["text_primary"], font=("Segoe UI", 18, "bold")).pack(pady=(22, 6))
        tk.Label(modal, text="Conecta ambos dispositivos a la misma red Wi-Fi y escanea este QR desde Oslo Móvil.", wraplength=390, justify="center", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 10)).pack(padx=24, pady=(0, 12))

        address = self.scan_service.addresses[0]
        payload = self.scan_service.pairing_payload(address)
        try:
            import qrcode
            from PIL import ImageTk
            image = qrcode.make(payload).resize((260, 260))
            modal.qr_image = ImageTk.PhotoImage(image)
            tk.Label(modal, image=modal.qr_image, bg="#FFFFFF", padx=8, pady=8).pack(pady=8)
        except ImportError:
            tk.Label(modal, text="Para mostrar el QR, instala las dependencias del lector.\nPuedes ingresar estos datos manualmente:", justify="center", bg=c["bg_card"], fg=c["warning"], font=("Segoe UI", 9)).pack(pady=12)

        tk.Label(modal, text=f"Dirección: http://{address}:{self.scan_service.port}", bg=c["bg_card"], fg=c["text_primary"], font=("Consolas", 10, "bold")).pack(pady=(10, 4))
        if len(self.scan_service.addresses) > 1:
            alternatives = "Direcciones alternativas: " + ", ".join(f"http://{item}:{self.scan_service.port}" for item in self.scan_service.addresses[1:])
            tk.Label(modal, text=alternatives, bg=c["bg_card"], fg=c["text_muted"], font=("Consolas", 8), wraplength=420).pack(padx=20, pady=3)
        tk.Label(modal, text=f"Clave temporal: {self.scan_service.token}", bg=c["bg_card"], fg=c["text_muted"], font=("Consolas", 8), wraplength=420).pack(padx=20)
        tk.Label(modal, text="La clave cambia al reiniciar la caja. Cierra esta ventana para terminar el emparejamiento.", wraplength=390, justify="center", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9)).pack(padx=20, pady=18)
        tk.Button(modal, text="Listo", command=modal.destroy, bg=c["accent"], fg=c["accent_fg"], relief="flat", padx=24, pady=8, font=("Segoe UI", 10, "bold")).pack(pady=(0, 18))

    def _abrir_alta_producto_codigo(self, codigo_barras):
        c = self.colors
        modal = tk.Toplevel(self.root)
        modal.title("Producto nuevo")
        modal.geometry("500x520")
        modal.resizable(False, False)
        modal.configure(bg=c["bg_card"])
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text="Código sin registrar", bg=c["bg_card"], fg=c["warning"], font=("Segoe UI", 17, "bold")).pack(pady=(18, 4))
        tk.Label(modal, text="Completa los datos del inventario para guardar el producto y continuar con la venta.", wraplength=430, justify="center", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9)).pack(padx=20, pady=(0, 12))

        form = tk.Frame(modal, bg=c["bg_card"], padx=24)
        form.pack(fill="both", expand=True)
        fields = [
            ("Código de barras", codigo_barras),
            ("SKU", codigo_barras),
            ("Nombre del producto", ""),
            ("Categoría", "General"),
            ("Costo", "0"),
            ("Precio de venta", "0"),
            ("Stock inicial", "0"),
            ("Stock mínimo", "5"),
        ]
        entries = {}
        for index, (label, initial) in enumerate(fields):
            column = index % 2
            row = index // 2
            tk.Label(form, text=label, bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=row * 2, column=column, sticky="w", padx=7, pady=(4, 2))
            entry = tk.Entry(form, width=27, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
            entry.insert(0, initial)
            entry.grid(row=row * 2 + 1, column=column, sticky="ew", padx=7, pady=(0, 8), ipady=5)
            entries[label] = entry
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        def guardar():
            try:
                ok, msg = inventario.agregar_producto(
                    entries["SKU"].get(), entries["Nombre del producto"].get(), entries["Categoría"].get(),
                    float(entries["Costo"].get().replace(",", ".")),
                    float(entries["Precio de venta"].get().replace(",", ".")),
                    int(entries["Stock inicial"].get()), int(entries["Stock mínimo"].get()),
                    codigo_barras=entries["Código de barras"].get()
                )
                if not ok:
                    messagebox.showwarning("No se pudo guardar", msg, parent=modal)
                    return
                modal.destroy()
                self.notificar(msg, "success")
                self.mostrar_vista("ventas")
                if self._buscar_codigo_venta:
                    self.root.after(100, lambda: self._buscar_codigo_venta(codigo_barras))
            except ValueError:
                messagebox.showerror("Datos inválidos", "Revisa costo, precio, stock y stock mínimo.", parent=modal)

        buttons = tk.Frame(modal, bg=c["bg_card"])
        buttons.pack(fill="x", padx=24, pady=(0, 18))
        tk.Button(buttons, text="Cancelar", command=modal.destroy, bg=c["bg_input"], fg=c["text_primary"], relief="flat", padx=16, pady=7).pack(side="left")
        tk.Button(buttons, text="Guardar producto", command=guardar, bg=c["success"], fg="#FFFFFF", relief="flat", padx=16, pady=7, font=("Segoe UI", 9, "bold")).pack(side="right")
        entries["Nombre del producto"].focus_set()

    def cerrar(self):
        if self.scan_service:
            self.scan_service.close()
        self.root.destroy()

    def alternar_tema(self):
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"
        self.colors = THEMES[self.theme_mode]
        self._aplicar_tema_global()
        self.notificar(f"Tema cambiado a modo {'Claro' if self.theme_mode == 'light' else 'Oscuro'}.", "info")

    def _aplicar_tema_global(self):
        self.root.configure(bg=self.colors["bg_main"])
        self._configurar_estilos()
        for w in self.root.winfo_children():
            w.destroy()
        self._construir_layout()
        self.mostrar_vista(self.vista_actual)

    def _configurar_estilos(self):
        c = self.colors
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Custom.Treeview",
            background=c["bg_card"],
            foreground=c["text_primary"],
            fieldbackground=c["bg_card"],
            borderwidth=0,
            rowheight=32,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=c["table_head"],
            foreground=c["accent"],
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            padding=(8, 8)
        )
        style.map("Custom.Treeview", background=[("selected", c["accent"])], foreground=[("selected", c["accent_fg"])])

        style.configure(
            "TCombobox",
            fieldbackground=c["bg_input"],
            background=c["bg_input"],
            foreground=c["text_primary"],
            arrowcolor=c["accent"],
            borderwidth=0
        )

    def _construir_layout(self):
        c = self.colors
        self.sidebar = tk.Frame(self.root, bg=c["bg_sidebar"], width=235)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand_frame = tk.Frame(self.sidebar, bg=c["bg_sidebar"], pady=24)
        brand_frame.pack(fill="x")
        tk.Label(
            brand_frame, text="OSLO", bg=c["bg_sidebar"],
            fg=c["accent"], font=("Segoe UI", 18, "bold")
        ).pack()
        tk.Label(
            brand_frame, text="ADMINISTRACIÓN & ERP", bg=c["bg_sidebar"],
            fg=c["text_muted"], font=("Segoe UI", 8, "bold")
        ).pack(pady=(2, 0))

        tk.Frame(self.sidebar, bg=c["border"], height=1).pack(fill="x", padx=16, pady=(0, 16))

        self.nav_buttons = {}
        menu_items = [
            ("dashboard", "  Panel Principal"),
            ("inventario", "  Inventario y Catálogo"),
            ("ventas", "  Punto de Venta"),
            ("compras", "  Compras a Proveedores"),
            ("calendario", "  Calendario y Notas"),
            ("finanzas", "  Libro Diario y Finanzas"),
        ]

        for key, label in menu_items:
            btn = tk.Button(
                self.sidebar, text=label, anchor="w", padx=20, pady=12,
                bg=c["bg_sidebar"], fg=c["text_primary"],
                activebackground=c["bg_input"], activeforeground=c["accent"],
                bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2",
                command=lambda k=key: self.mostrar_vista(k)
            )
            btn.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[key] = btn

        tk.Label(
            self.sidebar, text="Caja local • SQLite",
            bg=c["bg_sidebar"], fg=c["text_muted"], font=("Segoe UI", 8)
        ).pack(side="bottom", pady=16)

        self.main_area = tk.Frame(self.root, bg=c["bg_main"])
        self.main_area.pack(side="right", fill="both", expand=True, padx=24, pady=20)

        self.status_var = tk.StringVar(value="Sistema listo. Base de datos sincronizada.")
        self.status_bar = tk.Label(
            self.main_area, textvariable=self.status_var, anchor="w",
            bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9),
            padx=12, pady=6
        )
        self.status_bar.pack(side="bottom", fill="x", pady=(12, 0))

        self.content_frame = tk.Frame(self.main_area, bg=c["bg_main"])
        self.content_frame.pack(fill="both", expand=True)

    def notificar(self, mensaje, tipo="info"):
        c = self.colors
        colores = {
            "info": c["text_muted"],
            "success": c["success"],
            "error": c["danger"]
        }
        self.status_var.set(f"●  {mensaje}")
        self.status_bar.config(fg=colores.get(tipo, c["text_muted"]))

    def mostrar_vista(self, nombre_vista):
        self.vista_actual = nombre_vista
        c = self.colors
        for k, btn in self.nav_buttons.items():
            if k == nombre_vista:
                btn.config(bg=c["bg_input"], fg=c["accent"])
            else:
                btn.config(bg=c["bg_sidebar"], fg=c["text_primary"])

        for widget in self.content_frame.winfo_children():
            widget.destroy()

        vistas = {
            "dashboard": self._vista_dashboard,
            "inventario": self._vista_inventario,
            "ventas": self._vista_ventas,
            "compras": self._vista_compras,
            "calendario": self._vista_calendario,
            "finanzas": self._vista_finanzas,
        }
        vistas[nombre_vista]()

    # ==================== HELPERS UI ====================
    def _header(self, titulo, subtitulo, right_widget_fn=None):
        c = self.colors
        hdr = tk.Frame(self.content_frame, bg=c["bg_main"])
        hdr.pack(fill="x", pady=(0, 18))

        left = tk.Frame(hdr, bg=c["bg_main"])
        left.pack(side="left")
        tk.Label(left, text=titulo, bg=c["bg_main"], fg=c["text_primary"], font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(left, text=subtitulo, bg=c["bg_main"], fg=c["text_muted"], font=("Segoe UI", 10)).pack(anchor="w")

        if right_widget_fn:
            right = tk.Frame(hdr, bg=c["bg_main"])
            right.pack(side="right", anchor="center")
            right_widget_fn(right)

    def _crear_tabla(self, parent, columnas, anchos):
        c = self.colors
        container = tk.Frame(parent, bg=c["bg_card"])
        container.pack(fill="both", expand=True)

        scroll = ttk.Scrollbar(container, orient="vertical")
        tree = ttk.Treeview(container, columns=columnas, show="headings", style="Custom.Treeview", yscrollcommand=scroll.set)
        scroll.config(command=tree.yview)

        for col, ancho in zip(columnas, anchos):
            tree.heading(col, text=col)
            tree.column(col, width=ancho, anchor="center" if ancho < 120 else "w")

        scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        return tree

    def _crear_input(self, parent, label_text, row, col, width=22):
        c = self.colors
        tk.Label(parent, text=label_text, bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(
            row=row, column=col, sticky="w", padx=8, pady=(6, 2)
        )
        entry = tk.Entry(
            parent, width=width, bg=c["bg_input"], fg=c["text_primary"],
            insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10)
        )
        entry.grid(row=row + 1, column=col, sticky="ew", padx=8, pady=(0, 10), ipady=5)
        return entry

    # ==================== VISTA 1: DASHBOARD ====================
    def _vista_dashboard(self):
        c = self.colors

        def btn_tema(parent):
            texto = "☀️ Cambiar a Tema Claro" if self.theme_mode == "dark" else "🌙 Cambiar a Tema Oscuro"
            tk.Button(
                parent, text=texto, bg=c["bg_card"], fg=c["accent"],
                activebackground=c["bg_input"], activeforeground=c["accent"],
                font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=8, cursor="hand2",
                command=self.alternar_tema
            ).pack()

        self._header("Panel Principal", "Resumen ejecutivo en tiempo real de Oslo", right_widget_fn=btn_tema)

        ingresos, egresos, balance, valor_inv = finanzas.obtener_balance()
        alertas = inventario.verificar_stock_bajo()
        eventos_pend = [e for e in agenda.listar_eventos() if e["completado"] == 0]

        kpi_row = tk.Frame(self.content_frame, bg=c["bg_main"])
        kpi_row.pack(fill="x", pady=(0, 20))

        kpis = [
            ("BALANCE NETO", f"${balance:,.2f}", c["accent"]),
            ("INGRESOS TOTALES", f"${ingresos:,.2f}", c["success"]),
            ("EGRESOS TOTALES", f"${egresos:,.2f}", c["danger"]),
            ("CAPITAL EN INVENTARIO", f"${valor_inv:,.2f}", c["warning"]),
        ]

        for idx, (titulo, valor, color) in enumerate(kpis):
            card = tk.Frame(kpi_row, bg=c["bg_card"], padx=18, pady=16)
            card.pack(side="left", fill="both", expand=True, padx=(0 if idx == 0 else 10, 0))
            tk.Label(card, text=titulo, bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(card, text=valor, bg=c["bg_card"], fg=color, font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(6, 0))

        split = tk.Frame(self.content_frame, bg=c["bg_main"])
        split.pack(fill="both", expand=True)

        # Columna Izquierda: Alertas de Stock + Próximos Eventos
        left_col = tk.Frame(split, bg=c["bg_main"])
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        left_box = tk.Frame(left_col, bg=c["bg_card"], padx=16, pady=12)
        left_box.pack(fill="both", expand=True, pady=(0, 10))
        tk.Label(
            left_box, text=f"Alertas de Reposición ({len(alertas)})",
            bg=c["bg_card"], fg=c["warning"], font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 8))

        tree_alertas = self._crear_tabla(left_box, ("SKU", "Producto", "Stock", "Mínimo"), (80, 180, 65, 65))
        for a in alertas:
            tree_alertas.insert("", "end", values=(a["sku"], a["nombre"], a["stock"], a["stock_minimo"]))

        events_box = tk.Frame(left_col, bg=c["bg_card"], padx=16, pady=12)
        events_box.pack(fill="both", expand=True)
        tk.Label(
            events_box, text=f"Próximos Eventos Agendados ({len(eventos_pend)})",
            bg=c["bg_card"], fg=c["accent"], font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 8))

        tree_ev = self._crear_tabla(events_box, ("Fecha", "Hora", "Tipo", "Evento"), (95, 65, 100, 160))
        for ev in eventos_pend[:8]:
            tree_ev.insert("", "end", values=(ev["fecha"], ev["hora"], ev["tipo"], ev["titulo"]))

        # Columna Derecha: Últimos Movimientos Financieros
        right_box = tk.Frame(split, bg=c["bg_card"], padx=16, pady=14)
        right_box.pack(side="right", fill="both", expand=True)
        tk.Label(
            right_box, text="Últimos Movimientos Financieros",
            bg=c["bg_card"], fg=c["text_primary"], font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 10))

        tree_tx = self._crear_tabla(right_box, ("Tipo", "Monto", "Descripción"), (85, 100, 220))
        for tx in finanzas.listar_transacciones(18):
            tree_tx.insert("", "end", values=(tx["tipo"], f"${tx['monto']:,.2f}", tx["descripcion"]))

    # ==================== VISTA 2: INVENTARIO ====================
    def _vista_inventario(self):
        c = self.colors
        self._header("Inventario y Catálogo", "Gestión de productos tecnológicos, precios y niveles de stock")

        form_card = tk.Frame(self.content_frame, bg=c["bg_card"], padx=14, pady=10)
        form_card.pack(fill="x", pady=(0, 14))

        e_sku = self._crear_input(form_card, "SKU *", 0, 0, 14)
        e_nom = self._crear_input(form_card, "Nombre del Producto *", 0, 1, 26)
        e_cat = self._crear_input(form_card, "Categoría *", 0, 2, 18)
        e_cos = self._crear_input(form_card, "Costo ($) *", 0, 3, 12)
        e_ven = self._crear_input(form_card, "Precio Venta ($) *", 0, 4, 12)
        e_stk = self._crear_input(form_card, "Stock Inicial *", 0, 5, 10)
        e_min = self._crear_input(form_card, "Mínimo Alerta", 0, 6, 10)
        e_min.insert(0, "5")
        e_barcode = self._crear_input(form_card, "Código de barras", 2, 0, 22)

        def guardar():
            try:
                ok, msg = inventario.agregar_producto(
                    e_sku.get(), e_nom.get(), e_cat.get(),
                    float(e_cos.get()), float(e_ven.get()),
                    int(e_stk.get()), int(e_min.get() or 5),
                    codigo_barras=e_barcode.get()
                )
                if ok:
                    self.notificar(msg, "success")
                    for w in (e_sku, e_nom, e_cat, e_cos, e_ven, e_stk, e_barcode):
                        w.delete(0, tk.END)
                    cargar_tabla()
                else:
                    messagebox.showwarning("Validación", msg)
            except ValueError:
                messagebox.showerror("Error de formato", "Verifica que Costo, Venta y Stock sean números válidos.")

        tk.Button(
            form_card, text="+ Agregar Producto", bg=c["accent"], fg=c["accent_fg"],
            font=("Segoe UI", 10, "bold"), relief="flat", padx=14, pady=6, cursor="hand2",
            command=guardar
        ).grid(row=1, column=7, padx=8, pady=(0, 10))

        bar = tk.Frame(self.content_frame, bg=c["bg_main"])
        bar.pack(fill="x", pady=(0, 8))

        tk.Label(bar, text="Buscar:", bg=c["bg_main"], fg=c["text_muted"], font=("Segoe UI", 10)).pack(side="left")
        search_var = tk.StringVar()
        tk.Entry(
            bar, textvariable=search_var, width=32, bg=c["bg_input"],
            fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10)
        ).pack(side="left", padx=8, ipady=4)

        def eliminar_sel():
            sel = tree.selection()
            if not sel:
                return
            item = tree.item(sel[0])["values"]
            if messagebox.askyesno("Confirmar", f"¿Eliminar '{item[2]}' del catálogo?"):
                ok, msg = inventario.eliminar_producto(item[0])
                self.notificar(msg, "success" if ok else "error")
                cargar_tabla()

        tk.Button(
            bar, text="Eliminar Seleccionado", bg=c["danger"], fg="white",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2",
            command=eliminar_sel
        ).pack(side="right")

        tree = self._crear_tabla(
            self.content_frame,
            ("ID", "SKU", "Código de barras", "Producto", "Categoría", "Costo", "Precio Venta", "Stock", "Mínimo"),
            (45, 90, 140, 210, 115, 85, 100, 60, 65)
        )

        def cargar_tabla(*args):
            for r in tree.get_children():
                tree.delete(r)
            for p in inventario.listar_productos(search_var.get()):
                tree.insert("", "end", values=(
                    p["id"], p["sku"], p.get("codigo_barras") or "—", p["nombre"], p["categoria"],
                    f"${p['precio_costo']:,.2f}", f"${p['precio_venta']:,.2f}",
                    p["stock"], p["stock_minimo"]
                ))

        search_var.trace_add("write", cargar_tabla)
        cargar_tabla()

    # ==================== VISTA 3: VENTAS ====================
    def _vista_ventas(self):
        c = self.colors
        self._header("Punto de Venta", "Escanea o selecciona un producto, verifica la cantidad y confirma la cobranza")

        top = tk.Frame(self.content_frame, bg=c["bg_card"], padx=16, pady=14)
        top.pack(fill="x", pady=(0, 16))

        prods = inventario.listar_productos()
        clientes = ventas.listar_clientes()

        prod_map = {f"{p['id']} - {p['nombre']} (${p['precio_venta']:,.2f} | Stock: {p['stock']})": p["id"] for p in prods}
        cli_map = {f"{cl['id']} - {cl['nombre']}": cl["id"] for cl in clientes}

        tk.Label(top, text="Escanear código de barras", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=6)
        scan_entry = tk.Entry(top, width=28, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
        scan_entry.grid(row=1, column=0, padx=6, pady=6, ipady=5, sticky="w")

        tk.Label(top, text="Cliente:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", padx=6)
        cb_cli = ttk.Combobox(top, values=list(cli_map.keys()), width=28, state="readonly")
        if cli_map:
            cb_cli.current(0)
        cb_cli.grid(row=4, column=0, padx=6, pady=6, ipady=4)

        def nuevo_cliente():
            nom = simpledialog.askstring("Nuevo Cliente", "Nombre completo o empresa del cliente:")
            if nom:
                ok, msg = ventas.agregar_cliente(nom)
                if ok:
                    self.notificar(msg, "success")
                    self.mostrar_vista("ventas")

        tk.Button(
            top, text="+ Cliente", bg=c["bg_input"], fg=c["accent"],
            font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=5, cursor="hand2", command=nuevo_cliente
        ).grid(row=4, column=1, padx=(0, 14))

        tk.Label(top, text="Producto:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=3, column=2, sticky="w", padx=6)
        cb_prod = ttk.Combobox(top, values=list(prod_map.keys()), width=42, state="readonly")
        if prod_map:
            cb_prod.current(0)
        cb_prod.grid(row=4, column=2, padx=6, pady=6, ipady=4)

        tk.Label(top, text="Cantidad:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=3, column=3, sticky="w", padx=6)
        ent_cant = tk.Entry(top, width=10, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
        ent_cant.insert(0, "1")
        ent_cant.grid(row=4, column=3, padx=6, pady=6, ipady=5)

        def buscar_codigo(codigo=None):
            codigo = str(codigo if codigo is not None else scan_entry.get()).strip()
            if not codigo:
                self.notificar("Ingresa o escanea un código de barras.", "info")
                return
            producto = inventario.buscar_por_codigo_barras(codigo)
            if producto:
                etiqueta = next((label for label, product_id in prod_map.items() if product_id == producto["id"]), None)
                if etiqueta:
                    cb_prod.set(etiqueta)
                scan_entry.delete(0, tk.END)
                self.notificar(f"{producto['nombre']} seleccionado · ${producto['precio_venta']:,.2f} · Stock {producto['stock']}.", "success")
                return
            scan_entry.delete(0, tk.END)
            if messagebox.askyesno("Producto no encontrado", f"El código {codigo} no existe en el catálogo. ¿Quieres cargar el producto ahora?", parent=self.root):
                self._abrir_alta_producto_codigo(codigo)
            else:
                self.notificar(f"Código {codigo} no registrado.", "info")

        self._buscar_codigo_venta = buscar_codigo
        scan_entry.bind("<Return>", lambda event: buscar_codigo())
        tk.Button(top, text="Buscar código", bg=c["accent"], fg=c["accent_fg"], font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2", command=buscar_codigo).grid(row=1, column=1, padx=4)
        tk.Button(top, text="Conectar móvil", bg=c["bg_input"], fg=c["accent"], font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2", command=self._mostrar_vinculacion_lector).grid(row=1, column=2, padx=4, sticky="w")

        def procesar():
            if not prod_map or not cli_map:
                messagebox.showwarning("Faltan datos", "Asegúrate de tener al menos un producto y un cliente.")
                return
            try:
                c_id = cli_map[cb_cli.get()]
                p_id = prod_map[cb_prod.get()]
                cant = int(ent_cant.get())
                ok, msg = ventas.registrar_venta(c_id, p_id, cant)
                if ok:
                    self.notificar(msg, "success")
                    self.mostrar_vista("ventas")
                else:
                    messagebox.showerror("No se pudo vender", msg)
            except ValueError:
                messagebox.showerror("Error", "La cantidad debe ser un número entero.")

        tk.Button(
            top, text="Confirmar Venta", bg=c["success"], fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=16, pady=6, cursor="hand2", command=procesar
        ).grid(row=4, column=4, padx=12)

        # Barra de acciones sobre historial de ventas
        hist_bar = tk.Frame(self.content_frame, bg=c["bg_main"])
        hist_bar.pack(fill="x", pady=(0, 8))
        tk.Label(hist_bar, text="Historial Reciente de Ventas", bg=c["bg_main"], fg=c["text_primary"], font=("Segoe UI", 11, "bold")).pack(side="left")

        ventas_data = ventas.listar_ventas()
        ventas_by_id = {v["id"]: v for v in ventas_data}

        def eliminar_venta_sel():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Selección requerida", "Selecciona una venta de la tabla para eliminar.")
                return
            v_id = int(tree.item(sel[0])["values"][0])
            v_info = ventas_by_id.get(v_id)
            if messagebox.askyesno("Confirmar Eliminación", f"¿Eliminar la Venta #{v_id} ({v_info['producto']})?\n\nSe devolverán +{v_info['cantidad']} unidades al stock y se descontará el ingreso de caja."):
                ok, msg = ventas.eliminar_venta(v_id)
                if ok:
                    self.notificar(msg, "success")
                    self.mostrar_vista("ventas")
                else:
                    messagebox.showerror("Error", msg)

        def abrir_modal_editar_venta(event=None):
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Selección requerida", "Selecciona una venta de la tabla para editar.")
                return
            v_id = int(tree.item(sel[0])["values"][0])
            v_info = ventas_by_id.get(v_id)
            if not v_info:
                return

            modal = tk.Toplevel(self.root)
            modal.title(f"Editar Venta #{v_id}")
            modal.geometry("400x260")
            modal.configure(bg=c["bg_card"])
            modal.transient(self.root)
            modal.grab_set()

            tk.Label(modal, text=f"Producto: {v_info['producto']}", bg=c["bg_card"], fg=c["accent"], font=("Segoe UI", 11, "bold")).pack(pady=(16, 10))

            tk.Label(modal, text="Cliente:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=30)
            cb_edit_cli = ttk.Combobox(modal, values=list(cli_map.keys()), width=38, state="readonly")
            for idx, (label_c, cid) in enumerate(cli_map.items()):
                if cid == v_info["cliente_id"]:
                    cb_edit_cli.current(idx)
                    break
            cb_edit_cli.pack(pady=(2, 12), ipady=3)

            tk.Label(modal, text="Nueva Cantidad:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=30)
            ent_edit_cant = tk.Entry(modal, width=41, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
            ent_edit_cant.insert(0, str(v_info["cantidad"]))
            ent_edit_cant.pack(pady=(2, 16), ipady=5)

            def guardar_edicion():
                try:
                    nuevo_cli_id = cli_map[cb_edit_cli.get()]
                    nueva_cant = int(ent_edit_cant.get())
                    ok, msg = ventas.editar_venta(v_id, nuevo_cli_id, nueva_cant)
                    if ok:
                        self.notificar(msg, "success")
                        modal.destroy()
                        self.mostrar_vista("ventas")
                    else:
                        messagebox.showerror("Error al actualizar", msg, parent=modal)
                except ValueError:
                    messagebox.showerror("Error", "La cantidad debe ser un número entero válido.", parent=modal)

            tk.Button(
                modal, text="Guardar Cambios", bg=c["accent"], fg=c["accent_fg"],
                font=("Segoe UI", 10, "bold"), relief="flat", padx=18, pady=6, cursor="hand2", command=guardar_edicion
            ).pack()

        tk.Button(
            hist_bar, text="Eliminar Venta", bg=c["danger"], fg="white",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=eliminar_venta_sel
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            hist_bar, text="Editar Venta", bg=c["bg_input"], fg=c["accent"],
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=abrir_modal_editar_venta
        ).pack(side="right")

        tree = self._crear_tabla(self.content_frame, ("ID", "Fecha", "Cliente", "Producto", "Cant.", "Total Cobrado"), (60, 150, 200, 260, 80, 130))
        tree.bind("<Double-1>", abrir_modal_editar_venta)
        for v in ventas_data:
            tree.insert("", "end", values=(v["id"], v["fecha"], v["cliente"], v["producto"], v["cantidad"], f"${v['total']:,.2f}"))

    # ==================== VISTA 4: COMPRAS ====================
    def _vista_compras(self):
        c = self.colors
        self._header("Compras a Proveedores", "Abastecimiento de inventario, edición y anulación de órdenes de compra")

        top = tk.Frame(self.content_frame, bg=c["bg_card"], padx=16, pady=14)
        top.pack(fill="x", pady=(0, 16))

        prods = inventario.listar_productos()
        provs = compras.listar_proveedores()

        prod_map = {f"{p['id']} - {p['nombre']} (Stock actual: {p['stock']})": p["id"] for p in prods}
        prov_map = {f"{pr['id']} - {pr['nombre']}": pr["id"] for pr in provs}

        tk.Label(top, text="Proveedor:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=6)
        cb_prov = ttk.Combobox(top, values=list(prov_map.keys()), width=26, state="readonly")
        if prov_map:
            cb_prov.current(0)
        cb_prov.grid(row=1, column=0, padx=6, pady=6, ipady=4)

        def nuevo_prov():
            nom = simpledialog.askstring("Nuevo Proveedor", "Nombre del proveedor:")
            if nom:
                ok, msg = compras.agregar_proveedor(nom)
                if ok:
                    self.notificar(msg, "success")
                    self.mostrar_vista("compras")

        tk.Button(
            top, text="+ Proveedor", bg=c["bg_input"], fg=c["accent"],
            font=("Segoe UI", 9, "bold"), relief="flat", padx=8, pady=5, cursor="hand2", command=nuevo_prov
        ).grid(row=1, column=1, padx=(0, 12))

        tk.Label(top, text="Producto:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=6)
        cb_prod = ttk.Combobox(top, values=list(prod_map.keys()), width=34, state="readonly")
        if prod_map:
            cb_prod.current(0)
        cb_prod.grid(row=1, column=2, padx=6, pady=6, ipady=4)

        tk.Label(top, text="Cant.:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky="w", padx=6)
        ent_cant = tk.Entry(top, width=8, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
        ent_cant.insert(0, "10")
        ent_cant.grid(row=1, column=3, padx=6, pady=6, ipady=5)

        tk.Label(top, text="Costo Unit. ($):", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w", padx=6)
        ent_costo = tk.Entry(top, width=11, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
        ent_costo.grid(row=1, column=4, padx=6, pady=6, ipady=5)

        def procesar():
            if not prod_map or not prov_map:
                messagebox.showwarning("Faltan datos", "Registra primero al menos un producto en Inventario.")
                return
            try:
                pr_id = prov_map[cb_prov.get()]
                p_id = prod_map[cb_prod.get()]
                cant = int(ent_cant.get())
                costo = float(ent_costo.get())
                ok, msg = compras.registrar_compra(pr_id, p_id, cant, costo)
                if ok:
                    self.notificar(msg, "success")
                    self.mostrar_vista("compras")
                else:
                    messagebox.showerror("Error", msg)
            except ValueError:
                messagebox.showerror("Error", "Verifica que cantidad y costo sean números válidos.")

        tk.Button(
            top, text="Registrar Compra", bg=c["accent"], fg=c["accent_fg"],
            font=("Segoe UI", 10, "bold"), relief="flat", padx=14, pady=6, cursor="hand2", command=procesar
        ).grid(row=1, column=5, padx=10)

        hist_bar = tk.Frame(self.content_frame, bg=c["bg_main"])
        hist_bar.pack(fill="x", pady=(0, 8))
        tk.Label(hist_bar, text="Historial de Órdenes de Compra", bg=c["bg_main"], fg=c["text_primary"], font=("Segoe UI", 11, "bold")).pack(side="left")

        compras_data = compras.listar_compras()
        compras_by_id = {cm["id"]: cm for cm in compras_data}

        def eliminar_compra_sel():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Selección requerida", "Selecciona una compra de la tabla para eliminar.")
                return
            c_id = int(tree.item(sel[0])["values"][0])
            c_info = compras_by_id.get(c_id)
            if messagebox.askyesno("Confirmar Eliminación", f"¿Eliminar la Compra #{c_id} ({c_info['producto']})?\n\nSe descontarán -{c_info['cantidad']} unidades del stock y se reembolsará el egreso en caja."):
                ok, msg = compras.eliminar_compra(c_id)
                if ok:
                    self.notificar(msg, "success")
                    self.mostrar_vista("compras")
                else:
                    messagebox.showerror("No se puede eliminar", msg)

        def abrir_modal_editar_compra(event=None):
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Selección requerida", "Selecciona una compra de la tabla para editar.")
                return
            c_id = int(tree.item(sel[0])["values"][0])
            c_info = compras_by_id.get(c_id)
            if not c_info:
                return

            modal = tk.Toplevel(self.root)
            modal.title(f"Editar Compra #{c_id}")
            modal.geometry("400x310")
            modal.configure(bg=c["bg_card"])
            modal.transient(self.root)
            modal.grab_set()

            tk.Label(modal, text=f"Producto: {c_info['producto']}", bg=c["bg_card"], fg=c["accent"], font=("Segoe UI", 11, "bold")).pack(pady=(16, 10))

            tk.Label(modal, text="Proveedor:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=30)
            cb_edit_prov = ttk.Combobox(modal, values=list(prov_map.keys()), width=38, state="readonly")
            for idx, (label_p, pid) in enumerate(prov_map.items()):
                if pid == c_info["proveedor_id"]:
                    cb_edit_prov.current(idx)
                    break
            cb_edit_prov.pack(pady=(2, 10), ipady=3)

            tk.Label(modal, text="Nueva Cantidad:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=30)
            ent_edit_cant = tk.Entry(modal, width=41, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
            ent_edit_cant.insert(0, str(c_info["cantidad"]))
            ent_edit_cant.pack(pady=(2, 10), ipady=5)

            costo_unit_actual = round(c_info["total"] / c_info["cantidad"], 2) if c_info["cantidad"] else 0.0
            tk.Label(modal, text="Nuevo Costo Unitario ($):", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=30)
            ent_edit_costo = tk.Entry(modal, width=41, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
            ent_edit_costo.insert(0, str(costo_unit_actual))
            ent_edit_costo.pack(pady=(2, 16), ipady=5)

            def guardar_edicion():
                try:
                    nuevo_prov_id = prov_map[cb_edit_prov.get()]
                    nueva_cant = int(ent_edit_cant.get())
                    nuevo_costo = float(ent_edit_costo.get())
                    ok, msg = compras.editar_compra(c_id, nuevo_prov_id, nueva_cant, nuevo_costo)
                    if ok:
                        self.notificar(msg, "success")
                        modal.destroy()
                        self.mostrar_vista("compras")
                    else:
                        messagebox.showerror("Error al actualizar", msg, parent=modal)
                except ValueError:
                    messagebox.showerror("Error", "Verifica que cantidad y costo sean números válidos.", parent=modal)

            tk.Button(
                modal, text="Guardar Cambios", bg=c["accent"], fg=c["accent_fg"],
                font=("Segoe UI", 10, "bold"), relief="flat", padx=18, pady=6, cursor="hand2", command=guardar_edicion
            ).pack()

        tk.Button(
            hist_bar, text="Eliminar Compra", bg=c["danger"], fg="white",
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=eliminar_compra_sel
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            hist_bar, text="Editar Compra", bg=c["bg_input"], fg=c["accent"],
            font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=abrir_modal_editar_compra
        ).pack(side="right")

        tree = self._crear_tabla(self.content_frame, ("ID", "Fecha", "Proveedor", "Producto", "Cant.", "Total Pagado"), (60, 150, 200, 260, 80, 130))
        tree.bind("<Double-1>", abrir_modal_editar_compra)
        for cm in compras_data:
            tree.insert("", "end", values=(cm["id"], cm["fecha"], cm["proveedor"], cm["producto"], cm["cantidad"], f"${cm['total']:,.2f}"))

    # ==================== VISTA 5: CALENDARIO Y BLOC DE NOTAS ====================
    def _vista_calendario(self):
        c = self.colors
        self._header("Calendario y Bloc de Notas", "Planificación de entregas, recepción de pedidos y apuntes operativos")

        main_split = tk.Frame(self.content_frame, bg=c["bg_main"])
        main_split.pack(fill="both", expand=True)

        # ----- PANEL IZQUIERDO: CALENDARIO VISUAL + AGENDA DE EVENTOS -----
        left_panel = tk.Frame(main_split, bg=c["bg_card"], padx=16, pady=14)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # Cabecera del mes y navegación
        nav_cal = tk.Frame(left_panel, bg=c["bg_card"])
        nav_cal.pack(fill="x", pady=(0, 10))

        meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        def cambiar_mes(delta):
            self.cal_month += delta
            if self.cal_month > 12:
                self.cal_month = 1
                self.cal_year += 1
            elif self.cal_month < 1:
                self.cal_month = 12
                self.cal_year -= 1
            self.mostrar_vista("calendario")

        tk.Button(nav_cal, text="◀", bg=c["bg_input"], fg=c["text_primary"], bd=0, padx=10, pady=3, cursor="hand2",
                  command=lambda: cambiar_mes(-1)).pack(side="left")
        tk.Label(nav_cal, text=f"{meses_es[self.cal_month]} {self.cal_year}", bg=c["bg_card"],
                 fg=c["accent"], font=("Segoe UI", 12, "bold")).pack(side="left", expand=True)
        tk.Button(nav_cal, text="▶", bg=c["bg_input"], fg=c["text_primary"], bd=0, padx=10, pady=3, cursor="hand2",
                  command=lambda: cambiar_mes(1)).pack(side="right")

        # Cuadrícula de días del mes
        grid_cal = tk.Frame(left_panel, bg=c["bg_card"])
        grid_cal.pack(fill="x", pady=(0, 12))

        dias_sem = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for col_idx, d_name in enumerate(dias_sem):
            tk.Label(grid_cal, text=d_name, bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 8, "bold")).grid(row=0, column=col_idx, pady=2)
            grid_cal.columnconfigure(col_idx, weight=1)

        todos_eventos = agenda.listar_eventos()
        fechas_con_evento = {ev["fecha"] for ev in todos_eventos if ev["completado"] == 0}

        cal_matrix = calendar.monthcalendar(self.cal_year, self.cal_month)
        for r_idx, week in enumerate(cal_matrix, start=1):
            for c_idx, day in enumerate(week):
                if day == 0:
                    tk.Label(grid_cal, text="", bg=c["bg_card"]).grid(row=r_idx, column=c_idx, padx=2, pady=2)
                else:
                    fecha_str = f"{self.cal_year:04d}-{self.cal_month:02d}-{day:02d}"
                    es_sel = (fecha_str == self.selected_date)
                    tiene_ev = (fecha_str in fechas_con_evento)

                    bg_btn = c["accent"] if es_sel else (c["bg_input"] if tiene_ev else c["bg_main"])
                    fg_btn = c["accent_fg"] if es_sel else (c["warning"] if tiene_ev else c["text_primary"])
                    lbl_txt = f"{day}•" if tiene_ev and not es_sel else str(day)

                    def sel_dia(f=fecha_str):
                        self.selected_date = f
                        self.mostrar_vista("calendario")

                    tk.Button(
                        grid_cal, text=lbl_txt, bg=bg_btn, fg=fg_btn, bd=0,
                        font=("Segoe UI", 9, "bold" if (es_sel or tiene_ev) else "normal"),
                        cursor="hand2", pady=4, command=sel_dia
                    ).grid(row=r_idx, column=c_idx, sticky="ew", padx=2, pady=2)

        # Formulario rápido de nuevo evento para la fecha seleccionada
        form_ev = tk.Frame(left_panel, bg=c["bg_main"], padx=10, pady=10)
        form_ev.pack(fill="x", pady=(0, 10))

        tk.Label(form_ev, text=f"Nuevo Evento ({self.selected_date})", bg=c["bg_main"], fg=c["text_primary"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        cb_tipo_ev = ttk.Combobox(form_ev, values=["Recepción Pedido", "Entrega Cliente", "Pago Proveedor", "Reunión / Otro"], width=16, state="readonly")
        cb_tipo_ev.current(0)
        cb_tipo_ev.grid(row=1, column=0, padx=(0, 6), ipady=3)

        ent_hora = tk.Entry(form_ev, width=7, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 9))
        ent_hora.insert(0, "10:00")
        ent_hora.grid(row=1, column=1, padx=(0, 6), ipady=4)

        ent_tit_ev = tk.Entry(form_ev, width=24, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 9))
        ent_tit_ev.grid(row=1, column=2, padx=(0, 6), ipady=4, sticky="ew")
        form_ev.columnconfigure(2, weight=1)

        def crear_ev():
            ok, msg = agenda.agregar_evento(self.selected_date, ent_hora.get(), cb_tipo_ev.get(), ent_tit_ev.get())
            if ok:
                self.notificar(msg, "success")
                self.mostrar_vista("calendario")
            else:
                messagebox.showwarning("Validación", msg)

        tk.Button(form_ev, text="+ Agendar", bg=c["accent"], fg=c["accent_fg"], font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=10, pady=4, cursor="hand2", command=crear_ev).grid(row=1, column=3)

        # Lista de eventos agendados + botones completar/eliminar
        ev_actions = tk.Frame(left_panel, bg=c["bg_card"])
        ev_actions.pack(fill="x", pady=(0, 4))
        tk.Label(ev_actions, text="Agenda Programada", bg=c["bg_card"], fg=c["text_primary"], font=("Segoe UI", 10, "bold")).pack(side="left")

        tree_ev = self._crear_tabla(left_panel, ("ID", "Fecha", "Hora", "Tipo", "Título", "Estado"), (40, 90, 55, 115, 160, 85))
        for ev in todos_eventos:
            estado_txt = "✓ Listo" if ev["completado"] else "Pendiente"
            tree_ev.insert("", "end", values=(ev["id"], ev["fecha"], ev["hora"], ev["tipo"], ev["titulo"], estado_txt))

        def toggle_ev():
            sel = tree_ev.selection()
            if not sel:
                return
            ev_id = int(tree_ev.item(sel[0])["values"][0])
            agenda.alternar_estado_evento(ev_id)
            self.mostrar_vista("calendario")

        def del_ev():
            sel = tree_ev.selection()
            if not sel:
                return
            ev_id = int(tree_ev.item(sel[0])["values"][0])
            ok, msg = agenda.eliminar_evento(ev_id)
            if ok:
                self.notificar(msg, "success")
                self.mostrar_vista("calendario")

        tk.Button(ev_actions, text="Eliminar", bg=c["danger"], fg="white", font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=2, cursor="hand2", command=del_ev).pack(side="right", padx=(6, 0))
        tk.Button(ev_actions, text="✓ Marcar Listo", bg=c["success"], fg="white", font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=2, cursor="hand2", command=toggle_ev).pack(side="right")

        # ----- PANEL DERECHO: BLOC DE NOTAS PERSISTENTE -----
        right_panel = tk.Frame(main_split, bg=c["bg_card"], padx=16, pady=14, width=410)
        right_panel.pack(side="right", fill="both", expand=False)
        right_panel.pack_propagate(False)

        tk.Label(right_panel, text="Bloc de Notas Rápido", bg=c["bg_card"], fg=c["accent"], font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))

        self.nota_editando_id = None

        tk.Label(right_panel, text="Título de la nota:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ent_nota_tit = tk.Entry(right_panel, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
        ent_nota_tit.pack(fill="x", pady=(2, 8), ipady=5)

        tk.Label(right_panel, text="Contenido / Recordatorios:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        txt_nota = tk.Text(
            right_panel, height=9, bg=c["bg_input"], fg=c["text_primary"],
            insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10), padx=8, pady=8, wrap="word"
        )
        txt_nota.pack(fill="x", pady=(2, 10))

        btn_row_notas = tk.Frame(right_panel, bg=c["bg_card"])
        btn_row_notas.pack(fill="x", pady=(0, 12))

        def limpiar_editor_nota():
            self.nota_editando_id = None
            ent_nota_tit.delete(0, tk.END)
            txt_nota.delete("1.0", tk.END)

        def guardar_nota_btn():
            ok, msg = agenda.guardar_nota(ent_nota_tit.get(), txt_nota.get("1.0", tk.END), self.nota_editando_id)
            if ok:
                self.notificar(msg, "success")
                limpiar_editor_nota()
                self.mostrar_vista("calendario")
            else:
                messagebox.showwarning("Validación", msg)

        tk.Button(btn_row_notas, text="Guardar Nota", bg=c["accent"], fg=c["accent_fg"], font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=14, pady=5, cursor="hand2", command=guardar_nota_btn).pack(side="left")
        tk.Button(btn_row_notas, text="Nueva / Limpiar", bg=c["bg_input"], fg=c["text_primary"], font=("Segoe UI", 9),
                  relief="flat", padx=10, pady=5, cursor="hand2", command=limpiar_editor_nota).pack(side="left", padx=8)

        notas_list = agenda.listar_notas()
        notas_map = {n["id"]: n for n in notas_list}

        hdr_saved = tk.Frame(right_panel, bg=c["bg_card"])
        hdr_saved.pack(fill="x", pady=(4, 4))
        tk.Label(hdr_saved, text="Notas Guardadas (clic para abrir)", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).pack(side="left")

        tree_notas = self._crear_tabla(right_panel, ("ID", "Título", "Actualizada"), (40, 200, 120))
        for n in notas_list:
            tree_notas.insert("", "end", values=(n["id"], n["titulo"], n["fecha_actualizacion"][:16]))

        def cargar_nota_sel(event=None):
            sel = tree_notas.selection()
            if not sel:
                return
            n_id = int(tree_notas.item(sel[0])["values"][0])
            nota = notas_map.get(n_id)
            if nota:
                self.nota_editando_id = n_id
                ent_nota_tit.delete(0, tk.END)
                ent_nota_tit.insert(0, nota["titulo"])
                txt_nota.delete("1.0", tk.END)
                txt_nota.insert("1.0", nota["contenido"])

        def eliminar_nota_sel():
            sel = tree_notas.selection()
            if not sel:
                return
            n_id = int(tree_notas.item(sel[0])["values"][0])
            ok, msg = agenda.eliminar_nota(n_id)
            if ok:
                self.notificar(msg, "success")
                self.mostrar_vista("calendario")

        tree_notas.bind("<<TreeviewSelect>>", cargar_nota_sel)
        tk.Button(hdr_saved, text="Eliminar", bg=c["danger"], fg="white", font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=2, cursor="hand2", command=eliminar_nota_sel).pack(side="right")

    # ==================== VISTA 6: FINANZAS ====================
    def _vista_finanzas(self):
        c = self.colors
        self._header("Libro Diario y Finanzas", "Flujo de caja, ingresos, egresos y gastos operativos manuales")

        box = tk.Frame(self.content_frame, bg=c["bg_card"], padx=16, pady=12)
        box.pack(fill="x", pady=(0, 16))

        tk.Label(box, text="Tipo:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=6)
        cb_tipo = ttk.Combobox(box, values=["EGRESO", "INGRESO"], width=14, state="readonly")
        cb_tipo.current(0)
        cb_tipo.grid(row=1, column=0, padx=6, pady=6, ipady=4)

        tk.Label(box, text="Monto ($):", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=6)
        ent_monto = tk.Entry(box, width=16, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
        ent_monto.grid(row=1, column=1, padx=6, pady=6, ipady=5)

        tk.Label(box, text="Concepto / Descripción:", bg=c["bg_card"], fg=c["text_muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=6)
        ent_desc = tk.Entry(box, width=48, bg=c["bg_input"], fg=c["text_primary"], insertbackground=c["text_primary"], relief="flat", font=("Segoe UI", 10))
        ent_desc.grid(row=1, column=2, padx=6, pady=6, ipady=5)

        def registrar_mov():
            try:
                ok, msg = finanzas.registrar_transaccion(cb_tipo.get(), float(ent_monto.get()), ent_desc.get())
                if ok:
                    self.notificar(msg, "success")
                    self.mostrar_vista("finanzas")
                else:
                    messagebox.showwarning("Validación", msg)
            except ValueError:
                messagebox.showerror("Error", "Ingresa un monto numérico válido.")

        tk.Button(
            box, text="Registrar Movimiento", bg=c["accent"], fg=c["accent_fg"],
            font=("Segoe UI", 10, "bold"), relief="flat", padx=14, pady=6, cursor="hand2", command=registrar_mov
        ).grid(row=1, column=3, padx=12)

        tree = self._crear_tabla(self.content_frame, ("ID", "Fecha", "Tipo", "Monto", "Descripción"), (60, 160, 110, 130, 420))
        for tx in finanzas.listar_transacciones(100):
            tree.insert("", "end", values=(tx["id"], tx["fecha"], tx["tipo"], f"${tx['monto']:,.2f}", tx["descripcion"]))

if __name__ == "__main__":
    root = tk.Tk()
    app = OsloERP(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar)
    root.mainloop()
