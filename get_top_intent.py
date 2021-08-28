import pandas as pd
import numpy as np

import slang
import re
from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize
from collections import Counter
import random
from itertools import islice
import pickle
import spacy
from Contraction import contraction_lookup
from googleapiclient.discovery import build
import tensorflow as tf
import tensorflow_hub as hub
import tensorflow_text as text
from tensorflow import keras
import scipy.stats as st
from collections import defaultdict

nlp = spacy.load("en_core_web_sm")

class top_intent():
    def __init__(self,url,intent,model,contraction,key_phrase,filter_words=None,k=5):
        
        self.api_key=# enter your api key here
        self.youtube=build('youtube','v3',developerKey=self.api_key)
        self.cont = contraction

        self.slang_lookup={f" {k.lower()} ":f" {v.lower()} " for k,v in slang.slang_lookup.items()}
        self.contraction_lookup={f"{k.lower()}":f" {v.lower()} " for k,v in contraction_lookup.items()}


        self.slang_lookup["\n"]=" "
        del self.slang_lookup[" \n "]
      
        self.url=url
        self.key_phrase=key_phrase.split(",")
        if filter_words:
            self.filter_words=filter_words.lower()
            self.filter_words=filter_words.split(",")
        else:
            self.filter_words=None
            
        self.class_dict={0:"misc",1:"praise",2:"question",3:"request",4:"suggestion"}
        self.model=model
        with open('stop_words.pickle', 'rb') as handle:
            self.stopwords = pickle.load(handle)
        self.intent=intent
        self.k=k
    def take(self,n, iterable):
        "Return first n items of the iterable as a list"
        return list(islice(iterable, n))
    
    def add_space(self,x):
        x=x.split(" ")
        x="".join(list(map(lambda x:f" {x} ",x)))
        return x
    def remove_repeat_words(self,x):
        sent=" ".join(list(set(x.split(" "))))
        return sent
    
    def remove_stopwords(self,x):
        tokens=x.split(" ")
        filtered=[w for w in tokens if not w in self.stopwords]
    
        return " ".join(filtered)
    
    def extract_noun(self,x):
        nouns=[]    
        doc = nlp(x)
        for np in doc.noun_chunks:
            noun=np.text.split(" ")
            filtered=[w for w in noun if not w in self.stopwords]
            filtered=[w for w in filtered if w]
            filtered="_".join(filtered)
            
            nouns.append(filtered)
        return " ".join(nouns)
    
    def return_counts(self,x,word_count,p):
        match=p.findall(x)
        max_count=-1
        for m in match:
            count=word_count[m]
            if(count>max_count):
                max_count=count
        return max_count
    
    def plural_to_singular(self,x,wordcount):
        word=x
        singular=TextBlob(word).words.singularize()[0]
        if((singular!=word) and (singular in wordcount)):
            return None
        else:
            return singular
        
    def mark_top_words(self,x,word_counts):
        word_list=x.split(" ")
        sent=[]
        for w in word_list:
            if w in word_counts:
                word=f"< {w} >"
            else:
                word=w
            sent.append(word)
        return " ".join(sent)
    def text_preprocess_top_intent(self,df):
    
        df.loc[:,'comments_cleaned']=df['comments'].apply(lambda x:x.lower())
        df.loc[:,'comments_cleaned']=df['comments_cleaned'].apply(self.add_space)
        df.loc[:,'comments_cleaned']=df.comments_cleaned.replace(self.slang_lookup,regex=True)
        df.loc[:,'comments_cleaned']=df['comments_cleaned'].apply(lambda x:x.strip())
        df.loc[:,'comments_cleaned']=df.comments_cleaned.replace(self.contraction_lookup,regex=True)
        df.loc[:,"comments_cleaned"]=df.comments_cleaned.apply(lambda x:list(self.cont.expand_texts([x], precise=True))[0])

        df.loc[:,'comments_cleaned']=df['comments_cleaned'].apply(lambda x:re.sub('plz+'," please ",x))
        df.loc[:,'comments_cleaned']=df['comments_cleaned'].apply(lambda x:re.sub('pls+'," please ",x))

        url_pattern="http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|www.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

        df.loc[:,'comments_cleaned']=df['comments_cleaned'].apply(lambda x:re.sub(url_pattern," ",x))
        df.loc[:,'comments_cleaned']=df['comments_cleaned'].apply(lambda x:re.sub("[^a-zA-Z]"," ",x))

        return df
    
    def top_k(self,df):
        
        intent_df=df[df['preds']==self.intent]
        intent_df=self.text_preprocess_top_intent(intent_df)
        
  
        intent_df.loc[:,"comments_cleaned"]=intent_df.comments_cleaned.apply(self.remove_stopwords)
        intent_df.loc[:,"comments_cleaned"]=intent_df.comments_cleaned.apply(self.remove_repeat_words)
       
           
        list_words=intent_df.comments_cleaned.apply(lambda x:x.split(" ")).tolist()
        list_words=[item for i in list_words for item in i if item]
        
        wordcount=dict(Counter(list_words))
        wordcount={k:v for k,v in wordcount.items() if list(nlp(k).noun_chunks)}
        wordcount={k:v for k,v in wordcount.items() if self.plural_to_singular(k,wordcount)}
        wordcount={k:v for k,v in wordcount.items() if not k in self.key_phrase}
        wordcount={k:v for k,v in wordcount.items() if not k.lower() in self.stopwords}
     
        wordcount=dict(sorted(wordcount.items(), key=lambda item: item[1],reverse=True))
       
        countwords = defaultdict(list)

        for key, value in sorted(wordcount.items()):
            countwords[value].append(key)
        countwords=dict(sorted(countwords.items(), key=lambda item: item[0],reverse=True))
        print(countwords)
        if(len(countwords)==1):
            top_k_words=list(countwords.values())
        else:
            n=0
            top_k_words=[]
            for k,v in countwords.items():

                if(k>1):
                    top_k_words.append(v)
                elif(k==1):
                    rem_no=int(self.k)-n
                    one_word=[w for i,w in enumerate(v) if i<=rem_no]
                    top_k_words.append(one_word)
                    break
                elif(n>int(self.k)):
                    break
                n+=1
        top_k_words=[item for i in top_k_words for item in i]   

        pattern="|".join(list(map(lambda x:f"\\b{x}\\b",top_k_words)))
        p = re.compile(pattern)
        top_k_sents=intent_df[intent_df.comments_cleaned.apply(lambda x:True if p.findall(x) else False)]
        top_k_sents["word_counts"]=top_k_sents.comments_cleaned.apply(self.return_counts,args=(wordcount,p,))
        top_k_sents=top_k_sents.sort_values(by="word_counts",ascending=False)
        top_k_sents.loc["comments"]=top_k_sents.comments.apply(self.mark_top_words,args=(wordcount,))
        return top_k_sents
    
    def extract_comments(self):

        nextpage=[]
        comments=[]
        commentId=[]
        videoId=self.url.split("v=")[1]
        request2= self.youtube.commentThreads().list(
                    part="snippet",
                    videoId=videoId,
                    maxResults=100).execute()
        nextpageToken=request2.get("nextPageToken",None)
        stop_at=0
        while stop_at<=30:

            len_items=len(request2['items'])
            for i in range(1,len_items):
                comment_id=request2['items'][i]['id']
                comment=request2['items'][i]['snippet']['topLevelComment']['snippet']['textOriginal']
                comments.append(comment)
                commentId.append(comment_id)
            nextpageToken=request2.get("nextPageToken",None)
            if not nextpageToken:
                break
            request2 = self.youtube.commentThreads().list(
                    part="snippet",
                    videoId=videoId,
                    maxResults=100,
                    pageToken=f'{nextpageToken}').execute()
            stop_at+=1
        df=pd.DataFrame(data={"comments":comments,"commentId":commentId})
        df['comments']=df['comments'].apply(lambda x:x.strip())
        df['comments']=df['comments'].apply(lambda x:x if len(x.split())>2 else np.nan)
        df.dropna(axis=0,inplace=True)
        df.drop_duplicates(inplace=True)
        df.reset_index(inplace=True,drop=True)
       
        return df
    
    def text_preprocess(self,text):
    
        df=pd.DataFrame(data={"comments":text},index=[0])
        df.loc[:,'comments']=df['comments'].apply(lambda x:x.replace("’","'"))
        df.loc[:,'comments']=df['comments'].apply(lambda x:x.replace("‘","'"))
        df.loc[:,'comments']=df.comments.apply(lambda x:x.replace("“",'"'))
        df.loc[:,'comments']=df.comments.apply(lambda x:x.replace("”",'"'))

        df.loc[:,'comments']=df['comments'].apply(lambda x:x.lower())
        df.loc[:,'comments']=df['comments'].apply(self.add_space)
        df.loc[:,'comments']=df.comments.replace(self.slang_lookup,regex=True)
        df.loc[:,'comments']=df['comments'].apply(lambda x:x.strip())
        df.loc[:,'comments']=df.comments.replace(self.contraction_lookup,regex=True)
        df.loc[:,"comments"]=df.comments.apply(lambda x:list(self.cont.expand_texts([x], precise=True))[0])

        df.loc[:,'comments']=df['comments'].apply(lambda x:re.sub('plz+'," please ",x))
        df.loc[:,'comments']=df['comments'].apply(lambda x:re.sub('pls+'," please ",x))

        df.loc[:,'comments']=df['comments'].apply(lambda x:re.sub("[^a-zA-Z0-9?!,.:\"']"," ",x))

        df.loc[:,'comments']=df.comments.apply(lambda x:x.replace("?"," ? "))
        df.loc[:,'comments']=df.comments.apply(lambda x:x.replace("!"," ! "))
        df.loc[:,'comments']=df.comments.apply(lambda x:x.replace(","," , "))
        df.loc[:,'comments']=df.comments.apply(lambda x:x.replace("."," . "))
        df.loc[:,'comments']=df.comments.apply(lambda x:x.replace(":"," : "))
        df.loc[:,'comments']=df.comments.apply(lambda x:x.replace('"',' " '))


        test_sample=df.comments.values.tolist()

        pred = tf.nn.softmax(self.model(tf.constant(test_sample)))

        pred=tf.argmax(pred,axis=1).numpy().tolist()

        pred=self.class_dict[pred[0]]
        return pred
    
    
    
    def prediction(self):
        df=self.extract_comments()
        df['preds']=df.comments.apply(self.text_preprocess)
        return df
    
    def top_intent(self,prediction_df):
        if self.filter_words:
          
            intent_df=prediction_df[prediction_df['preds']==self.intent]
          
            intent_df.loc[:,"comments_lower"]=intent_df.comments.apply(lambda x:x.lower())
            pattern_filter="|".join(list(map(lambda x:f"\\b{x}\\b",self.filter_words)))
            p_filter = re.compile(pattern_filter)
            filtered_intents=intent_df[intent_df.comments_lower.apply(lambda x:True if p_filter.findall(x) else False)]
           
            filtered_intents.drop_duplicates(inplace=True)
            filtered_intents.reset_index(inplace=True,drop=True)
            return filtered_intents
        else:
            top_intents=self.top_k(prediction_df)
            top_intents.drop_duplicates(inplace=True)
            top_intents.reset_index(inplace=True,drop=True)
            return top_intents


