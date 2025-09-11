# The Veer Interpreter for the Mewar Language
# Version 1.1 - File Runner
#
# This version is updated to read and execute Mewar code from a file.

import sys
import shlex

# --- 1. Token Types ---
TT_KEYWORD    = 'KEYWORD'
TT_IDENTIFIER = 'IDENTIFIER'
TT_NUMBER     = 'NUMBER'
TT_STRING     = 'STRING'

# Define the keywords of our language
MEWAR_KEYWORDS = [
    'set', 'to', 'say'
]

# --- 2. AST (Abstract Syntax Tree) Nodes ---
# These classes define the structure of our parsed code.

class SetVariableNode:
    def __init__(self, identifier_token, value_node):
        self.identifier_token = identifier_token
        self.value_node = value_node
    def __repr__(self):
        return f'(Set:{self.identifier_token["value"]}={self.value_node})'

class NumberNode:
    def __init__(self, token):
        self.token = token
    def __repr__(self):
        return f'{self.token["value"]}'

class StringNode:
    def __init__(self, token):
        self.token = token
    def __repr__(self):
        return f'"{self.token["value"]}"'

class VariableAccessNode:
    def __init__(self, token):
        self.token = token
    def __repr__(self):
        return f'(Get:{self.token["value"]})'

class SayNode:
    def __init__(self, nodes_to_say):
        self.nodes_to_say = nodes_to_say
    def __repr__(self):
        return f'(Say:{self.nodes_to_say})'

# --- 3. Lexer ---
# Breaks the raw code into a list of classified tokens.

class Lexer:
    def __init__(self, code_line):
        self.code_line = code_line

    def run(self):
        # shlex is great for splitting lines while respecting quoted strings
        words = shlex.split(self.code_line)
        tokens = []
        for word in words:
            if word in MEWAR_KEYWORDS:
                tokens.append({'type': TT_KEYWORD, 'value': word})
            elif word.isdigit():
                tokens.append({'type': TT_NUMBER, 'value': int(word)})
            # A simple check for identifiers (variable names)
            elif word.isidentifier():
                tokens.append({'type': TT_IDENTIFIER, 'value': word})
            else: # If it's none of the above, it's treated as a string value from shlex
                tokens.append({'type': TT_STRING, 'value': word})
        return tokens

# --- 4. Parser ---
# Takes tokens and builds a structured AST.

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.token_index = -1
        self.current_token = None
        self.advance()

    def advance(self):
        self.token_index += 1
        self.current_token = self.tokens[self.token_index] if self.token_index < len(self.tokens) else None

    def parse(self):
        if not self.current_token:
            return None
        
        if self.current_token['type'] == TT_KEYWORD and self.current_token['value'] == 'set':
            return self.parse_set_statement()
        elif self.current_token['type'] == TT_KEYWORD and self.current_token['value'] == 'say':
            return self.parse_say_statement()
        
        # If no known keyword is found, return None
        return None

    def parse_set_statement(self):
        self.advance() # Move past 'set'
        identifier = self.current_token
        self.advance() # Move past IDENTIFIER
        if self.current_token is None or self.current_token['value'] != 'to':
            # Basic grammar check for the 'to' keyword
            return None 
        self.advance() # Move past 'to'
        
        value_node = None
        if self.current_token['type'] == TT_NUMBER:
            value_node = NumberNode(self.current_token)
        elif self.current_token['type'] == TT_IDENTIFIER:
            value_node = VariableAccessNode(self.current_token)
        return SetVariableNode(identifier, value_node)

    def parse_say_statement(self):
        self.advance() # Move past 'say'
        nodes = []
        while self.current_token:
            if self.current_token['type'] == TT_NUMBER:
                nodes.append(NumberNode(self.current_token))
            elif self.current_token['type'] == TT_STRING:
                nodes.append(StringNode(self.current_token))
            elif self.current_token['type'] == TT_IDENTIFIER:
                nodes.append(VariableAccessNode(self.current_token))
            self.advance()
        return SayNode(nodes)

# --- 5. Symbol Table ---
# Manages the memory of our program (stores variables).

class SymbolTable:
    def __init__(self):
        self.symbols = {}
    def get(self, name):
        return self.symbols.get(name, 0) # Return 0 if not found
    def set(self, name, value):
        self.symbols[name] = value

# --- 6. Interpreter ---
# "Walks" the AST and executes the commands.

class Interpreter:
    def visit(self, node, symbol_table):
        method_name = f'visit_{type(node).__name__}'
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, symbol_table)

    def no_visit_method(self, node, symbol_table):
        raise Exception(f'No visit_{type(node).__name__} method defined')

    def visit_SetVariableNode(self, node, symbol_table):
        var_name = node.identifier_token['value']
        # Visit the value node to get its actual value before setting
        value = self.visit(node.value_node, symbol_table)
        symbol_table.set(var_name, value)

    def visit_SayNode(self, node, symbol_table):
        output = [str(self.visit(element_node, symbol_table)) for element_node in node.nodes_to_say]
        print(" ".join(output))

    def visit_NumberNode(self, node, symbol_table):
        return node.token['value']
    def visit_StringNode(self, node, symbol_table):
        return node.token['value']
    def visit_VariableAccessNode(self, node, symbol_table):
        var_name = node.token['value']
        return symbol_table.get(var_name)

# --- 7. The Main "run" function ---
def run(program_code):
    symbol_table = SymbolTable()
    interpreter = Interpreter()
    
    # Filter out empty lines and comments
    lines = [line for line in program_code.split('\n') if line.strip() and not line.strip().startswith('#')]

    for line in lines:
        lexer = Lexer(line)
        tokens = lexer.run()
        if not tokens: continue
        
        parser = Parser(tokens)
        ast = parser.parse()
        if not ast: continue
        
        interpreter.visit(ast, symbol_table)

# --- Main Entry Point: Read and execute a file ---
if __name__ == "__main__":
    # Check if a filename was provided on the command line
    if len(sys.argv) != 2:
        print("Usage: python veer_interpreter.py <filename.mewar>")
    else:
        filename = sys.argv[1]
        try:
            with open(filename, 'r') as f:
                code = f.read()
                run(code)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")


