import sys
import re

class VeerInterpreter:
    def __init__(self):
        self.variables = {}
        self.program_counter = 0
        self.block_stack = []
        self.functions = {}
        self.call_stack = []

    def get_value(self, expression):
        expression = expression.strip()

        # --- FIX PART 1: Make get_value robust to empty strings ---
        if expression == '""' or expression == "''":
            return ""

        # --- NEW: List Creation Logic ---
        # If the expression is a list literal like [1, "hello", 5]
        if expression.startswith('[') and expression.endswith(']'):
            list_contents = expression[1:-1].strip()
            if not list_contents:
                return [] # Return an empty list if contents are empty
            # Split by comma, but ignore commas inside quotes
            parts = re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', list_contents)
            return [self.get_value(part) for part in parts]

        # --- UPDATED: Arithmetic Logic with String Concatenation ---
        operators = ['+', '-', '*', '/']
        for op in operators:
            # A simple check to avoid splitting negative numbers
            if op in expression and expression.rfind(op) > 0:
                parts = expression.rsplit(op, 1)
                val1 = self.get_value(parts[0])
                val2 = self.get_value(parts[1])

                # If '+' is used with a string, perform concatenation
                if op == '+' and (isinstance(val1, str) or isinstance(val2, str)):
                    return str(val1) + str(val2)
                
                try:
                    num1 = float(val1); num2 = float(val2)
                except (ValueError, TypeError):
                    raise ValueError(f"Cannot perform math on non-numeric value.")
                if op == '+': result = num1 + num2
                elif op == '-': result = num1 - num2
                elif op == '*': result = num1 * num2
                elif op == '/':
                    if num2 == 0: raise ZeroDivisionError("Cannot divide by zero.")
                    result = num1 / num2
                return int(result) if result == int(result) else result

        # --- Existing Logic (Unchanged) ---
        if expression.startswith('"') and expression.endswith('"'): return expression[1:-1]
        if expression.isdigit() or (expression.startswith('-') and expression[1:].isdigit()): return int(expression)
        if '[' in expression and expression.endswith(']'):
            match = re.match(r"(\w+)\[(.*)\]", expression)
            if match:
                list_name, index_expr = match.groups()
                if list_name in self.variables and isinstance(self.variables[list_name], list):
                    index = self.get_value(index_expr); return self.variables[list_name][index - 1]
                else: raise NameError(f"'{list_name}' is not a list or does not exist.")
        if expression in self.variables: return self.variables[expression]
        raise NameError(f"Unknown variable or expression '{expression}'")
    
    # --- FIX PART 2: Make execute_say smarter ---
    def execute_say(self, args_str):
        # If the arguments are empty (from 'say' or 'say ""'), print a newline and exit.
        if not args_str or args_str == '""':
            print()
            return
        
        parts = re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', args_str)
        output = [str(self.get_value(part.strip())) for part in parts]
        print(" ".join(output))

    # The rest of the interpreter is unchanged...
    def run(self, code):
        lines = code.split('\n')
        self.pre_scan_for_functions(lines)
        self.program_counter = 0
        while self.program_counter < len(lines):
            line_num = self.program_counter + 1; line = lines[self.program_counter].strip(); self.program_counter += 1
            if not line or line.startswith('#'): continue
            command_match = re.match(r"(\w+)", line)
            if not command_match: continue
            command = command_match.group(1); args_str = line[len(command):].strip()
            try:
                if command in self.functions: self.execute_function_call(command)
                elif command == "say": self.execute_say(args_str)
                elif command == "set": self.execute_set(line)
                elif command == "swap": self.execute_swap(line.split()[1:])
                # --- NEW: Add 'append' command to the interpreter ---
                elif command == "append": self.execute_append(args_str)
                elif command == "if":
                    condition_parts = line.split()[1:-1]; self.block_stack.append(('if',))
                    if not self.evaluate_condition(condition_parts): self.program_counter = self.find_matching_block_end(lines, self.program_counter)
                elif command == "else": self.program_counter = self.find_matching_block_end(lines, self.program_counter)
                elif command == "repeat": self.execute_repeat(line.split()[1:])
                elif command == "end": self.execute_end()
                else: print(f"Veer Error (Line {line_num}): Unknown command '{command}'")
            except Exception as e: print(f"Veer Runtime Error (Line {line_num}): {e}")

    # --- NEW: Command to add an item to a list ---
    def execute_append(self, args_str):
        parts = args_str.split(' to ', 1)
        if len(parts) != 2:
            raise SyntaxError("Invalid append syntax. Use 'append <value> to <list_name>'")
        
        value_expr = parts[0].strip()
        list_name = parts[1].strip()

        if list_name not in self.variables:
            raise NameError(f"Cannot append to '{list_name}' because it does not exist.")
        if not isinstance(self.variables[list_name], list):
            raise TypeError(f"Cannot append to '{list_name}' because it is not a list.")
            
        value_to_append = self.get_value(value_expr)
        self.variables[list_name].append(value_to_append)

    def execute_set(self, line):
        parts = line.split(' to ', 1); target_expr = parts[0].split()[1]; value_str = parts[1].strip()
        if value_str.startswith('ask '): self.execute_ask(f"set {target_expr} to {value_str}")
        else: self.set_value(target_expr, self.get_value(value_str))
    def set_value(self, target_expr, value):
        if '[' in target_expr:
            match = re.match(r"(\w+)\[(.*)\]", target_expr)
            list_name, index_expr = match.groups()
            self.variables[list_name][self.get_value(index_expr) - 1] = value
        else: self.variables[target_expr] = value
    def execute_swap(self, args):
        if len(args) != 3 or args[1] != "and": raise SyntaxError("Invalid swap syntax.")
        var1_name, var2_name = args[0], args[2]
        if var1_name not in self.variables or var2_name not in self.variables: raise NameError("Variable in swap not found.")
        self.variables[var1_name], self.variables[var2_name] = self.variables[var2_name], self.variables[var1_name]
    def pre_scan_for_functions(self, lines):
        for i, line in enumerate(lines):
            if line.strip().startswith("function "): self.functions[line.strip().split()[1]] = i + 1
    def execute_function_call(self, func_name):
        self.call_stack.append(self.program_counter); self.program_counter = self.functions[func_name]
    def execute_end(self):
        if not self.block_stack and self.call_stack: self.program_counter = self.call_stack.pop(); return
        if not self.block_stack: raise SyntaxError("Unexpected 'end'")
        block_type, *data = self.block_stack[-1]
        if block_type == 'if': self.block_stack.pop()
        elif block_type == 'repeat':
            loop_start_pc, count, iterator_var = data; self.variables[iterator_var] += 1
            if self.variables[iterator_var] <= count: self.program_counter = loop_start_pc
            else: self.block_stack.pop()
    def evaluate_condition(self, parts):
        lhs_expr, op, rhs_expr = parts[0], parts[1], " ".join(parts[2:])
        val1 = self.get_value(lhs_expr); val2 = self.get_value(rhs_expr)
        if isinstance(val1, str) or isinstance(val2, str): val1, val2 = str(val1), str(val2)
        else: val1, val2 = float(val1), float(val2)
        if op == "is": return val1 == val2
        if op == "isnot": return val1 != val2
        if op == ">": return val1 > val2
        if op == "<": return val1 < val2
        if op == ">=": return val1 >= val2
        if op == "<=": return val1 <= val2
        raise SyntaxError(f"Unknown comparison operator '{op}'")
    def execute_ask(self, line):
        target_expr = line.split(' to ', 1)[0].split()[1]; prompt = line.split('ask ', 1)[1][1:-1]
        user_input = input(prompt + " ")
        try:
            numeric_input = float(user_input)
            final_input = int(numeric_input) if numeric_input == int(numeric_input) else numeric_input
        except ValueError: final_input = user_input
        self.set_value(target_expr, final_input)
    def execute_repeat(self, args):
        count = self.get_value(args[0]); iterator_var = args[3]
        self.variables[iterator_var] = 1; loop_start_pc = self.program_counter
        self.block_stack.append(('repeat', loop_start_pc, count, iterator_var))
    def find_matching_block_end(self, lines, start_index):
        nesting_level = 1
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if line.startswith("if") or line.startswith("repeat") or line.startswith("function"): nesting_level += 1
            elif line == "end":
                nesting_level -= 1
                if nesting_level == 0: return i
            elif line == "else" and nesting_level == 1: return i
        return len(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Veer Interpreter v1.3"); print("Usage: python veer.py <filename.mewar>")
    else:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r') as f: mewar_code = f.read()
            interpreter = VeerInterpreter(); interpreter.run(mewar_code)
        except FileNotFoundError: print(f"Error: The file '{file_path}' was not found.")
        except Exception as e: print(f"An unexpected error occurred: {e}")
