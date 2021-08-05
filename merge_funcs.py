import sys

def parse_funcs_file(path) -> dict:
    data = {}
    with open(path, 'r') as file:
        for line in file.readlines():
            if line:
                name, addr = line.split(' - ')
                addr = int(addr, 16)
                data[addr] = name
    
    return data

file1, file2, output = sys.argv[1:]
data1 = parse_funcs_file(file1)
data2 = parse_funcs_file(file2)
data = data1

for addr, name in data2.items():
    other = data.get(addr)
    if other is not None:
        if name != other:
            print(f'0 - {other}\n1 - {name}')
            if int(input(f'0x{addr:X} choose: ')):
                data[addr] = name
    else:
        data[addr] = name

with open(output, 'w') as file:
    for addr, name in data.items():
        file.write(f'{name} - 0x{addr:X}\n')