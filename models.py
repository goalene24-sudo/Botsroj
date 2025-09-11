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
from plugins.utils import Ranks # استيراد الرتب لاستخدامها كقيمة افتراضية

# --- جدول للإعدادات العامة للبوت ---
class GlobalSettings(Base):
    __tablename__ = "global_settings"
    
    key = Column(String, primary_key=True)
    value = Column(JSON)

# --- جدول المجموعات (Chats) ---
class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(BigInteger, primary_key=True, index=True)
    is_active = Column(Boolean, default=True)
    total_msgs = Column(Integer, default=0)
    last_dhikr_time = Column(Integer, default=0)

    # --- (جديد) أعمدة لتخزين الإعدادات بصيغة JSON ---
    command_settings = Column(JSON, default={})
    lock_settings = Column(JSON, default={})
    
    users = relationship("User", back_populates="chat", cascade="all, delete-orphan")
    aliases = relationship("Alias", back_populates="chat", cascade="all, delete-orphan")
    message_history = relationship("MessageHistory", back_populates="chat", cascade="all, delete-orphan")

# --- جدول المستخدمين في المجموعات (Users) ---
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False, index=True)
    
    msg_count = Column(Integer, default=0)
    points = Column(Integer, default=0)
    sahaqat = Column(Integer, default=0)
    join_date = Column(String)
    bio = Column(String, default="لم يتم تعيين نبذة بعد.")
    custom_title = Column(String, nullable=True)
    
    # --- (جديد) عمود لتخزين رتبة المستخدم كرقم ---
    rank = Column(Integer, default=Ranks.MEMBER)
    
    achievements = Column(JSON, default=[]) 
    inventory = Column(JSON, default={})
    
    chat = relationship("Chat", back_populates="users")
    
    __table_args__ = (UniqueConstraint('user_id', 'chat_id', name='_user_chat_uc'),)

# --- جدول الاختصارات (Aliases) ---
class Alias(Base):
    __tablename__ = "aliases"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    alias_name = Column(String, nullable=False)
    command_name = Column(String, nullable=False)
    
    chat = relationship("Chat", back_populates="aliases")

# --- جدول سجل الرسائل (لأوامر التنظيف) ---
class MessageHistory(Base):
    __tablename__ = "message_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    msg_id = Column(BigInteger, nullable=False)
    msg_type = Column(String)
    
    chat = relationship("Chat", back_populates="message_history")

print(">> تم تحميل نماذج البيانات (الجداول) النهائية بنجاح. <<")
