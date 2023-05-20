import streamlit as st
from langchain import OpenAI
from langchain.text_splitter import TokenTextSplitter
import openai
from youtube_transcript_api import YouTubeTranscriptApi
import pytube
import re
import requests
from bs4 import BeautifulSoup

###########
# Constants
###########
MAX_TOKENS=3000
STOP_WORDS=['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"]

###########
# Functions
###########
def extractText(url):
  response = requests.get(url)
  response.close()
  soup = BeautifulSoup(response.text, 'html.parser')
  l=[]
  for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']): l.append(tag.get_text())
  return '\n'.join(l)

def preprocess(z):
  return ' '.join([word for word in re.sub(r'[^\w\s]', '', z).split() if word.lower() not in STOP_WORDS])

def prompt(z):
  return openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[{'role': 'user', 'content': z}])['choices'][0]['message']['content']

def translateShorten(z):
  text_splitter = TokenTextSplitter(chunk_size=MAX_TOKENS)
  docs = text_splitter.create_documents([z])
  l=[]
  for doc in docs:
    l.append(prompt(f'Translate to English and shorten: {doc.page_content}'))
  return '\n'.join(l)

def refine(llm,z):
  prevLen=0
  while llm.get_num_tokens(z) > MAX_TOKENS:
    text_splitter = TokenTextSplitter(chunk_size=MAX_TOKENS, chunk_overlap=0)
    docs = text_splitter.create_documents([z])
    if len(docs)==prevLen:
      st.stop()
    else:
      prevLen=len(docs)
    l = []
    l.append(prompt(f"Shorten: {docs[0].page_content}"))
    l.append(docs[0].page_content[-200:]) # chunk overlap
    for doc in docs[1:]:
      l.append(doc.page_content)
    z = ' '.join(l)
  return z

def summarize(z):
  return prompt(f"Summarize into unnumbered bullet points under different section headings which are preceded by appropriate emojis in your own words: {z}")

####################################################################################################

######
# Init
######
openai.api_key = st.secrets['openai_api_key']
llm = OpenAI(openai_api_key=openai.api_key)
st.set_page_config(page_title='SS')

######
# Main
######
with st.form('form'):
  url = st.text_input('URL',key='url')
  col1, col2 = st.columns(2)
  with col1:
    isSubmit = st.form_submit_button('Submit')
  with col2:
    def m(): st.session_state['url'] = ''
    isClear = st.form_submit_button('Clear', on_click=m)

if isSubmit:
  if url=='': url='https://www.youtube.com/watch?v=Py0uxliieL8&t=2670s'
  # url = 'https://www.youtube.com/live/q71X_VWk_-A?feature=share' # PrevMed
  # url = 'https://www.youtube.com/watch?v=yUaIG_r6Xes&t=3542' # AI Advantage
  # url = 'https://www.youtube.com/watch?v=wV4NBq9wbY4&t=7s' # Chinese
  # url = 'https://thenewstack.io/with-chatgpt-honeycomb-users-simply-say-what-theyre-looking-for/' # Text
  with st.spinner():
    id=pytube.extract.video_id(url)
    try:
      transcript=' '.join([z['text'] for z in YouTubeTranscriptApi.get_transcript(id,languages=['en','zh','zh-HK'])])
      isOk=True
    except:
      isOk=False
    if isOk:
      try:
        YouTubeTranscriptApi.list_transcripts(id).find_transcript(['en'])
      except:
        st.write('Chinese detected ....')
        transcript=translateShorten(transcript)
    else:
      transcript=extractText(url)
    ####################################################################################################
    text=preprocess(transcript)
    text = refine(llm,text)
    summary=summarize(text)
  st.write(summary)
