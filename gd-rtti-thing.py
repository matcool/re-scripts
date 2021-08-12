import gd
state = gd.memory.get_state()

playlayer_size = 0x538
cclayer_size = 284
gjgamelevel_size = 0x3b8
ccnode_size = 0xec
ccobject_size = 28
base = state.base_address
ptr = state.read_pointer

def demangle(name: str) -> str:
    if name.startswith('.?AV'):
        names = name[4:-2].split('@')
        return '::'.join(reversed(names))
    return name

def read_null_string(addr, stop_at=0):
    # string = bytearray()
    # chunk_size = 32
    # while state.read_byte(addr):
    #     if stop_at and len(string) > stop_at: return
    #     b = state.read_at(addr, chunk_size)
    #     try:
    #         i = b.index(0)
    #     except ValueError:
    #         i = chunk_size
    #     string += b[:i]
    #     if i == chunk_size: break
    #     addr += chunk_size
    # return string.decode()
    string = ''
    n = state.read_ubyte(addr)
    while n:
        if stop_at and len(string) > stop_at: return string
        string += chr(n)
        addr += 1
        n = state.read_ubyte(addr)
    return string


def get_name(addr):
    addr = state.read_pointer(addr)
    if not addr: return
    addr = state.read_pointer(addr - 4)
    if not addr: return
    addr = state.read_pointer(addr + 12)
    if not addr: return
    addr += 8
    s = read_null_string(addr, 100)
    # s = ''
    # while state.read_byte(addr):
    #     # wtf
    #     if len(s) > 100: return
    #     s += chr(state.read_ubyte(addr))
    #     addr += 1
    if not s.startswith('.?'): return
    return s

def go_through(addr, size):
    for i in range(0, size, 4):
        a = state.read_pointer(addr + i)
        name = get_name(a)
        if name:
            print(f'[0x{i:X}] - {demangle(name)}')
        # else:
        #     name = get_name(addr + i)
        #     if name:
        #         print(f'[0x{i:X}] - {demangle(name)}')

def truncate(s, l):
    return s if len(s) < l else s[:l] + ' [...]'

def strlen(addr) -> bool:
    start = addr
    while state.read_byte(addr):
        addr += 1
    return addr - start

def find_std_strings(addr, size):
    for i in range(0, size, 4):
        a = addr + i
        size = state.read_uint32(a + 16)
        capacity = state.read_uint32(a + 20)
        if capacity < 15: continue
        if size > capacity: continue
        # if not size: continue
        if size == 0 and capacity > 32: continue # idk
        if capacity == 15:
            l = strlen(a)
        else:
            if not state.read_pointer(a): continue
            l = strlen(state.read_pointer(a))
        if l != size: continue
        s = read_null_string(a if capacity == 15 else state.read_pointer(a), 51)
        print(f'[0x{i:X}] - ({size}) {truncate(s, 50)!r}')
# lvl = state.get_game_manager().get_play_layer().add(0x488).read_pointer()
# find_std_strings(state.get_game_manager().get_play_layer().address, playlayer_size)

# this macro is stinky

# #define HASH_ITER(hh,head,el,tmp)                                                \
# for((el)=(head),(tmp)=DECLTYPE(el)((head)?(head)->hh.next:NULL);                 \
#   el; (el)=(tmp),(tmp)=DECLTYPE(el)((tmp)?(tmp)->hh.next:NULL))

# typedef struct UT_hash_handle {
#    struct UT_hash_table *tbl;
#    void *prev;                       /* prev element in app order      */
#    void *next;                       /* next element in app order      */
#    struct UT_hash_handle *hh_prev;   /* previous hh in bucket order    */
#    struct UT_hash_handle *hh_next;   /* next hh in bucket order        */
#    void *key;                        /* ptr to enclosing struct's key  */
#    unsigned keylen;                  /* enclosing struct's key len     */
#    unsigned hashv;                   /* result of hash-fcn(key)        */
# } UT_hash_handle;

class CCDictElement:
    def __init__(self, addr):
        self.addr = addr
        self.string_key = read_null_string(addr)
        self.int_key = state.read_int32(addr + 0x100)
        self.value = state.read_pointer(addr + 0x104)
        # rest is ut_hash_handle

class CCDictionary:
    def __init__(self, addr):
        self.addr = addr
        self.elements = state.read_pointer(addr + 0x20)
        self.type = state.read_uint32(addr + 0x24)

    def __iter__(self):
        if self.type == 0: return
        el = self.elements
        tmp = state.read_pointer(el + 0x110)
        while el:
            de = CCDictElement(el)
            yield (de.string_key if self.type == 1 else de.int_key), de.value
            el = tmp
            tmp = state.read_pointer(tmp + 0x110) if tmp else None

def get_rtti(addr):
    vtable = state.read_pointer(addr)
    if not vtable: return
    rtti_complete_object_locator = state.read_pointer(vtable - 4)
    if not rtti_complete_object_locator: return
    rtti_class_hierarchy_descriptor = state.read_pointer(rtti_complete_object_locator + 16)
    if not rtti_class_hierarchy_descriptor: return
    # attributes = state.read_uint32(rtti_class_hierarchy_descriptor + 4)
    length = state.read_uint32(rtti_class_hierarchy_descriptor + 8)
    rtti_base_class_array = state.read_pointer(rtti_class_hierarchy_descriptor + 12)
    names = []
    for i in range(length):
        rtti_base_class_descriptor = state.read_pointer(rtti_base_class_array + i * 4)
        rtti_type_descriptor = state.read_pointer(rtti_base_class_descriptor)
        name = read_null_string(rtti_type_descriptor + 8, 100)
        names.append(name)
    return names

class CCArray:
    def __init__(self, addr):
        self.addr = addr
        self.data = state.read_pointer(addr + 0x20)
        self.size = state.read_uint32(self.data)
        self.capacity = state.read_uint32(self.data + 0x4)

    def __len__(self): return self.size
    def __getitem__(self, i):
        return state.read_pointer(state.read_pointer(self.data + 0x8) + i * 4)
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __repr__(self):
        return f'<CCArray size={self.size} capacity={self.capacity}>'
    def pretty(self, limit: int=20) -> str:
        s = '[' + ', '.join(demangle(get_name(i)) for _, i in zip(range(limit), self))
        if len(self) > limit:
            s += ' [...]'
        s += ']'
        return s
    def __str__(self):
        return self.pretty()

def std_string(addr) -> str:
    size = state.read_uint32(addr + 0x10)
    capacity = state.read_uint32(addr + 0x14)
    if capacity == 15:
        return read_null_string(addr, size)
    else:
        return read_null_string(state.read_pointer(addr), size)

def CCString(addr) -> str:
    return std_string(addr + 0x20)
    