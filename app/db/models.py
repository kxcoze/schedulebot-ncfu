from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSON

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=False)
    subgroup = Column(Integer, default=0)
    is_notified = Column(Boolean, default=False)
    notification_type = Column(String(16), default="all")
    foreign_lan = Column(String(64))
    pref_time = Column(Integer, default=0)

    links = Column(JSON, default=[])
    homework = Column(JSON, default=[])

    group_id = Column(Integer, ForeignKey("group.id"))


class Group(Base):
    __tablename__ = "group"
    id = Column(Integer, primary_key=True, unique=True, autoincrement=False)
    name = Column(String(20), unique=True, index=True)
    schedule_cur_week = Column(JSON)
    schedule_next_week = Column(JSON)

    users = relationship("User", backref="group", lazy="dynamic")
