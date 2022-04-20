from flask import Flask, render_template, request, jsonify, send_from_directory

from flask_mongoengine import MongoEngine
import json
from flask_uploads import configure_uploads, IMAGES, UploadSet, AUDIO, ALL
from scripts.classify_birds import classify
from scripts.email_service import send_email
from sys import modules
from os.path import basename, splitext

import subprocess
import uuid
import os
import cv2
from redis import Redis
from rq import Queue





host= os.getenv('HOST', "localhost")
pwd = os.getenv('Mail_PWD', "ABC")



app = Flask(__name__)
redis = Redis(host='redis', port=6379)
q = Queue(connection=redis)
app.config['SECRET_KEY'] = 'thisisasecret'
app.config['JSON_SORT_KEYS'] = False
app.config['UPLOADED_IMAGES_DEST'] = 'uploads/images'
app.config['UPLOADED_AUDIOS_DEST'] = 'uploads/audios'
app.config['UPLOADED_VIDEOS_DEST'] = 'uploads/videos'
app.config['MONGODB_SETTINGS'] = {
    'db': 'your_database',
    'host': 'mongodb',
    'port': 27017
}
db = MongoEngine()
db.init_app(app)

images = UploadSet('images', IMAGES)


audios = UploadSet('audios', AUDIO)
videos = UploadSet('videos', ALL)
configure_uploads(app, (images, audios, videos))




class Location(db.EmbeddedDocument):
    lat = db.FloatField()
    lon = db.FloatField()

class Environment(db.DynamicEmbeddedDocument):
    env_id = db.StringField()
    date = db.StringField()
    


class Movements(db.DynamicEmbeddedDocument):
    mov_id = db.StringField()
    start_date =db.StringField()
    end_date = db.StringField()
    audio= db.StringField()
    video = db.StringField()
    environment = db.EmbeddedDocumentField(Environment)

class Measurement(db.EmbeddedDocument):
    environment = db.ListField(db.EmbeddedDocumentField(Environment))
    movements = db.ListField(db.EmbeddedDocumentField(Movements))

class Mail(db.DynamicEmbeddedDocument):
    adresses = db.ListField(db.StringField())
    
class Box(db.DynamicDocument):
    box_id = db.StringField()
    name = db.StringField()
    location = db.EmbeddedDocumentField(Location)
    measurements = db.EmbeddedDocumentField(Measurement)
    mail = db.EmbeddedDocumentField(Mail)

def enqueueable(func):
    if func.__module__ == "__main__":
        func.__module__, _ = splitext(basename(modules["__main__"].__file__))
    return func

@enqueueable

# Create a working task queue  
def videoAnalysis(filename, movement_id, box_id):
    if  os.path.splitext(filename)[1] == ".h264":
        command = "MP4Box -add {} {}.mp4".format("./uploads/videos/" + filename, "./uploads/videos/" + os.path.splitext(filename)[0])
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
            filename = os.path.splitext(filename)[0] +".mp4"
        except subprocess.CalledProcessError as e:
            print('FAIL:\ncmd:{}\noutput:{}'.format(e.cmd, e.output))

    cap = cv2.VideoCapture('uploads/videos/' + filename)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(total_frames)
    result=[]
    images = 0
    for fno in range(0, total_frames, 20):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fno)
        _, image = cap.read()
        images +=1
        result.append(classify(image))
        # read next frame
    output = {}
    for i in range(len(result)): 
        for key in result[i]:
            if key in output:
                output[key]+=result[i][key]
            else:
                output[key]=result[i][key]
    print(output)
    output2 = {k: v / images for k, v in output.items()}
    marklist = sorted(output2.items(), key=lambda x:x[1], reverse=True)
    birds = dict(marklist)
    print(birds)

    box = Box.objects(box_id=box_id).first_or_404()

    movements= box.measurements.movements

    for i, movement in enumerate(movements):
        if movement.mov_id == movement_id:
            movements[i].detections = birds
            movements[i].video = filename

    box.measurements.movements= movements

    box.update(measurements= box.measurements)

    for mail in box.mail.adresses:
        try:
            send_email(mail, filename, 'uploads/videos/' + filename, birds, pwd )
        except:
            print("mail to " + mail + " failed")  
 
 
    return birds

@app.route('/')
def index():
    return render_template('./index.html') 



@app.route('/api/image', methods=['Get', 'POST'])
def image():
    if request.method=="POST":
        data = request.files['image']
        print (data)
        filename = images.save(data)
        result = classify('uploads/images/' + filename)

        return jsonify(
            result=result
    )
    return render_template('./index.html')

@app.route('/api/video', methods=['Get', 'POST'])
def video():
    if request.method=="POST":
        data = request.files['video']
        print (data, flush=True)
        filename = videos.save(data)
        command = "MP4Box -add {} {}.mp4".format("./uploads/videos/" + filename, "./uploads/videos/" + os.path.splitext(filename)[0])
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
             print('FAIL:\ncmd:{}\noutput:{}'.format(e.cmd, e.output))
        cap = cv2.VideoCapture('uploads/videos/' + os.path.splitext(filename)[0] +".mp4")
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(total_frames)
        result=[]
        images = 0
        for fno in range(0, total_frames, 20):
            cap.set(cv2.CAP_PROP_POS_FRAMES, fno)
            _, image = cap.read()
            images +=1
            result.append(classify(image))
	        # read next frame
        output = {}
        for i in range(len(result)): 
            for key in result[i]:
                if key in output:
                    output[key]+=result[i][key]
                else:
                    output[key]=result[i][key]
        print(output)
        output2 = {k: v / images for k, v in output.items()}
        marklist = sorted(output2.items(), key=lambda x:x[1], reverse=True)
        birds = dict(marklist)
        print(birds)
                
        return jsonify(
            result= birds
        )
    return render_template('./index.html')

@app.route('/api/audio', methods=['POST'])
def audio():
    if request.method=="POST":
        # this line goes to the console/terminal in flask dev server
        data = request.files['audio']
        print (data)
        # this line prints out the form to the browser
        #return jsonify(data)
        filename = audios.save(data)
        return filename
    return render_template('./index.html')

@app.route('/api/box', methods=['GET', 'POST'])
def add_box():
    if request.method=="POST":
        body = request.get_json()
        location = Location()
        location.lat = body['location']['lat']
        location.lon = body['location']['lon']
        measurement= Measurement()
        mail = Mail()
        list= mail.adresses
        for mailToInsert in body['mail']['adresses']:
            print(mailToInsert)
            list.append(mailToInsert)
        mail.adresses = list
        id = str(uuid.uuid4())
        #senseboxid = ""
        #if(body['senseboxID']):
        #    senseboxid = body['senseboxID']
        #else: 
        #    senseboxid

        print(mail)
        # Add object to movie and save
        box = Box(box_id = id, location=location, name=body['name'], measurements = measurement, mail=mail).save()
        return {"id": id}, 201
    boxes = Box.objects.only('box_id', "location", "name" ).exclude('_id')
    return  jsonify(boxes), 200

@app.route('/api/box/<box_id>', methods=['GET'])
def get_one_box(box_id: str):
    box = Box.objects(box_id=box_id).first_or_404()
    return jsonify(box), 200

@app.route('/api/environment/<box_id>', methods=['POST'])
def add_environment(box_id: str):
    content_type = request.headers.get('Content-Type')
    print(content_type, flush=True)
    
    box = Box.objects(box_id=box_id).first_or_404()

    body = request.get_json()
    print(body, flush=True)

    environmentClass = Environment()
    for name,value in body.items():
        setattr(environmentClass, name, value)
    env_id = str(uuid.uuid4())
    environmentClass.env_id = env_id

    environmentList = box.measurements.environment
    environmentList.insert(0, environmentClass)
    box.measurements.environment = environmentList
    box.update(measurements = box.measurements)

#TODO send E-Mail

    return jsonify(id = env_id), 200

@app.route('/api/movement/<box_id>', methods=['POST'])
def add_movement(box_id: str):
    content_type = request.headers.get('Content-Type')
    print(content_type, flush=True)
    box = Box.objects(box_id=box_id).first_or_404()


    ##TODO: Count Birds in image and Crop images to bird onyl 
    
    

    body = request.form['json']
    body = json.loads(body)
    print(body.items(), flush=True)



    movementsClass = Movements()
    mov_id = str(uuid.uuid4())
    movementsClass.mov_id = mov_id
    movementsClass.start_date = body['start_date']
    movementsClass.end_date = body['end_date']
    audio = request.files[body['audio']]
    filename = audios.save(audio)
    movementsClass.audio = str(host)+ "/api/uploads/audios/" + filename
    video = request.files[body['video']]
    filename = videos.save(video)
    movementsClass.video = "pending"
    

    environmentClass = Environment()
    for name,value in body['environment'].items():
        setattr(environmentClass, name, value)
    env_id = str(uuid.uuid4())
    environmentClass.env_id = env_id

    movementsClass.environment = environmentClass

    movementsClass.detections = {}

    
    movementList = box.measurements.movements
    movementList.insert(0, movementsClass)
    box.measurements.movements = movementList
    box.update(measurements = box.measurements)
    job= q.enqueue(videoAnalysis, filename, mov_id, box_id)  
    #print(movementList)

    return jsonify(id = mov_id), 200

@app.route('/api/uploads/images/<filename>')
def getImages(filename):
    return send_from_directory(app.config['UPLOADED_IMAGES_DEST'], filename)

@app.route('/api/uploads/audios/<filename>')
def getAudios(filename):
    return send_from_directory(app.config['UPLOADED_AUDIOS_DEST'], filename)

@app.route('/api/uploads/videos/<filename>')
def getVideos(filename):
    return send_from_directory(app.config['UPLOADED_VIDEOS_DEST'], filename)

#@app.route('/api')
#def api():
#    return render_template('./redoc/redoc.html')


if __name__==('__main__'):
    app.run(host="0.0.0.0", debug=False)