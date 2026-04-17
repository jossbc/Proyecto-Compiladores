from lark import Transformer, v_args, Lark
from lark.exceptions import UnexpectedInput, UnexpectedToken, UnexpectedCharacters, VisitError
import warnings
from CustomExceptions import PreviouslyDeclaredError, InitializationError


GRAMATICA = r"""
start: instrucciones

instrucciones: instruccion+

?instruccion: declaracion
    | impresion
    | asignacion_suelta
    | expr_suelta

declaracion: TIPO lista_vars EOI   -> _decl_instr

lista_vars: item_vars              -> _init_lista_vars
        | lista_vars "," item_vars -> _lista_vars

?item_vars: id       -> _id_decl
        | asig

asignacion_suelta : asig EOI -> _asig_instr

expr_suelta: expr EOI        -> _expr_instr

asig: id "=" expr            -> _asig

?expr: expr_num
    | expr_str

?expr_num: expr_num "+" termino     -> _sum
        | expr_num "-" termino      -> _rest
        | termino

?termino: termino "*" factor        -> _mult
        | termino "/" factor        -> _div
        | factor

?factor: factor "^" expo            -> _poten
    | expo

?expo: number
    | id_num                        -> _var
    | "(" expr_num ")"

?expr_str: "(" expr_str ")"
        | concat
        | rep
        | rpl
        | trim
        | sub_str
        | str_lit

?concat: concat "#+" str_lit        -> _concat
    | str_lit

?rep: expr_num "#*" str_lit         -> _repeat
?rpl: "replace" "(" str_lit "," str_lit "," str_lit ")"  -> _rpl
?trim: "trim" "(" str_lit ")"       -> _trim
?sub_str: "sub" "(" str_lit "," expr_num "," expr_num ")" -> _sub_str

?str_lit: string
    | id_str                        -> _var
    | "to_string" "(" expr_num ")"  -> _to_string

impresion: PRT "(" [lista_args] ")" EOI -> _print

lista_args: expr                    -> _init_lista_args
        | lista_args "," expr       -> _lista_args

?id: id_num | id_str
?number: SIGNED_NUMBER              -> _num
?string: ESCAPED_STRING             -> _str
TIPO: "int" | "string" | "float"
?id_num: CNAME                      -> _var_name
?id_str: CNAME                      -> _var_name
EOI: ";"
PRT: "cangri"

%import common.WS
%import common.CNAME
%import common.SIGNED_NUMBER
%import common.ESCAPED_STRING
%import common.CPP_COMMENT

%ignore CPP_COMMENT
%ignore WS
"""


@v_args(meta=True)
class Interprete(Transformer):
    def __init__(self, salida_callback=None, warn_callback=None):
        super().__init__(visit_tokens=True)
        self.analizador = Lark(GRAMATICA, propagate_positions=True)
        self.tabla_simbolos: dict = {}
        self.valores_por_tipo = {
            "int":    [0,    int, float],
            "float":  [0.0,  float, int],
            "string": ["",   str],
            "invalid": {""},
        }
        self._output_cb = salida_callback or print
        self._warn_cb   = warn_callback   or (lambda m: warnings.warn(m))

    def interpretar_archivo(self, path: str):
        with open(path, encoding="utf-8") as f:
            return self.interpretar_texto(f.read())

    def interpretar_texto(self, texto: str):
        resultado = {
            "ok": False,
            "tokens": [],
            "arbol_obj": None,
            "simbolos": {},
            "mensajes": [],
        }

        try:
            arbol = self.analizador.parse(texto)
            resultado["arbol_obj"] = arbol
            resultado["tokens"]    = self._extraer_tokens(texto)
        except (UnexpectedToken, UnexpectedCharacters, UnexpectedInput) as e:
            msg = self._fmt_sintaxis(e, texto)
            resultado["mensajes"].append(msg)
            resultado["tokens"] = self._extraer_tokens(texto)
            return resultado

        try:
            self.tabla_simbolos = {}
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                self.transform(arbol)
                for w in captured:
                    resultado["mensajes"].append(f"[Advertencia]: {w.message}")

            resultado["ok"]      = True
            resultado["simbolos"] = dict(self.tabla_simbolos)

        except VisitError as e:
            err = e.orig_exc
            resultado["mensajes"].append(str(err))
        except Exception as e:
            resultado["mensajes"].append(f"[Error inesperado]: {e}")

        return resultado

    def _extraer_tokens(self, texto: str):
        tokens = []
        try:
            for tok in self.analizador.lex(texto):
                tokens.append({
                    "linea":  tok.line,
                    "col":    tok.column,
                    "tipo":   tok.type,
                    "valor":  str(tok),
                    "end_line": getattr(tok, "end_line", tok.line),
                    "end_col":  getattr(tok, "end_column", tok.column),
                })
        except Exception:
            pass
        return tokens

    @staticmethod
    def _fmt_sintaxis(e, texto):
        linea = getattr(e, "line", "?")
        col   = getattr(e, "column", "?")        
        pos = getattr(e, "pos_in_stream", None)        
        if type(e).__name__ == "UnexpectedEOF":
            pos = len(texto)
        elif pos is None and hasattr(e, "token"):
            pos = getattr(e.token, "pos_in_stream", None)

        def pos_anterior():
            if pos is None or not texto:
                return linea, col
            
            texto_previo = texto[:pos].rstrip()
            if not texto_previo:
                return linea, col
            l = texto_previo.count('\n') + 1
            ultimo_salto = texto_previo.rfind('\n')
            if ultimo_salto == -1:
                c = len(texto_previo) + 1
            else:
                c = len(texto_previo) - ultimo_salto                
            return l, c
        base = f"[Error Sintáctico] L{linea}:C{col}"
        if type(e).__name__ == "UnexpectedEOF":
            l, c = pos_anterior()
            return f"[Error Sintáctico] L{l}:C{c} — Falta punto y coma ';'"
        if isinstance(e, UnexpectedToken):
            esperados = getattr(e, "accepts", None)
            if esperados is None:
                esperados = getattr(e, "expected", [])
            esperados_list = list(esperados)            
            if "EOI" in esperados_list or ";" in esperados_list:
                l, c = pos_anterior()
                return f"[Error Sintáctico] L{l}:C{c} — Falta punto y coma ';'"            
            return base + f" — Token inesperado '{e.token}'. Esperados: {esperados_list}"            
        if isinstance(e, UnexpectedCharacters):
            ch = getattr(e, "char", "?")
            permitidos = getattr(e, "allowed", set())            
            if "EOI" in permitidos or ";" in permitidos:
                l, c = pos_anterior()
                return f"[Error Sintáctico] L{l}:C{c} — Falta punto y coma ';'"               
            return base + f" — Carácter no válido: '{ch}'"            
        return base + f" — {e}"

    def __obtener_tipo__(self, valor):
        return {int: "int", float: "float", str: "string"}.get(type(valor), "invalid")

    def __agregar_a_tabla_simbolos__(self, id_, val, tipo, init, meta):
        if id_ in self.tabla_simbolos:
            raise PreviouslyDeclaredError(
                f"[Error]: Variable '{id_}' ya definida. [L{meta.line}:C{meta.column}]"
            )
        self.tabla_simbolos[id_] = {"valor": val, "tipo": tipo, "init": init}
        return val

    def __editar_tabla_simbolo__(self, id_, val, meta):
        if id_ not in self.tabla_simbolos:
            raise NameError(f"[Error]: Variable '{id_}' no definida.")
        tipo = self.tabla_simbolos[id_]["tipo"]
        compatible = any(isinstance(val, t) for t in self.valores_por_tipo[tipo][1:])
        if not compatible:
            raise TypeError(
                f"[Error]: tipo <{self.__obtener_tipo__(val)}> incompatible con <{tipo}> de [{id_}]. "
                f"[L{meta.line}:C{meta.column}]"
            )
        self.tabla_simbolos[id_]["init"] = True
        if tipo == "int":
            val = int(val)
        if tipo == "float":
            val = float(val)
        self.tabla_simbolos[id_]["valor"] = val

    @v_args(meta=True)
    def _var(self, meta, t):
        nombre = str(t[0])
        if nombre not in self.tabla_simbolos:
            raise NameError(f"[Error]: Variable '{nombre}' no definida.")
        if not self.tabla_simbolos[nombre]["init"]:
            raise InitializationError(
                f"[Error]: Variable '{nombre}' no inicializada. [L{meta.line}:C{meta.column}]"
            )
        return self.tabla_simbolos[nombre]["valor"]

    def _asig(self, t):
        return {"id": t[0], "valor": t[1]}

    def _num(self, t):
        return float(t[0])

    def _str(self, t):
        return t[0][1:-1]

    def _var_name(self, t):
        return str(t[0])

    def _sum(self, t):   return t[0] + t[1]

    def _rest(self, t):  return t[0] - t[1]

    def _mult(self, t):  return t[0] * t[1]
    
    @v_args(meta=True)
    def _div(self,meta, t):
        if t[1] == 0:
            raise ZeroDivisionError(f"[Error]: división entre cero. [L{meta.line}:C{meta.column}]")
        return t[0] / t[1]

    def _poten(self, t): return t[0] ** t[1]

    @v_args(meta=True)
    def _rpl(self, meta, t):
        for i, label in enumerate(["cadena origen", "buscar", "reemplazar"]):
            if not isinstance(t[i], str):
                raise TypeError(
                    f"[Error]: replace — arg {i+1} ({label}) debe ser string. "
                    f"[L{meta.line}:C{meta.column}]"
                )
        return t[0].replace(t[1], t[2])

    def _concat(self, t):   return str(t[0]) + str(t[1])

    def _repeat(self, t):   return str(t[1]) * int(t[0])

    def _trim(self, t):     return str(t[0]).strip()

    @v_args(meta=True)
    def _sub_str(self, meta, t):
        if not isinstance(t[0], str):
            raise TypeError(f"[Error]: sub() requiere string. [L{meta.line}:C{meta.column}]")
        return t[0][int(t[1]):int(t[2])]


    def _to_string(self, t): return str(t[0])

    def _print(self, t):
        if t and isinstance(t[0], list):
            line = " ".join(str(x) for x in t[0])
        else:
            line = ""
        self._output_cb(line)

    def _init_lista_args(self, t): return list(t)

    def _lista_args(self, t):      t[0].append(t[1]); return t[0]

    @v_args(meta=True)
    def _decl_instr(self, meta, t):
        tipo = str(t[0])
        defaults = self.valores_por_tipo[tipo]
        for it in t[1]:
            id_ = it["id"]
            if "valor" in it:
                val = it["valor"]
                compatible = isinstance(val, defaults[1]) or (len(defaults) > 2 and isinstance(val, defaults[2]))
                if not compatible:
                    raise TypeError(
                        f"[Error]: valor incompatible con tipo [{tipo}] en variable [{id_}]."
                    )
                if tipo in ("int", "float"):
                    val = float(val)
                self.__agregar_a_tabla_simbolos__(id_, val, tipo, True, meta)
            else:
                self.__agregar_a_tabla_simbolos__(id_, defaults[0], tipo, False, meta)


    def _init_lista_vars(self, t): return list(t)

    def _lista_vars(self, t):      t[0].append(t[1]); return t[0]

    def _id_decl(self, t):         return {"id": str(t[0])}

    @v_args(meta=True)
    def _asig_instr(self, meta, t):
        id_  = t[0]["id"]
        val  = t[0]["valor"]
        self.__editar_tabla_simbolo__(id_, val, meta)


    def _expr_instr(self, t):
        self._warn_cb("[Advertencia]: expresión suelta sin efecto.")
