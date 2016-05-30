#!/usr/bin/python
# coding=utf-8

####### Validation of a JSON file according to a JSON-rnc schema
###  Guy Lapalme (lapalme@iro.umontreal.ca) March 2015
##   revision for adding statistics on error messages, May 2015
########################################################################

## for displaying UTF-8 in the Textmate console
import sys 
reload(sys) 
sys.setdefaultencoding("utf-8")

import re,pprint,json,os,datetime,argparse

## flag for debugging
traceRead=False

from ParseJsonRnc       import parseJsonRnc,ppJson
from SplitJson          import jsonSplitter
from ValidateJsonObject import validateObject,errorSchema,printErrorStatistics,printErrorIdList,showNum

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
### validate a stream of json objects within a file according to a schema
#   prints the number of invalid objects
#   when no message are logged, print something on stderr every 10000 records
def validateStream(schema,idStr,stream,logMessages):
    if '$schema' not in schema or schema['$schema']!='http://json-schema.org/draft-04/schema#':
        print errorSchema([],"bad schema!!!")
        return
    idFn=None if idStr==None else lambda o:select(idStr.split("/"),o)
    nb=0
    nbInvalid=0
    nbBad=0
    for inJson in stream:
        try:
            if traceRead:print "$$$inJson="+inJson
            obj=json.loads(inJson)
            nb+=1
            id=str(nb)
            if idFn!=None:
                val=idFn(obj)
                if val!=None:
                    id=val
            if not(validateObject(obj,id,schema,logMessages)):
                nbInvalid+=1
            if not(logMessages) and nb%10000==0:
                sys.stderr.write("Processing record "+str(nb)+"\n")
        except ValueError as mess:
            if logMessages:
                print "Item "+str(nb)+": bad json object:"+str(mess)
            nbBad+=1
    if nbInvalid==0 and nbBad==0:
        print "All "+showNum(nb)+" objects are valid"
    else:
        print showNum(nb)+" objects read: "+showNum(nbInvalid)+" invalid, "+showNum(nbBad)+" bad"
    return nbInvalid


###########
### validate a series of json objects within a file according to a schema
#   returns the number of invalid objects
def validateObjects(schema,idStr,fileName,logMessages):
    if traceRead:print "validateObjects(%s,%s)"%(schema,fileName)
    return validateStream(schema,idStr,jsonSplitter((open(fileName) if fileName!=None else sys.stdin).read()),logMessages)

### 
#  validate lines in a file each of which is json object
#  returns the number of invalid lines
def validateLines(schema,idStr,fileName,logMessages):
    if traceRead:print "validateLines(%s,%s)"%(schema,fileName)
    return validateStream(schema,idStr,open(fileName) if fileName!=None else sys.stdin,logMessages)        

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
    parser=argparse.ArgumentParser(description="Parse a JSON-rnc schema and validate a JSON file according to it. "+
                            "The number of invalid objects (modulo 256) is returned as the exit code of the program.")
    parser.add_argument("--split","-s",help="Separate the input JSON objects each a single line.",action="store_true")
    parser.add_argument("--debug",help="Trace calls for debugging",action="store_true")
    parser.add_argument("-id",help="use this selector as a list of keys each separated by a slash, a.k.a. JSON pointer, (e.g. '_id/$oid') "
                                   "for identifying records in error messages instead of line numbers")
    parser.add_argument("--stats","-st",help="Output statistics about error messages",action="store_true")
    parser.add_argument("--nolog",help="Do not log error messages",action="store_true")
    parser.add_argument("--sed",help="Output list of erroneous ids in sed compatible format",action="store_true")
    parser.add_argument("schema",help="name of file containing the schema")
    parser.add_argument("json_file",help="name of the JSON file to validate",nargs='?')
    args=parser.parse_args()
    if args.debug : traceRead=True
    schema = getSchema(args.schema)
    if schema!=None:
        if args.split:
            nbInvalid=validateObjects(schema,args.id,args.json_file,not(args.nolog))
        else:
            nbInvalid=validateLines(schema,args.id,args.json_file,not(args.nolog))
        if args.stats:
            printErrorStatistics()
        if args.sed:
            printErrorIdList()
        exit(nbInvalid) # return the number of errors but in Linux it is given modulo 256...

