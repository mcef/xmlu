'''xmlu: a simple XML unmarshalling library

Uses lxml.etree if available, xml.etree.ElementTree otherwise.

Example usage:

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
{'c': ['y', 'z', None], 'b': ['qwe', 'asd'], 'bar': 'baz', 'num': 200}'''

try:
    from lxml import etree
except ImportError:
    from xml.etree import ElementTree as etree

class Type(object):
    '''Base class that represents types XML can be unmarshalled to..

    An instance of this type or its child types can be called, given an
    instance of etree._Element (etree being lxml.etree if available, else
    xml.etree.ElementTree).
    Child classes should implement the _convert method and may reimplement
    __init__, but should still have **kwargs in argument list and call
    Type.__init__(self, **kwargs) right after being called.'''
    def __init__(self, name=None, none=True):
        '''The constructor for a Type.

        Parameters:
        name: The name of the XML tag that should be unmarshalled with this
              type. If None, the tag name is taken from the field name this
              type is stored as in the Object. Stored into self._name.
        none: If True, any null XML values will be stored as None instead of
              being given to the Python type's constructor. Stored into
              self._none.

        The parameters will be ignored if the field name already exists in
        the class. Child types should act the same way with their parameters.'''
        if not hasattr(self, '_name'):
            self._name = name
        if not hasattr(self, '_none'):
            self._none = none

    def __call__(self, v):
        '''Calls self._convert(v).'''
        return self._convert(v)

    def _convert(self, v):
        '''Convert a etree._Element into an instance of the Python type
        represented by this class.
        
        Not implemented in Type. Child types should override this with their
        own methods.'''
        raise NotImplementedError()

class Object(Type):
    '''An object with predefined fields.

    Any fields that are an instance of Type and don't start with _ are
    converted into the type they represent.
    If the field has a non-None ._name, it is given the xml._Element with
    the tag corresponding to that name. Otherwise, its field name is used.
    Users should either extend this class, adding new Type fields, or create
    an instance of it and assign Type instances to its fields.
    
    Example usage:
    >>> xml = etree.fromstring('<foo bar="baz"><a/><b><s>qwe</s><s>asd</s></b><c x="y"/><c x="z"/><c/><i>200</i></foo>')
    >>> class MyObject(xmlu.Object):
    ...     _name = 'foo'
    ...     bar = xmlu.Attribute()
    ...     b = xmlu.List(xmlu.Str())
    ...     c = xmlu.Many(xmlu.AttributeOf('x'), name='c')
    ...     num = xmlu.Int(name='i')
    ... 
    >>> MyObject()(xml)
    {'c': ['y', 'z', None], 'b': ['qwe', 'asd'], 'bar': 'baz', 'num': 200}'''
    class _Object(object):
        def __init__(self):
            pass
        def __bool__(self):
            return bool(self.__dict__)
        def __contains__(self, key):
            return key in self.__dict__
        def __getitem__(self, key):
            return self.__dict__[key]
        def __iter__(self):
            return iter(self.__dict__)
        def __len__(self):
            return len(self.__dict__)
        def __repr__(self):
            return repr(self.__dict__)
        def __str__(self):
            return str(self.__dict__)
        def get(self, key, default=None):
            return self.__dict__.get(key, default)
        def has_key(self, key):
            return self.__dict__.has_key(key)
        def items(self):
            return self.__dict__.items()
        def iteritems(self):
            return self.__dict__.iteritems()
        def iterkeys(self):
            return self.__dict__.iterkeys()
        def itervalues(self):
            return self.__dict__.itervalues()
        def keys(self):
            return self.__dict__.keys()
        def values(self):
            return self.__dict__.values()
        def viewkeys(self):
            return self.__dict__.viewkeys()
        def viewvalues(self):
            return self.__dict__.viewvalues()

    def __init__(self, text=None, object=None, overwrite=False, **kwargs):
        '''The constructor.

        Parameters:
        text: If non-None and the XML node has any inner text, it's called
              with one string parameter containing the text, which it should
              convert to a Python type and return. The result is stored into
              self._text. If None, self._text is set to None.
        object: A function/type to use as the base object. Converted fields
                are added with setatrr and it should support hasattr too.
                If None, self._Object, a dict-like object, is used.
        overwrite: If True, fields are overwriten on duplicate tags, the last
                   one kept in the object. If False, only the first tag with
                   matching name is stored.'''
        Type.__init__(self, **kwargs)
        if not hasattr(self, '_object'):
            self._object = self._Object if object is None else object
        if not hasattr(self, '_text'):
            self._text = text
        if not hasattr(self, '_overwrite'):
            self._overwrite = overwrite

    def _convert(self, v):
        obj = self._object()
        mapping = {}
        for key in dir(self):
            if key and key[0] != '_':
                val = getattr(self, key)
                if isinstance(val, Type) and (self._overwrite or not hasattr(obj, key)):
                    if isinstance(val, Attribute):
                        if getattr(val, '_name', None) is None:
                            val._name = key
                        setattr(obj, key, val(v))
                    elif isinstance(val, Many):
                        setattr(obj, key, val(v))
                    else:
                        if val._name is not None:
                            mapping[val._name] = (key, val)
                        else:
                            mapping[key] = (key, val)
        for node in v:
            if node.tag in mapping:
                setattr(obj, mapping[node.tag][0], mapping[node.tag][1](node))
        if self._text is not None:
            if v.text is not None:
                obj._text = self._text(v.text)
            else:
                obj._text = None
        return obj

class List(Type):
    '''A Type representing a Python list with elements of one type.

    Example usage:
    >>> xml = etree.fromstring('<a><b>12</b><b>34</b><b>56</b><c>foo</c></a>')
    >>> xmlu.List(xmlu.Int(), tag='b', name='a')(xml)
    [12, 34, 56]'''
    def __init__(self, type, tag=None, **kwargs):
        '''The constructor.

        Parameters:
        type: The Type to convert elements to.
        tag: If not None, only elements with matching tag are included.'''
        Type.__init__(self, **kwargs)
        if not hasattr(self, '_type'):
            self._type = type
        if not hasattr(self, '_tag'):
            self._tag = tag

    def _convert(self, v):
        l = []
        for node in v:
            if self._tag is None or self._tag == node.tag:
                l.append(self._type(node))
        return l

class Many(Type):
    '''A Type representing a Python list with elements of one type.

    While otherwise almost like List, this type is handled specially by
    Object. Instead of giving it a node that's a child of the Object's node,
    this works on the same node as the Object.

    Example usage:
    >>> xml = etree.fromstring('<a><b>12</b><b>34</b><b>56</b><c>foo</c></a>')
    >>> myobj = xmlu.Object()
    >>> myobj.b = xmlu.Many(xmlu.Int(), name='b')
    >>> myobj(xml)
    {'b': [12, 34, 56]}'''
    def __init__(self, type, name, **kwargs):
        '''The constructor.

        Parameters:
        type: The Type to convert elements to.
        name: Only elements with tags matching this will be included.'''
        Type.__init__(self, name=name, **kwargs)
        if not hasattr(self, '_type'):
            self._type = type

    def _convert(self, v):
        l = []
        for node in v:
            if self._name is None or node.tag == self._name:
                l.append(self._type(node))
        return l

class Dict(Type):
    '''A Type representing a Python dict with elements of one type.

    Example usage:
    >>> xml = etree.fromstring('<x><a>12</a><b>34</b><c>56</c><a>78</a></x>')
    >>> xmlu.Dict(xmlu.Int())(xml)
    {'a': 12, 'c': 56, 'b': 34}
    >>> xmlu.Dict(xmlu.Int(), overwrite=True)(xml)
    {'a': 78, 'c': 56, 'b': 34}'''
    def __init__(self, type, overwrite=False, **kwargs):
        '''The constructor.

        Parameters:
        type: The Type to convert elements to.
        overwrite: If True, elements are overwriten on duplicate tags, the
                   last one kept in the dict. If False, only the first tag
                   with matching name is stored.'''
        Type.__init__(self, **kwargs)
        if not hasattr(self, '_type'):
            self._type = type
        if not hasattr(self, '_overwrite'):
            self._overwrite = overwrite

    def _convert(self, v):
        d = {}
        for node in v:
            if self._overwrite or node.tag not in d:
                d[node.tag] = self._type(node)
        return d

class Attribute(Type):
    '''A Type representing a tag's attribute.

    While otherwise almost like AttributeOf, this type is handled specially by
    Object. Instead of giving it a node that's a child of the Object's node,
    this works on the same node as the Object.

    Example usage:
    >>> xml = etree.fromstring('<x a="b"/>')
    >>> myobj = xmlu.Object()
    >>> myobj.a = xmlu.Attribute()
    >>> myobj.b = xmlu.Attribute(name='a')
    >>> myobj(xml)
    {'a': 'b', 'b': 'b'}'''
    def __init__(self, name=None, type=None, **kwargs):
        '''The constructor.

        Parameters:
        name: The tag name. If None, the Object field's name is used instead.
        type: The python type to convert the attribute to. It is called with
              one string parameter. If None, str is used.'''
        Type.__init__(self, name=name, **kwargs)
        if not hasattr(self, '_type'):
            if type is None:
                self._type = str
            else:
                self._type = type

    def _convert(self, v):
        s = v.attrib.get(self._name, None)
        if s is None and self._none:
            return None
        return self._type(s)

class AttributeOf(Type):
    '''A Type representing a tag's attribute.

    Example usage:
    >>> xml = etree.fromstring('<x a="b"/>')
    >>> xmlu.AttributeOf('a')(xml)
    'b' '''
    def __init__(self, attr, type=None, **kwargs):
        '''The constructor.

        Parameters:
        attr: The name of the attribute.
        type: The python type to convert the attribute to. It is called with
              one string parameter. If None, str is used.'''
        Type.__init__(self, **kwargs)
        if not hasattr(self, '_attr'):
            self._attr = attr
        if not hasattr(self, '_type'):
            if type is None:
                self._type = str
            else:
                self._type = type

    def _convert(self, v):
        s = v.attrib.get(self._attr, None)
        if s is None and self._none:
            return None
        return self._type(s)

class Int(Type):
    '''A Type representing a Python int.

    Example usage:
    >>> xml = etree.fromstring('<a>1</a>')
    >>> xmlu.Int()(xml)
    1'''
    def _convert(self, v):
        if v.text is None and self._none:
            return None
        return int(v.text)

class Float(Type):
    '''A Type representing a Python float.

    Example usage:
    >>> xml = etree.fromstring('<a>1.1</a>')
    >>> xmlu.Float()(xml)
    1.1'''
    def _convert(self, v):
        if v.text is None and self._none:
            return None
        return float(v.text)

class Complex(Type):
    '''A Type representing a Python complex.

    Example usage:
    >>> xml = etree.fromstring('<a>1.1+2.2j</a>') # all i are replaced with j
    >>> xmlu.Complex()(xml)
    (1.1+2.2j)'''
    def _convert(self, v):
        if v.text is None and self._none:
            return None
        return complex(v.text.replace('i', 'j'))

class Str(Type):
    '''A Type representing a Python str.

    Example usage:
    >>> xml = etree.fromstring('<a>foo  </a>')
    >>> xmlu.Str()(xml)
    'foo  '
    >>> xmlu.Str(strip=True)(xml)
    'foo' '''
    def __init__(self, strip=False, **kwargs):
        '''The constructor.

        Parameters:
        strip: If True, .strip() is called on the string.'''
        Type.__init__(self, **kwargs)
        self._strip = strip

    def _convert(self, v):
        if v.text is None and self._none:
            return None
        if isinstance(v.text, str):
            if self._strip:
                return v.text.strip()
            return v.text
        if self._strip:
            return v.text.encode('utf-8').strip()
        return v.text.encode('utf-8')

class Unicode(Type):
    '''A Type representing a Python unicode.

    Example usage:
    >>> xml = etree.fromstring('<a>foo  </a>')
    >>> xmlu.Unicode()(xml)
    u'foo  '
    >>> xmlu.Unicode(strip=True)(xml)
    u'foo' '''
    def __init__(self, strip=False, **kwargs):
        '''The constructor.

        Parameters:
        strip: If True, .strip() is called on the string.'''
        Type.__init__(self, **kwargs)
        self._strip = strip

    def _convert(self, v):
        if v.text is None and self._none:
            return None
        if self._strip:
            return unicode(v.text).strip()
        return unicode(v.text)

class Bool(Type):
    '''A Type representing a Python bool.

    This does not work the same as Python's bool().
    The following strings, case insensitive and stripped, are treated as True:
    'true', 't', '1', 'yes', 'y'

    Example usage:
    >>> xmlu.Bool(etree.fromstring('<a>true</a>'))
    True
    >>> xmlu.Bool(etree.fromstring('<a>foo bar</a>'))
    False'''
    def _convert(self, v):
        if v.text is None and self._none:
            return None
        if v.text.strip().lower() in ('true', 't', '1', 'yes', 'y'):
            return True
        return False

class Element(Type):
    '''A Type representing an etree._Element.

    This works as an identity function; the same element given as a parameter
    is returned. Type's none parameter is ignored.
    
    Example usage:
    >>> xml = etree.fromstring('<a/>')
    >>> e = xmlu.Element()(xml)
    >>> e is xml
    True'''
    def _convert(self, v):
        return v

class Value(Type):
    '''A Type representing a constant value.

    This will always return the same value, regardless of the XML node.
    
    Example usage:
    >>> xml = etree.fromstring('<a qwe="asd"><b>zxc</b></a>')
    >>> print xmlu.Value(123)(xml)
    123'''
    def __init__(self, value, **kwargs):
        '''The constructor.

        Parameters:
        value: The value to return.'''
        Type.__init__(self, **kwargs)
        self._value = value

    def _convert(self, v):
        return self._value

def unmarshal(xml, type):
    '''A helper function for unmarshalling xml.

    If xml is instance of basestring, calls type(etree.fromstring(xml)).
    If xml is instace of etree._Element, calls type(xml).
    Else, calls type(etree.parse(xml)).'''
    if isinstance(xml, etree._Element):
        pass
    if isinstance(xml, basestring):
        xml = etree.fromstring(xml)
    else:
        xml = etree.parse(xml)
    return type(xml)
