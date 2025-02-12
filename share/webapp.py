import argparse
import io
from PIL import Image
import datetime

import torch
import cv2
import numpy as np
import tensorflow as tf
from re import DEBUG, sub
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    send_file,
    url_for,
    Response,
)
from werkzeug.utils import secure_filename, send_from_directory
import os
import subprocess
from subprocess import Popen
import re
import requests
import shutil
import time
import glob

import os
import platform
import cv2
import threading
from alert import *
from ultralytics import YOLO

 
def clear_terminal():
    
    if platform.system() == "Windows":
        os.system("cls")  
    else:
        os.system("clear") 

music_file_path = "beep.mp3"

from ultralytics import YOLO

app = Flask(__name__)

@app.route("/")
def hello_world():
   
    if "image_path" in request.args:
        image_path = request.args["image_path"]
        return render_template("index.html", image_path=image_path)
    return render_template("index.html")

@app.route("/", methods=["GET", "POST"])
def predict_img():
    if request.method == "POST":
        if 'file' in request.files:
            f = request.files['file']
            basepath = os.path.dirname(__file__)
            filepath = os.path.join(basepath, 'uploads', f.filename)
            print("upload folder is ", filepath)
            f.save(filepath)
            predict_img.imgpath = f.filename
            print("printing predict_img :::::: ", predict_img)

            file_extension = f.filename.rsplit('.', 1)[1].lower()

            if file_extension == 'jpg':
               
                img = cv2.imread(filepath)

               
                model = YOLO('yolov8n.pt')
                detections = model(img, save=True)

                # Find the latest subdirectory in the 'runs/detect' folder
                folder_path = os.path.join(basepath, 'runs', 'detect')
                subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
                latest_subfolder = max(subfolders, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))

                # Construct the relative path to the detected image file
                static_folder = os.path.join(basepath, 'static', 'assets')
                relative_image_path = os.path.relpath(os.path.join(folder_path, latest_subfolder, f.filename), static_folder)
                image_path = os.path.join(folder_path, latest_subfolder, f.filename)
                print("Relative image path:", relative_image_path)  # Print the relative_image_path for debugging
                
                return render_template('index.html', image_path=relative_image_path, media_type='image')

            elif file_extension == "mp4":
                # Handle video upload
                video_path = filepath  # replace with your video path
                cap = cv2.VideoCapture(video_path)

                # get video dimensions
                frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Define the codec and create VideoWriter object
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(
                    "output.mp4", fourcc, 30.0, (frame_width, frame_height)
                )

                # initialize the YOLOv8 model here
                model = YOLO("yolov8n.pt")

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # do YOLOv9 detection on the frame here
                   
                    results = model(frame, save=True)  # working
                    print(results)
                    cv2.waitKey(1)

                    res_plotted = results[0].plot()
                    cv2.imshow("result", res_plotted)

                    # write the frame to the output video
                    out.write(res_plotted)

                    if cv2.waitKey(1) == ord("q"):
                        break

                return render_template('index.html', video_path='output.mp4', media_type='video')

    # If no file uploaded or GET request, return the template with default values
    return render_template("index.html", image_path="", media_type='image')


@app.route("/<path:filename>")
def display(filename):
    folder_path = "runs/detect"
    subfolders = [
        f
        for f in os.listdir(folder_path)
        if os.path.isdir(os.path.join(folder_path, f))
    ]
    latest_subfolder = max(
        subfolders, key=lambda x: os.path.getctime(os.path.join(folder_path, x))
    )
    directory = os.path.join(folder_path, latest_subfolder)
    print("printing directory: ", directory)
    files = os.listdir(directory)
    latest_file = files[0]

    print(latest_file)

    image_path = os.path.join(directory, latest_file)

    file_extension = latest_file.rsplit(".", 1)[1].lower()

    if file_extension == "jpg":
        return send_file(image_path, mimetype="image/jpeg")
    elif file_extension == "mp4":
        return send_file(image_path, mimetype="video/mp4")
    else:
        return "Invalid file format"

def get_frame():
    folder_path = os.getcwd()
    mp4_files = "output.mp4"
    print("files being read...")
    video = cv2.VideoCapture(mp4_files)  # detected video path
    while True:
        success, frame = video.read()
        if not success:
            print("file not being read")
            break
        else:
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n"
        )
        time.sleep(0.1)  # Control the frame rate to display one frame every 100 milliseconds:


# function to display the detected objects video on html page
@app.route("/video_feed")
def video_feed():
   
    return Response(get_frame(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/webcam_feed")
def webcam_feed():
    cap = cv2.VideoCapture(0)  # Open the webcam feed (0 for default camera)

    def generate():
        model = YOLO("yolov8n.pt")  

        while True:
            success, frame = cap.read()
            if not success:
                break

            clear_terminal()
            
            results = model(frame)

            cow_detected = False

           
            for detection in results[0].boxes:
                if int(detection.cls) == 19:  
                    
                    x1, y1, x2, y2 = map(int, detection.xyxy[0])  
                    confidence = float(detection.conf[0]) * 100

                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2) 
                    cv2.putText(
                        frame,
                        f"Cow: {confidence:.2f}%",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2,
                    )
                    cow_detected = True
            if cow_detected:
                threading.Thread(target=play_music, args=(music_file_path,)).start()        

           
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()

            yield (
                b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n"
            )

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flask app exposing yolov8 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    model = YOLO("yolov8n.pt")
    app.run(host="0.0.0.0", port=args.port, debug=True)