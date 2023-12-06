import random

AVERAGE_STACK_LEN = 10
STACK_SPREAD = 5
DROP_RATE = 0.9

MATRIX_ROWS = 100
MATRIX_SEATS = 100


def get_sector_mask(sector_all, sector_parsed, sector_name):
    sector_ords = [ord(char) for char in sector_name]
    name_number = 1
    for sec_ord in sector_ords:
        name_number *= sec_ord
    seed = name_number % (2 ** 32)


def get_global_mask():
    matrix = [[False] * MATRIX_SEATS for _ in range(MATRIX_ROWS)]
    stack_counter = 0
    all_counter = 0
    dropped_counter = 0
    for row in matrix:
        for i in range(MATRIX_SEATS):
            all_counter += 1
            if (stack_counter <= 0) or (dropped_counter / all_counter < DROP_RATE):
                row[i] = True
            else:
                dropped_counter += 1
                stack_counter -= 1