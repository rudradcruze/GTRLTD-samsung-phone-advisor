from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Phone(Base):
    __tablename__ = "phones"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), unique=True, index=True)
    release_date = Column(String(100))
    display = Column(Text)
    battery = Column(String(255))
    camera = Column(Text)
    ram = Column(String(100))
    storage = Column(String(255))
    price = Column(String(100))
    chipset = Column(String(255))
    os = Column(String(255))
    body = Column(Text)
    url = Column(String(500))

    def to_dict(self):
        return {
            "id": self.id,
            "model_name": self.model_name,
            "release_date": self.release_date,
            "display": self.display,
            "battery": self.battery,
            "camera": self.camera,
            "ram": self.ram,
            "storage": self.storage,
            "price": self.price,
            "chipset": self.chipset,
            "os": self.os,
            "body": self.body,
            "url": self.url
        }

    def specs_text(self):
        """Return a formatted text of all specifications for RAG"""
        return f"""
Model: {self.model_name}
Release Date: {self.release_date}
Display: {self.display}
Battery: {self.battery}
Camera: {self.camera}
RAM: {self.ram}
Storage: {self.storage}
Price: {self.price}
Chipset: {self.chipset}
OS: {self.os}
Body: {self.body}
"""


def init_db():
    """Initialize the database and create tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Database tables created successfully!")
