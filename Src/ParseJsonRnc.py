#!/usr/bin/python
# coding=utf-8

####### Parse a JSON-rnc schema to produce a JSON-schema file
###  Guy Lapalme (lapalme@iro.umontreal.ca) March 2015
########################################################################


import sys,re,json,codecs,datetime,argparse,os
from ppJson             import ppJson

## flags for debugging
traceParse=False

################################################################################################
#### tokenizer for the jsonrnc input
## tokenizer adapted from https://docs.python.org/3.4/library/re.html#writing-a-tokenizer

### reserved words
RESERVED={"integer":"INTEGER","number":"NUMBER","string":"STRING",
          "null":"NULL","boolean":"BOOLEAN","start":"START"}

def tokenizeRNC(input):
    token_specification = [
        # escaped quoted string regex taken from http://stackoverflow.com/questions/16130404/regex-string-and-escaped-quote
        ("STR",           r'"(?:\\.|[^"\\])*?"'+"|"+ r"'(?:\\.|[^'\\])*?'"),# double or single quoted string
        ("REGEX",         r"/.*?/"),                    # regex
        ("NUMBER",        r'\d+(\.\d*)?'),              # integer or decimal number
        ("IDENT",         r'[A-Za-z_][A-Za-z_0-9]*'),   # Identifiers
        ("INTERROGATION", r'\?'),
        ("OPEN_BRACE",    r'\{'),
        ("CLOSE_BRACE",   r'\}'),
        ("OPEN_BRACKET",  r'\['),
        ("CLOSE_BRACKET", r'\]'),
        ("OPEN_PAREN",    r'\('),
        ("CLOSE_PAREN",   r'\)'),
        ("VERT_BAR",      r'\|'),
        ("EQUAL",         r'='),
        ("AT",            r'@'),
        ("COMMA",         r','),
        ("COLON",         r':'),
        ("EOL",           r'\n'),
        ("SKIP",          r'[ \t]+|#.*'),  # Skip over spaces and tabs and comments
        ("UNDEF",         r'.')            # Any other character
    ]
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    line_num = 1
    line_start = 0
    for mo in re.finditer(tok_regex, input):
        kind = mo.lastgroup
        value = mo.group(kind)
        # print "kind:"+kind+"; value:"+value
        if kind == "EOL":
            line_start = mo.end()
            line_num += 1
        elif kind == "SKIP":
            pass
        elif kind == "UNDEF":
            yield Token("UNDEF",value,line_num,mo.start()-line_start)
        else:
            if kind == "IDENT" and value in RESERVED:
                kind = RESERVED[value]
            column = mo.start() - line_start
            yield Token(kind, value, line_num, column)
    yield Token("EOF"," ",line_num,0)

class Token:
    """packaging for the output of token"""
    def __init__(self, kind,value,line_num,column):
        self.kind=kind
        self.value=value
        self.line_num=line_num
        self.column=column
        # print self
    
    def __repr__(self):
        return "Token(%s:%s:%d:%d)"%(self.kind,self.value,self.line_num,self.column)

################################################################################################

### EBNF Grammar of the json-rnc input
# definitions = "start" = type | {definition} ;
# definition  = (identifier | string ) , ["=" , types] ;
#
# types       = type , ( {"," , type} | {"|" , type} ) ;
# type        = ("string" | "integer" | "number" | "boolean" | "null"     (* primitive types *)
#                | identifier | string                                    (* name of a user defined type *)
#                | "/", character-"/" , "/"                               (* regular expression without a slash *)
#               ) , [facets]
#               | "{" , [properties] , "}"                                (* object *)
#               | "[" , [types]  , "]"                                     (* array *)
#               | "(" , types   , ")" ;                                   (* grouping *)
# properties  = property , {[","] , property} ;
# property    = identifier , ["?"] , ":" , type  | "(" , properties , ")" ;
# facets      = "@(" , facetId , "=" , value , {",", facetId , "=" , value } ")" ;
# facetId     = "minimum" | "minimumExclusive" | "maximum" | "maximumExclusive"   (* for numbers *)
#               | "pattern" | "minLength" | "maxLength"                           (* for strings *)
#               | "minItems" | "maxItems"                                         (* for arrays *)
#               | "minProperties" | "maxProperties";                              (* for objects *)
#
# identifier  = letter , { letter | digit | "_" } | string ;
# number      = [ "-" ], digit, { digit } ["." , digit, { digit }];
# string      =   "'" , character , { character } , "'"
#               | '"' , character , { character } , '"' ;
# value       = number | string | "true" | "false" | "null";

## global shared variables for the parser functions 
schema = {
    "$schema":"http://json-schema.org/draft-04/schema#",
    "definitions":{}
    }

defs = schema["definitions"]
refs = set([])

token=None
tokenizer=None
lines=["**dummy**"] # lines of the input kept for error messages, line 0 added to make line numbers start at one...
errorsInSchema=0

def errorJsrnc(module,message,recoveryTokens):
    global lines,token,tokenizer,errorsInSchema,traceParse
    if traceParse:print ">>>errorJsrnc:"+module
    errorsInSchema+=1
    line = lines[token.line_num] if token.line_num<len(lines) else ""
    print "line %3d: %s"%(token.line_num,line),
    print ((token.column+10)*" ")+"↑:"+message
    if recoveryTokens!=None:
        endTokens=set(["EOF"]+recoveryTokens)
        while token.kind not in endTokens:
            token=tokenizer.next()

# definitions = "start" = type | {definition} ;
# definition  = (identifier | string ) , ["=" , types] ;
def parseDef(): ## modifies the global schema variable
    global token, tokenizer,defs, refs, schema,traceParse
    if traceParse:print ">>>parseDef:"+str(token)
    is_start=False
    typedef=None
    if token.kind in set(["IDENT","STR","START"]):
        is_start=token.kind=="START"
        ident=token.value[1:-1] if token.kind=="STR" else token.value
    else:
        errorJsrnc("parseDef","identifier expected at start of definition",["IDENT"])
        ident="**dummy**"
    token=tokenizer.next()
    if token.kind=="EQUAL":
        token=tokenizer.next()
    else:
        errorJsrnc("parseDef","equal expected in a definition",None)
    typedef = parseTypes()
    if ident in defs:
        errorJsrnc("parseDef","double definition for "+ident,None)
    if typedef!=None:
        if is_start:
            schema.update(typedef)
        defs[ident]= typedef
    if traceParse:ident+"="+json.dumps(typedef,indent=3)
    return

## types       = type , ( {"," , type} | {"|" , type} ) ;
def parseTypes(): ## =>  
    global token,tokenizer, traceParse
    if traceParse:print "<<parseTypes:"+str(token)
    res = parseType()
    if token.kind=="COMMA":
        res1=res
        res={res1}
        while token.kind=="COMMA":
            token=tokenizer.next()
            res1.update(parseType())
    elif token.kind=="VERT_BAR":
        res1=[res]
        res={"oneOf":res1}
        while token.kind=="VERT_BAR":
            token=tokenizer.next()
            res1.append(parseType())
    if traceParse:print ">>parseTypes:"+str(res)
    return res

## type        = ("string" | "integer" | "number" | "boolean" | "null"     (* primitive types *)
##                | identifier | string                                    (* name of a user defined type *)
##                | "/", character-"/" , "/"                               (* regular expression without a slash *)
##               ) , [facets]
##               | "{" , [properties] , "}"                                (* object *)
##               | "[" , [types]  , "]"                                     (* array *)
##               | "(" , types   , ")" ;                                   (* grouping *)
def parseType():
    global token,tokenizer,traceParse,refs
    if traceParse:print "<<parseType:"+str(token)
    res=None
    if token.kind in set(["STRING","INTEGER","NUMBER","BOOLEAN","NULL"]):
        res={"type":token.value}
        token=tokenizer.next()
        res=checkFacets(res)
    elif token.kind == "IDENT": 
        res={"$ref":"#/definitions/"+token.value}
        refs.add(token.value)
        token=tokenizer.next()
        res=checkFacets(res)
    elif token.kind == "STR":
        res={"$ref":"#/definitions/"+token.value[1:-1]}
        refs.add(token.value[1:-1])
        token=tokenizer.next()
        res=checkFacets(res)
    elif token.kind == "REGEX":
        res = {"type":"string","pattern":token.value[1:-1]}
        token=tokenizer.next()
        res=checkFacets(res)
    elif token.kind == "OPEN_BRACE":
        token=tokenizer.next()
        if token.kind == "CLOSE_BRACE": # skip object validation on {}
            token=tokenizer.next()
            res={"type":"object"}
            res=checkFacets(res)
        else:
            (props,required)=mergeProps(parseProps())
            res = {"type":"object","properties":props,"required":required}
            if token.kind == "CLOSE_BRACE":
                token=tokenizer.next()
                res=checkFacets(res)
            else:
                errorJsrnc("parseType","closing brace expected",["CLOSE_BRACE"])
    elif token.kind == "OPEN_BRACKET":
        token=tokenizer.next()
        if token.kind == "CLOSE_BRACKET": ## skip array validation on []
            token=tokenizer.next()
            res={"type":"array"}
            res=checkFacets(res)
        else:
            res = {"type":"array","items":parseTypes()}
            if token.kind == "CLOSE_BRACKET":
                token=tokenizer.next()
                res=checkFacets(res)
            else:
                errorJsrnc("parseType","closing bracket expected",["CLOSE_BRACKET"])
    elif token.kind == "OPEN_PAREN":
        token=tokenizer.next()
        res = parseTypes()
        if token.kind == "CLOSE_PAREN":
            token=tokenizer.next()
        else:
            errorJsrnc("parseType","closing parenthesis expected",["CLOSE_PAREN"])
    else:
        errorJsrnc("parseType","ident or json type expected",["IDENT","STR"])
    if traceParse:print ">>parseType:"+str(res)    
    return res

def mergeProps(props):
    if traceParse: print "<<mergeProp:"+str(props)
    res={}
    if props==None:return res
    required=[]
    if type(props) is not list:
        props=[props]
    for po in props:
        if po!=None and type(po) is tuple: ## None can happen in case of a schema error
            (prop,optional)=po
            key=prop.keys()[0]
            if key in res:
                errorJsrnc("mergeProps","repeated property name:"+key,None)
            res.update(prop)
            if not(optional):
                required.append(key)
    if traceParse: print ">>mergeProp:"+str((res,required))
    return (res,required)

# properties  = property , {[","] , property} ;
def parseProps(): ## => [{id:"nom",type:...,(optional:True)?}]
    global token,tokenizer,traceParse
    if traceParse:print "<<parseProps:"+str(token)
    res = [parseProp()]
    while token.kind in ["COMMA","IDENT","STR","OPEN_PAREN"]:
        if token.kind=="COMMA": token=tokenizer.next()
        res.append(parseProp())
    if traceParse:print ">>parseProps:"+str(res)
    return res

# property    = identifier , ["?"] , ":" , type  | "(" , properties , ")" ;
def parseProp(): ## => ({ident:type},optionel[boolean]) | None
    global token, tokenizer,traceParse,refs
    if traceParse:print "<<parseProp:"+str(token)
    res=None
    if token.kind in ["IDENT","STR"]:
        ident=token.value if token.kind=="IDENT" else token.value[1:-1]
        token=tokenizer.next()
        optional=False
        parsedType=None
        if token.kind =="INTERROGATION":
            optional=True
            token=tokenizer.next()
        if token.kind == "COLON":
            token=tokenizer.next()
            parsedType=parseType()
        res=({ident:parsedType},optional)
    elif token.kind=="OPEN_PAREN":
        token=tokenizer.next()
        res = parseProps()
        if token.kind == "CLOSE_PAREN":
            token=tokenizer.next()
        else:
            errorJsrnc("parseProp","closing paren expected",["CLOSE_PAREN"])        
    else:
        errorJsrnc("parseProp","ident, string or open parenthesis expected at the start of a prop",["IDENT","STR"])
    if traceParse:print ">>parseProp:"+str(res)
    return res

def checkFacets(res):
    global token,tokenizer
    if token.kind=="AT":
        token=tokenizer.next()
        theType=res["type"] if "type" in res else None # TODO: try to take into account the #ref 
        for facet in parseFacets(theType):
            res.update(facet)
    return res

# facets      = "@(" , facetId , "=" , value , {",", facetId , "=" , value } ")" ;
# facetId     = "minimum" | "minimumExclusive" | "maximum" | "maximumExclusive"   (* for numbers *)
#               | "pattern" | "minLength" | "maxLength" ;                         (* for strings *)
#               | "minItems" | "maxItems"                                         (* for arrays *)
#               | "minProperties" | "maxProperties";                              (* for objects *)
def parseFacets(theType):
    global token, tokenizer, traceParse
    if traceParse:print "<<parseFacets:"+str(token)
    facets=[]
    if token.kind=="OPEN_PAREN":
        token=tokenizer.next()
        while token.kind != "CLOSE_PAREN":
            if token.kind in ["IDENT","STR"]:
                ident=token.value
                if ident in ["minimum","maximum","minLength","maxLength"]:
                    token=tokenizer.next()
                    if token.kind == "EQUAL":
                        token=tokenizer.next()
                        if token.kind == "NUMBER":
                            facets.append({ident:int(token.value)})
                            token=tokenizer.next()
                            if theType!= None and ident in ["minimum","maximum"] and theType not in ["number","integer"]:
                                errorJsrnc("parseFacets","facet "+ident+" only applicable to numeric types",None);
                            elif theType!= None and ident in ["minLength","maxLength"] and theType !="string":
                                errorJsrnc("parseFacets","facet "+ident+" only applicable to string types",None);
                        else: 
                            errorJsrnc("parseFacets","number expected in facet "+ident,["NUMBER"])
                    else: 
                        errorJsrnc("parseFacets","= expected in facet",["IDENT","STR"])
                elif ident=="pattern":
                    token=tokenizer.next()
                    if token.kind == "EQUAL":
                        token=tokenizer.next()
                        if token.kind == "STR":
                            facets.append({ident:token.value[1:-1]})
                            token=tokenizer.next()
                            if theType!= None and theType != "string":
                                errorJsrnc("parseFacets","facet "+ident+" only applicable to string",None);
                        else:
                            errorJsrnc("parseFacets"," string expected as pattern facet",["STR"])
                    else: 
                        errorJsrnc("parseFacets","= expected in facet",["IDENT","STR"])
                elif ident == "exclusiveMinimum" or ident=="exclusiveMaximum":
                    token=tokenizer.next()
                    if token.kind == "EQUAL":
                        token=tokenizer.next()
                        if token.kind=="IDENT" and token.value in ["true","false"]:
                            facets.append({ident:token.value=="true"})
                            token=tokenizer.next()
                            if theType!= None and theType not in ["number","integer"]:
                                errorJsrnc("parseFacets","facet "+ident+" only applicable to numeric types",None);
                        else: 
                            errorJsrnc("parseFacets","boolean value expected for facet "+ident,["STR"]) 
                    else: 
                        errorJsrnc("parseFacets","= expected in facet",["IDENT","STR"])
                elif ident in ["minItems","maxItems","minProperties","maxProperties"]:
                    token=tokenizer.next()
                    if token.kind == "EQUAL":
                        token=tokenizer.next()
                        if token.kind == "NUMBER":
                            facets.append({ident:int(token.value)})
                            token=tokenizer.next()
                            if theType!= None and ident in ["minItems","maxItems"] and theType != "array":
                                errorJsrnc("parseFacets","facet "+ident+" only applicable to array types",None)
                            if theType!= None and ident in ["minProperties","maxProperties"] and theType != "object":
                                errorJsrnc("parseFacets","facet "+ident+" only applicable to object types",None)
                        else: 
                            errorJsrnc("parseFacets","number expected in facet "+ident,["NUMBER"])
                    else: 
                        errorJsrnc("parseFacets","= expected in facet",["IDENT","STR"])
                else: 
                    errorJsrnc("parseFacets","unrecognized facet:"+token.value,["IDENT","STR"])
                    break
            else: 
                errorJsrnc("parseFacets","identifier expected in facet",["IDENT","STR"])
                break
            if token.kind == "COMMA":
                token=tokenizer.next()
        token=tokenizer.next() # skip closing parenthesis
    else: 
        errorJsrnc("parseFacets","open parenthesis expected at the start of a facet",["IDENT","STR"])
    #todo: check that min{inum|Length|Items|Properties} are <= than the corresponding max...
    if traceParse:print ">>parseFacets:"+str(facets)
    return facets


# parse a file containing jsonrnc definitions and returns either a schema or 
# a number indicating the number of errors found during parsing
#
def parseJsonRnc(jsonrncContent):
    global token,tokenizer,lines
    for line in jsonrncContent: # must read all input for dealing with stdin
        lines.append(line)
    # print lines
    tokenizer = tokenizeRNC("".join(lines[1:]))
    token = tokenizer.next()
    try:
        while token.kind!="EOF":
            parseDef()
    except StopIteration:
        errorJsrnc("main","unexpected end of file",None)
    ## check missing definitions
    if "start" not in defs:
        errorJsrnc("main","no start definition",None)
    for ref in refs:
        if ref not in defs:
            errorJsrnc("main","no definition found for "+ref,None)
    return schema if errorsInSchema==0 else errorsInSchema

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description="Parse a JSON-rnc schema from a file or from stdin if no file is given. When there is no error in the schema, produce a JSON Schema on stdout")
    parser.add_argument("--debug",help="Trace calls for debugging",action="store_true")
    parser.add_argument("jsonrnc_file",help="name of the JSON-RNC file to parse",nargs='?')
    args=parser.parse_args()
    if args.debug : traceParse=True
    pythonSchemaFileName="standard input" if args.jsonrnc_file==None else args.jsonrnc_file
    if pythonSchemaFileName=="standard input" :
        schema=parseJsonRnc(codecs.getreader('utf8')(sys.stdin))
    else:
        if not os.path.exists(pythonSchemaFileName):
            print "schema file not found: "+pythonSchemaFileName
            exit(1)
        else:
            schema=parseJsonRnc(open(pythonSchemaFileName))
    if type(schema) is int:
        print str(schema)+" errors found in schema in "+pythonSchemaFileName
    else:
        schema["title"]="Created from JSON-RNC: "+pythonSchemaFileName
        schema["description"]="Written: "+datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # json.dump(schema,sys.stdout,indent=3,separators=(',', ':'))
        ppJson(sys.stdout,schema)
    