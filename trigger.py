def binary_search_matrix(matrix, target):
    if not matrix or not matrix[0]:
        return False
    print(matrix)
    print(target)
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

def transpose_matrix(matrix):
    """
    Transpose a matrix (convert rows to columns and columns to rows).
    
    Args:
        matrix (list): Input matrix as a 2D list
        
    Returns:
        list: Transposed matrix
        
    Raises:
        ValueError: If matrix is empty
    """
    if not matrix or not matrix[0]:
        raise ValueError("Matrix cannot be empty")
    
    # Get dimensions
    rows = len(matrix)
    cols = len(matrix[0])
    
    # Create a new matrix with swapped dimensions
    transposed = [[0 for _ in range(rows)] for _ in range(cols)]
    
    # Fill the transposed matrix
    for i in range(rows):
        for j in range(cols):
            transposed[j][i] = matrix[i][j]
    
    return transposed

# Example usage of matrix transpose
print("\nMatrix Transpose Examples:")

# Example 1: Square matrix (3x3)
matrix_3x3 = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

print_matrix(matrix_3x3, "Original 3x3 Matrix")
transposed_3x3 = transpose_matrix(matrix_3x3)
print_matrix(transposed_3x3, "Transposed 3x3 Matrix")

# Example 2: Rectangular matrix (2x4)
matrix_2x4 = [
    [1, 2, 3, 4],
    [5, 6, 7, 8]
]

print_matrix(matrix_2x4, "Original 2x4 Matrix")
transposed_2x4 = transpose_matrix(matrix_2x4)
print_matrix(transposed_2x4, "Transposed 2x4 Matrix (4x2)")

# Example 3: Single row matrix
matrix_1x3 = [
    [1, 2, 3]
]

print_matrix(matrix_1x3, "Original 1x3 Matrix")
transposed_1x3 = transpose_matrix(matrix_1x3)
print_matrix(transposed_1x3, "Transposed 1x3 Matrix (3x1)")

# Example 4: Empty matrix (error case)
try:
    empty_matrix = []
    transposed = transpose_matrix(empty_matrix)
except ValueError as e:
    print(f"\nError with empty matrix: {e}")

def create_adjacency_matrix(graph, directed=False):
    """
    Create an adjacency matrix from a graph representation.
    
    Args:
        graph (dict): Graph representation where keys are nodes and values are lists of connected nodes
        directed (bool): Whether the graph is directed (True) or undirected (False)
        
    Returns:
        list: Adjacency matrix as a 2D list
        
    Example:
        graph = {
            'A': ['B', 'C'],
            'B': ['A', 'D'],
            'C': ['A', 'D'],
            'D': ['B', 'C']
        }
        # Creates:
        # [[0, 1, 1, 0],
        #  [1, 0, 0, 1],
        #  [1, 0, 0, 1],
        #  [0, 1, 1, 0]]
    """
    if not graph:
        raise ValueError("Graph cannot be empty")
    
    # Get all unique nodes and sort them for consistent ordering
    nodes = sorted(graph.keys())
    n = len(nodes)
    
    # Create node to index mapping
    node_to_index = {node: i for i, node in enumerate(nodes)}
    
    # Initialize adjacency matrix with zeros
    adj_matrix = [[0 for _ in range(n)] for _ in range(n)]
    
    # Fill the adjacency matrix
    for node, neighbors in graph.items():
        i = node_to_index[node]
        for neighbor in neighbors:
            j = node_to_index[neighbor]
            adj_matrix[i][j] = 1
            if not directed:
                adj_matrix[j][i] = 1  # For undirected graphs, make it symmetric
    
    return adj_matrix

# Example usage of adjacency matrix creation
print("\nAdjacency Matrix Examples:")

# Example 1: Undirected graph
undirected_graph = {
    'A': ['B', 'C'],
    'B': ['A', 'D'],
    'C': ['A', 'D'],
    'D': ['B', 'C']
}

print("\nUndirected Graph:")
for node, neighbors in undirected_graph.items():
    print(f"{node} -> {neighbors}")

adj_matrix_undirected = create_adjacency_matrix(undirected_graph)
print_matrix(adj_matrix_undirected, "Adjacency Matrix (Undirected)")

# Example 2: Directed graph
directed_graph = {
    'A': ['B', 'C'],
    'B': ['D'],
    'C': ['D'],
    'D': []
}

print("\nDirected Graph:")
for node, neighbors in directed_graph.items():
    print(f"{node} -> {neighbors}")

adj_matrix_directed = create_adjacency_matrix(directed_graph, directed=True)
print_matrix(adj_matrix_directed, "Adjacency Matrix (Directed)")

# Example 3: Graph with self-loops
graph_with_loops = {
    'A': ['A', 'B'],
    'B': ['A', 'B', 'C'],
    'C': ['B', 'C']
}

print("\nGraph with Self-loops:")
for node, neighbors in graph_with_loops.items():
    print(f"{node} -> {neighbors}")

adj_matrix_loops = create_adjacency_matrix(graph_with_loops)
print_matrix(adj_matrix_loops, "Adjacency Matrix (with Self-loops)")

# Example 4: Empty graph (error case)
try:
    empty_graph = {}
    adj_matrix = create_adjacency_matrix(empty_graph)
except ValueError as e:
    print(f"\nError with empty graph: {e}")

def dummy_function(parameter1)
    print("Adding this function as dummy")
    print(parameter1)

dummy_function("testing")

def union_matrices(matrix1, matrix2):
    """
    Perform union operation on two matrices.
    The union combines elements from both matrices, keeping unique values.
    
    Args:
        matrix1 (list): First matrix as a 2D list
        matrix2 (list): Second matrix as a 2D list
        
    Returns:
        list: Resultant matrix containing unique elements from both matrices
        
    Raises:
        ValueError: If matrices are empty
    """
    # Check if matrices are empty
    if not matrix1 or not matrix2:
        raise ValueError("Matrices cannot be empty")
    
    # Convert matrices to sets of tuples for easy union operation
    set1 = {tuple(row) for row in matrix1}
    set2 = {tuple(row) for row in matrix2}
    
    # Perform union operation
    union_set = set1.union(set2)
    
    # Convert back to list of lists
    result = [list(row) for row in union_set]
    
    return result

# Example usage of matrix union
matrix1 = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

matrix2 = [
    [1, 2, 3],
    [10, 11, 12],
    [7, 8, 9]
]

try:
    result = union_matrices(matrix1, matrix2)
    print("\nMatrix Union Example:")
    print("\nMatrix 1:")
    for row in matrix1:
        print(row)
    print("\nMatrix 2:")
    for row in matrix2:
        print(row)
    print("\nResultant Matrix (Union of Matrix 1 and Matrix 2):")
    for row in result:
        print(row)
except ValueError as e:
    print(f"Error: {e}")

# Example 1: 3x3 matrix
matrix_3x3 = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

print_matrix(matrix_3x3, "3x3 Matrix")
# Example 2: 4x4 matrix with different start position
matrix_4x4 = [
    [1,  2,  3,  4],
    [5,  6,  7,  8],
    [9,  10, 11, 12],
    [13, 14, 15, 16]
]

print_matrix(matrix_4x4, "4x4 Matrix")

# Example 3: Rectangular matrix (3x4)
matrix_3x4 = [
    [1,  2,  3,  4],
    [5,  6,  7,  8],
    [9,  10, 11, 12]
]

print_matrix(matrix_3x4, "3x4 Matrix")

# Example 4: Invalid start position (error case)
try:
    invalid_start_matrix = [
        [1, 2, 3],
        [4, 5, 6]
    ]
    start_row = 2  # Invalid row index
    start_col = 1
    if start_row >= len(invalid_start_matrix) or start_col >= len(invalid_start_matrix[0]):
        raise ValueError("Invalid start position")
except ValueError as e:
    print(f"\nError with invalid start position: {e}")

