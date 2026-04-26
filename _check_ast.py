import ast
f1 = 'tests/test_association_discovery.py'
f2 = 'tests/test_learning_evolution_integration.py'
ast.parse(open(f1).read())
print(f'{f1}: AST parse OK')
ast.parse(open(f2).read())
print(f'{f2}: AST parse OK')
