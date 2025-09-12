# models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base

# --- جدول للإعدادات العامة للبوت (تم تصحيح الاسم) ---
class GlobalSetting(Base):
    __tablename__ = "global_settings"
    
    key = Column(String, primary_key=True)
    value = Column(String) # تم التغيير من JSON إلى String ليتوافق مع confess.py

# --- جدول المجموعات (Chats) ---
class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(BigInteger, primary_key=True, index=True)
    is_active = Column(Boolean, default=True)
    total_msgs = Column(Integer, default=0)
    
    # --- (جديد) حقل JSON لتخزين جميع إعدادات المجموعة ---
    settings = Column(JSON, default={})
    # سيحتوي هذا على: dhikr_enabled, dhikr_interval, max_warns, welcome_msg, dev_reply, etc.
    
    lock_settings = Column(JSON, default={})
    filtered_words = Column(JSON, default=[])
    custom_replies = Column(JSON, default={})
    
    users = relationship("User", back_populates="chat", cascade="all, delete-orphan")
    aliases = relationship("Alias", back_populates="chat", cascade="all, delete-orphan")
    message_history = relationship("MessageHistory", back_populates="chat", cascade="all, delete-orphan")

# (تمت الإضافة) هذا السطر سيقوم بحل خطأ استيراد 'Group'
Group = Chat

# --- جدول المستخدمين في المجموعات (Users) ---
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False, index=True)
    
    msg_count = Column(Integer, default=0)
    points = Column(Integer, default=0)
    sahaqat = Column(Integer, default=0)
    warns = Column(Integer, default=0) # <-- (جديد) عمود للتحذيرات
    join_date = Column(String)
    bio = Column(String, default="لم يتم تعيين نبذة بعد.")
    custom_title = Column(String, nullable=True)
    rank = Column(Integer, default=0)
    
    achievements = Column(JSON, default=[]) 
    inventory = Column(JSON, default={})
    
    chat = relationship("Chat", back_populates="users")
    
    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='_user_chat_uc'),)

# --- (لا تغيير على الجداول التالية) ---
class Alias(Base):
    __tablename__ = "aliases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    alias_name = Column(String, nullable=False)
    command_name = Column(String, nullable=False)
    chat = relationship("Chat", back_populates="aliases")

class MessageHistory(Base):
    __tablename__ = "message_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    msg_id = Column(BigInteger, nullable=False)
    msg_type = Column(String)
    chat = relationship("Chat", back_populates="message_history")

# --- (تمت الإضافة) الجداول المفقودة التي تم استنتاجها ---

class Vip(Base):
    __tablename__ = "vips"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='_vip_user_chat_uc'),)

class SecondaryDev(Base):
    __tablename__ = "secondary_devs"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='_secondarydev_user_chat_uc'),)

class Creator(Base):
    __tablename__ = "creators"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='_creator_user_chat_uc'),)

class BotAdmin(Base):
    __tablename__ = "bot_admins"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='_botadmin_user_chat_uc'),)

class CommandSetting(Base):
    __tablename__ = "command_settings"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    command = Column(String, nullable=False)
    is_enabled = Column(Boolean, default=True)
    __table_args__ = (UniqueConstraint('chat_id', 'command', name='_cmdsetting_chat_command_uc'),)

class CustomCommand(Base):
    __tablename__ = "custom_commands"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    response = Column(String, nullable=False)
    show_button = Column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('chat_id', 'name', name='_customcmd_chat_name_uc'),)

class Lock(Base):
    __tablename__ = "locks"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    lock_type = Column(String, nullable=False)
    is_locked = Column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('chat_id', 'lock_type', name='_lock_chat_type_uc'),)


print(">> تم تحميل نماذج البيانات (الجداول) النهائية والشاملة بنجاح. <<")
