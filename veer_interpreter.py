import sys
import re

class VeerInterpreter:
    def __init__(self):
        self.scopes = [{}]  # Global scope
        self.functions = {}
        self.lines = []
        self.program_counter = 0
        self.call_stack = []
        self._return_value = None

    def get_variable(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"Variable '{name}' is not defined.")

    def set_variable(self, name, value):
        match = re.match(r"(\w+)\[(.*)\]", name)
        if match:
            list_name, index_expr = match.groups()
            list_val = self.get_variable(list_name)
            if not isinstance(list_val, list):
                raise TypeError(f"'{list_name}' is not a list and cannot be indexed.")
            index = int(self.get_value(index_expr))
            if not 1 <= index <= len(list_val):
                raise IndexError(f"Index {index} is out of bounds for list '{list_name}'.")
            list_val[index - 1] = value
        else:
            # Set variable in the current (most local) scope that already contains it, or global scope.
            for scope in reversed(self.scopes):
                if name in scope:
                    scope[name] = value
                    return
            self.scopes[-1][name] = value


    def get_value(self, expression):
        expression = expression.strip()
        if expression.startswith('"') and expression.endsWith('"'): return expression[1:-1]
        if expression.startswith('[') and expression.endsWith(']'):
            list_contents = expression[1:-1].strip()
            if not list_contents: return []
            return [self.get_value(part) for part in re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', list_contents)]
        
        match = re.match(r"(\w+)\[(.*)\]", expression)
        if match:
            list_name, index_expr = match.groups()
            list_val = self.get_variable(list_name)
            if isinstance(list_val, list):
                index = int(self.get_value(index_expr))
                if not 1 <= index <= len(list_val):
                     raise IndexError(f"Index {index} is out of bounds for list '{list_name}'.")
                return list_val[index - 1]
            else: raise TypeError(f"'{list_name}' is not a list.")
        
        try:
            math_expr = re.sub(r'[a-zA-Z_][a-zA-Z0-9_]*', lambda m: str(self.get_variable(m.group(0))), expression)
            if re.fullmatch(r'[\d\s()+\-*/%.]+', math_expr):
                 return eval(math_expr, {'__builtins__': {}}, {})
        except Exception:
            pass

        try: return int(expression)
        except ValueError:
            try: return float(expression)
            except ValueError:
                 return self.get_variable(expression)

    def run(self, code):
        self.lines = code.split('\n')
        self.pre_scan_for_functions(self.lines)
        self.program_counter = 0

        while self.program_counter < len(self.lines):
            line_num = self.program_counter + 1
            line = self.lines[self.program_counter].split('#')[0].trim()

            if line.startswith("function "):
                self.program_counter = self.find_matching_block_end(self.program_counter + 1, find_else=False)
                self.program_counter += 1
                continue

            self.program_counter += 1
            if not line: continue
            
            try:
                self.execute_line(line)
            except Exception as e:
                print(f"Veer Runtime Error (Line {line_num}): {e}")
                return

    def execute_line(self, line):
        parts = line.split()
        command = parts[0]
        args_str = line[len(command):].strip()

        if command == "say": self.execute_say(args_str)
        elif command == "set": self.execute_set(args_str)
        elif command == "call": self.execute_call(args_str)
        elif command == "return": self.execute_return(args_str)
        elif command == "if": self.execute_if(args_str)
        elif command == "else": self.execute_else()
        elif command == "while": self.execute_while(args_str)
        elif command == "for": self.execute_for(args_str)
        elif command == "repeat": self.execute_repeat(args_str)
        elif command == "end": self.execute_end()
        elif command == "append": self.execute_append(args_str)
        else:
             raise SyntaxError(f"Unknown command '{command}'")

    def execute_say(self, args_str):
        parts = args_str.split('+')
        output = "".join(str(self.get_value(p)) for p in parts)
        print(output)

    def execute_set(self, args_str):
        target, value_expr = re.split(r'\s+to\s+', args_str, 1)
        if value_expr.startswith("call "):
            self.execute_call(value_expr[5:])
            value = self._return_value
            self._return_value = None
        elif value_expr.startswith("ask "):
            prompt = value_expr.split('"')[1]
            value = input(prompt + " ")
            try: 
                num_val = float(value)
                value = int(num_val) if num_val == int(num_val) else num_val
            except ValueError: pass
        else:
            value = self.get_value(value_expr)
        self.set_variable(target, value)

    def execute_if(self, args_str):
        condition_str = args_str.split(' then', 1)[0]
        result = self.evaluate_condition(condition_str)
        self.scopes.append({'type': 'if', 'result': result})
        if not result:
            self.program_counter = self.find_matching_block_end(self.program_counter, find_else=True)

    def execute_else(self):
        last_block = self.scopes[-1]
        if last_block.get('type') == 'if' and last_block.get('result') is True:
            self.program_counter = self.find_matching_block_end(self.program_counter, find_else=False)
        elif last_block.get('type') != 'if':
            raise SyntaxError("'else' without a preceding 'if'")

    def execute_while(self, args_str):
        loop_start_pc = self.program_counter - 1
        condition_str = args_str.split(' then', 1)[0]
        if self.evaluate_condition(condition_str):
            self.scopes.append({'type': 'while', 'start': loop_start_pc})
        else:
            self.program_counter = self.find_matching_block_end(self.program_counter, find_else=False)
    
    def execute_for(self, args_str):
        parts = args_str.split()
        iterator_var, list_name = parts[1], parts[3]
        iterable = self.get_variable(list_name)
        if not isinstance(iterable, list): raise TypeError(f"Cannot iterate over '{list_name}'.")

        loop_start_pc = self.program_counter
        if iterable:
            self.set_variable(iterator_var, iterable[0])
            self.scopes.append({'type': 'for', 'start': loop_start_pc, 'iterator': iterator_var, 'list': iterable, 'index': 0})
        else:
            self.program_counter = self.find_matching_block_end(loop_start_pc, find_else=False)

    def execute_repeat(self, args_str):
        count = int(self.get_value(args_str.split()[0]))
        loop_start_pc = self.program_counter
        if count > 0:
            self.scopes.append({'type': 'repeat', 'start': loop_start_pc, 'count': count, 'iteration': 1})
        else:
            self.program_counter = self.find_matching_block_end(loop_start_pc, find_else=False)

    def execute_append(self, args_str):
        value_expr, list_name = [p.strip() for p in args_str.split(' to ', 1)]
        list_val = self.get_variable(list_name)
        if not isinstance(list_val, list): raise TypeError(f"Cannot append to '{list_name}'.")
        list_val.append(self.get_value(value_expr))

    def execute_end(self):
        if self.call_stack:
             stack_frame = self.call_stack.pop()
             if stack_frame.get('target_variable') and self._return_value is None:
                 self.set_variable(stack_frame['target_variable'], None)
             self.scopes.pop()
             self.program_counter = stack_frame['pc']
             return

        if not self.scopes or len(self.scopes) <= 1:
            raise SyntaxError("Unexpected 'end' statement.")

        last_block = self.scopes[-1]
        block_type = last_block.get('type')

        if block_type == 'if':
            self.scopes.pop()
        elif block_type == 'while':
            self.program_counter = last_block['start']
        elif block_type == 'for':
            last_block['index'] += 1
            if last_block['index'] < len(last_block['list']):
                self.set_variable(last_block['iterator'], last_block['list'][last_block['index']])
                self.program_counter = last_block['start']
            else:
                self.scopes.pop()
        elif block_type == 'repeat':
            if last_block['iteration'] < last_block['count']:
                last_block['iteration'] += 1
                self.program_counter = last_block['start']
            else:
                self.scopes.pop()

    def evaluate_condition(self, condition_str):
        if " or " in condition_str:
            parts = condition_str.split(" or ", 1)
            return self.evaluate_condition(parts[0]) or self.evaluate_condition(parts[1])
        if " and " in condition_str:
            parts = condition_str.split(" and ", 1)
            return self.evaluate_condition(parts[0]) and self.evaluate_condition(parts[1])

        operators = ["==", "!=", ">=", "<=", ">", "<", "isnot", "is"]
        op_found = None
        for op in operators:
            search_op = f' {op} '
            if search_op in condition_str:
                op_found = op
                break
        
        if not op_found: raise SyntaxError(f"Unknown operator in condition: '{condition_str}'")

        parts = condition_str.split(f' {op_found} ', 1)
        lhs = self.get_value(parts[0])
        rhs = self.get_value(parts[1])
        
        if op_found in ("is", "=="): return lhs == rhs
        if op_found in ("isnot", "!="): return lhs != rhs
        if op_found == ">": return float(lhs) > float(rhs)
        if op_found == "<": return float(lhs) < float(rhs)
        if op_found == ">=": return float(lhs) >= float(rhs)
        if op_found == "<=": return float(lhs) <= float(rhs)

    def pre_scan_for_functions(self, lines):
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("function "):
                match = re.match(r"function\s+(\w+)(?:\s+with\s+(.*?))?\s+then", line)
                if match:
                    func_name, params_str = match.groups()
                    params = [p.strip() for p in params_str.split(',')] if params_str else []
                    self.functions[func_name] = {'start': i + 1, 'params': params}

    def execute_call(self, args_str, target_variable=None):
        match = re.match(r"(\w+)(?:\s+with\s+(.*?))?$", args_str)
        if not match: raise SyntaxError(f"Invalid function call syntax: '{args_str}'")
        
        func_name, args_expr_str = match.groups()
        if func_name not in self.functions: raise NameError(f"Function '{func_name}' is not defined.")

        func_info = self.functions[func_name]
        arg_values = [self.get_value(p) for p in re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', args_expr_str)] if args_expr_str else []

        if len(arg_values) != len(func_info['params']):
            raise TypeError(f"Function '{func_name}' expects {len(func_info['params'])} arguments, but got {len(arg_values)}.")

        new_scope = {}
        for param_name, arg_value in zip(func_info['params'], arg_values):
            new_scope[param_name] = arg_value
        
        self.scopes.append(new_scope)
        self.call_stack.append({'pc': self.program_counter, 'target_variable': target_variable})
        self.program_counter = func_info['start']

    def execute_return(self, args_str):
        if not self.call_stack: raise SyntaxError("'return' used outside of a function.")
        
        return_value = self.get_value(args_str) if args_str else None
        stack_frame = self.call_stack.pop()
        
        self.program_counter = stack_frame['pc']
        self.scopes.pop()

        if stack_frame['target_variable']:
            self.set_variable(stack_frame['target_variable'], return_value)
        else:
            self._return_value = return_value
    
    def find_matching_block_end(self, start_index, find_else=False):
        level = 1
        i = start_index
        while i < len(self.lines):
            line = self.lines[i].strip().split('#')[0].trim()
            if line.startswith(("if ", "function ", "while ", "for ", "repeat ")): level += 1
            elif find_else and line == "else" and level == 1: return i
            elif line == "end":
                level -= 1
                if level == 0: return i
            i += 1
        return len(self.lines) - 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Veer Interpreter (Definitive Edition)"); print("Usage: python veer_interpreter.py <filename.mewar>")
    else:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r') as f: mewar_code = f.read()
            interpreter = VeerInterpreter(); interpreter.run(mewar_code)
        except FileNotFoundError: print(f"Error: The file '{file_path}' was not found.")
        except Exception as e: print(f"An unexpected error occurred: {e}")

