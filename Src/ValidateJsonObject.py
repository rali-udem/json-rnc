#!/usr/bin/python
# coding=utf-8

####### Validation of a JSON object according to a JSON-rnc schema
###  Guy Lapalme (lapalme@iro.umontreal.ca) March 2015
##   revision for adding statistics on error messages, May 2015
########################################################################

## for displaying UTF-8 in the Textmate console
import sys 
reload(sys) 
sys.setdefaultencoding("utf-8")

import re

traceValidate=False

# global schema
rootSchema=None

def errorValidate(sels,mess,infos):
    return "%s\t%s\t%s\n"%("/".join(sels),mess,infos)
def errorSchema(sels,mess,infos):
    return "! Error in schema !\t"+errorValidate(sels,mess,infos)
    
def isString(value):
    return isinstance(value,(str,unicode))
def showVal(value,width=50):
    if type(value) is bool:
        val="true" if value else "false"
    elif value==None:val="null"
    else: val=str(value)
    return val if len(val)<width else val[0:width-13]+"..."+val[-10:]

### recursively find a definition within a partial schema (sch) using a selector
#   this function makes use of the global schema
def deref(selects,schema):
    global traceValidate,rootSchema
    if traceValidate: print "$$deref(%s,%s)"%(str(selects),showVal(schema))
    if len(selects)==0:
        return schema
    field=selects[0]
    if field=="#":
        return deref(selects[1:],rootSchema)
    if field in schema:
        return deref(selects[1:],schema[field])
    else:
        raise NameError("could not find:"+field) 

### 
#  validate object o according to a schema keeping track of selectors (sels)
#  that are used to identify errors 
#  return "" if no error otherwise returns an error message
def validate(sels,schema,parent,o):
    global traceValidate
    if traceValidate: print "$$validate:%s:%s:%s"%("/".join(sels),showVal(schema),showVal(o))
    if "oneOf" in schema:
        allMess=[]
        for alt in schema["oneOf"]:
            mess=validate(sels,alt,schema,o)
            if traceValidate: print "$$$"+showVal(alt)+"=>"+mess
            if mess=="":
                return ""
            allMess.append(mess)
        return showVal(o)+" does not match any alternative:\n -"+" -".join(allMess) # returns combined error message
    if "type" in schema :
        theType=schema['type']
        if theType in ["integer","number","boolean","string","boolean","null"]:
            valid=validateSimpleType(sels,theType,o)
            if valid!="": return valid
            return validateFacets(sels,schema,o)
        if theType=="object":
            if type(o) is dict:
                # check length of object
                nbProps=len(o)
                valid=""
                # print "nbProps:%d,%d,%d"%(nbProps,schema["minProperties"],schema["maxProperties"])
                if "minProperties" in schema:
                    if nbProps<schema["minProperties"]:
                        valid+=errorValidate(sels,"object length less than "+str(schema["minProperties"]),showVal(o))
                if "maxProperties" in schema:
                    if nbProps>schema["maxProperties"]:
                        valid+=errorValidate(sels,"object length greater than "+str(schema["maxProperties"]),showVal(o))
                # check properties
                if "additionalProperties" in schema and type(schema["additionalProperties"]) is not bool:
                    # validate only values, not field names
                    for field in iter(o):
                        newSels=list(sels)
                        newSels.append(field)
                        valid+=validate(newSels,schema["additionalProperties"],parent,o[field])
                    return valid
                elif 'properties' in schema:
                    if "required" in schema:
                        return validateProperties(sels,schema['properties'],schema['required'],schema,o)
                    else:
                        return errorSchema(sels,"'required' field not in schema","")
                else:
                    return valid # no property validation when there is no 'properties' field
            else:
                return errorValidate(sels,"object expected:",showVal(o))
        if theType =="array":
            if type(o) is list:
                if 'items' in schema: 
                    schemaItems=schema['items']
                    valid=""
                    newSels=list(sels)
                    no=0
                    for elem in o: #check each element of the array
                        valid+=validate(newSels+["["+str(no)+"]"],schemaItems,[],elem)
                        no+=1
                    if "minItems" in schema:
                        if no<schema["minItems"]:
                            valid+=errorValidate(newSels,"array length less than "+str(schema["minItems"]),showVal(o))
                    if "maxItems" in schema:
                        if no>schema["maxItems"]:
                            valid+=errorValidate(newSels,"array length greater than "+str(schema["maxItems"]),showVal(o))
                    return valid
                else:
                    return "" # no validation when no item is defined...
            else:
                return errorValidate(sels,"array expected:",showVal(o))
        else:
            return errorSchema(sels,"unexpected type:",str(theType))
    if "$ref" in schema: # hack replace in the schema the type reference by its definition 
        try:
            typeref=schema["$ref"]
            newType=deref(typeref.split("/"),parent)
            schema.update(newType)
            del schema["$ref"]
            return validate(sels+["("+typeref+")"],schema,parent,o)
        except NameError as err: # we could not dereference...
            return str(err)+" in "+typeref
    return errorSchema(sels,"Schema without type, oneOf nor $ref:",showVal(schema))

def validateProperties(sels,props,required,parent,obj):
    global traceValidate
    if traceValidate:print "$$validateProperties:%s:%s:%s"%(showVal(props),str(required),showVal(obj))
    valid=""
    if not(type(obj) is dict):
        return errorValidate(sels,"object expected:",showVal(obj))
    # validate required fields
    for field in required:
        if field in obj:
            newSels=list(sels) # update selector list
            newSels.append(field)
            valid+=validate(newSels,props[field],parent,obj[field])
        else:
            valid+=errorValidate(sels,"missing required field:"+field,"")
    # validate the other fields of the object
    # validate if fields are present or not
    for field in iter(obj):
        if field not in required: # required fields have already been validated
            newSels=list(sels)    # update the selector list
            newSels.append(field)
            if field in props:
                valid+=validate(newSels,props[field],parent,obj[field])
            else:
                valid+=errorValidate(sels,"unexpected field in object:"+field,"")
    return valid

def validateSimpleType(sels,schemaType,value):
    global traceValidate
    if traceValidate:print "$$validateSimpleType:%s:%s:%s"%(str(schemaType),showVal(value),str(type(value)))
    if schemaType=="string":
        return "" if isString(value) \
                  else errorValidate(sels,"string expected:",showVal(value)) 
    if schemaType=="integer":
        return "" if type(value) is int \
                  else errorValidate(sels,"integer expected:",showVal(value))
    if schemaType=="number":
        return "" if isinstance(value,(int,float)) \
                  else errorValidate(sels,"number expected:",showVal(value))
    if schemaType=="boolean":
        return "" if type(value) is bool \
                  else errorValidate(sels,"boolean expected:",showVal(value))
    if schemaType=="null":
        return "" if value==None \
                  else errorValidate(sels,"null expected:",showVal(value))
    return errorSchema(sels,"unknown schemaType:",schemaType)

def validateFacets(sels,schema,value):
    global traceValidate
    if traceValidate:print "$$validateFacets:%s:%s"%(str(schema),str(value))
    valid=""
    theType=schema["type"]
    if theType in ["integer","number"]:
        if isinstance(value,(int,float)):
            if "minimum" in schema:
                low=schema["minimum"]
                if value < low :
                    valid+=errorValidate(sels,"illegal value:",str(value)+" < "+str(low))
            if "exclusiveMinimum" in schema:
                low=schema["exclusiveMinimum"]
                if value <= low : 
                    valid+=errorValidate(sels,"illegal value:",str(value)+" <= "+ str(low)+" excl")
            if "maximum" in schema:
                high=schema["maximum"]
                if value > high :
                    valid+=errorValidate(sels,"illegal value:",str(value)+" > "+str(high))
            if "exclusiveMaximum" in schema:
                high=schema["exclusiveMaximum"]
                if value >= high : 
                   valid+=errorValidate(sels,"illegal value:",str(value)+" >= "+ str(high)+" excl")
        else:
            valid+=errorValidate(sels,"numeric value expected:",value)
    if theType=="string":
        if isString(value):
            if "pattern" in schema:
                regex="^"+schema["pattern"]+"$"   # do an "anchored match" of the regex
                valid += "" if re.match(regex,value) \
                            else errorValidate(sels,"no match:",regex+"<>"+value)
            length=len(value)
            if "minLength" in schema :
                low = schema["minLength"]
                if length<low:
                    valid+=errorValidate(sels,"illegal length:",str(length)+" < "+str(low))
            if "maxLength" in schema :
                high = schema["maxLength"]
                if length>high:
                    valid+=errorValidate(sels,"illegal length:",str(length)+" > "+str(high))
        else:
            valid+=errorValidate(sels,"string expected:",str(value))
    return valid

### show n ,an integer, with a space as a blank separator right aligned 
##              in a field of 'width' chars (expanded if necessary)
##  I have never managed to understand how to use the locale aware thousand separator       
def showNum(n,width=0):
    s=str(n)
    res=""
    while len(s)>3:
        res=" "+s[-3:]+res
        s=s[:-3]
    s+=res
    return (width-len(s))*" "+s

# error type table for statistics
errorTable={}
def printErrorStatistics():
    global errorTable
    if len(errorTable)==0:return
    errors=sorted(errorTable.items(),key=lambda i:i[1],reverse=True)
    print "Error Statistics"
    for (mess,nb) in errors:
        print showNum(nb,15)+"\t"+mess

# list of ids of erroneous objects
errorIdList=[]
def printErrorIdList():
    global errorIdList
    print ";".join([id+"p" for id in errorIdList])

## validate a single json object (json), identified by recordId (a string), according to a json schema
def validateObject(obj,recordId, schema,logMessages,traceRead):
    global rootSchema,errorTable, errorIdList,traceValidate
    rootSchema=schema
    traceValidate=traceRead
    mess=validate([],schema,None,obj)
    if mess!="":
        errorIdList.append(recordId)
        if logMessages:
            print recordId+":"+showVal(obj,100)+"\n"+mess,
        for messLine in mess.split("\n")[0:-1]: ## mess can contain more than one error message
            messType=":".join(messLine.split("\t")[0:2])
            if messType in errorTable: 
                errorTable[messType]+=1
            else: 
                errorTable[messType]=1
            if re.search("does not match any alternative",messLine):
                break # stats for only the first line of alternative errors 
        return False
    return True
