Mewar Programming Language (& the Veer Interpreter)
Mewar is a simple, readable programming language designed from the ground up for absolute beginners. Its syntax is intended to be as close to natural language as possible.

This repository contains Veer, the official interpreter for the Mewar language, written in Python.

Language Features (v1.0)
Variables: set name to "value"

Output: say "Hello", name

Input: set age to ask "How old are you?"

Conditionals: if ... then / else / end

Loops: repeat 5 times using i (Coming in v1.2)

Comments: # This is a comment

How to Run
Ensure you have Python 3 installed.

Download the veer_interpreter.py file.

Create a Mewar program file (e.g., my_program.mewar).

Run the interpreter from your terminal:

python veer_interpreter.py my_program.mewar

Example Program
Here is an example of Mewar's syntax in action.

# my_program.mewar
say "--- Program Start ---"

set num1 to 50
set num2 to 99

say "Before swap:"
say "Number 1:" num1
say "Number 2:" num2

set temp to num1
set num1 to num2
set num2 to temp

say "After swap:"
say "Number 1:" num1
say "Number 2:" num2
