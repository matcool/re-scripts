# imports functions from a dump txt
# @author mat
# @category Matscripts
import os
import re
import time

save_path = askFile('open the dump file', 'Load')
if save_path and os.path.exists(str(save_path)):
	file = open(str(save_path), 'r')
	data = file.read()
	file.close()
	for line in data.splitlines():
		name, addr = line.split(' - ')
		# cant be bothered to implement nested namespaces
		if line.startswith('std::'): continue
		namespace, name = name.split('::', 1)
		addr = toAddr(int(addr, 16) + 0x400000)
		func = getFunctionContaining(addr)
		if not func: continue
		if func.getName(True) != namespace + '::' + name:
			if re.match(r'^FUN_[0-9a-fA-F]{8}$', func.getName()) is None:		
				getState().setCurrentAddress(addr)
				if not askYesNo('Replace this', 'Do you want to replace\n{}\nwith ->\n{}'.format(func.getName(True), line)):
					continue
		else:
			continue
		# if func.getParentNamespace().name != 'Global': continue
		namespace = getNamespace(None, namespace)
		if namespace:
			#getState().setCurrentAddress(addr)
			start()
			print('renaming ' + str(line))
			#time.sleep(1)
			func.setParentNamespace(namespace)
			func.setName(name, ghidra.program.model.symbol.SourceType.USER_DEFINED)
			end(True)
		else:
			print('wat')
else:
	popup('No')
