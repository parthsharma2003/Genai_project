def binary_search_matrix(matrix, target):
    if not matrix or not matrix[0]:
        return False

    rows = len(matrix)
    cols = len(matrix[0])

    left, right = 0, rows * cols - 1

    while left <= right:
        mid = (left + right) // 2
        # Convert mid to matrix indices
        row = mid // cols
        col = mid % cols

        if matrix[row][col] == target:
            return True
        elif matrix[row][col] < target:
            left = mid + 1
        else:
            right = mid - 1

    return False

# Example usage:
matrix = [
    [1, 3, 5, 7],
    [10, 11, 16, 20],
    [23, 30, 34, 60]
]
target = 3

print(binary_search_matrix(matrix, target))  # Output: True

def add_matrices(matrix1, matrix2):
    """
    Add two matrices of the same dimensions.
    
    Args:
        matrix1 (list): First matrix as a 2D list
        matrix2 (list): Second matrix as a 2D list
        
    Returns:
        list: Resultant matrix after addition
        
    Raises:
        ValueError: If matrices have different dimensions
    """
    # Check if matrices are empty
    if not matrix1 or not matrix2:
        raise ValueError("Matrices cannot be empty")
    
    # Check if matrices have the same dimensions
    if len(matrix1) != len(matrix2) or len(matrix1[0]) != len(matrix2[0]):
        raise ValueError("Matrices must have the same dimensions")
    
    # Initialize result matrix with zeros
    result = [[0 for _ in range(len(matrix1[0]))] for _ in range(len(matrix1))]
    
    # Add corresponding elements
    for i in range(len(matrix1)):
        for j in range(len(matrix1[0])):
            result[i][j] = matrix1[i][j] + matrix2[i][j]
    
    return result

# Example usage of matrix addition
matrix1 = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

matrix2 = [
    [9, 8, 7],
    [6, 5, 4],
    [3, 2, 1]
]

try:
    result = add_matrices(matrix1, matrix2)
    print("Matrix 1:")
    for row in matrix1:
        print(row)
    print("\nMatrix 2:")
    for row in matrix2:
        print(row)
    print("\nResultant Matrix:")
    for row in result:
        print(row)
except ValueError as e:
    print(f"Error: {e}")

def multiply_matrices(matrix1, matrix2):
    """
    Multiply two matrices.
    
    Args:
        matrix1 (list): First matrix as a 2D list
        matrix2 (list): Second matrix as a 2D list
        
    Returns:
        list: Resultant matrix after multiplication
        
    Raises:
        ValueError: If matrices cannot be multiplied (invalid dimensions)
    """
    # Check if matrices are empty
    if not matrix1 or not matrix2:
        raise ValueError("Matrices cannot be empty")
    
    # Check if matrices can be multiplied
    if len(matrix1[0]) != len(matrix2):
        raise ValueError("Invalid matrix dimensions for multiplication")
    
    # Initialize result matrix with zeros
    result = [[0 for _ in range(len(matrix2[0]))] for _ in range(len(matrix1))]
    
    # Perform matrix multiplication
    for i in range(len(matrix1)):
        for j in range(len(matrix2[0])):
            for k in range(len(matrix2)):
                result[i][j] += matrix1[i][k] * matrix2[k][j]
    
    return result

# Example usage of matrix multiplication
matrix1 = [
    [1, 2, 3],
    [4, 5, 6]
]

matrix2 = [
    [7, 8],
    [9, 10],
    [11, 12]
]

try:
    result = multiply_matrices(matrix1, matrix2)
    print("\nMatrix Multiplication Example:")
    print("\nMatrix 1:")
    for row in matrix1:
        print(row)
    print("\nMatrix 2:")
    for row in matrix2:
        print(row)
    print("\nResultant Matrix (Matrix 1 × Matrix 2):")
    for row in result:
        print(row)
except ValueError as e:
    print(f"Error: {e}")

# Example of invalid multiplication
invalid_matrix1 = [
    [1, 2],
    [3, 4]
]

invalid_matrix2 = [
    [5, 6, 7],
    [8, 9, 10],
    [11, 12, 13]
]

print("\nInvalid Matrix Multiplication Example:")
try:
    result = multiply_matrices(invalid_matrix1, invalid_matrix2)
except ValueError as e:
    print(f"Error: {e}")

def subtract_matrices(matrix1, matrix2):
    """
    Subtract two matrices of the same dimensions.
    
    Args:
        matrix1 (list): First matrix as a 2D list
        matrix2 (list): Second matrix as a 2D list
        
    Returns:
        list: Resultant matrix after subtraction (matrix1 - matrix2)
        
    Raises:
        ValueError: If matrices have different dimensions
    """
    # Check if matrices are empty
    if not matrix1 or not matrix2:
        raise ValueError("Matrices cannot be empty")
    
    # Check if matrices have the same dimensions
    if len(matrix1) != len(matrix2) or len(matrix1[0]) != len(matrix2[0]):
        raise ValueError("Matrices must have the same dimensions")
    
    # Initialize result matrix with zeros
    result = [[0 for _ in range(len(matrix1[0]))] for _ in range(len(matrix1))]
    
    # Subtract corresponding elements
    for i in range(len(matrix1)):
        for j in range(len(matrix1[0])):
            result[i][j] = matrix1[i][j] - matrix2[i][j]
    
    return result

# Example usage of matrix subtraction
matrix1 = [
    [10, 20, 30],
    [40, 50, 60],
    [70, 80, 90]
]

matrix2 = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

try:
    result = subtract_matrices(matrix1, matrix2)
    print("\nMatrix Subtraction Example:")
    print("\nMatrix 1:")
    for row in matrix1:
        print(row)
    print("\nMatrix 2:")
    for row in matrix2:
        print(row)
    print("\nResultant Matrix (Matrix 1 - Matrix 2):")
    for row in result:
        print(row)
except ValueError as e:
    print(f"Error: {e}")

# Example of invalid subtraction
invalid_matrix1 = [
    [1, 2],
    [3, 4]
]

invalid_matrix2 = [
    [5, 6, 7],
    [8, 9, 10]
]

print("\nInvalid Matrix Subtraction Example:")
try:
    result = subtract_matrices(invalid_matrix1, invalid_matrix2)
except ValueError as e:
    print(f"Error: {e}")

def print_matrix(matrix, title="Matrix"):
    """
    Print a matrix in a nicely formatted way.
    
    Args:
        matrix (list): Matrix to print as a 2D list
        title (str): Optional title for the matrix display
    """
    if not matrix:
        print(f"{title}: Empty matrix")
        return
        
    print(f"\n{title}:")
    # Find the maximum width of any element for proper alignment
    max_width = max(len(str(element)) for row in matrix for element in row)
    
    # Print each row with proper alignment
    for row in matrix:
        print("│", end=" ")
        for element in row:
            print(f"{str(element):>{max_width}}", end=" ")
        print("│")
    print()  # Add a blank line after matrix

# Example usage of matrix printing
test_matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

print_matrix(test_matrix, "Test Matrix")

# Example with different sized numbers
test_matrix2 = [
    [1, 200, 3],
    [40, 5, 6000],
    [7, 800, 9]
]

print_matrix(test_matrix2, "Test Matrix with Different Sized Numbers")

# Example with the matrix operations
matrix1 = [
    [10, 20, 30],
    [40, 50, 60],
    [70, 80, 90]
]

matrix2 = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

try:
    # Addition
    result_add = add_matrices(matrix1, matrix2)
    print_matrix(matrix1, "Matrix 1")
    print_matrix(matrix2, "Matrix 2")
    print_matrix(result_add, "Result of Addition")
    
    # Subtraction
    result_sub = subtract_matrices(matrix1, matrix2)
    print_matrix(result_sub, "Result of Subtraction")
    
    # Multiplication
    matrix3 = [
        [1, 2],
        [3, 4],
        [5, 6]
    ]
    matrix4 = [
        [7, 8, 9],
        [10, 11, 12]
    ]
    result_mul = multiply_matrices(matrix3, matrix4)
    print_matrix(matrix3, "Matrix 3")
    print_matrix(matrix4, "Matrix 4")
    print_matrix(result_mul, "Result of Multiplication")
    
except ValueError as e:
    print(f"Error: {e}")

def spiral_traverse_matrix(matrix):
    """
    Traverse a matrix in spiral order (clockwise from outer to inner).
    
    Args:
        matrix (list): Input matrix as a 2D list
        
    Returns:
        list: Elements of the matrix in spiral order
        
    Raises:
        ValueError: If matrix is empty
    """
    if not matrix or not matrix[0]:
        raise ValueError("Matrix cannot be empty")
    
    result = []
    rows = len(matrix)
    cols = len(matrix[0])
    
    # Define boundaries
    top = 0
    bottom = rows - 1
    left = 0
    right = cols - 1
    
    while top <= bottom and left <= right:
        # Traverse right
        for i in range(left, right + 1):
            result.append(matrix[top][i])
        top += 1
        
        # Traverse down
        for i in range(top, bottom + 1):
            result.append(matrix[i][right])
        right -= 1
        
        # Traverse left
        if top <= bottom:
            for i in range(right, left - 1, -1):
                result.append(matrix[bottom][i])
            bottom -= 1
        
        # Traverse up
        if left <= right:
            for i in range(bottom, top - 1, -1):
                result.append(matrix[i][left])
            left += 1
    
    return result

# Example usage of spiral traversal
print("\nSpiral Traversal Examples:")

# Example 1: 3x3 matrix
matrix_3x3 = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

print_matrix(matrix_3x3, "3x3 Matrix")
spiral_result = spiral_traverse_matrix(matrix_3x3)
print("Spiral traversal result:", spiral_result)

# Example 2: 4x4 matrix
matrix_4x4 = [
    [1,  2,  3,  4],
    [5,  6,  7,  8],
    [9,  10, 11, 12],
    [13, 14, 15, 16]
]

print_matrix(matrix_4x4, "4x4 Matrix")
spiral_result = spiral_traverse_matrix(matrix_4x4)
print("Spiral traversal result:", spiral_result)

# Example 3: Rectangular matrix (3x4)
matrix_3x4 = [
    [1,  2,  3,  4],
    [5,  6,  7,  8],
    [9,  10, 11, 12]
]

print_matrix(matrix_3x4, "3x4 Matrix")
spiral_result = spiral_traverse_matrix(matrix_3x4)
print("Spiral traversal result:", spiral_result)

# Example 4: Empty matrix (error case)
try:
    empty_matrix = []
    spiral_result = spiral_traverse_matrix(empty_matrix)
except ValueError as e:
    print(f"\nError with empty matrix: {e}")

