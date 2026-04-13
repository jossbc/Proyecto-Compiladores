from lark import Transformer, v_args, Lark
from lark.exceptions import UnexpectedInput, UnexpectedToken, UnexpectedCharacters, VisitError
import warnings
from CustomExceptions import *




@v_args(meta=True)
class Interprete(Transformer):
    def __init__(self):
        super().__init__(visit_tokens=True)

        gramatica = """
start: instrucciones

instrucciones: instruccion+

?instruccion: declaracion 
    | impresion
    | asignacion_suelta
    | expr_suelta

declaracion: TIPO lista_vars EOI   -> _decl_instr

lista_vars: item_vars             -> _init_lista_vars
        | lista_vars "," item_vars     -> _lista_vars

?item_vars: id        -> _id_decl
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

?concat: concat "#+" str_lit                                 -> _concat 
    | str_lit

?rep: expr_num "#*" str_lit                                  -> _repeat
?rpl: "replace" "(" str_lit "," str_lit "," str_lit ")"      -> _rpl
?trim: "trim" "(" str_lit ")"                                -> _trim
?sub_str: "sub" "(" str_lit "," expr_num "," expr_num ")"    -> _sub_str

?str_lit: string
    | id_str                                                -> _var
    | "to_string" "(" expr_num ")"                          -> _to_string

impresion: "cangri" "(" [lista_args] ")" EOI                -> _print

lista_args: expr                                            -> _init_lista_args
        | lista_args "," expr                               -> _lista_args

?id: id_num | id_str
?number: SIGNED_NUMBER                       -> _num
?string: ESCAPED_STRING                      -> _str
TIPO: "int" | "string" | "float"
?id_num: CNAME                               -> _var_name
?id_str: CNAME                               -> _var_name
EOI: ";"

%import common.WS
%import common.CNAME
%import common.SIGNED_NUMBER
%import common.ESCAPED_STRING
%import common.CPP_COMMENT

%ignore CPP_COMMENT
%ignore WS
"""

        self.analizador = Lark(gramatica, propagate_positions=True)

        self.tabla_simbolos = {}
        self.valores_por_tipo = {"int": [0, int, float], "float": [0.0, float, int], "string": ["", str],
                                 "invalid": {""}}
        
    def interpretar_desde_archivo(self, nombre_archivo):
        with open(nombre_archivo, 'r') as f:
            texto = f.read()
            self.interpretar_texto(texto)

    def interpretar_texto(self, texto_entrada):
        try:
            result = self.transform(self.analizador.parse(texto_entrada))
            print()
            print(result)
            
        except UnexpectedToken as e:
            print(f"[Error de Sintaxis (token)]: Token inesperado en la línea {e.line}, columna {e.column}.")
            print(e.get_context(texto_entrada))
            
            esperados = e.expected
            print("DEBUG Token Esperados:", esperados)
            
            if 'EOI' in esperados:
                print(" -> [Sugerencia]: Parece que olvidaste un punto y coma (';').")
            elif ')' in esperados or 'RPAR' in esperados:
                print(" -> [Sugerencia]: Te faltó cerrar un paréntesis ')' o la estructura está incompleta.")
            else:
                print(f" -> [Sugerencia]: Revisa la sintaxis. Se esperaba encontrar: {', '.join(esperados)}")

        except UnexpectedCharacters as e:
            print(f"[Error de Sintaxis (char)]: Carácter no válido en la línea {e.line}, columna {e.column}.")
            print(e.get_context(texto_entrada))
            
            esperados = e.allowed
            print("DEBUG Token Esperados:", esperados)
            caracter_malo = texto_entrada[e.pos_in_stream] 
            
            operadores_validos = ['+', '-', '*', '/', '^', '=', '#', '(', ')', ',', ';', '.', '"', '_']
            
            if not caracter_malo.isalnum() and caracter_malo not in operadores_validos and caracter_malo not in ' \t\n\r':
                print(f" -> [Sugerencia]: El símbolo '{caracter_malo}' no pertenece a este lenguaje. Quítalo o corrígelo.")
                
            elif caracter_malo == '(':
                print(" -> [Sugerencia]: Encontré un paréntesis '(' inesperado.")
                
            elif 'EOI' in esperados or '";"' in esperados:
                print(" -> [Sugerencia]: Parece que olvidaste un punto y coma (';') al final de la instrucción anterior.")
                
            elif '")"' in esperados or ')' in esperados or 'RPAR' in esperados or any("ANON" in s for s in esperados):
                print(" -> [Sugerencia]: Demasiados parámetros o símbolo inesperado. Se esperaba cerrar la función con ')'.")
                
            else:
                print(" -> [Sugerencia]: Revisa que no haya palabras mal escritas cerca de esta zona.")
        
        except UnexpectedInput as e:
            print(f"[Error de Sintaxis Genérico]: Error linea {e.line}, columna {e.column}.")
            print(e.get_context(texto_entrada))
            
        except VisitError as e:
            error_real = e.orig_exc
            
            if isinstance(error_real, TypeError):
                print(f"\n{error_real}")
                print(" -> [Sugerencia]: Revisa que estés asignando el tipo de dato correcto.")
                
            elif isinstance(error_real, NameError):
                print(f"\n{error_real}")
                print(" -> [Sugerencia]: Asegúrate de declarar la variable antes de usarla.")
                
            elif isinstance(error_real, PreviouslyDeclaredError):
                print(f"\n{error_real}")
                print(" -> [Sugerencia]: Asegúrate de declarar la variable solamente una vez.")
                
            elif isinstance(error_real, InitializationError):
                print(f"\n{error_real}")
                print(" -> [Sugerencia]: Asegúrate de inicializar la variable antes de usarla.")
                
            elif isinstance(error_real, ZeroDivisionError):
                print(f"\n{error_real}")
                print(" -> [Sugerencia]: Las matemáticas prohíben dividir entre cero. Cambia el denominador.")
                
            else:
                print(f"\n[Error de Ejecución]: {error_real}")

    def __obtener_tipo__(valor):

        tipos_dict = {
            int: "int",
            float: "float",
            str: "string"
        }
        return tipos_dict.get(type(valor), "invalid")

    def __agregar_a_tabla_simbolos__(self, id, val, tipo, init, meta):
        if id in self.tabla_simbolos:
            raise PreviouslyDeclaredError(f"[Error]: Variable '{id}' ya definida. [L{meta.line}:C{meta.column}]")
        self.tabla_simbolos[id] = {"valor": val, "tipo": tipo, "init": init}
        return val

    def __editar_tabla_simbolo__(self, id, val, meta):
        if not id in self.tabla_simbolos:
            raise NameError(f"[Error]: Variable '{id}' no definida.")

        tipo = self.tabla_simbolos[id]["tipo"]

        compatible = False
        for t in self.valores_por_tipo[tipo][1:]:
            if isinstance(val, t):
                compatible = True
                break

        if not compatible:
            raise TypeError(
                f'[Error]: el tipo <{self.__obtener_tipo__(val)}> no es compatible con el tipo <{tipo}> de [{id}].[L{meta.line}:C{meta.column}]')

        if not self.tabla_simbolos[id]["init"]:
            self.tabla_simbolos[id]["init"] = True

        if tipo == "int":
            val = float(val)
        elif tipo == "float":
            val = float(val)

        self.tabla_simbolos[id]["valor"] = val


    @v_args(meta=True)
    def _var(self, meta, t):
        nombre = str(t[0])
        if nombre not in self.tabla_simbolos:
            raise NameError(f"[Error]: Variable '{nombre}' no definida.")

        if not self.tabla_simbolos[nombre]["init"]:
            raise InitializationError(f"[Error]: Variable '{nombre}' no inicializada. [L{meta.line}:C{meta.column}]")
        return self.tabla_simbolos[nombre]["valor"]

    @v_args(meta=True)
    def _asig(self, meta, t):
        return {"id": t[0], "valor": t[1]}

    @v_args(meta=True)
    def _num(self, meta, t):
        return float(t[0])

    @v_args(meta=True)
    def _str(self, meta, t):
        return t[0][1:-1]

    @v_args(meta=True)
    def _var_name(self, meta, t):
        return str(t[0])

    @v_args(meta=True)
    def _sum(self, meta, t):
        return t[0] + t[1]

    @v_args(meta=True)
    def _rest(self, meta, t):
        return t[0] - t[1]

    @v_args(meta=True)
    def _mult(self, meta, t):
        return t[0] * t[1]

    @v_args(meta=True)
    def _div(self, meta, t):
        if t[1] == 0:
            raise ZeroDivisionError(f'[Error]: división entre cero. [L{meta.line}:C{meta.column}]')
        return t[0] / t[1]

    @v_args(meta=True)
    def _poten(self, meta, t):
        return t[0] ** t[1]

    @v_args(meta=True)
    def _rpl(self, meta, t):
        if not isinstance(t[0], str):
            raise TypeError(f'[Error]: Operacion replace invalida para tipo <{self.__obtener_tipo__(t[0])}>.[L{meta.line}:C{meta.column}]')

        if not isinstance(t[1], str):
            raise TypeError(f'[Error]: Se esperaba un string para buscar. Se recibio <{self.__obtener_tipo__(t[1])}>.[L{meta.line}:C{meta.column}]')

        if not isinstance(t[2], str):
            raise TypeError(
                f'[Error]: Se esperaba un string para reemplazar. Se recibio <{self.__obtener_tipo__(t[2])}>.[L{meta.line}:C{meta.column}]')

    @v_args(meta=True)
    def _concat(self, meta, t):
        return str(t[0]) + str(t[1])

    @v_args(meta=True)
    def _repeat(self, meta, t):
        return str(t[1]) * int(t[0])

    @v_args(meta=True)
    def _trim(self, meta, t):
        return str(t[0]).strip()

    @v_args(meta=True)
    def _sub_str(self, meta, t):
        if not isinstance(t[0], str):
            raise TypeError(f'[Error]: Operacion invalida para tipo <{self.__obtener_tipo__(t[0])}>.[L{meta.line}:C{meta.column}]')

        if not isinstance(t[1], int) and not isinstance(t[1], float):
            raise TypeError(
                f'[Error]: Se esperaba tipo <int> o <float>. Se recibio tipo <{self.__obtener_tipo__(t[1])}>.[L{meta.line}:C{meta.column}]')

        if not isinstance(t[2], int) and not isinstance(t[2], float):
            raise TypeError(
                f'[Error]: Se esperaba tipo <int> o <float>. Se recibio tipo <{self.__obtener_tipo__(t[2])}>.[L{meta.line}:C{meta.column}]')

        return t[0][int(t[1]):int(t[2])]

    @v_args(meta=True)
    def _to_string(self, meta, t):
        return str(t[0])

    @v_args(meta=True)
    def _print(self, meta, t):
        if t and isinstance(t[0], list):
            print(*t[0])
        else:
            print()

    @v_args(meta=True)
    def _init_lista_args(self, meta, t):
        return t

    @v_args(meta=True)
    def _lista_args(self, meta, t):
        t[0].append(t[1])
        return t[0]

    @v_args(meta=True)
    def _decl_instr(self, meta, t):
        tipo = str(t[0])
        valores_default = self.valores_por_tipo[tipo]
        for it in t[1]:
            print(it)
            tipo_correcto = False
            id = it["id"]
            if "valor" in it:
                val = it["valor"]
                if isinstance(val, valores_default[1]):
                    tipo_correcto = True
                elif len(valores_default) > 2 and isinstance(val, valores_default[2]):
                    tipo_correcto = True

                if tipo_correcto:
                    if tipo == "int":
                        val = float(val)
                    if tipo == "float":
                        val = float(val)
                    if tipo == "string":
                        val = str(val)

                    self.__agregar_a_tabla_simbolos__(id, val, tipo, True, meta)
                else:
                    val_str = val if tipo == "string" else f'"{val}"'
                    raise TypeError(f'[ERROR]: el valor [{val_str}] no escompatible con el tipo [{tipo}]')
            else:
                self.__agregar_a_tabla_simbolos__(id, valores_default[0], tipo, False, meta)


    @v_args(meta=True)
    def _init_lista_vars(self, meta, t):
        return t

    @v_args(meta=True)
    def _lista_vars(self, meta, t):
        t[0].append(t[1])
        return t[0]

    @v_args(meta=True)
    def _id_decl(self, meta, t):
        return {"id": str(t[0])}

    @v_args(meta=True)
    def _asig_instr(self, meta, t):
        id = t[0]["id"]
        val = t[0]["valor"]
        self.__editar_tabla_simbolo__(id, val,meta)
        val = val if not self.tabla_simbolos[id]["tipo"] == "string" else f'"{val}"'
        print(f'[INFO]: Asignacion a variable [{id}] con valor <{val}>')

    @v_args(meta=True)
    def _expr_instr(self, meta, t):
        warnings.warn("[Advertencia]: Esta instruccion no causa ningun efecto.")
        return

