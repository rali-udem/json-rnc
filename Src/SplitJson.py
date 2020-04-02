#!/usr/bin/python
# coding=utf-8

####### Splitting of a JSON file into single line objects
###  Guy Lapalme (lapalme@iro.umontreal.ca) March 2015
########################################################################

## truc pour afficher du UTF-8 dans la console TextMate
import sys 
reload(sys) 
sys.setdefaultencoding("utf-8")

import re,argparse

traceSplitter=False

## generator that yields the next json object in input
#  by keeping track of the levels of braces and brackets not counting them within strings

## tokenizer adapted from https://docs.python.org/3.4/library/re.html#writing-a-tokenizer
def jsonSplitter(input):
    if traceSplitter:print "jsonSplitter:"+input
    token_specification = [
        ("SKIP",          r'\s+'), # skip blanks and newlines
         # escaped quoted string syntax taken from http://stackoverflow.com/questions/16130404/regex-string-and-escaped-quote
        ("STRING",        r'"(?:\\.|[^"\\])*?"'+"|"+ r"'(?:\\.|[^'\\])*?'"),# double or single quoted string
        ("OPEN_BRACE",    r'\{'),
        ("CLOSE_BRACE",   r'\}'),
        ("OPEN_BRACKET",  r'\['),
        ("CLOSE_BRACKET", r'\]'),
        ("OTHER",         r'[^ \n{}[\]\"\']+')
    ]
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    level=0
    res=""
    for mo in re.finditer(tok_regex, input,re.DOTALL):
        kind = mo.lastgroup
        value = mo.group(kind)
        # print "mo:"+kind+":"+value
        if kind=="SKIP":continue
        if   kind=="OPEN_BRACKET"  or kind=="OPEN_BRACE" :level+=1
        elif kind=="CLOSE_BRACKET" or kind=="CLOSE_BRACE":level-=1
        elif kind=="STRING": res=res.replace('\n','\\n') # reinsert newlines within strings
        res+=value
        if traceSplitter: print str(level)+":"+res
        if level==0:
            yield res
            res=""

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description="Split stdin into single line JSON objects")
    parser.add_argument("--debug",help="Trace calls for debugging",action="store_true")
    args=parser.parse_args()
    if args.debug : traceSplitter=True
    # it seems that sys.stdin.read() does not work from the console... but readlines() does
    splitter = jsonSplitter("".join(sys.stdin.readlines())) 
    try:
        while True:
            jsonUnit=splitter.next()
            print jsonUnit
    except StopIteration:
            pass
