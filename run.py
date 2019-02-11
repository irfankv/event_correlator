from flask import Flask, render_template, url_for, redirect, flash, request, jsonify, session
from functools import wraps
from forms import RegistrationForm, LoginForm
import os
import re
import subprocess
from os.path import join, isfile, isdir
import const
from cec_authentication import LDAPAuth
from macdatabase import MacDatabase
import paramiko
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0a13cefc676d2d3280ba245'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

data = dict()

user_cec = LDAPAuth()

def isValid(file):
	invalidFiles = ['.abort', '_temp', '.DS_Store']
	for f in invalidFiles:
		if f in file:
			return False
	return True

def login_required(f):
	@wraps(f)
	def wrap(*args, **kwargs):
	        if 'user' in session:
	            return f(*args, **kwargs)
	        else:
	            flash("You need to login first.", "info")
	            return redirect(url_for('login'))
	return wrap


def getTFTP_LOC(subfolder=None):
	if subfolder is None:
		return const.TFTP_LOC % (session['user'])
	else:
		return join(const.TFTP_LOC % (session['user']), subfolder)

def mySession(host, username, password):
    conn = paramiko.SSHClient()
    conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    st = conn.connect (host, username=username, password=password, look_for_keys=False)
    #stdin, stdout, stderr = conn.exec_command("show version")
    return conn


@app.route('/home')
@login_required
def home():
	#print(data)
	'''session['user'] = 'pratraut'
	session['interval'] = const.INTERVAL
	session['archive_duration'] = const.ARCHIVE_DURATION		
	session['archive_max_size'] = const.ARCHIVE_MAX_SIZE
	'''		
	return render_template('home.html', data=data)

@app.route('/_loadDevices', methods=['GET', 'POST'])
@login_required
def _loadDevices():
	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)
	print("Loading Devices from", TFTP_LOC)
	if os.path.exists(TFTP_LOC):
		#username = session['user']
		#user_path = join(TFTP_LOC, username)
		devices = [d for d in os.listdir(TFTP_LOC) if isdir(join(TFTP_LOC, d)) and d[0] != '.']
		return jsonify({'devices' : devices})
	else:
		print("%s doesnt exist." % TFTP_LOC)
		devices = {}
		return jsonify({'devices' : devices})

@app.route('/_updateSession', methods=['GET', 'POST'])
@login_required
def _updateSession():
	field = request.args.get('field')
	val = request.args.get('val')
	
	if 'Interval' in field:
		session['interval'] = val
	elif 'Size' in field:
		session['archive_max_size'] = val
	else:
		session['archive_duration'] = val

	return 'OK'

@app.route('/_abortTraces', methods=['GET', 'POST'])
@login_required
def _abortTraces():
	device_name = request.args.get('device_name')
	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)
	file_path = join(TFTP_LOC, device_name, "%s.abort" % device_name)
	file = open(file_path, "w")
	file.close()
	msg = "Trace collection aborted Successfully."
	return jsonify({'message': msg})#url_for('deviceDetails', dname=device_name))

@app.route('/deviceDetails/<dname>')
@login_required
def deviceDetails(dname):
	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)
	device_name = dname #request.args.('device_name')
	
	user_path = join(TFTP_LOC, device_name)
	#print(user_path)
	files = [f for f in os.listdir(user_path) if isfile(join(user_path, f)) and isValid(f)]
	
	data['device'] = device_name
	data['files'] = files
	
	#if request.method == 'POST':
	#	print("CB = ", request.form.getlist('file-cb'))

		
	#print(devices)
	return render_template('deviceDetails.html', data=data)


@app.route('/_startTracing', methods=['GET', 'POST'])
@login_required
def _startTracing():
	device_name = request.args.get('device_name')
	new_cmd = request.args.get('new_cmd')
	username = session['user']

	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)
	file_path = join(TFTP_LOC, device_name, "%s.abort" % device_name)

	if os.path.exists(file_path):
		os.remove(file_path)
	
	TFTP_LOC = join(getTFTP_LOC(const.TRACE_FOLDER), device_name)
	#new_cmd = new_cmd.replace(" ", "_")
	
	#file_path = join(TFTP_LOC, session['user'], device_name, new_cmd)
	#print(user_path)
	#print(device_name)
	#print(new_cmd)

	# actual tracing code
	mac_obj = MacDatabase()
	res = mac_obj.findUserDevice(username = username, device = device_name)
	
	#print("Res = ", res)
	#print("Type = ", type(res))
	if not res:
		flash('Something went wrong', 'error')
		print('something went wrong')
		return None

	cmds = new_cmd.split(",")
	cmdlist = [cmd.strip() for cmd in cmds ]
	for cmd in cmds:
		cmdlist.append(cmd.strip())

	cmd = '/router/bin/python3 /tmp/event_trace_ssh.py %s %s %s "%s" %s %s %s %s' % (res['ip'], res['username'], res['password'], str(cmdlist), const.TFTP_ADDR, TFTP_LOC, device_name, session['interval'])
	print("Executing cmd :", cmd)
	conn = mySession(host="asr9k-dtpxe-lnx", username="root", password="C15c0&!2")
	sftp = conn.open_sftp()
	sftp.put("event_trace_ssh.py", '/tmp/event_trace_ssh.py')
	sftp.close()
	
	stdin, stdout, stderr = conn.exec_command(cmd)

	'''print("STDOUT = ")
	for line in stdout:
		print(line)

	print("STDERR = ")
	for line in stderr:
		print(line)
	
	conn.close()'''
	#print("Executing command - %s" % cmd)
	if stdout:
		print("Command Executed Successfully")

	#redirect(url_for('deviceDetails', dname=device_name))

	new_cmds = []
	for new_cmd in cmdlist:
		u_score = new_cmd.replace(" ", "_")
		new_cmds.append(u_score + "_" + res['ip'].replace(".", "_"))

	start_time = time.time()
	flag = False

	for line in stdout:
		if new_cmds[0] in line:
			flag = True
			break
		if (time.time() - start_time) > 60:
			break

	if not flag:
		new_cmds.clear()

	print("Flag =", flag)
	return jsonify({'device' : device_name, 'file_names' : new_cmds})


@app.route('/_deleteFile', methods=['GET', 'POST'])
@login_required
def _deleteFile():
	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)

	device_name = request.args.get('device_name')
	del_cmd = request.args.get('del_cmd')
	
	file_path = join(TFTP_LOC, device_name, del_cmd)
	print(file_path)
	os.remove(file_path)
	#print(devices)
	return jsonify({'device' : device_name, 'file_name' : del_cmd})


@app.route('/_getDeviceDetails', methods=['GET', 'POST'])
@login_required
def _getDeviceDetails():
	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)
	device_name = request.args.get('device_name')
	username = session['user']
	user_path = join(TFTP_LOC, device_name)
	files = [f for f in os.listdir(user_path) if isfile(join(user_path, f))]
	return jsonify({'device' : device_name, 'files' : files})


def _total_size(source):
	total_size = os.path.getsize(source)
	for item in os.listdir(source):
		itempath = os.path.join(source, item)
		if os.path.isfile(itempath):
			total_size += os.path.getsize(itempath)
		elif os.path.isdir(itempath):
			total_size += _total_size(itempath)
	return total_size

@app.route('/_getRepoUtilization', methods=['GET', 'POST'])
@login_required
def _getRepoUtilization():
	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)

	#user_path = join(TFTP_LOC, session['user'])
	total_size = _total_size(TFTP_LOC)
	total_size = "%.2f" % (total_size / 1024 / 1024)
	print("Size : ", total_size)
	return jsonify({'size' : total_size})

def getFormatedLine(line):
	datepattern = re.compile("\w{3}\s*\d{1,2}\s*\d{2}:\d{2}:\d{2}.\d{3}") 
	timestamp = None
	try:
		matcher = datepattern.search(line)
		#print(matcher.group(0))
		line = line.replace(matcher.group(0), "<div id='timestamp'>" + matcher.group(0) + "</div>")
		line = "<div id='log'>" + line + "</div>"
		timestamp = matcher.group(0)
	except:
		line = "<div id='log-header'>" + line + "</div>"

	return line, timestamp


@app.route('/_getDeviceFile', methods=['GET', 'POST'])
@login_required
def _getDeviceFile():
	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)
	device_name = request.args.get('device_name')
	username = session['user']
	file_name = request.args.get('file_name')

	chunk_number = int(request.args.get('chunk_number'))
	chunk_start = chunk_number * const.CHUNK_SIZE
	chunk_end = (chunk_number + 1) * const.CHUNK_SIZE	
	file_path = join(TFTP_LOC, device_name, file_name)
	content = ""
	with open(file_path, "r") as f:
		for i, line in enumerate(f):
			if i >= chunk_start and i < chunk_end:
				line, timestamp = getFormatedLine(line)
				content += line 
			if i >= chunk_end:
				break
	return jsonify({'file_name' : file_name, 'file_content' : content, 'device_name' : device_name})

def withinOffset(timestamp, second):
	if timestamp is None:
		return False

	sec = int(timestamp[:-4][-2:])

	prev_offset = int(second) - const.SECOND_OFFSET
	next_offset = int(second) + const.SECOND_OFFSET

	if sec >= prev_offset and sec <= next_offset:
		return True
	return False

@app.route('/_searchQuery', methods=['GET'])
@login_required
def _searchQuery():
	device_name = request.args.get('device_name')
	username = session['user']
	file_names = request.args.get('file_names')
	query = request.args.get('query')

	#Update query till min
	second = None
	_, code = getFormatedLine(query)
	if code is not None:
		second = query[:-4][-2:]
		query = query[:-7]

	#print(device_name)
	file_names = eval(file_names, {'__builtins__':None}, {})
	print(file_names)
	#print(query)
	#for file in file_names:
	#	print("FILE = ", file)

	result = {}
	TFTP_LOC = getTFTP_LOC(const.TRACE_FOLDER)

	for file in file_names:
		file_path = join(TFTP_LOC, device_name, file)
		print("PATH = ", file_path)
		cmd = "grep '" + query + "' " + file_path + " > temp_res"
		print("CMD = ", cmd)
		#res = sp.check_output(cmd, shell=True)
		os.system(cmd)
		res = ""
		with open("temp_res", "r") as fp:
			for line in fp:
				line, timestamp = getFormatedLine(line)
				if second is not None:
					if withinOffset(timestamp, second):
						res += line
				else:
					res += line

		result[file] = res
		os.remove("temp_res")
	'''	with open(file_path, "r") as fp:
			for line in fp:
				if query in line:
					result[file] += line
	'''

	return jsonify({'file_names' : file_names, 'device_name' : device_name, 'result': result})

@app.route('/about')
def about():
	return render_template('about.html', title="About")


@app.route("/logout")
@login_required
def logout():
	#if(session.pop(session['user'], None)):
	session.clear()
	flash("Logged out", 'success')

	return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@app.route("/login", methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		authentic = user_cec.auth(form.cec_username.data,form.password.data)
		if authentic: 
			
			session['user'] = form.cec_username.data
			session['interval'] = const.INTERVAL
			session['archive_duration'] = const.ARCHIVE_DURATION		
			session['archive_max_size'] = const.ARCHIVE_MAX_SIZE
			#print("session user")
			#print(session['user'])
			#print("loggedin_user is:")
			#print(loggedin_user)
			
			flash('You have been logged in!', 'success')
			return redirect(url_for('home'))
		else:
			flash('Login Unsuccessful. Please check username and password', 'danger')
	return render_template('login.html', title='Login', form=form)


@app.route('/register', methods=['POST', 'GET'])
@login_required
def register():
	#mac_obj = MacDatabase()
	#x = mac_obj.count_collec()
	#print(x)

	#print("in register")
	form = RegistrationForm()
	if form.validate_on_submit():
		machine_ip = request.form.get('machine_ip')
		device_name = request.form.get('device_name')
		device_username = request.form.get('device_username')
		device_password = request.form.get('device_password')
		device_details = request.form.get('device_details') 
		user = session['user']

		print("[%s, %s, %s, %s, %s]"%( request.form.get('machine_ip'), request.form.get('device_name'), 
			request.form.get('device_username'), request.form.get('device_password'), request.form.get('device_details') ))
		mac_obj = MacDatabase()
		insert_mac = mac_obj.insert(user, machine_ip, device_name, device_username, device_password, device_details)
		#print(insert_mac)
		#print(type(insert_mac))
		#mac_rec = mac_obj.findmac(device_name)
		#print(mac_rec)
		#print(type(mac_rec))
		'''if mac_rec is not False:
			print("in not false")
			mac_data = []
			for record in mac_rec:
				print("in records")
				user = record["user"]
				ip = record["ip"]
				device_name = record["device_name"]
				rec_uname = record["username"]
				rec_pass = record["password"]

				print("printing manually")
				print(ip)
				print(user)
				print(device_name)
				print(rec_uname)
				print(rec_pass)

				mac_data.append((user, ip, device_name, rec_uname, rec_pass))
				print(mac_data)
		'''
		TFTP_LOC = join(getTFTP_LOC(const.TRACE_FOLDER), request.form.get('device_name'))
		
		if not os.path.exists(TFTP_LOC):
			#print("in not exists")
			#path = join(getTFTP_LOC(const.TRACE_FOLDER), request.form.get('device_name'))
			#print(path)
			os.makedirs(TFTP_LOC)

			parent_path = getTFTP_LOC()
			command = "chmod -R 777"+" "+parent_path
			#print(command)
			cmmd = os.popen(command)
					
			if(cmmd and insert_mac):
				#print("in cmd")
				flash(f'Device Registered Successfully.', 'success') 
			else:
				print("no")
		
		return redirect(url_for('home'))
	return render_template('register.html', title="Registration", form=form, data=data)


if __name__ == '__main__':
	#app.run(debug=True, port=5005)
	app.run(host='0.0.0.0', debug=False, port=5005)

