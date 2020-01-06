JSON (lines) validation with a RELAX-NG compact syntax
==============================================

[Guy Lapalme][], RALI-DIRO, Université de Montréal

# 1. Motivation

In the context of a research project, we received files with millions of lines, each of which were in [JSON][]: they were in [JSON lines][] format. We realized that although all lines were valid according to the JSON syntax (they had been created by a program after all), not all of them followed the same expected format by our application, because the web scraping process used was not very reliable. To borrow terms from the [XML jargon][], the JSON was well-formed, but not valid according to an agreed schema defining its intended syntax.

We looked for the equivalent of an XML Schema for JSON and became aware of the [JSON schema][] effort which defines the structure of JSON files by means of another JSON file. This approach is similar to what has been done with [XML Schema][] or [Relax-NG][] that are themselves defined in XML.

As we found the *JSON schema* notation too verbose (similar to XML-Schemas), we looked for an alternative akin to the [compact syntax of Relax-NG][]. The only reference we could find was in the form of an [unimplemented proposal][] by [Egbert Teeselink][]. So we decided to implement a similar proposal for validating *JSON lines* files. Of course, it can also be used for validating a single JSON structure.

Moreover, JSON Schema validators that we experimented at the time with were limited to the validation of a single JSON object and stopped at the first error with a simple pass or fail diagnostic; they were not giving any hints as the position of the error value within the object.

Section 2 presents the JSON-RNC syntax which is an adaptation of the compact syntax of Relax-NG to the particular case of JSON. The goal of the specification is to be as intuitive as possible in order to mimic the skeleton of a valid JSON value. It can be understood as an abstraction of the JSON value in which the value corresponding to a key is replaced by its type. This is similar to the recent systems that generate a *JSON schema* from a JSON record. Section 3 gives examples of use and section 4 briefly sketches its Python implementation which transforms the input in JSON-RNC syntax into a valid *JSON schema* which is then interpreted during validation. Section 5 describes how to apply the validation process installed with instructions given in section 6.

Although the JSON-RNC parser can be seen as a preprocessor for *JSON schema*, it does not deal with all the *JSON schema* validation cases, even though it might be an interesting exercise to try.

# 2. JSON-RNC

A JSON-RNC specification is a list of type definitions each of which is an identifier followed by an equal sign and a *type*. The *root* definition is the one associated with the `start` keyword.

A *type* can be one of the following:

- a **simple JSON type** indicated by one of the following keywords: `string`, `integer`, `number`, `boolean` and `null`.
- a **JSON object type** defined by a list of key-value pairs (we call them properties) within braces. A property is written as an identifier for the key, a colon and finally the type of its value.  
For example, `{a:string, b:number}` defines the type for an object with two key-value pairs: the first (`a`) should be associated with a string value, while the second (`b`) is associated with a number. It would thus deem valid the JSON object `{"a":"hello","b":3}`.  
The key does not need to be written within quotes if it is an *ordinary* identifier, i.e. it starts with a letter and only uses letters, numbers and underscores. But if the key name is the same as a keyword or uses *strange* characters such as a dollar sign, a dash or a dot, it must be put within quotes.  
Here are a few remarks about keys:
  - in a JSON object, all keys must be different (this is checked by the schema validator), and there is no ordering between properties within a single object;
  - all keys specified in the schema must appear in the object, unless they are marked as *optional* by appending a question mark (`?`) to the key ;
  - the keys are always quoted strings in the JSON value; to simplify the JSON-RNC schema a key does not have to be quoted it only contains alphanumeric characters;
  - if the key field contains a single `*`, then the key values can be arbitrary strings but they must still all be different; this is useful when a object is used a *data base* in which keys can be any string but are all different to uniquely identify a record; but the structure of each record should be validated.
-   a **list of types separated by a vertical bar** indicating that the object must match one of these types; for example `integer|{a:string}` will match either an integer or an object with a single key `a`.
-   a **JSON array type** defined with a type or a list of types; all elements in the array will have to match this type; so `[{a:string, b:number}]` will match a list of objects each being composed of the same two key-value pairs. An empty array (`[]`) will also match this expression.
-   a **type within parentheses** for grouping, most often choices between alternatives.
-   an **identifier** which should refer to an existing type definition; forward references are accepted but all references must have been defined at the end of the JSON-RNC file.
-   although it defeats the purpose of a validator, we found it useful to allow to skip the validation of an object or an array by indicating an empty object (`{}`) or an empty array (`[]`). To explicitly match an empty array, use `[]@(maxItems=0)`. To match an empty object, use `{}@(maxProperties=0)`.


A simple type can be followed by a *facets* as they are called in [XML Schema][] which define constraints on the value of the type. Facets are called validation keywords in [JSON-Schema][]. Facets are defined with list of pairs of validation keywords followed by an equal sign and a value. All facets are written within parentheses preceded by the at-sign (`@`). The currently implemented facets are:

-   `pattern`: defines a regular expression that the string value should match). For example: `string@(pattern="[A-Z][0-9]")` would match a two character string, the first character being a capital letter and the second a digit. Note that the pattern is checked as being *anchored*, i.e. the expression must match the whole value. As this is an often encountered facet, a pattern facet can also be written within slashes provided the regular expression does not contain a slash. So the previous type could be written simply as `/[A-Z][0-9]/`. In particular, // should be used to match a value which is an empty string.
-   `minLength`, `maxLength` specifies the minimum (resp. maximum) length of the string value.
-   `minimum`, `maximum` specifies the minimum (resp. maximum) value a numeric value can take.
-   `exclusiveMinimum`, `exclusiveMaximum` is a boolean (`true` or `false`) that indicates whether the allowed value includes the specified minimum (resp. maximum)
-   `minItems`,`maxItems` specifies the minimum (resp. maximum) number of elements in the array
-   `minProperties`,`maxProperties` specifies the minimum (resp. maximum) number of properties in the object

### 2.1 EBNF specification of JSON-RNC

This specification of JSON-RNC definitions is formalized the following [EBNF grammar][], `definitions` being the starting symbol. Terminals are written between quotation marks, comma indicates concatenation, alternation is marked with a vertical bar (`|`), parentheses are used for grouping, brackets `[ ]` indicate an optional part and braces `{ }` indicate repetition 0 or more times of its content. Comments in the grammar are indicated between starred parentheses `(* *)`.

    definitions = "start" = type | {definition} ;
    definition  = (identifier | string ) , ["=" , types] ; 

    types       = type , ( {"," , type} | {"|" , type} ) ;
    type        = ("string" | "integer" | "number" | "boolean" | "null"     (* primitive types *) 
                   | identifier | string                                    (* name of a user defined type *) 
                   | "/", character-"/" , "/"                               (* regular expression without a slash *) 
                  ) , [facets]                                              
                  | "{" , [properties] , "}"                                (* object *) 
                  | "[" , [type]  , "]"                                     (* array *) 
                  | "(" , types   , ")" ;                                   (* grouping *) 
    properties  = property , {(",") , property} ;
    property    = (identifier , ["?"] , ":" , type | "*")  | "(" , properties , ")" ;
    facets      = "@(" , facetId , "=" , value , {",", facetId , "=" , value } ")" ;
    facetId     = "minimum" | "exclusiveMinimum" | "maximum" | "exclusiveMaximum"   (* for numbers *)
                  | "pattern" | "minLength" | "maxLength"                           (* for strings *)
                  | "minItems" | "maxItems"                                         (* for arrays *)
                  | "minProperties" | "maxProperties";                              (* for objects *)

    identifier  = letter , { letter | digit | "_" } ;
    number      = [ "-" ], digit, { digit } ["." , digit, { digit }];
    string      =   "'" , character , { character } , "'" 
                  | '"' , character , { character } , '"' ;
    value       = number | string | "true" | "false" | "null";

Comments in a schema appear after a dash `#`. The comment runs until the end of the current line. Spaces, tabs and newlines can be used freely except for delimiting comments and identifiers and patterns.

**Important**: note that a definition can only define a `type`, not `properties`.

# 3. Examples of schema

### 3.1 Simple example

Given the following schema

    # a comment to skip
    start = person
    person = {name:string,
              id:(string|{no:number}),
              address:number@(minimum=10,maximum=100),
              postalCode? : cpRE
    }
    cpRE = /[A-Z][0-9][A-Z] [0-9][A-Z][0-9]/

The first line is a comment, the second line indicates that the root type is the one given by the definition of `person` which is an object with four properties with the following keys:

-   `name` whose value is a string
-   `id` whose value can either be a string or an object with a property named `no`
-   `address` associated with a number between 10 and 100
-   `postalcode` whose value is a string matching a regular expression, but this property is optional

When the following JSON objects

    {"name":"Guy","id":"Lapalme","address":45, "postalCode":"H0H 0H0"}
    {"id":{"no":24},"name":"Luc","address":75}
    {"id":true,"address":3,"name":null}

are validated against the above schema, it will validate the first two JSON but will output the following error messages for the third object:

    3:{u'id': True, u'name': None, u'address': 3}
    name :: string expected =>null
    id :: object expected:true
    address :: illegal facet: value 3 not between 10 and 100

    3 objects read: 1 invalid

The first line indicates the record number of the invalid JSON object (limited to 100 characters) and then indicates that wrong types were encountered for `name` and `id`, while the value for the `address` property does not lie between the `minimum` and `maximum` allowed bounds.

### 3.2 A more complete example

Here is our formulation of the [original example of Egbert Teeselink][]

    ## adaptation of the "contrived example" of relax-json given at
    ##     https://github.com/eteeselink/relax-json

    start = [BookList | Store]

    BookList = { books: [ Book ], owner: string }

    Book = {
      title: string, subtitle?: string, author: string,
      ISBN: string,  weight: number,    type: BookType,
      # add keys with 'special' names
      "number"?: integer, "$id"?: string 
    }

    Store = { name: string, url: string }

    BookType = /Paperback/ | /Hardcover/

which validates the following JSON array

    [{"owner":"George Clooney",
      "books":[{"type":"Paperback",
                "author":"Richard Scarry",
                "ISBN":"978-9024380329",
                "weight":112,
                "title":"Mijn leuk wereldje"},
               {"ISBN":"978-1559500401",
                "weight":130.4,
                "author":"Malaclypse the Younger",
                "$id":"C4567",
                "title":"Principia Discordia",
                "number":48,
                "subtitle":"Or, How I Found Goddess and What I Did to Her When I Found Her: The Magnum Opiate of Malaclypse the Younger",
                "type":"Hardcover"}]},
     {"owner":"George Bush",
      "books":[]},
     {"url":"http://www.amazon.com",
      "name":"Amazon"},
     {"url":"http://www.lulu.com",
      "name":"Lulu"}]

We leave it as an *exercise to the reader* to see why this JSON object (an array of either `Booklist` or `Store`) is valid against the above schema.

# 4. Implementation

We implemented the validation in Python in two steps.

-   A recursive descent parser checks if the JSON-RNC follows the syntax and semantics of the specification language and outputs appropriate error messages. The parser transforms the JSON-RNC input into a Python dictionary which, when serialized in JSON, is a valid [JSON Schema V-7][]. Only a small subset of the [JSON schema][] specification is used. For example, the JSON Schema corresponding to our first example is the following:

        {"$ref":"#/definitions/person",
         "$schema":"http://json-schema.org/draft-07/schema#",
         "definitions":{"cpRE":{"pattern":"[A-Z][0-9][A-Z] [0-9][A-Z][0-9]",
                                "type":"string"},
                        "person":{"additionalProperties":false,
                                  "properties":{"address":{"maximum":100,
                                                           "minimum":10,
                                                           "type":"number"},
                                                "id":{"oneOf":[{"type":"string"},
                                                               {"additionalProperties":false,
                                                                "properties":{"no":{"type":"number"}},
                                                                "required":["no"],
                                                                "type":"object"}]},
                                                "name":{"type":"string"},
                                                "postalCode":{"$ref":"#/definitions/cpRE"}},
                                  "required":["name","id","address"],
                                  "type":"object"}}}

-   If the previous step is successful, the resulting schema is used as input to a validation process against a file containing JSON objects. Appropriate error messages are output when an *invalid* JSON object is encountered.
-   Some care is taken not to recompile a schema that has not changed between validations over different files.

# 5. Using the validator


**Validation** of a JSON lines file (`f.jsonl`) in which each line is a JSON object validated according to a JSON-RNC schema:

    ./ValidateJsonRnc.py schema.jsonrnc f.jsonl

If no JSON lines file is specified, it validates the standard input.

*Command line arguments*

- *-s* or *--split* : if multiple JSON objects are on a single line or if a JSON spans multiple lines, the validator will split and merge them before validation. This argument is set by default if the source file has a `.json` extension.
- *-id* : objects that do not conform to the schema are usually identified by their line number in the file. If another field or sequence of fields could prove more useful as identification, it can be specified as the value for the `-id` optional flag. Its value is a list of keys each separated by a slash (e.g. `'_id/$oid'`) ([JSON Pointer][] notation). When the '-id' flag is given, the validator will check that ids are not repeated within the whole file.
- *-st* or *--stats* : at the end of execution, output the number of occurrences of each error message
- *--nolog* : do not output the error messages, usually in conjunction with *-st*
- *-sed* : output a list of erroneous line numbers in compatible format for use with the command "sed -n" to display the corresponding line
- *-h* or *--help* : output usage of the validator command

**Splitting and flattening of a JSON file** can be done with:

    ./SplitJson.py

If the JSON file has objects spanning many lines of the input, its format can be reorganized with this filter that reads the standard input for JSON objects and outputs each JSON object on a single line. Newlines within strings are replaced with `\n` so that they are correctly read back. This is the process used by the *-s* command argument of the validator.

**Parsing** the schema can be also done separately to produce on stdout a pretty-printed JSON file with the Python data structure using:

    ./ParseJsonRnc.py schema.jsonrnc


# 6. Installation

Python 2.7 source files are in the `Src` directory and a few examples can be found in the `Tests` directory.

  [JSON Pointer]: http://tools.ietf.org/html/draft-ietf-appsawg-json-pointer-07#section-5
  [JSON Schema V-7]: http://json-schema.org/documentation.html "JSON Schema - Documentation"
  [JSON schema]: http://json-schema.org "JSON Schema and Hyper-Schema"
  [original example of Egbert Teeselink]: https://github.com/eteeselink/relax-json
  [EBNF grammar]: http://www.wikiwand.com/en/Extended_Backus–Naur_Form
  [XML Schema]: http://www.w3.org/TR/xmlschema-2/#rf-facets "XML Schema Part 2: Datatypes Second Edition"
  [JSON-Schema]: http://json-schema.org/latest/json-schema-validation.html "JSON Schema: interactive and non interactive validation"
  [Guy Lapalme]: http://www.iro.umontreal.ca/~lapalme
  [JSON]: http://json.org "JSON"
  [JSON lines]: http://jsonlines.org "JSON Lines"
  [XML jargon]: http://www.iro.umontreal.ca/~lapalme/ForestInsteadOfTheTrees/HTML/index.html "XML: Looking at the Forest Instead of the Trees"
  [JSON schema]: http://json-schema.org "JSON Schema and Hyper-Schema"
  [XML Schema]: http://www.w3.org/XML/Schema "W3C XML Schema"
  [Relax-NG]: http://www.relaxng.org "RELAX NG home page"
  [compact syntax of Relax-NG]: http://www.relaxng.org/compact-20021121.html "RELAX NG Compact Syntax"
  [unimplemented proposal]: https://github.com/eteeselink/relax-json
  [Egbert Teeselink]: http://superset.eu "superset - good software"
  