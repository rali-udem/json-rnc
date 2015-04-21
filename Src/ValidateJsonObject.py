#!/usr/bin/python
# coding=utf-8

####### Validation of a JSON object according to a JSON-rnc schema
###  Guy Lapalme (lapalme@iro.umontreal.ca) March 2015
########################################################################

## truc pour afficher du UTF-8 dans la console TextMate
import sys 
reload(sys) 
sys.setdefaultencoding("utf-8")

import re

traceValidate=False

# global schema
rootSchema=None

def errorValidate(sels,mess):
    return "%s :: %s\n"%("/".join(sels),mess)
def errorSchema(sels,mess):
    return "! Error in schema ! "+errorValidate(sels,mess)
    
def isString(value):
    return isinstance(value,(str,unicode))
def showVal(value,width=50):
    if value==True:val="true"
    elif value==False:val="false"
    elif value==None:val="null"
    else: val=str(value)
    return val if len(val)<width else val[0:width-13]+"..."+val[-10:]

### recursively find a definition within a partial schema (sch) using a selector
#   this function makes use of the global schema
def deref(selects,schema):
    global traceValidate,rootSchema
    # if traceValidate: print "$$deref(%s,%s)"%(str(selects),showVal(sch))
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
        for alt in schema["oneOf"]:
            mess=validate(sels,alt,schema,o)
            # if traceValidate: print "$$$"+showVal(alt)+"=>"+mess
            if mess=="":
                return ""
        return mess # returns the last error message
    if "type" in schema :
        theType=schema['type']
        if theType=="object":
            if 'properties' in schema:
                if "required" in schema:
                    return validateProperties(sels,schema['properties'],schema['required'],schema,o)
                else:
                    return errorSchema(sels,"'required' field not in schema")
            else:
                return "" # no validation when there is no property field
        if theType in ["integer","number","boolean","string","boolean","null"]:
            valid=validateSimpleType(sels,theType,o)
            if valid!="": return valid
            return validateFacets(sels,schema,o)
        if theType =="array":
            if type(o) is list:
                if 'items' in schema:
                    schemaItems=schema['items']
                    valid=""
                    newSels=list(sels)
                    no=0
                    for elem in o:
                        valid+=validate(newSels+["["+str(no)+"]"],schemaItems,[],elem)
                        no+=1
                    return valid
                else:
                    return "" # no validation when no item is defined...
            else:
                return errorValidate(sels,"tableau attendu=>"+showVal(o))
        else:
            return errorSchema(sels,"type inattendu=>"+str(theType))
    if "$ref" in schema: # hack qui remplace dans le schéma la référence au type par sa définition
        try:
            typeref=schema["$ref"]
            newType=deref(typeref.split("/"),parent)
            schema.update(newType)
            del schema["$ref"]
            return validate(sels+["("+typeref+")"],schema,parent,o)
        except NameError as err: # ici si on ne peut déréfencer...
            return str(err)+" in "+typeref
    return errorSchema(sels,"Schema sans type, ni $ref:"+showVal(schema))

def validateProperties(sels,props,required,parent,obj):
    global traceValidate
    if traceValidate:print "$$validateProperties:%s:%s:%s"%(showVal(props),str(required),showVal(obj))
    valid=""
    if not(type(obj) is dict):
        return errorValidate(sels,"object expected:"+showVal(obj))
    # validate required fields
    for field in required:
        if field in obj:
            newSels=list(sels) # ajuster la liste des sélecteurs
            newSels.append(field)
            if field in obj:
                valid+=validate(newSels,props[field],parent,obj[field])
        else:
            valid+=errorValidate(sels,"missing required field =>"+field)
    # validate the other fields of the object
    # validate if fields are present or not
    for field in iter(obj):
        if field not in required: # required fields have already been validated
            newSels=list(sels)    # update the selector list
            newSels.append(field)
            if field in props:
                valid+=validate(newSels,props[field],parent,obj[field])
            else:
                valid+=errorValidate(sels,"unexpected field in object =>"+field)
    return valid

def validateSimpleType(sels,schemaType,value):
    global traceValidate
    if traceValidate:print "$$validateSimpleType:%s:%s:%s"%(str(schemaType),showVal(value),str(type(value)))
    if schemaType=="string":
        return "" if isString(value) \
                  else errorValidate(sels,"string expected =>"+showVal(value)) 
    if schemaType=="integer":
        return "" if type(value) is int \
                  else errorValidate(sels,"integer expected =>"+showVal(value))
    if schemaType=="number":
        return "" if isinstance(value,(int,float)) \
                  else errorValidate(sels,"number expected =>"+showVal(value))
    if schemaType=="boolean":
        return "" if type(value) is bool \
                  else errorValidate(sels,"boolean expected =>"+showVal(value))
    if schemaType=="null":
        return "" if value==None \
                  else errorValidate(sels,"null expected =>"+showVal(value))
    return errorSchema(sels,"unknown schemaType =>"+schemaType)

def validateFacets(sels,schema,value):
    global traceValidate
    if traceValidate:print "$$validateFacets:%s:%s"%(str(schema),str(value))
    valid=""
    theType=schema["type"]
    if theType in ["integer","number"]:
        if isinstance(value,(int,float)):
            if "minimum" in schema:
                low=schema["minimum"]
                if "exclusiveMinimum" in schema and schema["exclusiveMinimum"]:
                   if value <= low : 
                       valid+=errorValidate(sels,"illegal value: "+str(value)+" <= "+ str(low))
                elif value < low :
                       valid+=errorValidate(sels,"illegal value: "+str(value)+" < "+str(low))
            if "maximum" in schema:
                high=schema["maximum"]
                if "exclusiveMaximum" in schema and schema["exclusiveMaximum"]:
                   if value >= high : 
                       valid+=errorValidate(sels,"illegal value: "+str(value)+" >= "+ str(high))
                elif value > high :
                   valid+=errorValidate(sels,"illegal value: "+str(value)+" < "+str(high))
        else:
            valid+=errorValidate(sels,"numeric value expected: "+value)
    if theType=="string":
        if isString(value):
            if "pattern" in schema:
                regex=schema["pattern"]
                valid += "" if re.match(regex,value) \
                            else errorValidate(sels,"no match:"+regex+"<>"+value)
            length=len(value)
            if "minLength" in schema :
                low = schema["minLength"]
                if length<low:
                    valid+=errorValidate(sel,"illegal length:"+str(value)+" < "+low)
            if "maxLength" in schema :
                high = schema["maxLength"]
                if length>high:
                    valid+=errorValidate(sel,"illegal length:"+str(value)+" > "+low)
        else:
            valid+=errorValidate(sels,"string expected:"+str(value))
    return valid

## validate a single json object (json), identified by recordId (a string), according to a json schema
def validateObject(obj,recordId, schema):
    global rootSchema
    rootSchema=schema
    mess=validate([],schema,None,obj)
    if mess!="":
        print recordId+":"+showVal(obj,100)+"\n"+mess
        return False
    return True
