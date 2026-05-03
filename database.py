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
        Index("ix_user_server_alias", "server_id", "archipelago_alias")
    )

    server: Mapped["Server"] = relationship("Server", foreign_keys=[server_id], back_populates="users")
    
class Player(base):
    __tablename__ = "player"
    
    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_name: Mapped[str] = mapped_column(String)
    archipelago_alias: Mapped[str] = mapped_column(String)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id"], ["server.server_id"], ondelete="CASCADE"),
        Index("ix_player_server_alias", "server_id", "archipelago_alias")
    )
    
    server: Mapped["Server"] = relationship("Server", foreign_keys=[server_id], back_populates="players")
    received_items: Mapped[list["ReceivedItem"]] = relationship("ReceivedItem", back_populates="player", cascade="all, delete-orphan")
    bounties: Mapped[list["Bounty"]] = relationship("Bounty", back_populates="player", cascade="all, delete-orphan")
    
class Game(base):
    __tablename__ = "game"
    
    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_name: Mapped[str] = mapped_column(String, primary_key=True)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id"], ["server.server_id"], ondelete="CASCADE"),
    )
    
    server: Mapped["Server"] = relationship("Server", foreign_keys=[server_id], back_populates="games")
    items: Mapped[list["Item"]] = relationship("Item", back_populates="game", cascade="all, delete-orphan")
    locations: Mapped[list["Location"]] = relationship("Location", back_populates="game", cascade="all, delete-orphan")

class Item(base):
    __tablename__ = "item"

    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_name: Mapped[str] = mapped_column(String)
    item_name: Mapped[str] = mapped_column(String)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id", "game_name"], ["game.server_id", "game.game_name"], ondelete="CASCADE"),
        Index("ix_item_lookup", "server_id", "game_name", "item_name")
    )
    
    game: Mapped["Game"] = relationship("Game", foreign_keys=[server_id, game_name], back_populates="items")
    bounties: Mapped[list["Bounty"]] = relationship("Bounty", back_populates="item", viewonly=True)
    received_items: Mapped[list["ReceivedItem"]] = relationship("ReceivedItem", back_populates="item", viewonly=True)
    

class Location(base):
    __tablename__ = "location"

    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_name: Mapped[str] = mapped_column(String)
    location_name: Mapped[str] = mapped_column(String)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id", "game_name"], ["game.server_id", "game.game_name"], ondelete="CASCADE"),
    )
    
    game: Mapped["Game"] = relationship("Game", foreign_keys=[server_id, game_name], back_populates="locations")
    received_items: Mapped[list["ReceivedItem"]] = relationship("ReceivedItem", back_populates="location", viewonly=True)

class ReceivedItem(base):
    __tablename__ = "received_item"
    
    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(Integer)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id", "slot"], ["player.server_id", "player.slot"], ondelete="CASCADE"),
        ForeignKeyConstraint(["server_id", "item_id"], ["item.server_id", "item.item_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["server_id", "location_id"], ["location.server_id", "location.location_id"], ondelete="CASCADE")
    )
    
    player: Mapped["Player"] = relationship("Player", foreign_keys=[server_id, slot], back_populates="received_items")
    item: Mapped["Item"] = relationship("Item", foreign_keys=[server_id, item_id], back_populates="received_items", viewonly=True)
    location: Mapped["Location"] = relationship("Location", foreign_keys=[server_id, location_id], back_populates="received_items", viewonly=True)

class Bounty(base):
    __tablename__ = "bounty"

    server_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    __table_args__ = (
        ForeignKeyConstraint(["server_id", "slot"], ["player.server_id", "player.slot"], ondelete="CASCADE"),
        ForeignKeyConstraint(["server_id", "item_id"], ["item.server_id", "item.item_id"], ondelete="CASCADE")
    )
    
    player: Mapped["Player"] = relationship("Player", foreign_keys=[server_id, slot], back_populates="bounties", overlaps="bounties")
    item: Mapped["Item"] = relationship("Item", foreign_keys=[server_id, item_id], back_populates="bounties", overlaps="player,bounties")

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
    return session.query(Player).filter_by(server_id=user.server_id, archipelago_alias=user.archipelago_alias).first()
        
def get_user_by_player(player: Player) -> User:
    return session.query(User).filter_by(server_id=player.server_id, archipelago_alias=player.archipelago_alias).first()

def create_player(server_id: int, slot: int, archipelago_alias: str, game_name: str):
    player = Player(server_id=server_id, slot=slot, archipelago_alias=archipelago_alias, game_name=game_name)
    session.add(player)
    session.commit()

def get_player(server_id: int, slot: int) -> Player:
    return session.get(Player, {"server_id": server_id, "slot": slot})

def create_received_item(server_id: int, slot: int, item_id: int, location_id: int):
    if not has_received_item(server_id, slot, location_id):
        received_item = ReceivedItem(server_id=server_id, slot=slot, item_id=item_id, location_id=location_id)
        session.add(received_item)
        session.commit()
    
def has_received_item(server_id: int, slot: int, location_id: int) -> bool:
    if session.get(ReceivedItem, {"server_id": server_id, "slot": slot, "location_id": location_id}):
        return True
    return False

def get_item(server_id: int, item_id: int) -> Item:
    return session.get(Item, {"server_id": server_id, "item_id": item_id})

def get_location(server_id: int, location_id: int) -> Location:
    return session.get(Location, {"server_id": server_id, "location_id": location_id})

def get_item_by_name(player: Player, item_name: str) -> Item:
    return session.query(Item).filter_by(server_id=player.server_id, game_name=player.game_name, item_name=item_name).first()

def create_bounty(player: Player, item: Item):
    bounty = Bounty(server_id=player.server_id, slot=player.slot, item_id=item.item_id)
    session.add(bounty)
    session.commit()
    
def get_bounty(player: Player, item: Item) -> Bounty:
    return session.get(Bounty, {"server_id": player.server_id, "slot": player.slot, "item_id": item.item_id})

def set_game_items_and_locations(server_id: int, game_name: str, items: dict[str, int], locations: dict[str, int]):
    game = session.get(Game, {"server_id": server_id, "game_name": game_name})
    if not game:
        server = session.get(Server, {"server_id": server_id})
        game = Game(server_id=server_id, game_name=game_name)
        server.games.append(game)
    game.items.clear()
    game.locations.clear()
    session.commit()
    
    for name, id in items.items():
        item = Item(server_id=game.server_id, game_name=game.game_name, item_id=id, item_name=name)
        game.items.append(item)

    for name, id in locations.items():
        location = Location(server_id=game.server_id, game_name=game.game_name, location_id=id, location_name=name)
        game.locations.append(location)
    session.commit()
        
def commit():
    session.commit()

engine = create_engine("sqlite:///bot_data.db")
session = Session(engine)
base.metadata.create_all(engine)