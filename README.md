JSON validation with a RELAX-NG compact syntax
==============================================

[Guy Lapalme][], RALI-DIRO, Université de Montréal

Motivation
----------

In the context of a research project, we received a file with millions of lines, each of which were in [JSON][]. We realized that although all lines were valid according to the JSON syntax, not all of them followed the same expected format. To borrow terms from the [XML jargon][], the JSON was well-formed, but not valid according to an agreed schema defining its intended syntax.

We looked for the equivalent of an XML Schema for JSON and became aware of the [JSON schema][] effort which defines the structure of JSON files by means of another JSON file. This approach is similar to what has been done with [XML Schema][] or [Relax-NG][] that are themselves defined in XML.

We found this JSON Schema notation quite cumbersome, so we looked for an alternative similar to the [compact syntax of Relax-NG][]. The only reference we could find was in the form of an [unimplemented proposal][] by [Egbert Teeselink][]. So we decided to implement a similar proposal for our needs.

Moreover, JSON Schema validators that we experimented with were limited to the validation of a single JSON object and stopped at the first error with a simple pass or fail diagnostic; they were not giving any hints as the position of the error value within the object.

The complete documentation is in file index.html or on [RALI's website][].


  [Guy Lapalme]: http://www.iro.umontreal.ca/~lapalme
  [JSON]: http://json.org "JSON"
  [XML jargon]: http://www.iro.umontreal.ca/~lapalme/ForestInsteadOfTheTrees/HTML/index.html "XML: Looking at the Forest Instead of the Trees"
  [JSON schema]: http://json-schema.org "JSON Schema and Hyper-Schema"
  [XML Schema]: http://www.w3.org/XML/Schema "W3C XML Schema"
  [Relax-NG]: http://www.relaxng.org "RELAX NG home page"
  [compact syntax of Relax-NG]: http://www.relaxng.org/compact-20021121.html "RELAX NG Compact Syntax"
  [unimplemented proposal]: https://github.com/eteeselink/relax-json
  [Egbert Teeselink]: http://superset.eu "superset - good software"
  [RALI's website]: http://www-labs.iro.umontreal.ca/~lapalme/JSON-RNC/Json-RelaxNG-compact.html
  