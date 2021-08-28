#!/usr/bin/env python
# coding: utf-8

# In[3]:




from flask import Flask,redirect,url_for,render_template,request

import os
import shutil

import tensorflow as tf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pycontractions import Contractions
import re
import scipy.stats as st
from get_top_intent import top_intent
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

tf.get_logger().setLevel('ERROR')



saved_model_path = 'model/checkpoint_4'
model = tf.saved_model.load(saved_model_path)
contraction=Contractions(api_key="glove-twitter-100")




api_key= # enter your api key here
client_secrets_file = # enter client secret file name (.json file)
youtube=build('youtube','v3',developerKey=api_key)
scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
credentials = flow.run_local_server(port=8080,prompt="consent")

api_service_name = "youtube"
api_version = "v3"
youtube_comment = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)




# Code for flask application
app=Flask(__name__)
cached_prediction={}

@app.route("/",methods=["POST","GET"])
def get_user_request():

    if request.method== "POST":

        url=request.form['url']
        videoId=url.split("v=")[1]
        user_intent=request.form['intent'].lower()
        K=request.form["K"]
        key_phrase=request.form["keyPhrase"]
        filter_words=request.form["filter"]
        
        if(user_intent=="criticism/others"):
            user_intent='misc'
        elif(user_intent=="idea/suggestion/advice"):
            user_intent="suggestion"
        elif(user_intent=="request/asking"):
            user_intent="request"
        
        intent=top_intent(url,user_intent,model,contraction,key_phrase,filter_words=filter_words,k=K)
        
        global intent_result
        
        
        if not videoId in cached_prediction:
            pred_df=intent.prediction()
            cached_prediction[videoId]=pred_df
            intent_result=intent.top_intent(pred_df)
        else:
            
            intent_result=intent.top_intent(cached_prediction[videoId])
            
        intent_result=intent_result.loc[:,['comments','commentId']].values
    
        return redirect(url_for("intent_results"))
    else:
        return render_template("youtube_input.html")

@app.route("/top_intent.html",methods=["POST","GET"])
def intent_results():
    if request.method=="POST":
        global commentId
        commentId=dict(request.form)
        commentId=list(commentId.keys())[0]
        print(commentId)
        return redirect(url_for("reply"))
    else:
        return render_template("top_intent.html",intent=intent_result)


@app.route("/reply",methods=["POST","GET"])
def reply():
   
    if request.method=="POST":
        reply_text=request.form["replyText"]
        youtube_request = youtube_comment.comments().insert(
        part="snippet",
        body={
          "snippet": {
            "parentId": f"{commentId}",
            "textOriginal": f"{reply_text}"
          }
        }
    )
        response = youtube_request.execute()
        return redirect(url_for("intent_results"))
        
    else:
        return render_template("reply.html")

if __name__=="__main__":
    app.run(debug=False)
    






