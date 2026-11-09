'''
Scope is the region of a program in which a variable name can be
accessed.

Python resolves names using the LEGB rule:

    L - Local:     inside the current function
    E - Enclosing: inside an outer function containing the current function
    G - Global:    at the module level
    B - Built-in:  predefined Python names, such as print() and len()

Python searches in this order: Local -> Enclosing -> Global -> Built-in.
'''

# Example 1 Local Variable

print('\nExample 1 Local Variable\n')

def show():
    x = 100
    print(x)

show()

# Example 2 try to access it outside the function

'''
print('\nExample 2 try to access it outside the function\n')

def show():
    x = 100
    print(x)

show()
print(x) # name 'x' is not defined

'''         

# Example 3: Same local name in two functions

print('\nExample 3: Same local name in two functions\n')

def first():
    x = 10
    print("First:", x)

def second():
    x = 20
    print("Second:", x)

first()              # First: 10
second()             # Second: 20

# Each function has its own local x. The variables do not overwrite each other.

# 4. GLOBAL SCOPE
# A variable assigned at the module level is global to that module.

# Example 1: Read a global variable inside a function

print('\nExample 1: Read a global variable inside a function\n')

x = 100

def show():
    print(x)

show()               # 100

# Python looks in the function’s local scope first. If x is not found there, it looks in the global scope.

print('\nExample 2: Local variable shadows a global variable\n')

x = 100

def show():
    x = 200
    print("Inside:", x)

show()               # Inside: 200
print("Outside:", x) # Outside: 100

# The assignment x = 200 creates a local variable. It does not change the global x.

# Example 3: Modify a global variable using global

print('\nExample 3: Modify a global variable using global\n')
x = 100

def update():
    global x
    x = 200

update()
print(x)             # 200

# The global keyword tells Python that assignments to x in this function refer to the module-level variable.

# Example 4: Multiple functions modify the same global variable
print('\nExample 4: Multiple functions modify the same global variable\n')
x = 10

def first():
    global x
    x = 20

def second():
    global x
    x = 30

first()
print(x)             # 20

second()
print(x)             # 30

# Both functions update the same global variable.

# 5. ENCLOSING SCOPE AND NESTED FUNCTIONS

# A function defined inside another function can access variables in the outer function.

# Example 1: Read an enclosing variable

print('\nExample 1: Read an enclosing variable\n')
def outer():
    x = 100

    def inner():
        print('inner',x)

    inner()

outer()  # 100

# Example 2: Local variable shadows the enclosing variable

print('\nExample 2: Local variable shadows the enclosing variable\n')

def outer():
    x = 100

    def inner():
        x = 200
        print("Inner:", x)

    inner()
    print("Outer:", x)

outer()

# Output: Inner: 200 Outer: 100

# The assignment inside inner() creates a local x in inner().

# Example 3: Modify an enclosing variable using nonlocal

print('\nExample 3: Modify an enclosing variable using nonlocal\n')

x = 10000
def outer():
    x = 100

    def inner():
        nonlocal x
        x = 200

    inner()
    print(x)

outer()              # 200
print(x)             # 10000

# The nonlocal keyword refers to a variable in the nearest enclosing function scope. It does not refer to a global variable.

# 6. GLOBAL VS NONLOCAL

# global: - Refers to a module-level variable. - Used when a function needs to assign to that global variable.

# nonlocal: - Refers to a variable in an enclosing function. - Used inside nested functions. - Requires that the variable already exists in an enclosing function scope.

# Example:

print('\n6. GLOBAL VS NONLOCAL\n')

x = 10

def outer():
    y = 20

    def inner():
        global x
        nonlocal y
        x = 100
        y = 200

    inner()
    print(y)

outer()
print(x)

# Output: 200 100

# 7. READING A VARIABLE BEFORE ASSIGNING IT

# This example raises UnboundLocalError:

print('\n7. READING A VARIABLE BEFORE ASSIGNING IT\n')

'''
x = 100

def show():
    print(x)
    x = 200

show() # Throw Error

'''

# Why? Because Python sees the assignment to x inside show() and treats x as a local variable throughout that function. The print statement tries to read that local variable before it has a value.

# Correct version when you intend to modify the global variable:

x = 100

def show():
    global x
    print(x)
    x = 200

show()               # Prints 100
print(x)             # 200


