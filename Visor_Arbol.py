import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

try:
    from Interprete import Interprete
    LARK_OK = True
except ImportError as e:
    LARK_OK = False
    LARK_ERR = str(e)

BG          = "#F0F0F0"
BG_EDITOR   = "#FFFFFF"
BG_PANEL    = "#FFFFFF"
COLOR_BTN   = "#D0D0D0"
COLOR_HDR   = "#4A6FA5"
COLOR_HDR_FG= "#FFFFFF"
COLOR_OK    = "#2E7D32"
COLOR_ERR   = "#C62828"
FONT_NORMAL = ("Arial", 10)
FONT_MONO   = ("Courier New", 10)
FONT_BOLD   = ("Arial", 10, "bold")
FONT_TITLE  = ("Arial", 12, "bold")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Analizador Léxico / Sintáctico")
        self.geometry("1100x680")
        self.minsize(800, 500)
        self.configure(bg=BG)
        self._output_lines = []
        self._construir_ui()
        if not LARK_OK:
            messagebox.showerror(
                "Dependencia faltante",
                f"Falta el módulo 'lark'.\n\nInstálalo con:\n  pip install lark\n\nError: {LARK_ERR}"
            )

    def _construir_ui(self):
        self._construir_barra()
        panel_principal = tk.PanedWindow(
            self, orient="horizontal",
            bg="#AAAAAA", sashwidth=4
        )
        panel_principal.pack(fill="both", expand=True, padx=4, pady=4)
        izq  = self._construir_panel_izquierdo(panel_principal)
        der  = self._construir_panel_derecho(panel_principal)
        panel_principal.add(izq, minsize=280, width=420)
        panel_principal.add(der, minsize=380)

    def _construir_barra(self):
        barra = tk.Frame(self, bg=COLOR_HDR, padx=6, pady=5)
        barra.pack(fill="x", side="top")
        tk.Label(
            barra, text="Analizador Léxico/Sintáctico",
            bg=COLOR_HDR, fg=COLOR_HDR_FG, font=FONT_TITLE
        ).pack(side="left", padx=(4, 20))
        tk.Button(
            barra, text="Analizar",
            command=self._analizar,
            bg="#1B5E20", fg="white",
            font=FONT_BOLD, relief="raised", bd=2, padx=10
        ).pack(side="left", padx=3)
        tk.Button(
            barra, text="Abrir .txt",
            command=self._abrir_archivo,
            bg=COLOR_BTN, fg="black",
            font=FONT_NORMAL, relief="raised", bd=2, padx=8
        ).pack(side="left", padx=3)
        tk.Button(
            barra, text="Limpiar",
            command=self._limpiar,
            bg=COLOR_BTN, fg="black",
            font=FONT_NORMAL, relief="raised", bd=2, padx=8
        ).pack(side="left", padx=3)
        self._lbl_estado = tk.Label(
        )
        self._lbl_estado.pack(side="right", padx=10)

    def _construir_panel_izquierdo(self, parent):
        frame = tk.LabelFrame(
            parent, text=" Código fuente ",
            bg=BG, font=FONT_BOLD, padx=4, pady=4
        )
        tk.Label(
            frame,
            text="Escribe o carga tu código. Usa $ al final para indicar fin.",
            bg=BG, font=("Arial", 9), fg="#555555"
        ).pack(anchor="w", pady=(0, 3))
        self.editor = scrolledtext.ScrolledText(
            frame,
            wrap="none",
            font=FONT_MONO,
            bg=BG_EDITOR, fg="#000000",
            insertbackground="black",
            relief="sunken", bd=2,
            padx=6, pady=6,
            undo=True,
        )
        self.editor.pack(fill="both", expand=True)
        pie = tk.Frame(frame, bg=BG)
        pie.pack(fill="x", pady=(2, 0))
        self._lbl_pos = tk.Label(pie, text="Línea 1, Col 1", bg=BG, font=("Arial", 8), fg="#777")
        self._lbl_pos.pack(side="right")
        self.editor.bind("<KeyRelease>",    self._actualizar_pos)
        self.editor.bind("<ButtonRelease>", self._actualizar_pos)
        return frame

    def _actualizar_pos(self, event=None):
        pos = self.editor.index("insert")
        l, c = pos.split(".")
        self._lbl_pos.config(text=f"Línea {l}, Col {int(c)+1}")

    def _construir_panel_derecho(self, parent):
        frame = tk.Frame(parent, bg=BG)
        nb = ttk.Notebook(frame)
        nb.pack(fill="both", expand=True)
        self._tab_lexico   = tk.Frame(nb, bg=BG_PANEL)
        self._tab_sintax   = tk.Frame(nb, bg=BG_PANEL)
        self._tab_arbol    = tk.Frame(nb, bg=BG_PANEL)
        self._tab_simbolos = tk.Frame(nb, bg=BG_PANEL)
        self._tab_salida   = tk.Frame(nb, bg=BG_PANEL)
        nb.add(self._tab_lexico,   text="  Léxico  ")
        nb.add(self._tab_sintax,   text="  Sintáctico  ")
        nb.add(self._tab_arbol,    text="  Árbol  ")
        nb.add(self._tab_simbolos, text="  Símbolos  ")
        nb.add(self._tab_salida,   text="  Salida  ")
        nb.select(4)
        self._construir_tab_lexico()
        self._construir_tab_sintax()
        self._construir_tab_arbol()
        self._construir_tab_simbolos()
        self._construir_tab_salida()

        return frame

    def _construir_tab_lexico(self):
        p = self._tab_lexico
        tk.Label(p, text="Tokens encontrados por el analizador léxico:",
                 bg=BG_PANEL, font=FONT_BOLD).pack(anchor="w", padx=8, pady=(6, 2))
        columnas = ("linea", "col", "tipo", "valor", "longitud")
        encabezados = ("Línea", "Col", "Tipo de Token", "Valor", "Long.")
        frame_tabla = tk.Frame(p, bg=BG_PANEL)
        frame_tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._tabla_lex = ttk.Treeview(
            frame_tabla, columns=columnas,
            show="headings", selectmode="browse"
        )
        anchos = (55, 45, 160, 160, 55)
        for col, enc, ancho in zip(columnas, encabezados, anchos):
            self._tabla_lex.heading(col, text=enc)
            self._tabla_lex.column(col, width=ancho, anchor="w")
        sb_v = ttk.Scrollbar(frame_tabla, orient="vertical",   command=self._tabla_lex.yview)
        sb_h = ttk.Scrollbar(frame_tabla, orient="horizontal", command=self._tabla_lex.xview)
        self._tabla_lex.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        self._tabla_lex.grid(row=0, column=0, sticky="nsew")
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h.grid(row=1, column=0, sticky="ew")
        frame_tabla.grid_rowconfigure(0, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)
        self._tabla_lex.tag_configure("TIPO",           background="#E8EAF6")
        self._tabla_lex.tag_configure("CNAME",          background="#E3F2FD")
        self._tabla_lex.tag_configure("SIGNED_NUMBER",  background="#E8F5E9")
        self._tabla_lex.tag_configure("ESCAPED_STRING", background="#F3E5F5")
        self._tabla_lex.tag_configure("EOI",            background="#F5F5F5")
        self._tabla_lex.tag_configure("OTRO",           background="#FFF8E1")
        self._lbl_total_tokens = tk.Label(
            p, text="", bg=BG_PANEL, font=FONT_NORMAL, fg="#444"
        )
        self._lbl_total_tokens.pack(anchor="w", padx=8, pady=(0, 4))

    def _mostrar_lexico(self, tokens):
        for fila in self._tabla_lex.get_children():
            self._tabla_lex.delete(fila)
        for tok in tokens:
            tipo = tok["tipo"]
            if tipo in ("TIPO", "CNAME", "SIGNED_NUMBER", "ESCAPED_STRING", "EOI"):
                tag = tipo
            else:
                tag = "OTRO"
            self._tabla_lex.insert("", "end",
                values=(tok["linea"], tok["col"], tipo, tok["valor"], len(tok["valor"])),
                tags=(tag,)
            )
        self._lbl_total_tokens.config(
            text=f"Total de tokens encontrados: {len(tokens)}"
        )

    def _construir_tab_sintax(self):
        p = self._tab_sintax
        tk.Label(p, text="Resultado del análisis sintáctico:",
                 bg=BG_PANEL, font=FONT_BOLD).pack(anchor="w", padx=8, pady=(6, 2))
        self._txt_sintax_resultado = scrolledtext.ScrolledText(
            p, height=5, wrap="word",
            font=FONT_MONO,
            bg="#F9F9F9", fg="#000",
            relief="sunken", bd=2,
            padx=8, pady=6,
            state="disabled"
        )
        self._txt_sintax_resultado.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(p, text="Resumen de la instrucciones analizadas:",
                 bg=BG_PANEL, font=FONT_BOLD).pack(anchor="w", padx=8, pady=(2, 2))
        self._txt_sintax_resumen = scrolledtext.ScrolledText(
            p, height=8, wrap="word",
            font=FONT_MONO,
            bg="#F9F9F9", fg="#000",
            relief="sunken", bd=2,
            padx=8, pady=6,
            state="disabled"
        )
        self._txt_sintax_resumen.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _mostrar_sintax(self, resultado):
        ok       = resultado["ok"]
        mensajes = resultado["mensajes"]
        if ok:
            color_bg = "#E8F5E9"
            color_fg = COLOR_OK
            texto    = "   Análisis completado sin errores."
        else:
            color_bg = "#FFEBEE"
            color_fg = COLOR_ERR
            texto    = "X  Error encontrado:\n" + "\n".join(mensajes)
        self._txt_sintax_resultado.config(state="normal", bg=color_bg, fg=color_fg)
        self._txt_sintax_resultado.delete("1.0", "end")
        self._txt_sintax_resultado.insert("end", texto)
        self._txt_sintax_resultado.config(state="disabled")
        tokens   = resultado["tokens"]
        simbolos = resultado["simbolos"]
        lineas   = self.editor.get("1.0", "end").split("\n")
        lineas_codigo = len([l for l in lineas if l.strip()])
        resumen = (
            f"Líneas de código analiz. : {lineas_codigo}\n"
            f"Tokens detectados        : {len(tokens)}\n"
            f"Variables declaradas     : {len(simbolos)}\n"
            f"Instrucciones cangri     : {sum(1 for t in tokens if t['valor'] == 'cangri')}\n"
            f"Operadores aritméticos   : {sum(1 for t in tokens if t['valor'] in ('+', '-', '*', '/', '^'))}\n"
            f"Operadores de cadena     : {sum(1 for t in tokens if t['valor'] in ('#*', '#+'))}\n"
        )
        self._txt_sintax_resumen.config(state="normal")
        self._txt_sintax_resumen.delete("1.0", "end")
        self._txt_sintax_resumen.insert("end", resumen)
        self._txt_sintax_resumen.config(state="disabled")

    def _construir_tab_arbol(self):
        p = self._tab_arbol
        cabecera = tk.Frame(p, bg=BG_PANEL)
        cabecera.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(cabecera, text="Árbol sintáctico (Lark):",
                 bg=BG_PANEL, font=FONT_BOLD).pack(side="left")
        frame_arbol = tk.Frame(p, bg=BG_PANEL)
        frame_arbol.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._arbol_tree = ttk.Treeview(frame_arbol, selectmode="browse")
        sb_v = ttk.Scrollbar(frame_arbol, orient="vertical",   command=self._arbol_tree.yview)
        sb_h = ttk.Scrollbar(frame_arbol, orient="horizontal", command=self._arbol_tree.xview)
        self._arbol_tree.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        self._arbol_tree.grid(row=0, column=0, sticky="nsew")
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h.grid(row=1, column=0, sticky="ew")
        frame_arbol.grid_rowconfigure(0, weight=1)
        frame_arbol.grid_columnconfigure(0, weight=1)
        self._arbol_tree.tag_configure("nodo",  foreground="#1565C0")
        self._arbol_tree.tag_configure("token", foreground="#2E7D32")
        self._arbol_tree.tag_configure("error", foreground=COLOR_ERR)

    def _mostrar_arbol(self, resultado):
        tree = self._arbol_tree
        for item in tree.get_children():
            tree.delete(item)
        arbol_obj = resultado.get("arbol_obj")
        if arbol_obj is None:
            tree.insert("", "end", text="(sin árbol — hay errores de sintaxis)", tags=("error",))
            return
        self._insertar_nodo(tree, "", arbol_obj)
        for item in tree.get_children():
            tree.item(item, open=True)

    def _insertar_nodo(self, tree, parent, nodo):
        from lark import Tree, Token
        if isinstance(nodo, Tree):
            iid = tree.insert(parent, "end",
                              text=f"[{nodo.data}]",
                              tags=("nodo",), open=False)
            for hijo in nodo.children:
                self._insertar_nodo(tree, iid, hijo)
        elif isinstance(nodo, Token):
            tree.insert(parent, "end",
                        text=f'{nodo.type} = "{nodo}"',
                        tags=("token",))
        else:
            tree.insert(parent, "end", text=str(nodo))

    def _construir_tab_simbolos(self):
        p = self._tab_simbolos
        tk.Label(p, text="Tabla de símbolos (variables declaradas):",
                 bg=BG_PANEL, font=FONT_BOLD).pack(anchor="w", padx=8, pady=(6, 2))
        columnas = ("nombre", "tipo", "valor", "inicializada")
        encabezados = ("Nombre", "Tipo", "Valor", "Inicializada")
        frame_tabla = tk.Frame(p, bg=BG_PANEL)
        frame_tabla.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._tabla_sym = ttk.Treeview(
            frame_tabla, columns=columnas,
            show="headings", selectmode="browse"
        )
        anchos = (130, 80, 160, 100)
        for col, enc, ancho in zip(columnas, encabezados, anchos):
            self._tabla_sym.heading(col, text=enc)
            self._tabla_sym.column(col, width=ancho, anchor="w")
        sb_v = ttk.Scrollbar(frame_tabla, orient="vertical", command=self._tabla_sym.yview)
        self._tabla_sym.configure(yscrollcommand=sb_v.set)
        self._tabla_sym.grid(row=0, column=0, sticky="nsew")
        sb_v.grid(row=0, column=1, sticky="ns")
        frame_tabla.grid_rowconfigure(0, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)
        self._tabla_sym.tag_configure("si",  background="#E8F5E9")
        self._tabla_sym.tag_configure("no",  background="#FFEBEE")

    def _mostrar_simbolos(self, simbolos: dict):
        for fila in self._tabla_sym.get_children():
            self._tabla_sym.delete(fila)
        if not simbolos:
            self._tabla_sym.insert("", "end", values=("(sin variables)", "", "", ""))
            return
        for nombre, info in simbolos.items():
            tag      = "si" if info["init"] else "no"
            init_str = "Sí" if info["init"] else "No"
            self._tabla_sym.insert("", "end",
                values=(nombre, info["tipo"], str(info["valor"]), init_str),
                tags=(tag,)
            )

    def _construir_tab_salida(self):
        p = self._tab_salida
        tk.Label(p, text="Salida del programa (instrucciones cangri):",
                 bg=BG_PANEL, font=FONT_BOLD).pack(anchor="w", padx=8, pady=(6, 2))
        self._txt_salida = scrolledtext.ScrolledText(
            p, height=10, wrap="word",
            font=FONT_MONO,
            bg="#1E1E1E", fg="#00FF88",
            insertbackground="#00FF88",
            relief="sunken", bd=2,
            padx=8, pady=6,
            state="disabled"
        )
        self._txt_salida.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        tk.Label(p, text="Errores / Advertencias:",
                 bg=BG_PANEL, font=FONT_BOLD).pack(anchor="w", padx=8, pady=(2, 2))
        self._txt_errores = scrolledtext.ScrolledText(
            p, height=5, wrap="word",
            font=FONT_MONO,
            bg="#FFF3F3", fg=COLOR_ERR,
            relief="sunken", bd=2,
            padx=8, pady=6,
            state="disabled"
        )
        self._txt_errores.pack(fill="x", padx=8, pady=(0, 8))

    def _mostrar_salida(self, resultado):
        self._txt_salida.config(state="normal")
        self._txt_salida.delete("1.0", "end")
        if self._output_lines:
            self._txt_salida.insert("end", "\n".join(self._output_lines))
        else:
            self._txt_salida.insert("end", "(sin salida)")
        self._txt_salida.config(state="disabled")
        self._txt_errores.config(state="normal")
        self._txt_errores.delete("1.0", "end")
        if resultado["mensajes"]:
            self._txt_errores.config(bg="#FFF3F3", fg=COLOR_ERR)
            self._txt_errores.insert("end", "\n".join(resultado["mensajes"]))
        else:
            self._txt_errores.config(bg="#E8F5E9", fg=COLOR_OK)
            self._txt_errores.insert("end", "✔  Sin errores ni advertencias.")
        self._txt_errores.config(state="disabled")

    def _analizar(self):
        if not LARK_OK:
            messagebox.showerror("Error", "Instala lark primero:\n  pip install lark")
            return
        codigo = self.editor.get("1.0", "end-1c").strip()
        if not codigo:
            messagebox.showinfo("Vacío", "Escribe o carga código antes de analizar.")
            return
        if codigo.endswith("$"):
            codigo = codigo[:-1].rstrip()
        self._output_lines = []

        def tarea():
            try:
                interp = Interprete(
                    salida_callback=lambda l: self._output_lines.append(l),
                    warn_callback=lambda m: None,
                )
                resultado = interp.interpretar_texto(codigo)
                self.after(0, lambda: self._mostrar_resultado(resultado))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error interno", str(e)))
        threading.Thread(target=tarea, daemon=True).start()

    def _mostrar_resultado(self, resultado):
        self._mostrar_lexico(resultado["tokens"])
        self._mostrar_sintax(resultado)
        self._mostrar_arbol(resultado)
        self._mostrar_simbolos(resultado["simbolos"])
        self._mostrar_salida(resultado)

    def _abrir_archivo(self):
        ruta = filedialog.askopenfilename(
            title="Abrir archivo de código",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")]
        )
        if ruta:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("end", contenido)

    def _limpiar(self):
        self.editor.delete("1.0", "end")
        for tabla in (self._tabla_lex, self._arbol_tree, self._tabla_sym):
            for fila in tabla.get_children():
                tabla.delete(fila)
        for widget in (
            self._txt_sintax_resultado, self._txt_sintax_resumen,
            self._txt_salida, self._txt_errores
        ):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.config(state="disabled")
        self._lbl_total_tokens.config(text="")

if __name__ == "__main__":
    app = App()
    app.mainloop()
