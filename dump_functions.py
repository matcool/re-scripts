# dump all ur funcs into a file
# @author mat
# @category Matscripts
import os

save_path = askFile('hi', 'save')
if save_path and not os.path.exists(str(save_path)):
    file = open(str(save_path), 'w')
    #for c in currentProgram.getSymbolTable().getClassNamespaces():
    #    for i in currentProgram.getSymbolTable().getSymbols(c):
    #        if i.getSymbolType().toString() == 'Function':
    for i in currentProgram.getSymbolTable().getAllSymbols(False):
        n = i.getParentNamespace()
        if i.getSymbolType() == ghidra.program.model.symbol.SymbolType.FUNCTION \
        and not i.isGlobal() \
        and n.getName() != 'std' \
        and i.getSource() == ghidra.program.model.symbol.SourceType.USER_DEFINED:
            s = '::'.join(i.getPath()) + ' - ' + hex(i.getAddress().unsignedOffset - 0x400000)[:-1]
            file.write(s + '\n')
    file.close()
else:
    popup('No')
