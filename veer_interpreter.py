import sys
import re

class VeerInterpreter:
    def __init__(self):
        self.variables = {}
        self.program_counter = 0
        self.block_stack = []
        self.functions = {}
        self.call_stack = []

    def run(self, code):
        lines = code.split('\n')
        self.pre_scan_for_functions(lines)

        self.program_counter = 0
        while self.program_counter < len(lines):
            line_num = self.program_counter + 1
            line = lines[self.program_counter].strip()
            self.program_counter += 1

            if not line or line.startswith('#') or line.startswith("function"):
                continue

            parts = line.split()
            command = parts[0]
            try:
                if command in self.functions: self.execute_function_call(command)
                elif command == "say": self.execute_say(parts[1:])
                elif command == "set": self.execute_set(line)
                elif command == "if":
                    condition_parts = parts[1:-1]
                    self.block_stack.append(('if',))
                    if not self.evaluate_condition(condition_parts):
                        self.program_counter = self.find_matching_block_end(lines, self.program_counter)
                elif command == "else": self.program_counter = self.find_matching_block_end(lines, self.program_counter)
                elif command == "repeat": self.execute_repeat(parts[1:])
                elif command == "swap": self.execute_swap(parts[1:]) # Our new command
                elif command == "end": self.execute_end()
                else: print(f"Veer Error (Line {line_num}): Unknown command '{command}'")
            except Exception as e: print(f"Veer Runtime Error (Line {line_num}): {e}")

    def execute_swap(self, args):
        """Executes 'swap var1 and var2'"""
        if len(args) != 3 or args[1] != "and":
            raise SyntaxError("Invalid swap syntax. Expected: swap <var1> and <var2>")
        var1_name, var2_name = args[0], args[2]
        if var1_name not in self.variables or var2_name not in self.variables:
            raise NameError("One or both variables in swap do not exist.")
        # The magic of swapping in one line of Python
        self.variables[var1_name], self.variables[var2_name] = self.variables[var2_name], self.variables[var1_name]

    # All other methods are unchanged from v0.5
    def pre_scan_for_functions(self, lines):
        for i, line in enumerate(lines):
            if line.strip().startswith("function "): self.functions[line.strip().split()[1]] = i + 1
    def execute_function_call(self, func_name):
        self.call_stack.append(self.program_counter)
        self.program_counter = self.functions[func_name]
    def execute_end(self):
        if not self.block_stack and self.call_stack:
            self.program_counter = self.call_stack.pop()
            return
        if not self.block_stack: raise SyntaxError("Unexpected 'end'")
        block_type, *data = self.block_stack[-1]
        if block_type == 'if': self.block_stack.pop()
        elif block_type == 'repeat':
            loop_start_pc, count, iterator_var = data
            self.variables[iterator_var] += 1
            if self.variables[iterator_var] <= count: self.program_counter = loop_start_pc
            else: self.block_stack.pop()
    def get_value(self, expression):
        expression = expression.strip()
        if expression.startswith('"') and expression.endswith('"'): return expression[1:-1]
        if expression.isdigit() or (expression.startswith('-') and expression[1:].isdigit()): return int(expression)
        if '[' in expression and expression.endswith(']'):
            match = re.match(r"(\w+)\[(.*)\]", expression)
            if match:
                list_name, index_expr = match.groups()
                if list_name in self.variables and isinstance(self.variables[list_name], list):
                    index = self.get_value(index_expr)
                    return self.variables[list_name][index - 1]
                else: raise NameError(f"'{list_name}' is not a list or does not exist.")
        if expression in self.variables: return self.variables[expression]
        raise NameError(f"Unknown variable or expression '{expression}'")
    def execute_set(self, line):
        parts = line.split(' to ', 1)
        var_name_part = parts[0].split()
        if '[' in var_name_part[1]:
            match = re.match(r"(\w+)\[(.*)\]", var_name_part[1])
            list_name, index_expr = match.groups()
            index = self.get_value(index_expr)
            value = self.get_value(parts[1])
            self.variables[list_name][index - 1] = value
            return
        var_name = var_name_part[1]
        value_str = parts[1].strip()
        if value_str.startswith('[') and value_str.endswith(']'):
            list_contents = value_str[1:-1].split(',')
            self.variables[var_name] = [self.get_value(item) for item in list_contents]
        elif value_str.startswith('ask '): self.execute_ask(f"set {var_name} to {value_str}")
        else: self.variables[var_name] = self.get_value(value_str)
    def execute_say(self, args):
        full_arg_str = " ".join(args)
        expressions = re.split(r',\s*(?![^\[\]]*\])', full_arg_str)
        output = [str(self.get_value(expr)) for expr in expressions]
        print(" ".join(output))
    def evaluate_condition(self, parts):
        lhs_expr, op, rhs_expr = parts[0], parts[1], " ".join(parts[2:])
        val1 = self.get_value(lhs_expr); val2 = self.get_value(rhs_expr)
        if isinstance(val1, str) or isinstance(val2, str): val1, val2 = str(val1), str(val2)
        else: val1, val2 = int(val1), int(val2)
        if op == "is": return val1 == val2
        if op == "isnot": return val1 != val2
        if op == ">": return val1 > val2
        if op == "<": return val1 < val2
        if op == ">=": return val1 >= val2
        if op == "<=": return val1 <= val2
        raise SyntaxError(f"Unknown comparison operator '{op}'")
    def execute_ask(self, line):
        parts = line.split(); var_name = parts[1]; prompt = " ".join(parts[4:])[1:-1]
        user_input = input(prompt + " "); self.variables[var_name] = self.get_value(user_input)
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
    final_program = """
# Final Test for Mewar v1.0
say "--- Variable Swap Test ---"

set cup1 to "Milk"
set cup2 to "Water"

say "Before swap: Cup 1 has", cup1, "and Cup 2 has", cup2

# Use our new command!
swap cup1 and cup2

say "After swap:  Cup 1 has", cup1, "and Cup 2 has", cup2
"""
    print(">>> Starting Veer Interpreter v1.0...")
    print("-" * 20)
    interpreter = VeerInterpreter()
    interpreter.run(final_program)
    print("-" * 20)
    print(">>> Mewar v1.0 Program finished.")
