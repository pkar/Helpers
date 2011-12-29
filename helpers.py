#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
# pylint: disable-msg=

""" General helper functions

.. moduleauthor:: Paul Karadimas <paulkar@gmail.com>

"""

import os
#import sys
import re
import pytz
from datetime import datetime, timedelta, tzinfo
import cPickle
import zlib
import json
import time
import random
#from itertools import izip, cycle

#import sys
#sys.setrecursionlimit(4000)
#PICKLE_MAX_RECURSION_DEPTH = 4000

from HTMLParser import HTMLParser, HTMLParseError

class MLStripper(HTMLParser):
    """ HTML tag remover

    """
    def __init__(self):
        """ _

        """
        self.reset()
        self.fed = []

    def handle_data(self, data):
        """  _

        """
        self.fed.append(data)

    def get_data(self):
        """ n/a

        """
        return ' '.join(self.fed)

def strip_tags(html):
    """ Remove any html tags from a string
    Attempts to use MLStripper, if it fails
    then a simple regex is used

    Args:
        * `html` (str): html string

    Returns:
        ``str``.
    """
    stripped = ''
    mls = MLStripper()
    try:
        mls.feed(html)
        stripped = mls.get_data()
    except HTMLParseError:
        stripped = re.sub(r'<[^>]*?>', ' ', html)

    return stripped

def json_prep(obj):
    """ Prepare any type of object for conversion to json by:
        1. Converting datetime objects to ISO8601 format.
    
    Returns:
        * A copy of the object

    """
    if isinstance(obj, dict):
        return_dict = {}
        for key, value in obj.items():
            return_dict[key] = json_prep(value)
        return return_dict
            
    if isinstance(obj, list):
        return_list = []
        for value in obj:
            return_list.append(json_prep(value))
        return return_list
    
    if isinstance(obj, datetime):
        return encode_datetime(obj, add_html=False)

    if isinstance(obj, ObjectId):
        return str(obj)
    
    return obj

def zdumps(obj):
    """ Helpers to serialize and compress objects

    Args:
        * `obj` (object): object to compress and serialize

    Returns:
        ``str``. 

    """
    #sys.setrecursionlimit(PICKLE_MAX_RECURSION_DEPTH)
    return zlib.compress(cPickle.dumps(obj, cPickle.HIGHEST_PROTOCOL))

def bin_zdumps(obj):
    """ Helper to serialize and compress objects and 
    convert to mongo Binary format safe for insert

    Args:
        * `obj` (object): object to compress and serialize

    Returns:
        ``Binary``. 

    """
    return Binary(zdumps(obj))

def zloads(zstr):
    """ Helper to uncompress and deserialize an object
    Args:
        * `zstr` (str): compressed and serialized object

    Returns:
        ``object``. 
    """
    #sys.setrecursionlimit(PICKLE_MAX_RECURSION_DEPTH)
    return cPickle.loads(zlib.decompress(zstr))

def jzdumps(obj):
    """ Helpers to serialize and compress objects

    Args:
        * `obj` (object): object to compress and serialize

    Returns:
        ``str``. 

    """
    #sys.setrecursionlimit(PICKLE_MAX_RECURSION_DEPTH)
    return zlib.compress(json.dumps(json_prep(obj)))

def jzloads(jzstr):
    """ Helper to uncompress and deserialize a json object
    Args:
        * `jzstr` (str): compressed and json serialized object

    Returns:
        ``object``. 

    Raises:
        ``ValueError``

    """
    #sys.setrecursionlimit(PICKLE_MAX_RECURSION_DEPTH)
    return json.loads(zlib.decompress(jzstr))

def convert_bytes(bytes_):
    """ Convert int total byte value to human readable

    Args:
        * `bytes_` (int): number of bytes to convert

    Returns:
        ``str``. Bytes in human readable form

    """
    if not bytes_:
        bytes_ = 0.0
    bytes_ = float(bytes_)
    if bytes_ >= 1099511627776:
        terabytes = bytes_ / 1099511627776
        size = '%.2fT' % terabytes
    elif bytes_ >= 1073741824:
        gigabytes = bytes_ / 1073741824
        size = '%.2fG' % gigabytes
    elif bytes_ >= 1048576:
        megabytes = bytes_ / 1048576
        size = '%.2fM' % megabytes
    elif bytes_ >= 1024:
        kilobytes = bytes_ / 1024
        size = '%.2fK' % kilobytes
    else:
        size = '%.2fb' % bytes_
    return size


ZERO = timedelta(0)
class Utc(tzinfo):
    """ UTC

    """
    def utcoffset(self):
        """

        """
        return ZERO

    def tzname(self):
        """

        """
        return "UTC"

    def dst(self):
        """

        """
        return ZERO
UTC = Utc()

class FixedOffset(tzinfo):
    """Fixed offset in hours and minutes from UTC

    """
    def __init__(self, offset_hours, offset_minutes, name):
        self.__offset = timedelta(hours=offset_hours, minutes=offset_minutes)
        self.__name = name

    def utcoffset(self):
        """

        """
        return self.__offset

    def tzname(self):
        """

        """
        return self.__name

    def dst(self):
        """

        """
        return ZERO

    def __repr__(self):
        return "<FixedOffset %r>" % self.__name


# Adapted from http://delete.me.uk/2005/03/iso8601.html
ISO8601_REGEX = re.compile(r"(?P<year>[0-9]{4})(-(?P<month>[0-9]{1,2})"
    r"(-(?P<day>[0-9]{1,2})((?P<separator>.)(?P<hour>[0-9]{2}):"
    r"(?P<minute>[0-9]{2})(:(?P<second>[0-9]{2})(\.(?P<fraction>[0-9]+))?)?"
    r"(?P<timezone>Z|(([-+])([0-9]{2}):([0-9]{2})))?)?)?)?")
TIMEZONE_REGEX = re.compile(r"(?P<prefix>[+-])(?P<hours>[0-9]{2})."
    r"(?P<minutes>[0-9]{2})")

class ParseError(Exception):
    """Raised when there is a problem parsing a date string"""


def parse_timezone(tzstring, default_timezone=UTC):
    """ Parses ISO 8601 time zone specs into tzinfo offsets

    """
    if tzstring == "Z":
        return default_timezone
    # This isn't strictly correct, but it's common to encounter dates without
    # timezones so I'll assume the default (which defaults to UTC).
    # Addresses issue 4.
    if tzstring is None:
        return default_timezone
    tim_ = TIMEZONE_REGEX.match(tzstring)
    prefix, hours, minutes = tim_.groups()
    hours, minutes = int(hours), int(minutes)
    if prefix == "-":
        hours = -hours
        minutes = -minutes
    return FixedOffset(hours, minutes, tzstring)

def parse_date(datestring, default_timezone=UTC):
    """ Parses ISO 8601 dates into datetime objects

    The timezone is parsed from the date string. However it is quite common to
    have dates without a timezone (not strictly correct). In this case the
    default timezone specified in default_timezone is used. This is UTC by
    default.
    """
    if not isinstance(datestring, basestring):
        raise ParseError("Expecting a string %r" % datestring)
    tim_ = ISO8601_REGEX.match(datestring)
    if not tim_:
        raise ParseError("Unable to parse date string %r" % datestring)
    groups = tim_.groupdict()
    tz_ = parse_timezone(groups["timezone"], default_timezone=default_timezone)
    if groups["fraction"] is None:
        groups["fraction"] = 0
    else:
        groups["fraction"] = int(float("0.%s" % groups["fraction"]) * 1e6)
    return datetime(int(groups["year"]), int(groups["month"]), 
        int(groups["day"]), int(groups["hour"]), int(groups["minute"]), 
        int(groups["second"]), int(groups["fraction"]), tz_)

def convert_datetime(dateitem, direction = 'string'):
    """ Takes a string or a date and converts it to a
    format JSON will accept (such as sessions)
    
    Args:
        * `dateitem` (str)(datetime): the item to convert
        * `dir` (str): What direction to Convert to.
            It accepts 'string' (convert datetime TO string) (default option)
        or 'datetime' (convert string to datetime)
        
    Returns:
        ``str`` ``datetime``. The end result converted over
    """
    if (direction == 'string'):
        return dateitem.strftime('%b %d %Y %I:%M:%S%f%p')
    else:
        if dateitem:
            return datetime.strptime(dateitem, '%b %d %Y %I:%M:%S%f%p')

    return ''

 
def decode_datetime(datestring):
    """ Take an ISO8601 string and convert to datetime object
    Its either <div data-date="2010-09-15T15:44:43Z" class="iso8601" 
        title="2010-09-15T15:44:43Z">2010-09-15T15:44:43Z</div>
    or 2010-09-14T20:30:22Z

    Args:
        * `datestring` (str,unicode): ISO8601 string %Y-%m-%dT%H:%M:%SZ

    Returns:
        ``datetime.datetime``.

    """
    # Remove any html
    datestring = strip_tags(datestring)

    try:
        dateobject = datetime.strptime(datestring, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        raise

    return dateobject

def encode_datetime(dateobject, class_='iso8601', tz_=None, add_html=True):
    """ISO8601 RFC 3339 format

    Args:
        * `dateobject` (datetime,str,unicode): object to encode, should be UTC
        * `class_` (str): iso8601/
        * `tz_` (str): users timezone offset(America/Chicago, US/Central)
        * `add_html`(bool): wrap return iso string in html

    Returns:
        ``str``. Datetime in ISO 8601/RFC 3339 format with surrounding html

    """
    if not dateobject:
        return ''

    def wrap_html(iso_string, class_, date_string):
        """ Return an html wrapped version of date

        """
        return '<div data-date="{0}" class="{1}" title="{2}">{2}</div>'.format(
            iso_string, class_, date_string)

    if type(dateobject) in (unicode, str):
        try:
            dateobject = datetime.fromtimestamp(float(dateobject))
        except ValueError:
            #logging.info(dateobject)
            # its a string already in iso format
            #return wrap_html(dateobject, class_, dateobject)
            if not "<div" in dateobject and dateobject[-1] == "Z":
                if add_html:
                    return wrap_html(dateobject, 'iso8601', dateobject)
                else:
                    return dateobject
            else:
                return dateobject

    iso_string = dateobject.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Offset datetime object by users timezone
    if tz_:
        dateobject = dateobject.replace(tzinfo=pytz.utc)
        dateobject = dateobject.astimezone(pytz.timezone(tz_))

    date_string = ''
    if class_ == 'gridDate':
        #date_string = dateobject.strftime('%Y/%m/%d %H:%M')
        date_string = dateobject.strftime('%m-%d-%Y %I:%M %p')
    elif class_ == 'iso8601':
        date_string = iso_string

    if add_html:
        date_string = wrap_html(iso_string, class_, date_string)

    return date_string

def utf8_prep(obj):
    """ Converting strings in object to utf8.  Used
    in importing to filter incompatible characters

    Returns:
        * A copy of the object

    """
    if isinstance(obj, dict):
        return_dict = {}
        for key, value in obj.items():
            return_dict[key] = utf8_prep(value)
        return return_dict
            
    if isinstance(obj, list):
        return_list = []
        for value in obj:
            return_list.append(utf8_prep(value))
        return return_list

    if isinstance(obj, str):
        return unicode(obj, errors='ignore').encode('utf-8')
    elif isinstance(obj, unicode):
        return obj.decode('utf-8', 'replace')
    
    return obj

def random_string(string_length):
    """ Generate random string of length

    Args:
        * `string_length` (int):

    """
    return os.urandom(string_length)

def increase_id(val):
    """ Given a string or integer value get the next
    item in the sequence, only looks at alpha numeric characters
    all others stay the same

    alpha numeric sequence
    0-9 --> 48-57
    A-Z --> 65-90
    a-z --> 97-122

    Args:
        * val (str or int):id to increase

    Returns:
        * ``str``. increased value

    >>> increase_id('1')
    '2'
    >>> increase_id('1-2')
    '1-3'
    >>> increase_id('1-a')
    '1-b'
    >>> increase_id('1-A')
    '1-B'
    >>> increase_id('1-Z')
    '2-A'

    """
    new_val = val
    # Increment obj val and update 
    if isinstance(val, int) or val.isdigit():
        new_val = str(int(val) + 1)
    else:
        new_val = list(reversed(list(new_val)))

        for idx, val in enumerate(new_val):
            ord_val = ord(val)
            if 48 <= ord_val <= 57:
                if ord_val == 57:
                    new_val[idx] = '0'
                else:
                    new_val[idx] = chr(ord_val + 1)
                    break
            elif 97 <= ord_val <= 122:
                if ord_val == 122:
                    new_val[idx] = 'a'
                else:
                    new_val[idx] = chr(ord_val + 1)
                    break
            elif 65 <= ord_val <= 90:
                if ord_val == 90:
                    new_val[idx] = 'A'
                else:
                    new_val[idx] = chr(ord_val + 1)
                    break
        new_val = ''.join(reversed(new_val))

    return new_val


def print_timing(func):
    """ Performance evaluation decorator to get times for functions
    Usage:

        @libs.helpers.print_timing

    """
    def wrapper(*arg):
        """ Wrap function with time and print out total execution time

        """
        t1_ = time.time()
        res = func(*arg)
        t2_ = time.time()
        print '{0} took {1:-f} ms'.format(func.func_name, (t2_-t1_)*1000.0)
        return res

    return wrapper

class MarkovText(object):
    """ A Markov chain is collection of random variables {X_t}
    (where the index t runs through 0, 1, …) having the property that,
    given the present, the future is conditionally independent of the past.

    The algorithm is,

    1. Have text which will serve as the corpus from which 
        we choose the next transitions.
    2. Start with two consecutive words from the text. 
        The last two words constitute the present state.
    3. Generating next word is the markov transition. 
        To generate the next word, look in the corpus, and find which words are
        present after the given two words. Choose one of them randomly.
    4. Repeat 2, until text of required size is generated.

    The last two words are the current state.
    Next word depends on last two words only, or on present state only.
    The next word is randomly chosen from a statistical model of the corpus.
    
    "The quick brown fox jumps over the brown fox who is slow jumps 
    over the brown fox who is dead."
    cache = {
        ('The', 'quick'): ['brown'],
        ('brown', 'fox'): ['jumps', 'who', 'who'],
        ('fox', 'jumps'): ['over'],
        ('fox', 'who'): ['is', 'is'],
        ('is', 'slow'): ['jumps'],
        ('jumps', 'over'): ['the', 'the'],
        ('over', 'the'): ['brown', 'brown'],
        ('quick', 'brown'): ['fox'],
        ('slow', 'jumps'): ['over'],
        ('the', 'brown'): ['fox', 'fox'],
        ('who', 'is'): ['slow', 'dead.'],
    }

    Now if we start with "brown fox", the next word can be "jumps" or "who".
    If we choose "jumps", then the current state is "fox jumps" and next 
    word is over, and so on.
    
    Attributes:
        `_cache` (dict):
        `_words` (list): split list of words from given input text
        `_word_size` (int): length of input text

    """
    _cache = {}
    _words = []
    _word_size = 0

    def __init__(self, text):
        """ 
        Args:
            `text` (

        """
        if not text:
            text = ''

        self._cache = {}
        if isinstance(text, file):
            self._words = self._file_to_words(text)
        else:
            self._words = text.split()

        self._word_size = len(self._words)
        self._cache_database()
    
    def _cache_database(self):
        """ Generate internal cache.

        The quick brown

        cache = {
            ('The', 'quick'): ['brown'],
        }

        """
        for word1, word2, word3 in self._triples():
            key = (word1, word2)
            if key in self._cache:
                self._cache[key].append(word3)
            else:
                self._cache[key] = [word3]

        # Add end words
        if self._word_size > 2:
            key = (self._words[-2], self._words[-1])
            self._cache[key] = [self._words[0]]
            key = (self._words[-1], self._words[0])
            self._cache[key] = [self._words[1]]

    def _triples(self):
        """ Generates triples from the given data string. 
        So if our string were "What a lovely day", we'd 
        generate (What, a, lovely) and then (a, lovely, day).

        """

        if len(self._words) < 3:
            return

        for i in range(len(self._words) - 2):
            yield (self._words[i], self._words[i+1], self._words[i+2])


    def _file_to_words(self, file_):
        """ Take a file input and generate a split list on space
        Args:
            `file_` (file): input file of text only.

        """
        file_.seek(0)
        data = file_.read()
        return data.split()


    def generate_markov_text(self, size=25):
        """ _

        Args:
            `size` (int): size of returned text

        """
        if self._word_size < 3:
            return ' '.join(self._words)

        # Grab a random seed from the list, ensuring its not 
        # one of the last two
        seed = random.randint(0, self._word_size - 3)
        # Get the word pair in the sequence
        word1, word2 = self._words[seed], self._words[seed + 1]
        gen_words = []
        for idx in xrange(size):
            gen_words.append(word1)
            word1, word2 = word2, random.choice(self._cache[(word1, word2)])
        return ' '.join(gen_words)



class LoremIpsum():
    """ Utility functions for generating "lorem ipsum" Latin text.

    Attributes:
        `_common_paragraph` (str):
        `_words` (tuple(str)):
        `_common_words` (tuple(str)):
    """

    _common_paragraph = """Lorem ipsum dolor sit amet, consectetur 
    adipisicing elit, sed do eiusmod tempor incididunt ut labore et 
    dolore magna aliqua. Ut ad minim veniam, quis nostrud exercitation 
    ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute 
    irure dolor in reprehenderit in voluptate velit esse cillum dolore 
    eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non 
    proident, sunt in culpa qui officia deserunt mollit anim id est laborum."""

    _words = ('exercitationem', 'perferendis', 'perspiciatis', 'laborum', 
            'eveniet', 'sunt', 'iure', 'nam', 'nobis', 'eum', 'cum', 
            'officiis', 'excepturi', 'odio', 'consectetur', 'quasi', 
            'aut', 'quisquam', 'vel', 'eligendi',
            'itaque', 'non', 'odit', 'tempore', 'quaerat', 'dignissimos',
            'facilis', 'neque', 'nihil', 'expedita', 'vitae', 'vero', 'ipsum',
            'nisi', 'animi', 'cumque', 'pariatur', 'velit', 'modi', 'natus',
            'iusto', 'eaque', 'sequi', 'illo', 'sed', 'ex', 'et', 
            'voluptatibus', 'tempora', 'veritatis', 'ratione', 'assumenda', 
            'incidunt', 'nostrum',
            'placeat', 'aliquid', 'fuga', 'provident', 'praesentium', 'rem',
            'necessitatibus', 'suscipit', 'adipisci', 'quidem', 'possimus',
            'voluptas', 'debitis', 'sint', 'accusantium', 'unde', 'sapiente',
            'voluptate', 'qui', 'aspernatur', 'laudantium', 'soluta', 'amet',
            'quo', 'aliquam', 'saepe', 'culpa', 'libero', 'ipsa', 'dicta',
            'reiciendis', 'nesciunt', 'doloribus', 'autem', 'impedit', 'minima',
            'maiores', 'repudiandae', 'ipsam', 'obcaecati', 'ullam', 'enim',
            'totam', 'delectus', 'ducimus', 'quis', 'voluptates', 'dolores',
            'molestiae', 'harum', 'dolorem', 'quia', 'voluptatem', 'molestias',
            'magni', 'distinctio', 'omnis', 'illum', 'dolorum', 'voluptatum', 
            'ea',
            'quas', 'quam', 'corporis', 'quae', 'blanditiis', 'atque', 
            'deserunt',
            'laboriosam', 'earum', 'consequuntur', 'hic', 'cupiditate',
            'quibusdam', 'accusamus', 'ut', 'rerum', 'tror', 'minus', 'eius',
            'ab', 'ad', 'nemo', 'fugit', 'officia', 'at', 'in', 'id', 'quos',
            'reprehenderit', 'numquam', 'iste', 'fugiat', 'sit', 'inventore',
            'beatae', 'repellendus', 'magnam', 'recusandae', 'quod', 
            'explicabo',
            'doloremque', 'aperiam', 'consequatur', 'asperiores', 'commodi',
            'optio', 'dolor', 'labore', 'temporibus', 'repellat', 'veniam',
            'architecto', 'est', 'esse', 'mollitia', 'nulla', 'a', 'similique',
            'eos', 'alias', 'dolore', 'tenetur', 'deleniti', 'porro', 'facere',
            'maxime', 'corrupti', 'frabius', 'ragique')

    _common_words = ('lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur',
            'adipisicing', 'elit', 'sed', 'do', 'eiusmod', 'tempor', 
            'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua')

    def __init__(self):
        """ _

        """
        pass

    def sentence(self):
        """
        Returns a randomly generated sentence of lorem ipsum text.

        The first word is capitalized, and the sentence ends in either a 
        period or question mark. Commas are added at random.
        """
        # Determine the number of comma-separated sections and number of words 
        # in each section for this sentence.
        sections = [u' '.join(
            random.sample(self._words, random.randint(3, 12))) for idx \
                    in range(random.randint(1, 5))]
        sen = u', '.join(sections)
        # Convert to sentence case and add end punctuation.
        return u'%s%s%s' % (sen[0].upper(), sen[1:], random.choice('?.'))

    def paragraph(self):
        """
        Returns a randomly generated paragraph of lorem ipsum text.

        The paragraph consists of between 1 and 4 sentences, inclusive.
        """
        return u' '.join([self.sentence() for idx \
                in range(random.randint(1, 4))])

    def paragraphs(self, count, common=True):
        """
        Returns a list of paragraphs as returned by paragraph().

        If `common` is True, then the first paragraph will be the standard
        'lorem ipsum' paragraph. Otherwise, the first paragraph will be random
        Latin text. Either way, subsequent paragraphs will be random Latin text.
        """
        paras = []
        for i in range(count):
            if common and i == 0:
                paras.append(self._common_paragraph)
            else:
                paras.append(self.paragraph())
        return paras

    def words(self, count=1, common=False):
        """
        Returns a string of `count` lorem ipsum words separated by a single 
        space.

        If `common` is True, then the first 19 words will be the standard
        'lorem ipsum' words. Otherwise, all words will be selected randomly.
        """
        if common:
            word_list = list(self._common_words)
        else:
            word_list = []
        clen = len(word_list)
        if count > clen:
            count -= clen
            while count > 0:
                clen = min(count, len(self._words))
                count -= clen
                word_list += random.sample(self._words, clen)
        else:
            word_list = word_list[:count]
        return u' '.join(word_list)


def ip_addr_range(start_addr, end_addr):
    """
    Note does not check start > end

    Args:
        * `start_addr` (str): valid ip string 10.0.0.1
        * `end_addr` (str): valid ip string 10.0.0.2

    """
    def incr_addr(addr_list):
        """ Increase the tuple address

        Args:
            * `addr_list` (list): list of split by . ip

        """
        addr_list[3] += 1
        for i in (3, 2, 1):
            if addr_list[i] == 256:
                addr_list[i] = 0
                addr_list[i-1] += 1

    def as_string(addr_list):
        """ Convert to string form

        """
        return ".".join(map(str, addr_list))

    start_addr_list = map(int, start_addr.split("."))
    end_addr_list = map(int, end_addr.split("."))

    cur_addr_list = start_addr_list[:]
    yield as_string(cur_addr_list)
    for i in range(4):
        while cur_addr_list[i] < end_addr_list[i]:
            incr_addr(cur_addr_list)
            yield as_string(cur_addr_list)




def get_list_of_ips_from_ranges(ranges):
    """ Given a string of ranges in the form
    209.34.76.0-209.34.76.255
    209.34.84.0-209.34.84.255
    Generate a list of potential ips

    Args:
        * `ranges` (str): line by line dash separated list of ip ranges

    """
    range_list = []
    ranges = [ran_.strip() for ran_ in ranges.split('\n') if ran_]
    ranges = [ran_.split('-') for ran_ in ranges if ran_]

    for range_ in ranges:
        if len(range_) == 2:
            start = range_[0]
            end = range_[1]
            range_list.append(start)
            for addr in ip_addr_range(start, end):
                if addr not in range_list:
                    range_list.append(addr)

    return range_list



class Retry(object):
    """ The retry decorator reruns a funtion tries 
    times if an exception occurs.

    Attributes:
        `default_exceptions` (Exception): 

    Usage:

        >>> from retry_decorator import Retry
        >>> @Retry(2)
        ... def fail_fn():
        ...     raise Exception("failed")
        ... 
        >>> fail_fn()
        Retry, exception: failed
        Retry, exception: failed
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "retry_decorator.py", line 32, in fn
            raise exception
        Exception: failed
            
    """
    default_exceptions = (Exception)

    def __init__(self, tries, exceptions=None, delay=0):
        """
        Decorator for retrying a function if exception occurs
        
        tries -- num tries 
        exceptions -- exceptions to catch
        delay -- wait between retries
        """
        self.tries = tries
        if exceptions is None:
            exceptions = Retry.default_exceptions
        self.exceptions =  exceptions
        self.delay = delay

    def __call__(self, f):
        """ _

        """
        def fn(*args, **kwargs):
            """ _

            """
            exception = None
            for _ in range(self.tries):
                try:
                    return f(*args, **kwargs)
                except self.exceptions, e:
                    print "Retry, exception: "+str(e)
                    time.sleep(self.delay)
                    exception = e
            #if no success after tries, raise last exception
            raise exception
        return fn

mobile_b = re.compile(r"""
    smartphone|android|iphone|ipad|ipod|avantgo|blackberry|blazer|compal|
    elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|
    mmp|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|
    symbian|treo|up\\.(browser|link)|vodafone|wap|windows (ce|phone)|
    xda|xiino""", re.I|re.M)

mobile_v = re.compile(r"""
    1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|
    ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|
    au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|
    bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|
    da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|
    em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|
    gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|
    hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|
    i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|
    ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|
    kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|e\\-|e\\/|\\-[a-w])|libw|lynx|
    m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(di|rc|ri)|
    mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|
    mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|
    tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|
    pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|
    psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|
    rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|
    se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|
    sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|
    t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|
    to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|
    vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|
    vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|
    wmlb|wonu|x700|xda(\\-|2|g)|yas\\-|your|zeto|zte\\-""", re.I|re.M)


def is_mobile(request):
    """ Checks if request is from a mobile device

    Args:
        `lines` (list): vcard file lines
    Returns:
        ``dict``.

    """
    is_mobile = False
    user_agent = request.headers.get('User-Agent')
    if user_agent:
        if mobile_b.search(user_agent) or mobile_v.search(user_agent[0:4]):
            is_mobile = True

    return is_mobile

