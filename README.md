JSON validation with a RELAX-NG compact syntax
==============================================

[Guy Lapalme][], RALI-DIRO, Université de Montréal

# 1. Motivation

In the context of a research project, we received a file with millions of lines, each of which were in [JSON][]. We realized that although all lines were valid according to the JSON syntax, not all of them followed the same expected format. To borrow terms from the [XML jargon][], the JSON was well-formed, but not valid according to an agreed schema defining its intended syntax.

We looked for the equivalent of an XML Schema for JSON and became aware of the [JSON schema][] effort which defines the structure of JSON files by means of another JSON file. This approach is similar to what has been done with [XML Schema][] or [Relax-NG][] that are themselves defined in XML.

We found this JSON Schema notation quite cumbersome, so we looked for an alternative similar to the [compact syntax of Relax-NG][]. The only reference we could find was in the form of an [unimplemented proposal][] by [Egbert Teeselink][]. So we decided to implement a similar proposal for our needs.

Moreover, JSON Schema validators that we experimented with were limited to the validation of a single JSON object and stopped at the first error with a simple pass or fail diagnostic; they were not giving any hints as the position of the error value within the object.

Section 2 presents the JSON-RNC syntax which is an adaptation of the compact syntax of Relax-NG to the particular case of JSON. The goal of the specification is to be as intuitive as possible in order to mimic the skeleton of a valid JSON value. It can be understood as an abstraction of the JSON value in which the value corresponding to a key is replaced by its type. Section 3 gives examples of use and section 4 briefly sketches its Python implementation. Section 5 describes how to call the validation process installed with instructions given in section 6.

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
  - the keys are always strings; they must be quoted in the JSON value but do not have to be quoted in the JSON-RNC schema.
-   a **JSON array type** defined with a type within square brackets; all elements in the array will have to match this type; so `[{a:string, b:number}]` will match a list of objects each being composed of the same two key-value pairs.
-   a **list of types separated by a vertical bar** indicating that the object must match one of these types; for example `integer|{a:string}` will match either an integer or an object with a single key `a`.
-   a **type within parentheses** for grouping, most often choices between alternatives.
-   an **identifier** which should refer to an existing type definition; forward references are accepted but all references must have been defined at the end of the JSON-RNC file.
-   although it defeats the purpose of a validator, we found it useful to allow to skip the validation of an object or an array by indicating an empty object (`{}`) or an empty array (`[]`).


A simple type can be followed by a *facets* as they are called in [XML Schema][] which define constraints on the value of the type. Facets are called validation keywords in [JSON-Schema][]. Facets are defined with list of pairs of validation keywords followed by an equal sign and a value. All facets are written within parentheses preceded by the at-sign (`@`). The currently implemented facets are:

-   `pattern`: defines a regular expression that the string value should match). For example: `string@(pattern="[A-Z][0-9]")` would match a two character string, the first character being a capital letter and the second a digit. As this is an often encountered facet, a pattern facet can also be written within slashes provided the regular expression does not contain a slash. So the previous type could be written simply as `/[A-Z][0-9]/`.
-   `minLength`, `maxLength` specifies the minimum (resp. maximum) length of the string value.
-   `minimum`, `maximum` specifies the minimum (resp. maximum) value a numeric value can take.
-   `minimumExclusive`, `maximumExclusive` is a boolean (`true` or `false`) that indicates whether the allowed value includes the specified minimum (resp. maximum)

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
    property    = identifier , ["?"] , ":" , type  | "(" , properties , ")" ;
    facets      = "@(" , facetId , "=" , value , {",", facetId , "=" , value } ")" ;
    facetId     = "minimum" | "minimumExclusive" | "maximum" | "maximumExclusive"   (* for numbers *)
                  | "pattern" | "minLength" | "maxLength" ;                         (* for strings *)

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

    start = [(BookList | Store)]

    BookList = { books: [ Book ], owner: string }

    Book = {
      title: string, subtitle?: string, author: string,
      ISBN: string,  weight: number,    type: BookType,
      # add keys with 'special' names
      "number"?: integer, "$id"?: string 
    }

    Store = { name: string, url: string }

    BookType = (/Paperback/ | /Hardcover/)

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

-   A recursive descent parser checks if the JSON-RNC follows the syntax and semantics of the specification language and outputs appropriate error messages. The parser transforms the JSON-RNC input into a Python dictionary which, when serialized in JSON, is a valid [JSON Schema V-4][]. Only a small subset of the [JSON schema][] specification is used. For example, the JSON Schema corresponding to our first example is the following:

        {"definitions":{"start":{"$ref":"#/definitions/person"},
                        "cpRE":{"pattern":"[A-Z][0-9][A-Z] [0-9][A-Z][0-9]",
                                "type":"string"},
                        "person":{"required":["name",
                                              "id",
                                              "address"],
                                  "type":"object",
                                  "properties":{"postalCode":{"$ref":"#/definitions/cpRE"},
                                                "address":{"minimum":"minimum",
                                                           "type":"number",
                                                           "maximum":"maximum"},
                                                "name":{"type":"string"},
                                                "id":{"oneOf":[{"type":"string"},
                                                               {"required":["no"],
                                                                "type":"object",
                                                                "properties":{"no":{"type":"number"}}}]}}}},
         "$schema":"http://json-schema.org/draft-04/schema#",
         "title":"Created from JSON-RNC: Tests/Test1.jsonrnc",
         "description":"Written: 2015-04-04 21:06",
         "$ref":"#/definitions/person"}

-   If the previous step is successful, the resulting schema is used as input to a validation process against a file containing JSON objects. Appropriate error messages are output when an *invalid* JSON object is encountered.
-   Some care is taken not to recompile a schema that has not changed between validations over different files.

# 5. Using the validator


**Validation** of a JSON file (`f.json`) in which each line is a JSON object validated according to a JSON-RNC schema:

    ./ValidateJsonRnc.py schema.jsonrnc f.json

- If JSON objects are not on a single line, adding `-s` optional flag will split and merge them on a single line.
- Objects that do not conform to the schema are usually identified by their line number in the file. If another field or sequence of fields could prove more useful as identification, it can be specified as the value for the `-id` optional flag. Its value is a list of keys each separated by a slash (e.g. `'_id/$oid'`) ([JSON Pointer][] notation).

**Splitting and flattening of a JSON file** can be done with:

    ./SplitJson.py

If the JSON file has objects spanning many lines of the input, its format can be reorganized with this filter that reads the standard input for JSON objects and outputs each JSON object on a single line. Newlines within strings are replaced with `\n` so that they are correctly read back.

**Parsing** the schema can be also done separately to produce on stdout a pretty-printed JSON file with the Python data structure using:

    ./ParseJsonRnc.py schema.jsonrnc

If no schema file is given it will process the standard input.

# 6. Installation

Python 2.7 source files are in the Src directory and a few examples can be found in the Tests directory.

  [JSON Pointer]: http://tools.ietf.org/html/draft-ietf-appsawg-json-pointer-07#section-5
  [JSON Schema V-4]: http://json-schema.org/documentation.html "JSON Schema - Documentation"
  [JSON schema]: http://json-schema.org "JSON Schema and Hyper-Schema"
  [original example of Egbert Teeselink]: https://github.com/eteeselink/relax-json
  [EBNF grammar]: http://www.wikiwand.com/en/Extended_Backus–Naur_Form
  [XML Schema]: http://www.w3.org/TR/xmlschema-2/#rf-facets "XML Schema Part 2: Datatypes Second Edition"
  [JSON-Schema]: http://json-schema.org/latest/json-schema-validation.html "JSON Schema: interactive and non interactive validation"
  [Guy Lapalme]: http://www.iro.umontreal.ca/~lapalme
  [JSON]: http://json.org "JSON"
  [XML jargon]: http://www.iro.umontreal.ca/~lapalme/ForestInsteadOfTheTrees/HTML/index.html "XML: Looking at the Forest Instead of the Trees"
  [JSON schema]: http://json-schema.org "JSON Schema and Hyper-Schema"
  [XML Schema]: http://www.w3.org/XML/Schema "W3C XML Schema"
  [Relax-NG]: http://www.relaxng.org "RELAX NG home page"
  [compact syntax of Relax-NG]: http://www.relaxng.org/compact-20021121.html "RELAX NG Compact Syntax"
  [unimplemented proposal]: https://github.com/eteeselink/relax-json
  [Egbert Teeselink]: http://superset.eu "superset - good software"
  