from typing import Optional
from sqlalchemy import *
from sqlalchemy.orm import *

base = declarative_base()

class Server(base):
    __tablename__ = "server"

    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    archipelago_password: Mapped[Optional[str]] = mapped_column(String)
    reporting_channel: Mapped[Optional[int]] = mapped_column(Integer)
    memes_channel: Mapped[Optional[int]] = mapped_column(Integer)

    users: Mapped[list["User"]] = relationship("User", back_populates="server", cascade="all, delete-orphan")
    players: Mapped[list["Player"]] = relationship("Player", back_populates="server", cascade="all, delete-orphan")
    games: Mapped[list["Game"]] = relationship("Game", back_populates="server", cascade="all, delete-orphan")


class User(base):
    __tablename__ = "user"

    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    archipelago_alias: Mapped[Optional[str]] = mapped_column(String)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id"], ["server.server_id"], ondelete="CASCADE"),
    )

    server: Mapped["Server"] = relationship("Server", foreign_keys=[server_id], back_populates="users")
    
player_games = Table(
    "player_games",
    base.metadata,
    Column("server_id", Integer, primary_key=True),
    Column("slot", Integer, primary_key=True),
    Column("game_name", String, primary_key=True),
    ForeignKeyConstraint(["server_id", "slot"], ["player.server_id", "player.slot"], ondelete="CASCADE"),
    ForeignKeyConstraint(["server_id", "game_name"], ["game.server_id", "game.game_name"], ondelete="CASCADE")
)
    
class Player(base):
    __tablename__ = "player"
    
    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    archipelago_alias: Mapped[str] = mapped_column(String)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id"], ["server.server_id"], ondelete="CASCADE"),
    )
    
    server: Mapped["Server"] = relationship("Server", foreign_keys=[server_id], back_populates="players")
    games: Mapped[list["Game"]] = relationship("Game", secondary=player_games, back_populates="players")
    recieved_items: Mapped[list["ReceivedItem"]] = relationship("ReceivedItem", back_populates="player", cascade="all, delete-orphan")
    bounties: Mapped[list["Bounty"]] = relationship("Bounty", back_populates="player", cascade="all, delete-orphan")
    
class ReceivedItem(base):
    __tablename__ = "recieved_item"
    
    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    location: Mapped[int] = mapped_column(Integer, primary_key=True)
    item: Mapped[int] = mapped_column(Integer)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id", "slot"], ["player.server_id", "player.slot"], ondelete="CASCADE"),
    )
    
    player: Mapped["Player"] = relationship("Player", foreign_keys=[server_id, slot], back_populates="recieved_items")
    
class Game(base):
    __tablename__ = "game"
    
    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_name: Mapped[str] = mapped_column(String, primary_key=True)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id"], ["server.server_id"], ondelete="CASCADE"),
    )
    
    server: Mapped["Server"] = relationship("Server", foreign_keys=[server_id], back_populates="games")
    players: Mapped[list["Player"]] = relationship("Player", secondary=player_games, back_populates="games")
    items: Mapped[list["GameItem"]] = relationship("GameItem", back_populates="game", cascade="all, delete-orphan")

class GameItem(base):
    __tablename__ = "game_item"

    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_name: Mapped[str] = mapped_column(String, primary_key=True)
    item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_name: Mapped[str] = mapped_column(String)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id", "game_name"], ["game.server_id", "game.game_name"], ondelete="CASCADE"),
    )
    
    game: Mapped["Game"] = relationship("Game", foreign_keys=[server_id, game_name], back_populates="items")
    bounties: Mapped[list["Bounty"]] = relationship("Bounty", back_populates="item", cascade="all, delete-orphan", overlaps="bounties")

class Bounty(base):
    __tablename__ = "bounty"

    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot: Mapped[int] = mapped_column(Integer)
    game_name: Mapped[str] = mapped_column(String, primary_key=True)
    item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id", "slot"], ["player.server_id", "player.slot"], ondelete="CASCADE"),
        ForeignKeyConstraint(["server_id", "game_name", "item_id"], ["game_item.server_id", "game_item.game_name", "game_item.item_id"], ondelete="CASCADE")
    )
    
    player: Mapped["Player"] = relationship("Player", foreign_keys=[server_id, slot], back_populates="bounties", overlaps="bounties")
    item: Mapped["GameItem"] = relationship("GameItem", foreign_keys=[server_id, game_name, item_id], back_populates="bounties", overlaps="player,bounties")

def get_server(server_id: int) -> Server:
    server = session.get(Server, server_id)
    if not server:
        server = Server(server_id=server_id)
        session.add(server)
        session.commit()
    return server

def get_user(server_id: int, user_id: int) -> User:
    user = session.get(User, {"server_id": server_id, "user_id": user_id})
    if not user:
        user = User(server_id=server_id, user_id=user_id)
        session.add(user)
        session.commit()
    return user

def get_player_by_user(user: User) -> Player:
    for player in user.server.players:
        if player.archipelago_alias == user.archipelago_alias:
            return player

def create_player(server_id: int, slot: int, archipelago_alias: str):
    player = Player(server_id=server_id, slot=slot, archipelago_alias=archipelago_alias)
    session.add(player)
    session.commit()

def get_player(server_id: int, slot: int) -> Player:
    return session.get(Player, {"server_id": server_id, "slot": slot})

def create_recieved_item(server_id: int, slot: int, location: int, item: int):
    recieved_item = ReceivedItem(server_id=server_id, slot=slot, location=location, item=item)
    session.add(recieved_item)
    session.commit()
    
def has_recieved_item(server_id: int, slot: int, location: int) -> bool:
    if session.get(ReceivedItem, {"server_id": server_id, "slot": slot, "location": location}):
        return True
    return False

def get_item_by_name(player: Player, item_name: str) -> GameItem:
    for game in player.games:
        for item in game.items:
            if item.item_name == item_name:
                return item
    return None

def create_bounty(player: Player, item: GameItem):
    bounty = Bounty(server_id=player.server_id, slot=player.slot, game_name=item.game_name, item_id=item.item_id)
    session.add(bounty)
    session.commit()
    
def get_bounty(player: Player, item: GameItem) -> Bounty:
    return session.get(Bounty, {"server_id": player.server_id, "slot": player.slot, "game_name": item.game_name, "item_id": item.item_id})

def set_game_items(server_id: int, game_name: str, items: dict[str, int]):
    game = session.get(Game, {"server_id": server_id, "game_name": game_name})
    if not game:
        game = Game(server_id=server_id, game_name=game_name)
        session.add(game)
    game.items.clear()
    
    for name, id in items.items():
        item = GameItem(server_id=game.server_id, game_name=game.game_name, item_id=id, item_name=name)
        game.items.append(item)
    session.commit()
        
def commit():
    session.commit()

engine = create_engine("sqlite:///bot_data.db")
session = Session(engine)
base.metadata.create_all(engine)