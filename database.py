from sqlalchemy import *
from sqlalchemy.orm import *

base = declarative_base()

class Server(base):
    __tablename__ = "server"

    server_id = Column(Integer, primary_key=True)
    reporting_channel = Column(Integer)
    memes_channel = Column(Integer)

    players = relationship("Player", back_populates="server")


class Player(base):
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
        session.commit()
    return server

def get_player(server_id: int, player_id: int):
    player = session.get(Player, {"server_id": server_id, "player_id": player_id})
    if not player:
        player = Player(server=get_server(server_id), player_id=player_id)
        session.add(player)
        session.commit()
    return player

def commit():
    session.commit()

engine = create_engine("sqlite:///bot_data.db")
session = Session(engine)
base.metadata.create_all(engine)