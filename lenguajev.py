from lark import Transformer, v_args, Lark
from lark.exceptions import UnexpectedInput
import warnings
from CustomExceptions import InitializationError


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

parser = Lark(gramatica)

@v_args( meta = True )
class Interprete(Transformer):
    def __init__(self):
        self.tabla_simbolos = {}
        self.valores_por_tipo = {"int": [0, int, float], "float": [0.0, float, int], "string": ["", str], "invalid" : {""}}

    def __obtener_tipo__(valor):

        tipos_dict = {
            int: "int",
            float: "float",
            str: "string"
        }
    
        return tipos_dict.get(type(valor), "invalid")

    def __agregar_a_tabla_simbolos__(self, id, val, tipo, init):
        if id in self.tabla_simbolos:
            raise NameError(f"[Error]: Variable '{id}' ya definida.")
        self.tabla_simbolos[id] = {"valor": val, "tipo": tipo, "init": init}
        return val
    
    def __editar_tabla_simbolo__(self, id, val):
        if not id in self.tabla_simbolos:
            raise NameError(f"[Error]: Variable '{id}' no definida.")
        
        tipo = self.tabla_simbolos[id]["tipo"]

        compatible = False
        for t in self.valores_por_tipo[tipo][1:]:
            if isinstance(val, t):
                compatible = True
                break
        
        if not compatible:
            raise TypeError(f'[Error]: el tipo <{self.__obtener_tipo__(val)}> no es compatible con el tipo <{tipo}> de [{id}]')
        
        if not self.tabla_simbolos[id]["init"]:
            self.tabla_simbolos[id]["init"] = True

        if tipo == "int":
            val = int(val)
        elif tipo == "float":
            val = float(val)

        self.tabla_simbolos[id]["valor"] = val
    
    def _var(self, t):
        nombre = str(t[0])
        if nombre not in self.tabla_simbolos:
            raise NameError(f"[Error]: Variable '{nombre}' no definida.")
        
        if not self.tabla_simbolos[nombre]["init"]:
            raise InitializationError(f"[Error]: Variable '{nombre}' no inicializada.")
        return self.tabla_simbolos[nombre]["valor"]

    def _asig(self, t):
        return {"id": t[0], "valor": t[1]}

    
    def _num(self, t): return float(t[0])
    def _str(self, t): return t[0][1:-1] 
    def _var_name(self, t): return str(t[0])

    
    def _sum(self, t):
        return t[0] + t[1]
    def _rest(self, t): return t[0] - t[1]
    def _mult(self, t): return t[0] * t[1]
    def _div(self, t): 
        if t[1] == 0:
            raise ZeroDivisionError(f'[Error]: intento de division entre cero.')
        return t[0] / t[1]
    def _poten(self, t): return t[0] ** t[1]

    def _rpl(self, t):
        if not isinstance(t[0], str):
            raise TypeError(f'[Error]: Operacion replace invalida para tipo <{self._obtener_tipo_(t[0])}>')
        
        if not isinstance(t[1], str):
            raise TypeError(f'[Error]: Se esperaba un string para buscar. Se recibio <{self._obtener_tipo_(t[1])}>')
            
        if not isinstance(t[2], str):
            raise TypeError(f'[Error]: Se esperaba un string para reemplazar. Se recibio <{self._obtener_tipo_(t[2])}>')
        
        return t[0].replace(t[1], t[2])
        
    def _concat(self, t): return str(t[0]) + str(t[1])
    def _repeat(self, t): return str(t[1]) * int(t[0])
    def _trim(self, t): return str(t[0]).strip()
    
    def _sub_str(self, t):
        if not isinstance(t[0], str):
            raise TypeError(f'[Error]: Operacion invalida para tipo <{self.__obtener_tipo__(t[0])}>')
        
        if not isinstance(t[1], int) and not isinstance(t[1], float):
            raise TypeError(f'[Error]: Se esperaba tipo <int> o <float>. Se recibio tipo <{self.__obtener_tipo__(t[1])}>')
        
        if not isinstance(t[2], int) and not isinstance(t[2], float):
            raise TypeError(f'[Error]: Se esperaba tipo <int> o <float>. Se recibio tipo <{self.__obtener_tipo__(t[2])}>')
        
        return t[0][int(t[1]):int(t[2])]
    
    def _to_string(self, t): return str(t[0])

    
    def _print(self, t):
        if isinstance(t[0], list):
            print(*t[0])
        else:
            print()

    def _init_lista_args(self, t):
        return t

    def _lista_args(self, t):
        t[0].append(t[1])
        return t[0]

    def _decl_instr(self, t):
        tipo = str(t[0])
        valores_default = self.valores_por_tipo[tipo]
        for it in t[1]:
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
                        val = int(val)
                    if tipo == "float":
                        val = float(val)
                    if tipo == "string":
                        val = str(val)

                    self.__agregar_a_tabla_simbolos__(id, val, tipo, init=True)
                else:
                    val_str =  val if tipo == "string" else f'"{val}"'
                    raise TypeError(f'[ERROR]: el valor [{val_str}] no escompatible con el tipo [{tipo}]')
            else:
                self.__agregar_a_tabla_simbolos__(id, valores_default[0], tipo, init=False)

    
    def _init_lista_vars(self, t): 
        return t

    def _lista_vars(self, t):
        t[0].append(t[1])
        return t[0]

    def _id_decl(self, t):
        return {"id": str(t[0])} 

    def _asig_instr(self, t):
        id = t[0]["id"]
        val = t[0]["valor"]
        self.__editar_tabla_simbolo__(id, val)
        val = val if not self.tabla_simbolos[id]["tipo"] == "string" else f'"{val}"'
        print(f'[INFO]: Asignacion a variable [{id}] con valor <{val}>')

    
    def _expr_instr(self, t):
        warnings.warn("[Advertencia]: Esta instruccion no causa ningun efecto.")
        return
    

with open('test.txt',  'r') as f:

    test = f.read()
    inter = Interprete()
    try:
        result = inter.transform(parser.parse(test))

    except UnexpectedInput as e:
        print(f"[Error de Sintaxis]: Error linea {e.line}, columna {e.column}.")
        print(e.get_context(test))