#!/usr/bin/python
# coding=utf-8

####### Validation of a JSON file according to a JSON-rnc schema
###  Guy Lapalme (lapalme@iro.umontreal.ca) March 2015
########################################################################

## truc pour afficher du UTF-8 dans la console TextMate
import sys 
reload(sys) 
sys.setdefaultencoding("utf-8")
import json

#### prettyprint a JSON in more compact format
##   that I find more readable

def out(file,s):file.write(s)
def outQuoted(file,s):out(file,'"'+s+'"')

def ppJson(file,obj,level=0):
    if isinstance(obj,(str,unicode)):
        if '"' in obj or '\\' in obj:
            outQuoted(file,obj.replace('\\','\\\\').replace('"','\\"'))
        else: 
            outQuoted(file,obj)
    elif isinstance(obj,(int,float,bool)) or obj==None:
        out(file,str(obj))
    elif type(obj) is dict:
        out(file,"{")
        n=len(obj)
        i=1
        for key in sorted(obj):
            if i>1 : out(file,"\n"+(level+1)*" ")
            outQuoted(file,key)
            out(file,":")
            ppJson(file,obj[key],level+1+len(key)+3) # largeur de [{" de la clé
            if i<n: out(file,",")
            i+=1
        out(file,"}")
    elif type(obj) is list:
        out(file,"[")
        n=len(obj)
        i=1
        for elem in obj:
            if i>1: out(file,"\n"+(level+1)*" ")
            ppJson(file,elem,level+1)
            if i<n: out(file,",")
            i+=1
        out(file,"]")
    if level==0:out(file,"\n")

if __name__ == '__main__':
    obj=json.load(sys.stdin)
    ppJson(sys.stdout,obj)

