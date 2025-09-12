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
        """
        UPGRADED: Can now evaluate simple arithmetic expressions.
        The heart of the Mewar language's calculation ability.
        """
        expression = expression.strip()

        # --- NEW: Arithmetic Logic ---
        # We process operators in a specific order for potential future expansion.
        # For now, it finds the first operator.
        operators = ['+', '-', '*', '/']
        for op in operators:
            if op in expression:
                parts = expression.split(op, 1)
                # Recursively call get_value to resolve operands (which could be variables)
                val1 = self.get_value(parts[0])
                val2 = self.get_value(parts[1])

                # Ensure operands are numbers
                try:
                    num1 = float(val1)
                    num2 = float(val2)
                except (ValueError, TypeError):
                    raise ValueError(f"Cannot perform math on non-numeric value.")

                # Perform the calculation
                if op == '+': result = num1 + num2
                elif op == '-': result = num1 - num2
                elif op == '*': result = num1 * num2
                elif op == '/':
                    if num2 == 0: raise ZeroDivisionError("Cannot divide by zero.")
                    result = num1 / num2
                
                # Return integer if the result is a whole number, else float
                return int(result) if result == int(result) else result

        # --- Existing Logic for non-math expressions ---
        if expression == '""' or expression == "''": return ""
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

    # --- `execute_set` now works with math automatically via `get_value` ---
    def execute_set(self, line):
        parts = line.split(' to ', 1)
        var_name_part = parts[0].split()
        target_expr = var_name_part[1]
        value_str = parts[1].strip()

        # The get_value function now handles the entire right side, including math
        if value_str.startswith('ask '):
             self.execute_ask(f"set {target_expr} to {value_str}")
        else:
             final_value = self.get_value(value_str)
             self.set_value(target_expr, final_value)
    
    def set_value(self, target_expr, value):
        """Helper to set a value to either a simple variable or a list item."""
        if '[' in target_expr:
            match = re.match(r"(\w+)\[(.*)\]", target_expr)
            list_name, index_expr = match.groups()
            index = self.get_value(index_expr)
            self.variables[list_name][index - 1] = value
        else:
            self.variables[target_expr] = value
            
    # The rest of the interpreter remains largely the same...
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
                elif command == "if":
                    condition_parts = line.split()[1:-1]; self.block_stack.append(('if',))
                    if not self.evaluate_condition(condition_parts): self.program_counter = self.find_matching_block_end(lines, self.program_counter)
                elif command == "else": self.program_counter = self.find_matching_block_end(lines, self.program_counter)
                elif command == "repeat": self.execute_repeat(line.split()[1:])
                elif command == "end": self.execute_end()
                else: print(f"Veer Error (Line {line_num}): Unknown command '{command}'")
            except Exception as e: print(f"Veer Runtime Error (Line {line_num}): {e}")
    def execute_say(self, args_str):
        if not args_str: print(); return
        parts = re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', args_str)
        output = [str(self.get_value(part.strip())) for part in parts]
        print(" ".join(output))
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
        # We need to parse the target variable correctly from the 'set ... to ask' line
        target_expr = line.split(' to ', 1)[0].split()[1]
        prompt = line.split('ask ', 1)[1][1:-1]
        user_input = input(prompt + " ")
        # Convert to number if possible
        try:
            numeric_input = float(user_input)
            final_input = int(numeric_input) if numeric_input == int(numeric_input) else numeric_input
        except ValueError:
            final_input = user_input
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
        print("Veer Interpreter v1.2"); print("Usage: python veer.py <filename.mewar>")
    else:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r') as f: mewar_code = f.read()
            interpreter = VeerInterpreter(); interpreter.run(mewar_code)
        except FileNotFoundError: print(f"Error: The file '{file_path}' was not found.")
        except Exception as e: print(f"An unexpected error occurred: {e}")

