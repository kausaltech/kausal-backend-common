from __future__ import annotations


def _highlight_cell_in_line(line: str, cell_index: int) -> str:
    parts = line.split()
    if cell_index >= len(parts):
        return line
    target = parts[cell_index]
    pos = 0
    for i, part in enumerate(parts):
        pos = line.find(part, pos)
        if i == cell_index:
            highlight = ' ' * pos + '^' * len(target)
            return f'{line}\n{highlight}'
        pos += len(part)
    return line


def _parse_column_value(value_str: str) -> str | int | bool:
    if value_str == '+':
        return True
    if value_str == '-':
        return False
    try:
        return int(value_str)
    except ValueError:
        return value_str


valuetype = str | int | bool

def parse_table(input_str: str) -> tuple[tuple[str, ...], list[tuple[valuetype, ...]]]:
    """Parse a whitespace-separated table into headers and type-checked data rows.

    Intended for use in pytest parameterization where you want to define test cases
    in a readable tabular format with automatic type inference.

    Input format:
    - First line: column headers (whitespace-separated)
    - Subsequent lines: data rows (whitespace-separated)
    - All rows must have the same number of columns
    - The amount of whitespace does not matter but it's highly advisable to align the columns using spaces
    - Comments: Use '#' to add comments; everything after '#' on a line is ignored
    - Lines containing only comments or whitespace are ignored

    Type inference:
    - '+' is parsed as True
    - '-' is parsed as False
    - Values parseable as integers are converted to int
    - All other values remain as strings
    - Column types for the whole table are inferred from the first data row
    - All subsequent rows must match these types

    Args:
        input_str: Whitespace-separated table with header row and data rows

    Returns:
        Tuple of (headers, rows) where headers is a tuple of column names
        and rows is a list of tuples containing typed values. Can be passed
        directly as parameters to pytest.parametrize like this:

        @pytest.parametrize(*parse_table("table data"))

    Raises:
        ValueError: If rows have mismatched column counts or incompatible types
    """
    original_lines = input_str.strip().split('\n')
    lines = []
    for line in original_lines:
        line_without_comment = line.split('#')[0]
        if line_without_comment.strip():
            lines.append(line_without_comment)

    if len(lines) < 2:
        raise ValueError('Input must have at least a header row and one data row')

    headers = tuple(lines[0].split())
    num_columns = len(headers)

    first_row_parts = lines[1].split()
    if len(first_row_parts) != num_columns:
        raise ValueError(f'First data row has {len(first_row_parts)} elements but header has {num_columns}\n{lines[1]}')

    column_types = []
    first_row = []
    for part in first_row_parts:
        value = _parse_column_value(part)
        column_types.append(type(value))
        first_row.append(value)

    rows = [tuple(first_row)]

    for i, line in enumerate(lines[2:], start=2):
        parts = line.split()
        if len(parts) != num_columns:
            raise ValueError(f'Row {i} has {len(parts)} elements but expected {num_columns}\n{line}')

        row = []
        for j, (part, expected_type) in enumerate(zip(parts, column_types)):
            value = _parse_column_value(part)
            if not isinstance(value, expected_type):
                highlighted = _highlight_cell_in_line(line, j)
                raise ValueError(
                    f'Row {i}, column {j}: expected {expected_type.__name__}, got {type(value).__name__}\n{highlighted}'
                )
            row.append(value)

        rows.append(tuple(row))

    return headers, rows
