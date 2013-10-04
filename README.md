## xmlu
#### A simple XML unmarshalling library.

Uses lxml.etree if available, xml.etree.ElementTree otherwise.

Example usage:
```python
>>> import xmlu
>>> from lxml import etree
>>> xml = etree.fromstring('<foo bar="baz"><a/><b><s>qwe</s><s>asd</s></b><c x="y"/><c x="z"/><c/><i>200</i></foo>')
>>> class MyObject(xmlu.Object):
...     _name = 'foo' # _name, _none and other parameters can be specified this way; unnecessary in root object
...     bar = xmlu.Attribute() # Attribute is handled specially, it works on the same node as Object
...     b = xmlu.List(xmlu.Str()) # List will handle all nodes inside a node
...     c = xmlu.Many(xmlu.AttributeOf('x'), name='c') # Many is a special List
...     num = xmlu.Int(name='i') # A standard Python type; name parameter is used instead of field name
... 
>>> unmarshalled = MyObject()(xml)
>>> print unmarshalled.bar
baz
>>> print unmarshalled['bar']
baz
>>> print unmarshalled
{'c': ['y', 'z', None], 'b': ['qwe', 'asd'], 'bar': 'baz', 'num': 200}
```
