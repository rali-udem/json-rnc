#!/usr/bin/python
# coding=utf-8
schema={'$ref': '#/definitions/debut',
 '$schema': 'http://json-schema-rnc.org',
 'definitions': {'debut': {'properties': {'address': {'properties': {'city': {'type': 'string'},
                                                                     'streetAddress': {'type': 'string'}},
                                                      'required': ['city'],
                                                      'type': 'object'},
                                          'phoneNumber': {'items': {'properties': {'code': {'type': 'integer'},
                                                                                   'location': {'type': 'string'}},
                                                                    'required': ['location',
                                                                                 'code'],
                                                                    'type': 'object'},
                                                          'type': 'array'}},
                           'required': ['address', 'phoneNumber'],
                           'type': 'object'}}}