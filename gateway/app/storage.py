from __future__ import annotations

import json
import os
import time
import uuid
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import create_engine, Column, String, Float, Integer, LargeBinary, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pseudo = Column(String(32), unique=True, nullable=False)
    created_at = Column(Float, default=time.time)
    consent_at = Column(Float, default=time.time)
    sequence = Column(JSON, default=lambda: ["face", "body", "hand"])
    randomized = Column(Integer, default=0)
    failures = Column(Integer, default=0)
    locked_until = Column(Float, default=0)


class Template(Base):
    __tablename__ = "templates"
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    layer = Column(String, primary_key=True)
    features = Column(LargeBinary, nullable=False)
    version = Column(Integer, default=1)
    updated_at = Column(Float, default=time.time)


class Attempt(Base):
    __tablename__ = "auth_attempts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    started_at = Column(Float, default=time.time, index=True)
    layers = Column(JSON)
    scores = Column(JSON)
    result = Column(String)
    latency_ms = Column(Float)


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(JSON)


class VaultItem(Base):
    __tablename__ = "vault_items"
    id = Column(String, primary_key=True, default="active")
    object_key = Column(String, default="original-meme.png")
    caption = Column(String, default="MECHNI FEHEM HATA CHY")


class Database:
    def __init__(self, config):
        args = {"check_same_thread": False} if config.database_url.startswith("sqlite") else {}
        self.engine = create_engine(config.database_url, connect_args=args, pool_pre_ping=True)
        self.session = sessionmaker(self.engine, expire_on_commit=False)
        self.cipher = AESGCM(bytes.fromhex(config.encryption_key))

    def initialize(self):
        Base.metadata.create_all(self.engine)
        with self.session.begin() as db:
            if not db.get(VaultItem, "active"):
                db.add(VaultItem())
            if not db.get(Setting, "minimum_score"):
                db.add(Setting(key="minimum_score", value=0.8))

    def encrypt(self, user_id, layer, value):
        nonce = os.urandom(12)
        return nonce + self.cipher.encrypt(nonce, json.dumps(value).encode(), f"{user_id}:{layer}".encode())

    def decrypt(self, template):
        data = template.features
        return json.loads(self.cipher.decrypt(data[:12], data[12:], f"{template.user_id}:{template.layer}".encode()))
