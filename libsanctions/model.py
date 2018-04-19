import logging
import countrynames
from collections import OrderedDict
from normality import stringify, collapse_spaces
from dalet import parse_date
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, Unicode
from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import ForeignKey

from libsanctions.config import DATABASE_URI
from libsanctions.util import clean_obj

log = logging.getLogger(__name__)
Base = declarative_base()
engine = create_engine(DATABASE_URI)
session_factory = sessionmaker(bind=engine)
session = scoped_session(session_factory)


class Stringify(TypeDecorator):
    impl = Unicode

    def process_bind_param(self, value, dialect):
        return stringify(value)


class Date(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        return parse_date(value)


class JsonRowMixIn(object):

    def to_row(self):
        data = OrderedDict()
        data['entity_id'] = self.entity_id
        data.update(self.to_json())
        return data


class NameMixIn(object):
    _name = Column('name', Stringify, nullable=True)
    title = Column(Stringify, nullable=True)
    first_name = Column(Stringify, nullable=True)
    second_name = Column(Stringify, nullable=True)
    third_name = Column(Stringify, nullable=True)
    father_name = Column(Stringify, nullable=True)
    last_name = Column(Stringify, nullable=True)

    @hybrid_property
    def name(self):
        if self._name is not None:
            return self._name
        names = (self.first_name, self.second_name, self.third_name,
                 self.father_name, self.last_name)
        names = [n for n in names if n is not None]
        if len(names):
            names = ' '.join(names)
            return collapse_spaces(names)

    @name.setter
    def name(self, name):
        name = stringify(name)
        if name is not None:
            name = collapse_spaces(name)
        self._name = name

    def to_name_dict(self):
        data = OrderedDict()
        data['name'] = self.name
        data['first_name'] = self.first_name
        data['second_name'] = self.second_name
        data['third_name'] = self.third_name
        data['father_name'] = self.father_name
        data['last_name'] = self.last_name
        data['title'] = self.title
        return data

    def from_name_dict(self, data):
        self.name = data.get('name')
        self.first_name = data.get('first_name')
        self.second_name = data.get('second_name')
        self.third_name = data.get('third_name')
        self.father_name = data.get('father_name')
        self.last_name = data.get('last_name')
        self.title = data.get('title')


class CountryMixIn(object):
    country_name = Column(Stringify, nullable=True)
    country_code = Column(Stringify, nullable=True)

    @property
    def country(self):
        return self.country_code or self.country_name

    @country.setter
    def country(self, name):
        self.country_name = name
        self.country_code = countrynames.to_code(name)

    def to_country_dict(self):
        data = OrderedDict()
        data['country'] = self.country_name
        data['country_code'] = self.country_code
        return data

    def from_country_dict(self, data):
        self.country_name = data.get('country')
        self.country_code = data.get('country_code')


class QualityMixIn(object):
    QUALITY_WEAK = 'weak'
    QUALITY_STRONG = 'strong'

    quality = Column(Stringify, nullable=True)


class Alias(Base, NameMixIn, QualityMixIn, JsonRowMixIn):
    """An alternate name for an indivdual."""
    __tablename__ = 'alias'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Unicode, ForeignKey('data.id'))
    entity = relationship("Entity", backref="aliases")
    type = Column(Stringify, nullable=True)
    description = Column(Stringify, nullable=True)

    def __init__(self, entity_id, name=None):
        self.entity_id = entity_id
        self.name = name

    def to_json(self):
        data = self.to_name_dict()
        data['type'] = self.type
        data['quality'] = self.quality
        data['description'] = self.description
        return data

    def from_json(self, data):
        self.from_name_dict(data)
        self.type = data.get('type')
        self.quality = data.get('quality')
        self.description = data.get('description')


class Address(Base, CountryMixIn, JsonRowMixIn):
    """An address associated with an entity."""
    __tablename__ = 'address'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String, ForeignKey('data.id'))
    entity = relationship("Entity", backref="addresses")
    text = Column(Stringify, nullable=True)
    note = Column(Stringify, nullable=True)
    street = Column(Stringify, nullable=True)
    street_2 = Column(Stringify, nullable=True)
    postal_code = Column(Stringify, nullable=True)
    city = Column(Stringify, nullable=True)
    region = Column(Stringify, nullable=True)

    def __init__(self, entity_id):
        self.entity_id = entity_id

    def to_json(self):
        data = self.to_country_dict()
        data.update({
            'text': self.text,
            'note': self.note,
            'street': self.street,
            'street_2': self.street_2,
            'postal_code': self.postal_code,
            'city': self.city,
            'region': self.region,
        })
        return data

    def from_json(self, data):
        self.from_country_dict(data)
        self.text = data.get('text')
        self.note = data.get('note')
        self.street = data.get('street')
        self.street_2 = data.get('street_2')
        self.postal_code = data.get('postal_code')
        self.city = data.get('city')
        self.region = data.get('region')


class Identifier(Base, CountryMixIn, JsonRowMixIn):
    """A document issued to an entity."""
    __tablename__ = 'identifier'

    TYPE_PASSPORT = u'passport'
    TYPE_NATIONALID = u'nationalid'
    TYPE_OTHER = u'other'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String, ForeignKey('data.id'))
    entity = relationship("Entity", backref="identifiers")
    type = Column(Stringify, nullable=True)
    description = Column(Stringify, nullable=True)
    number = Column(Stringify, nullable=True)
    issued_at = Column(Date, nullable=True)

    def __init__(self, entity_id):
        self.entity_id = entity_id

    def to_json(self):
        data = OrderedDict()
        data['type'] = self.type
        data['number'] = self.number
        data.update(self.to_country_dict())
        data['issued_at'] = self.issued_at
        data['description'] = self.description
        return data

    def from_json(self, data):
        self.from_country_dict(data)
        self.type = data.get('type')
        self.number = data.get('number')
        self.issued_at = data.get('issued_at')
        self.description = data.get('description')


class Nationality(Base, CountryMixIn, JsonRowMixIn):
    """A nationality associated with an entity."""
    __tablename__ = 'nationality'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String, ForeignKey('data.id'))
    entity = relationship("Entity", backref="nationalities")

    def __init__(self, entity_id):
        self.entity_id = entity_id

    def to_json(self):
        return self.to_country_dict()

    def from_json(self, data):
        self.from_country_dict(data)


class BirthDate(Base, QualityMixIn, JsonRowMixIn):
    """Details regarding the birth of an entity."""
    __tablename__ = 'birth_date'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String, ForeignKey('data.id'))
    entity = relationship("Entity", backref="birth_dates")
    date = Column(Date, nullable=True)

    def __init__(self, entity_id):
        self.entity_id = entity_id

    def to_json(self):
        data = OrderedDict()
        data['quality'] = self.quality
        data['date'] = self.date
        return data

    def from_json(self, data):
        self.quality = data.get('quality')
        self.date = data.get('date')


class BirthPlace(Base, QualityMixIn, CountryMixIn, JsonRowMixIn):
    """Details regarding the birth of an entity."""
    __tablename__ = 'birth_place'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String, ForeignKey('data.id'))
    entity = relationship("Entity", backref="birth_places")
    place = Column(Stringify, nullable=True)
    description = Column(Stringify, nullable=True)

    def __init__(self, entity_id):
        self.entity_id = entity_id

    def to_json(self):
        data = OrderedDict()
        data['quality'] = self.quality
        data.update(self.to_country_dict())
        data['place'] = self.place
        data['description'] = self.description
        return data

    def from_json(self, data):
        self.from_country_dict(data)
        self.quality = data.get('quality')
        self.place = data.get('place')
        self.description = data.get('description')


class Entity(Base, NameMixIn):
    """A company or person that is subject to a sanction."""
    __tablename__ = 'data'

    TYPE_ENTITY = 'entity'
    TYPE_INDIVIDUAL = 'individual'
    TYPE_VESSEL = 'vessel'

    GENDER_MALE = 'male'
    GENDER_FEMALE = 'female'

    id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    type = Column(String, nullable=True)
    summary = Column(Stringify, nullable=True)
    function = Column(Stringify, nullable=True)
    program = Column(Stringify, nullable=True)
    url = Column(Stringify, nullable=True)
    gender = Column(Stringify, nullable=True)
    listed_at = Column(Date, nullable=True)
    updated_at = Column(Date, nullable=True)
    timestamp = Column(DateTime, nullable=False)

    def __init__(self, source, id):
        self.source = source
        self.id = id
        self.timestamp = datetime.utcnow()

    def create_alias(self, name=None):
        alias = Alias(self.id, name=name)
        session.add(alias)
        return alias

    def create_address(self):
        address = Address(self.id)
        session.add(address)
        return address

    def create_identifier(self):
        identifier = Identifier(self.id)
        session.add(identifier)
        return identifier

    def create_nationality(self):
        nationality = Nationality(self.id)
        session.add(nationality)
        return nationality

    def create_birth_date(self):
        birth_date = BirthDate(self.id)
        session.add(birth_date)
        return birth_date

    def create_birth_place(self):
        birth_place = BirthPlace(self.id)
        session.add(birth_place)
        return birth_place

    def save(self):
        self.timestamp = datetime.utcnow()
        session.commit()
        log.info("[%s]: %s", self.id, self.name)
        # from pprint import pprint
        # pprint(self.to_json())

    def to_row(self):
        data = OrderedDict()
        data['id'] = self.id
        data['source'] = self.source
        data['type'] = self.type
        data.update(self.to_name_dict())
        data['program'] = self.program
        data['function'] = self.function
        data['summary'] = self.summary
        data['url'] = self.url
        data['gender'] = self.gender
        data['listed_at'] = self.listed_at
        data['updated_at'] = self.updated_at
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def to_json(self):
        data = self.to_row()
        data['aliases'] = [a.to_json() for a in self.aliases]
        data['addresses'] = [a.to_json() for a in self.addresses]
        data['identifiers'] = [i.to_json() for i in self.identifiers]
        data['nationalities'] = [n.to_json() for n in self.nationalities]
        data['birth_dates'] = [b.to_json() for b in self.birth_dates]
        data['birth_places'] = [b.to_json() for b in self.birth_places]
        return clean_obj(data)

    @classmethod
    def from_json(cls, data):
        entity = cls(data.get('source'), data.get('id'))
        session.add(entity)
        entity.from_name_dict(data)
        entity.type = data.get('type')
        entity.program = data.get('program')
        entity.function = data.get('function')
        entity.summary = data.get('summary')
        entity.url = data.get('url')
        entity.gender = data.get('gender')
        entity.listed_at = data.get('listed_at')
        entity.updated_at = data.get('updated_at')
        # entity.timestamp = data.get('timestamp')

        for subdata in data.get('aliases', []):
            alias = entity.create_alias()
            alias.from_json(subdata)

        for subdata in data.get('addresses', []):
            address = entity.create_address()
            address.from_json(subdata)

        for subdata in data.get('identifiers', []):
            identifier = entity.create_identifier()
            identifier.from_json(subdata)

        for subdata in data.get('nationalities', []):
            nationality = entity.create_nationality()
            nationality.from_json(subdata)

        for subdata in data.get('birth_dates', []):
            birth_date = entity.create_birth_date()
            birth_date.from_json(subdata)

        for subdata in data.get('birth_places', []):
            birth_place = entity.create_birth_place()
            birth_place.from_json(subdata)

        session.add(entity)

    @classmethod
    def by_id(cls, source, id):
        q = session.query(cls)
        q = q.filter(cls.id == id)
        q = q.filter(cls.source == source)
        return q.first()
