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
from database import Base, engine

# --- جدول المجموعات (Chats) ---
# سيحتوي هذا الجدول على معلومات وإعدادات كل مجموعة
class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(BigInteger, primary_key=True, index=True) # Chat ID
    is_active = Column(Boolean, default=True)
    total_msgs = Column(Integer, default=0)
    last_dhikr_time = Column(Integer, default=0)
    
    # علاقات لربط الجداول الأخرى بهذه المجموعة
    users = relationship("User", back_populates="chat", cascade="all, delete-orphan")
    aliases = relationship("Alias", back_populates="chat", cascade="all, delete-orphan")
    message_history = relationship("MessageHistory", back_populates="chat", cascade="all, delete-orphan")

# --- جدول المستخدمين في المجموعات (Users) ---
# سيحتوي هذا الجدول على معلومات كل مستخدم في كل مجموعة ينضم إليها
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True) # User's Telegram ID
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False, index=True)
    
    msg_count = Column(Integer, default=0)
    points = Column(Integer, default=0)
    sahaqat = Column(Integer, default=0)
    join_date = Column(String)
    
    # سنستخدم نوع JSON لتخزين البيانات المعقدة مثل المخزون والأوسمة
    achievements = Column(JSON, default=[]) 
    inventory = Column(JSON, default={})
    
    # علاقة لربط المستخدم بالمجموعة
    chat = relationship("Chat", back_populates="users")
    
    # قيد لضمان عدم تكرار نفس المستخدم في نفس المجموعة
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

# --- رسالة تأكيد عند تحميل الملف ---
print(">> تم تحميل نماذج البيانات (الجداول) بنجاح. <<")