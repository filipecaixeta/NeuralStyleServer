import os,json,glob,time
from flask import Flask,render_template,Response,request
from PIL import Image, ImageOps
from threading import Thread,Lock
from subprocess import Popen, PIPE
import signal
import shutil

NEURAL_STYLE_PATH = "../neural-style/"

def listDir(path):
	files = glob.glob('static/'+path+'/*')
	files.sort(key=os.path.getmtime)
	files = [os.path.basename(f) for f in files]
	return files[::-1]

def createThumb(path,file,size=(256,256)):
	image = Image.open(path+file)
	thumb = ImageOps.fit(image, size, Image.ANTIALIAS)
	thumb.save(path+'thumbnail/'+file)

def getFileName(file):
	file = os.path.basename(file).replace('.','-')
	return file

def createResultsDir(content,style):
	path = "static/results/"
	dirName = getFileName(content) + "_" + getFileName(style) + "_"
	dirName += hex(int((time.time()*10000000)))[2:]
	if not os.path.exists(path+dirName):
		os.makedirs(path+dirName)
	return path,dirName


app = Flask(__name__,static_folder='static')

@app.route("/")
def index():
	return render_template("index.html")

@app.route('/submissions.json')
def submissions():
	folders = listDir("results")
	js = json.dumps(folders)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@app.route('/images/<path:folder>', methods = ['GET'])
def api_images(folder):
	pictures = listDir(folder)
	js = json.dumps(pictures)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@app.route('/status.json')
def status():
	js = json.dumps(pq.getAll())
	resp = Response(js, status=200, mimetype='application/json')
	return resp

@app.route('/remove/', methods=['POST'])
def removeProcess():
	pid = request.form.get('pid')
	pq.removeProcess(pid)
	if os.path.exists("static/results/"+pid):
		shutil.rmtree("static/results/"+pid)
	return 'stopped'

@app.route('/uploadfile/<path:folder>', methods=['POST'])
def upload_file(folder):
	# check if the post request has the file part
	if 'file' not in request.files or request.files['file'].filename=='':
		return 'lol',200
	file = request.files['file']
	if file:
		path = "static/%s/"%(folder)
		filename = hex(int((time.time()*10000000)))[2:] + '.'
		filename = filename + file.filename.split(".")[-1]

		file.save(path+filename)
		createThumb(path,filename)
		
		pictures = listDir(folder+'/thumbnail')
		js = json.dumps(pictures)
		resp = Response(js, status=200, mimetype='application/json')
		return resp

@app.route('/processimages/', methods=['POST'])
def processimages():
	content_img = request.form.get('content_img')
	style_img = request.form.get('style_img')
	args = request.form.get('args')
	output = hex(int((time.time()*10000000)))[2:] + '.jpg'

	outputDirPath,dirName = createResultsDir(content_img,style_img)

	command = "bash th "
	command = command + NEURAL_STYLE_PATH + "neural_style.lua"
	command = command + " -style_image %s -content_image %s -gpu -1"%(style_img,content_img)
	# command = command + " --content_img_dir ./ --style_imgs_dir ./ --device /cpu:0"
	# command += " -proto_file "+NEURAL_STYLE_PATH+"models/train_val.prototxt -output_image teste.jpg"
	command += " -output_image %s/img.png "%(outputDirPath+dirName)
	command += args
	pq.addProcess(dirName,command)
	return str(pq.q.getAll()),200

class Queue():
	def __init__(self):
		self.lock = Lock()
		self.q = []
		self.data = {}
		self.current = []

	def get(self):
		self.lock.acquire()
		try:
			elem = None
			if len(self.q)!=0:
				id = self.q[0]
				self.q = self.q[1:]
				elem = self.data.get(id,None)
				self.current = [id,elem]
			else:
				self.lock.release()
				return
		except Exception as e:
			pass
		finally:
			self.lock.release()
			return elem

	def put(self,id,data):
		self.lock.acquire()
		try:
			self.data[id] = data
			self.q.append(id)
		except Exception as e:
			pass
		finally:
			self.lock.release()
			return id

	def getAll(self):
		self.lock.acquire()
		try:
			data = [[id,self.data.get(id,None)] for id in self.q]
		except Exception as e:
			pass
		finally:
			self.lock.release()
			return self.current,data

	def isEmpty(self):
		return len(self.q)==0

	def remove(self,id):
		try:
			self.q.remove(id)
			del(self.data[id])
		except Exception as e:
			pass

Saida = ""

pProcess=None

lockPopen = Lock()

def f(q):
	while not q.isEmpty():
		global pProcess
		lockPopen.acquire()
		d = q.get()
		print(d.split(' '))
		pProcess = Popen(d.split(' '), stdout=PIPE)
		lockPopen.release()
		pProcess.wait()
		q.current=[]


class ProcessQueue():
	def __init__(self):
		self.q = Queue()
		self.worker = Thread(target=f, args=(self.q,))
		self.worker.start()

	def addProcess(self,id,data):
		self.q.put(id,data)
		if not self.worker.is_alive():
			self.worker = Thread(target=f, args=(self.q,))
			self.worker.start()

	def isProcessing(self):
		self.worker.is_alive()

	def getAll(self):
		current,q=self.q.getAll()
		return {'queue':q,'current':current,'status':'running' if self.worker.is_alive()==True else 'stopped'}

	def stopCurrent(self):
		global pProcess
		pProcess.terminate()

	def removeProcess(self,id):
		lockPopen.acquire()
		try:
			if self.q.current[0]==id:
				global pProcess
				pProcess.terminate()
			else:
				self.q.remove(id)
		except Exception as e:
			pass
		finally:
			lockPopen.release()


pq = ProcessQueue();

# python Documents\neural-style-server\main.py
