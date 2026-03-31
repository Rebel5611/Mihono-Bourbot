from sqlalchemy import *
from sqlalchemy.orm import *

Base = declarative_base()

class Server(Base):
    __tablename__ = "server"

    server_id = Column(Integer, primary_key=True)
    reporting_channel = Column(Integer)
    memes_channel = Column(Integer)

    # relationship to Player
    players = relationship("Player", back_populates="server")


class Player(Base):
    __tablename__ = "player"

    server_id = Column(Integer, ForeignKey("server.server_id"), primary_key=True)
    player_id = Column(Integer, primary_key=True)
    player_alias = Column(String)

    server = relationship("Server", back_populates="players")

def get_server(server_id: int):
    server = session.get(Server, server_id)
    if not server:
        server = Server(server_id=server_id)
        session.add(server)
    return server

engine = create_engine("sqlite:///bot_data.db", isolation_level="AUTOCOMMIT")
session = Session(engine)
Base.metadata.create_all(engine)