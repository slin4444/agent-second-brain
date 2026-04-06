import os, youtube_transcript_api  
proxies={'http': 'http://slin4444:tMRbPE9vWK@179.60.183.51:49155', 'https': 'http://slin4444:tMRbPE9vWK@179.60.183.51:49155'}  
try:  
    t_list = youtube_transcript_api.YouTubeTranscriptApi(proxies=proxies).list('uboqyhorx2A')  
    t = t_list.find_transcript(['ru', 'en'])  
    print(t.fetch()[0])  
except Exception as e: print(e)  
