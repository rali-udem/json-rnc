#!/usr/local/bin/python3
# coding=utf-8

####### Validation of a JSON file according to a JSON-rnc schema
###  Guy Lapalme (lapalme@iro.umontreal.ca) March 2015
########################################################################

import json

## to sort object fields without accents
import unicodedata
def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str.decode("utf-8"))
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

MAXLENGTH = 100

#### prettyprint a JSON in more compact format
##   that I find more readable
def ppJson(file,obj,level=0,sortkeys=False):
    # auxiliary function that creates a string
    def pp(obj,level,res):
        def out(s):
            nonlocal res
            res += s

        def quoted(s):
            if '\\' in s: s = s.replace('\\', '\\\\')
            if '"' in s: s = s.replace('"', '\\"')
            if '\n' in s: s = s.replace('\n', '\\n')
            return '"' + s + '"'

        if isinstance(obj,str):
            out(quoted(obj))
        elif obj==None:
            out("null")
        elif type(obj) is bool:
            out("true" if obj else "false")
        elif isinstance(obj,(int,float)):
            out(str(obj))
        elif type(obj) is dict:
            keys=list(obj.keys())
            if sortkeys: keys.sort(key=remove_accents)
            out("{"+
                (",\n"+(level+1)*" ").join(map(lambda key:quoted(key)+":"+pp(obj[key],level+1+len(key)+3,""),keys))
                +"}")
        elif type(obj) is list:
            children = list(map(lambda elem:pp(elem,level+1,"") ,obj))
            indent = any(map(lambda elem: isinstance(elem,(list,dict)),obj))
            if not indent: # check if all children fit on the same line
                if sum(map(lambda e:len(e),children))+len(list(children))+level+2 > MAXLENGTH:
                    indent = True
            out("["+
                ((",\n"+(level+1)*" ") if indent else ",").join(children)
                +"]")
        return res
    file.write(pp(obj,level,""))
    file.write("\n")

if __name__ == '__main__':
    import sys
    content = sys.stdin.read().strip()
    try: # reading the whole file in case it is a single valid JSON
        ppJson(sys.stdout,json.loads(content))
    except json.JSONDecodeError as e:
        # read many json objects from stdin, each object possibly spanning more than one line
        # taken from: http://stackoverflow.com/questions/20400818/python-trying-to-deserialize-multiple-json-objects-in-a-file-with-each-object-s
        for line in content.split("\n"):
            while True:
                try:
                    obj=json.loads(line)
                    ppJson(sys.stdout,obj)
                    break
                except:
                    line += next(sys.stdin)
