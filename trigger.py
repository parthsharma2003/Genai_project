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

