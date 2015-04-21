#!/usr/bin/python
# coding=utf-8

####### Validation of a JSON file according to a JSON-rnc schema
###  Guy Lapalme (lapalme@iro.umontreal.ca) March 2015
########################################################################

## truc pour afficher du UTF-8 dans la console TextMate
import sys 
reload(sys) 
sys.setdefaultencoding("utf-8")

import re,pprint,json,os,datetime,argparse

## flag for debugging
traceRead=False

from ParseJsonRnc       import parseJsonRnc,ppJson
from SplitJson          import jsonSplitter
from ValidateJsonObject import validateObject,errorSchema


# recursively search for a value in an object
# sels is a list of field names
def select(sels,obj):
    if len(sels)==0:return obj
    s=sels[0]
    if s in obj: 
        return select(sels[1:],obj[s])
    else: 
        return None

###########
### validate a series of json objects within a file according to a schema
#
def validateObjects(schema,idStr,fileName):
    if traceRead:print "validateObjects(%s,%s)"%(schema,fileName)
    if '$schema' not in schema or schema['$schema']!='http://json-schema.org/draft-04/schema#':
        print errorSchema([],"bad schema!!!")
        return
    idFn=None if idStr==None else lambda o:select(idStr.split("/"),o)
    nb=0
    nbInvalid=0
    nbBad=0
    for inJson in jsonSplitter((open(fileName) if fileName!=None else sys.stdin).read()):
        try:
            if traceRead:print "$$$inJson="+inJson
            obj=json.loads(inJson)
            nb+=1
            id=str(nb)
            if idFn!=None:
                val=idFn(obj)
                if val!=None:
                    id=val
            if not(validateObject(obj,id,schema)):
                nbInvalid+=1
        except ValueError as mess:
            print "Item "+str(nb)+": bad json object:"+str(mess)
            nbBad+=1
    if nbInvalid==0 and nbBad==0:
        print "All %d objects are valid"%nb
    else:
        print "%d objects read: %d invalid, %d bad"%(nb,nbInvalid,nbBad)

### 
#  validate lines in a file each of which is json object
def validateLines(schema,idStr,fileName):
    if traceRead:print "validateLines(%s,%s)"%(schema,fileName)
    if '$schema' not in schema or schema['$schema']!='http://json-schema.org/draft-04/schema#':
        print errorSchema([],"bad schema!!!")
        return
    nb=0
    nbInvalid=0
    nbBad=0
    idFn=None if idStr==None else lambda o:select(idStr.split("/"),o)
    for line in (open(fileName) if fileName!=None else sys.stdin):
        try:
            nb+=1
            if traceRead:print "$$$line "+str(nb)+"="+line
            obj=json.loads(line)
            id=str(nb)
            if idFn!=None:
                val=idFn(obj)
                if val!=None:
                    id=val
            if not(validateObject(obj,str(id),schema)):
                nbInvalid+=1
        except ValueError as mess:
            print "Line "+str(nb)+": bad json object:"+str(mess)
            # print line
            nbBad+=1
    if nbInvalid==0 and nbBad==0:
        print "All %d objects are valid"%nb
    else:
        print "%d objects read: %d invalid, %d bad"%(nb,nbInvalid,nbBad)
        

## taken from http://stackoverflow.com/questions/237079/how-to-get-file-creation-modification-date-times-in-python
def modificationDate(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)

## save a schema as a JSON Schema file
def saveSchema(schema,pythonSchemaFileName):
    if traceRead:print "saveSchema:"+pythonSchemaFileName
    out=open(pythonSchemaFileName,"w")
    # json.dump(schema,out,indent=3,separators=(',', ': '))
    ppJson(out,schema)
    return schema

## read an existing schema
def readSchema(pythonSchemaFileName):
    if traceRead:print "readSchema:"+pythonSchemaFileName
    schema = json.load(open(pythonSchemaFileName))
    if traceRead:
        print "schema read:\n"
        pprint.pprint(schema)
    return schema
    
## find a JSON-RNC schema: if the JSON Schema file is older than the JSON-RNC schema parse it
def getSchema(jsonrncFile):
    if traceRead:print "getSchema:"+jsonrncFile
    pythonSchemaFileName=jsonrncFile+".json"
    if os.path.exists(pythonSchemaFileName):
        schemaCreationTime=modificationDate(pythonSchemaFileName)
        if schemaCreationTime > modificationDate(jsonrncFile):
            return readSchema(pythonSchemaFileName)
    schema=parseJsonRnc(open(jsonrncFile))
    if type(schema) is int:
        print str(schema)+" errors found in schema in "+pythonSchemaFileName
        return None
    return saveSchema(schema,pythonSchemaFileName)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description="Parse a JSON-rnc schema and validate a JSON file according to it.")
    parser.add_argument("--split","-s",help="Separate the input JSON objects each a single line.",action="store_true")
    parser.add_argument("--debug",help="Trace calls for debugging",action="store_true")
    parser.add_argument("-id",help="use this selector as a list of keys each separated by a slash, a.k.a. JSON pointer, (e.g. '_id/$oid') "
                                   "for identifying records in error messages instead of line numbers")
    parser.add_argument("schema",help="name of file containing the schema")
    parser.add_argument("json_file",help="name of the JSON file to validate",nargs='?')
    args=parser.parse_args()
    if args.debug : traceRead=True
    schema = getSchema(args.schema)
    if schema!=None:
        if args.split:
            validateObjects(schema,args.id,args.json_file)
        else:
            validateLines(schema,args.id,args.json_file)
