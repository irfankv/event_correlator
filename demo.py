# \"['show version', 'show ipv4']\"
# \"[\'show bfd trace\']\"
def getformat(cmdlist):
	print(cmdlist)

	str = ''
	for x in cmdlist:
		str += '\'' + x + '\'' + ','
	return "\\\"[" + str.strip(',') + "]\\\""


cmd = []
cmd.append('show version')
#cmd.append('show ipv4')

print('/router/bin/python3 /tmp/event_trace_ssh.py 5.27.2.68 lab lab "%s" None /auto/tftp-bng-regression/pratraut/traces/BB13-PE4 BB13-PE4 60' % getformat(cmd))