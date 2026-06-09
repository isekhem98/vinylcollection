from sqlalchemy import (create_engine, Column, Integer, String, Float, Text, ForeignKey)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()
SessionLocal = None

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    vinyls = relationship('Vinyl', back_populates='owner')

class Vinyl(Base):
    __tablename__ = 'vinyls'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    release_id = Column(String(64), index=True)
    title = Column(String(1024), default='')
    artist = Column(String(512), default='')
    year = Column(Integer)
    label = Column(String(512), default='')
    catno = Column(String(128), default='')
    format = Column(String(256), default='')
    country = Column(String(128), default='')
    genre = Column(String(256), default='')
    style = Column(String(256), default='')
    condition = Column(String(32), default='')
    purchase_price = Column(Float)
    purchase_date = Column(String(32), default='')
    discogs_url = Column(String(1024), default='')
    cover_image_url = Column(String(2048), default='')
    lowest_price = Column(Float)
    price_currency = Column(String(8), default='EUR')
    num_for_sale = Column(Integer, default=0)
    tracklist_count = Column(Integer, default=0)
    notes = Column(Text, default='')
    condition_prices = Column(Text, nullable=True)
    tags = Column(String(512), default='')
    purchase_location = Column(String(255), default='')
    owner = relationship('User', back_populates='vinyls')

    def to_dict(self):
        return {
            'id': self.id,
            'release_id': self.release_id,
            'title': self.title,
            'artist': self.artist,
            'year': self.year,
            'label': self.label,
            'catno': self.catno,
            'format': self.format,
            'country': self.country,
            'genre': self.genre,
            'style': self.style,
            'condition': self.condition,
            'purchase_price': self.purchase_price,
            'purchase_date': self.purchase_date,
            'discogs_url': self.discogs_url,
            'cover_image_url': self.cover_image_url,
            'lowest_price': self.lowest_price,
            'price_currency': self.price_currency,
            'num_for_sale': self.num_for_sale,
            'tracklist_count': self.tracklist_count,
            'notes': self.notes,
            'condition_prices': self.condition_prices,
            'tags': self.tags,
            'purchase_location': self.purchase_location,
        }

class Config(Base):
    __tablename__ = 'config'
    key = Column(String(255), primary_key=True)
    value = Column(Text)


def init_db(database_url: str):
    global SessionLocal
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)


def get_session():
    if SessionLocal is None:
        raise RuntimeError('SessionLocal not initialized; call init_db() first')
    return SessionLocal()
