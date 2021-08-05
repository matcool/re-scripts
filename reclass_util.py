import sys
import zipfile
import xml.etree.ElementTree as ET
import re

if len(sys.argv) < 3 or (sys.argv[2] == 'dump' and len(sys.argv) < 4):
    print('usage: reclass_util.py file {dump, dump-all} [class to dump]')
    exit(1)

NAMING_CONVENTION = 'best'
if '-snake' in sys.argv: NAMING_CONVENTION = 'snake'
elif '-ugly' in sys.argv: NAMING_CONVENTION = 'ugly'
elif '-none' in sys.argv: NAMING_CONVENTION = None

with zipfile.ZipFile(sys.argv[1], 'r') as file:
    with file.open('Data.xml', 'r') as data:
        root = ET.fromstring(data.read())

classes = {}
for c in root.find('classes').findall('class'):
    classes[c.attrib['uuid']] = c

def skip(iterable, n):
    for _ in range(n):
        next(iterable)
    yield from iterable

def get_class_size(target) -> int:
    size = 0
    for node in target:
        size += get_node_size(node)
    return size

def get_node_size(node) -> int:
    t = node.attrib['type']
    if t == 'ClassInstanceNode':
        return get_class_size(classes[node.attrib['reference']])
    elif t == 'ArrayNode':
        return int(node.attrib['count']) * get_node_size(node[0])
    elif t == 'UnionNode':
        n = 0
        for child in node:
            n = max(n, get_node_size(child))
        return n
    elif t == 'Utf8TextNode':
        return int(node.attrib['length'])
    elif t == 'Utf8TextPtrNode':
        return 4
    elif t == 'DoubleNode':
        return 8
    elif t == 'BoolNode':
        return 1
    else:
        match = re.search(r'\d+', t)
        if match:
            return int(match[0]) // 8
        else:
            return 4

COCOS_CLASSES = {'CCArray', 'CCObject', 'CCNode', 'CCDictionary', 'CCParticleSystemQuad', 'CCPoint', 'CCSize', 'CCRect', 'CCDrawNode', 'CCSprite', 'CCLayer', 'CCLabelBMFont', 'CCMotionStreak', 'CCSpriteBatchNode'}

def get_neat_name(node) -> str:
    t = node.attrib['type']
    mapping = {
        'BoolNode': 'bool',
        'DoubleNode': 'double',
        'FloatNode': 'float',
        'Int32Node': 'int',
        'UInt32Node': 'unsigned int',
        'Int16Node': 'short',
        'UInt16Node': 'unsigned short',
        'VirtualMethodTableNode': 'vtable'
    }
    if t in mapping: return mapping[t]
    if t == 'PointerNode':
        if len(node):
            return get_neat_name(node[0]) + '*'
        return 'void*'
    elif t == 'ClassInstanceNode':
        name = classes[node.attrib['reference']].attrib['name']
        if name in COCOS_CLASSES:
            name = 'cocos2d::' + name
        return name
    elif t == 'EnumNode':
        return node.attrib['reference']
    elif t == 'ArrayNode':
        return get_neat_name(node[0]) + f'[{node.attrib["count"]}]'
    else:
        # print('what', t)
        return 'unknown'

def capitalize(s: str) -> str:
    # str.capitalize forces the rest of the string to be lowercase
    # so here just leave it be
    return s[0:1].upper() + s[1:]

def get_stupid_prefix_for_type(node_type: str, node, neat_name: str) -> str:
    if node_type == 'PointerNode':
        return 'p'
    elif node_type.startswith('Int'):
        return 'n'
    elif node_type == 'BoolNode':
        return 'b'
    elif node_type == 'FloatNode':
        return 'f'
    elif node_type == 'DoubleNode':
        return 'd'
    elif node_type == 'EnumNode':
        return 'e'
    elif neat_name == 'std::string':
        return 's'
    elif neat_name in {'cocos2d::CCPoint', 'cocos2d::CCRect'}:
        return 'ob'
    else:
        print('unknown node type:', node_type)
        return 'unk'

def gen_header(target: 'Element') -> str:
    inherits = []
    i = 0
    offset = 0
    while i < len(target) and target[i].attrib['type'] == 'ClassInstanceNode':
        parent = classes[target[i].attrib['reference']]
        offset += get_class_size(parent)
        inherits.append(get_neat_name(target[i]))
        i += 1
        break # multiple inheritance is weird

    output = f'class {target.attrib["name"]}'
    if inherits:
        output += ' : ' + ', '.join(inherits)
    output += ' {\n'
    
    last = offset
    for node in skip(iter(target), i):
        size = get_node_size(node)
        name = node.attrib['name']
        node_type = node.attrib['type']

        #print(f'0x{offset:02X}', node.attrib['type'], node.attrib['name'], size)
        if not node_type.startswith('Hex'):
            pad = offset - last
            if pad and (offset % 4 != 0 or pad >= 4) or size <= pad:
                output += f'\tPAD({pad});\n'
            # print(f'0x{offset:02X} {name} {offset - last}')
            neat_name = get_neat_name(node)
            output += f'\t{neat_name} '
            if re.match(r'N[0-9A-F]{8}', name):
                output += f'unk{offset:03X};'
                if node.attrib['comment']:
                    output += ' // ' + node.attrib['comment']
            else:
                if NAMING_CONVENTION == 'best':
                    # m_camelCase (the best)
                    name = 'm_' + ''.join(capitalize(n) if i else n for i, n in enumerate(name.split(' ')))
                elif NAMING_CONVENTION == 'snake':
                    # snake_case (doesnt fit in with the rest of gd.h)
                    name = name.replace(' ', '_').lower()
                elif NAMING_CONVENTION == 'ugly':
                    # m_tPascalCase (stupidest)
                    name = 'm_' + get_stupid_prefix_for_type(node_type, node, neat_name) + ''.join(capitalize(i) for i in name.split(' '))

                output += f'{name}; // 0x{offset:03X} {node.attrib["comment"]}'
            # output += f'\t{get_neat_name(node)} {name}; // 0x{offset:02X} {node.attrib["comment"]}\n'
            output += '\n'
            last = offset + size

        offset += size

    if offset - last:
        output += f'\tPAD({offset - last});\n'

    output += f'}}; // size: 0x{offset:X}'

    return output

if sys.argv[2] == 'dump':
    for c in classes.values():
        if c.attrib['name'] == sys.argv[3]:
            print(gen_header(c))
            break
elif sys.argv[2] == 'dump-all':
    for c in classes.values():
        print(gen_header(c))