import time
import datetime
import threading
import re
import logging
import os
import paramiko
import logging
import sys
import warnings

#print('------ test ---- ')
#print("argv is ", sys.argv)
ip_addr = sys.argv[1]
user_name = sys.argv[2]
password = sys.argv[3]
#print("Commands = ", sys.argv[4])
cmd = eval(sys.argv[4], {'__builtins__':None}, {})
tftp_addr = sys.argv[5]
log_path = sys.argv[6]
host_name = sys.argv[7]
interval = sys.argv[8]
exec_on_stby = False
hostname = host_name
cmd_lst = cmd

'''print("Type of cmd :", type(cmd))
print("Commands are :")
for c in cmd:
    print(c)
'''
print('arguments are -> %s %s %s %s %s %s %s %s %s' %(ip_addr,user_name,password,cmd,tftp_addr,log_path,host_name,interval,exec_on_stby))
#print(type(cmd))
#print("Commands = ", cmd)
#print("Command list = ", eval(sys.argv[4], {'__builtins__':None}, {}))


#ip_addr = '5.27.2.68'
#tftp_addr = '202.153.144.26'
#user_name = 'lab'
#password = 'lab'
#log_path = '/auto/tftp-viking-blr/kkumarav/'
#exec_on_stby = False
#hostname = 'BB13-PE4'
#interval = 60

#cmd_lst = ['show version','show ipv4 interface brief','show mpls traffic-eng tunnels','show mpls traffic-eng trace','show ethernet cfm peer meps','show ethernet cfm trace','show bfd trace','show bfd trace error','show ospf trace','show isis trace all']

#cmd_lst = ['show mpls traffic-eng trace','show bfd trace','show ethernet cfm traffic-eng']



class collector(threading.Thread):
    def __init__ (self, ip_addr, user_name, password, cmd, thread_name, exec_on_stby):
        threading.Thread.__init__(self)
        self.ip_addr = ip_addr
        self.user_name = user_name
        self.password = password
        self.cmd = cmd
        self.thread_name = thread_name
        self.exec_on_stby = exec_on_stby
        self.first_run = True

    def run(self):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.raiseExceptions=False

        print('Executing command - %s - in thread - %s' %(self.cmd, self.thread_name))
        ip_lst = ip_addr.split('.')
        ip_fle_name = '_'.join(ip_lst)
        if len(self.cmd.split('/')) > 1:
            cmd_slsh_join = '_'.join(self.cmd.split('/'))
            fle_name = '_'.join(cmd_slsh_join.split(' '))
        else:
            fle_name = '_'.join(self.cmd.split(' '))
        #print('file name is - %s cmd is - %s' %(fle_name,self.cmd))
        file_name = os.path.join(log_path, fle_name + '_' + ip_fle_name)
        if 'tech' in self.cmd or 'tech-support' in self.cmd:
            print('show tech - file name is - %s --> cmd is - %s' %(file_name,self.cmd))
            sh_tech_file = cmd + ' file tftp://' + tftp_addr + '/' + file_name
            st = conn.connect (self.ip_addr, username = self.user_name, password = self.password, look_for_keys=False)
            stdin, stdout, stderr = conn.exec_command(sh_tech_file)
            time.sleep(5)
        else:
            if self.exec_on_stby :
                tn.write('show redundancy | in STANDBY\r')
                op = tn.read_until(prompt)
                pat = 'Node Redundancy Partner \(([0-9A-Z\/]+)\) is in STANDBY role'
                reop = re.search(pat,op)
                stby_rp = reop.group(1)
                tn.write('run attach '+stby_rp+'\r')
                tn.read_until('#')
                tn.write('/pkg/bin/exec -a \r')
                op1 = tn.read_until(prompt)
                tn.write('term len 0 \r')
                op1 = tn.read_until(prompt)
                if len(self.cmd.split('/')) > 1:
                    cmd_slsh_join = '_'.join(self.cmd.split('/'))
                    fle_name = '_'.join(cmd_slsh_join.split(' '))
                    file_name = log_path+fle_name+'_'+ip_fle_name+'_stby'
                else:
                    fle_name = '_'.join(self.cmd.split(' '))
                    file_name = log_path+fle_name+'_'+ip_fle_name+'_stby'
                
            if self.first_run :
                print('First run for cmd %s creating file %s' %(self.cmd, file_name)) 
                fle = open(file_name,'w+')
                self.first_run = False
                first_cmd_exec = True

            cnt = 0
            continue_flag = True
            while continue_flag:
                tme_now = datetime.datetime.isoformat(datetime.datetime.now())
                tme_lst = tme_now.split('T')
                tme = ' '.join(tme_lst)
                #print('%s -> file name is - %s --> cmd is - %s' %(tme,file_name,self.cmd))
                cmd = self.cmd
                if first_cmd_exec:
                    first_cmd_exec = False
                    send_cmd = self.cmd
                else:
                    if 'trace' in cmd:
                        send_cmd = self.cmd + ' | begin "'+next_time+'"'

                print('%s -> file name is - %s --> cmd is - %s' %(tme,file_name,send_cmd))
                st = conn.connect (self.ip_addr, username = self.user_name, password = self.password, look_for_keys=False)
                stdin, stdout, stderr = conn.exec_command(send_cmd)

                if 'trace' in cmd:
                    temp_file = open(file_name+'_temp','w+')
                    temp_file.write(stdout.read().decode('utf-8'))
                    temp_file.close()
                else:
                    fle.write(stdout.read().decode('utf-8'))

                pat = '[A-Z\/0-9\-\:'+hostname+'\#]+'
                #time.sleep(interval)
                fle.write('\r\n'+tme+'\r\n\n')
                if 'trace' in self.cmd:
                    temp_file = open(file_name +'_temp','r+')
                    print('Opened temp file -> %s' %file_name+'_temp')
                    fle.write(temp_file.read())
                    temp_file.seek(0)
                    lines = temp_file.readlines()
                    last_line = lines[-1]
                    pat = r'[A-Z\/0-9\-\#\:]+'
                    if re.match(pat, last_line):
                        last_line = lines[-2]
                    nxt_tme_lst = last_line.split(' ')[0:4]
                    print('last line is -> %s' %last_line)
                    next_time = ' '.join(nxt_tme_lst)
                    print ( ' Next time = %s for cmd = %s' %(next_time,send_cmd))
                    temp_file.close()
                    os.remove(file_name +'_temp')

                    fle.write('Iteration Count = %i , time = %s'%(cnt,next_time))
                    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

                print('HOSTNAME = %s' %hostname)
                #time.sleep(interval)

                fle.close()
                fle = open(file_name,'a')
                if hostname+'.abort' in os.listdir(log_path):
                    print('.abort file detected ... Exiting')
                    fle.close()
                    conn.close()
                    continue_flag = False
                else:
                    print('======== %s =======' %(log_path+hostname+'.abort'))
                    print('abort file not found ... Continuing ...')
                    cnt += 1
                    time.sleep(int(interval))

if __name__ == "__main__":

    #print('------ test ---- ')
    #print(sys.argv)
    #ip_addr = sys.argv[1]
    #user_name = sys.argv[2]
    #password = sys.argv[3]
    #cmd = sys.argv[4]
    #tftp_addr = sys.argv[5]
    #log_path = sys.argv[6]
    #host_name = sys.argv[7]
    #interval = sys.argv[8]
    #exec_on_stby = False
    #exit()
    warnings.simplefilter("ignore")
    index = 0
    threads =[]
    for cmd in cmd_lst:
        if len(cmd.split('/')) > 1:
            cmd_slsh_join = '_'.join(cmd.split('/'))
            fle_name = '_'.join(cmd_slsh_join.split(' '))
        else:
            fle_name = '_'.join(cmd.split(' '))
        thread = collector(ip_addr = ip_addr, user_name = user_name, password = password, cmd = cmd, thread_name = fle_name, exec_on_stby = exec_on_stby)
        #print(' cmd = %s ' %cmd)
        threads.append(thread)
        index += 1

    index = 0
    for thrd in threads:
        print('thread - %s' %index)
        index += 1
        thrd.start()
        time.sleep(2)
    
