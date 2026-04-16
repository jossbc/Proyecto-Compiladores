from Interprete import Interprete
from lark.tree import pydot__tree_to_png

inter = Interprete()

tree = (inter.interpretar_desde_archivo("test.txt"))

pydot__tree_to_png(tree, filename="arb")