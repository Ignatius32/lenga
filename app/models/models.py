from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    keycloak_id = Column(String, unique=True, index=True, nullable=False)
    dni = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class UserRole(Base):
    __tablename__ = 'user_roles'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'), primary_key=True)


class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)


class UserGroup(Base):
    __tablename__ = 'user_groups'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)


class QueuePermission(Base):
    __tablename__ = 'queue_permissions'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    queue_id = Column(Integer, ForeignKey('queues.id'))


class Building(Base):
    __tablename__ = 'buildings'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    spaces = relationship('Space', back_populates='building')


class Space(Base):
    __tablename__ = 'spaces'
    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey('buildings.id'))
    space_type_id = Column(Integer, ForeignKey('space_types.id'), nullable=True)
    space_template_id = Column(Integer, ForeignKey('space_templates.id'), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)
    building = relationship('Building', back_populates='spaces')


class SpaceType(Base):
    __tablename__ = 'space_types'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    meta = Column('metadata', Text, nullable=True)


class SpaceTemplate(Base):
    __tablename__ = 'space_templates'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)


class SpaceTemplateField(Base):
    __tablename__ = 'space_template_fields'
    id = Column(Integer, primary_key=True)
    space_template_id = Column(Integer, ForeignKey('space_templates.id'))
    name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # text, select, number, etc.
    options = Column(Text, nullable=True)


class StockCategory(Base):
    __tablename__ = 'stock_categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class StockType(Base):
    __tablename__ = 'stock_types'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    meta = Column('metadata', Text, nullable=True)


class StockItem(Base):
    __tablename__ = 'stock_items'
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('stock_categories.id'))
    stock_type_id = Column(Integer, ForeignKey('stock_types.id'), nullable=True)
    name = Column(String, nullable=False)
    sku = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='Available')


class ActivityCategory(Base):
    __tablename__ = 'activity_categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class ActivityType(Base):
    __tablename__ = 'activity_types'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    meta = Column('metadata', Text, nullable=True)


class ActivityTypeField(Base):
    __tablename__ = 'activity_type_fields'
    id = Column(Integer, primary_key=True)
    activity_type_id = Column(Integer, ForeignKey('activity_types.id'))
    name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # text, select, space
    options = Column(Text, nullable=True)


class ActivityFieldValue(Base):
    __tablename__ = 'activity_field_values'
    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('activities.id'))
    field_id = Column(Integer, ForeignKey('activity_type_fields.id'))
    value = Column(Text, nullable=True)


class Activity(Base):
    __tablename__ = 'activities'
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('activity_categories.id'))
    activity_type_id = Column(Integer, ForeignKey('activity_types.id'), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    organizer_user_id = Column(Integer, ForeignKey('users.id'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)


class SpaceBooking(Base):
    __tablename__ = 'space_bookings'
    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('activities.id'))
    space_id = Column(Integer, ForeignKey('spaces.id'))
    status = Column(String, nullable=False, default='Pending')


class StockBooking(Base):
    __tablename__ = 'stock_bookings'
    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('activities.id'))
    item_id = Column(Integer, ForeignKey('stock_items.id'))
    status = Column(String, nullable=False, default='Pending')


class SpaceFieldValue(Base):
    __tablename__ = 'space_field_values'
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey('spaces.id'))
    field_name = Column(String, nullable=False)
    value = Column(Text, nullable=True)


class Queue(Base):
    __tablename__ = 'queues'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)


class AgentAssignment(Base):
    __tablename__ = 'agent_assignments'
    id = Column(Integer, primary_key=True)
    agent_user_id = Column(Integer, ForeignKey('users.id'))
    queue_id = Column(Integer, ForeignKey('queues.id'))
    access_level = Column(String, nullable=True)


class TicketType(Base):
    __tablename__ = 'ticket_types'
    id = Column(Integer, primary_key=True)
    queue_id = Column(Integer, ForeignKey('queues.id'))
    name = Column(String, nullable=False)


class TicketTypeAllowedGroup(Base):
    __tablename__ = 'ticket_type_allowed_groups'
    ticket_type_id = Column(Integer, ForeignKey('ticket_types.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)


class TicketTypeField(Base):
    __tablename__ = 'ticket_type_fields'
    id = Column(Integer, primary_key=True)
    ticket_type_id = Column(Integer, ForeignKey('ticket_types.id'))
    name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # e.g., text, select, space
    options = Column(Text, nullable=True)  # JSON-encoded list for select options


class TicketFieldValue(Base):
    __tablename__ = 'ticket_field_values'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    field_id = Column(Integer, ForeignKey('ticket_type_fields.id'))
    value = Column(Text, nullable=True)


class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='New')
    priority = Column(String, nullable=True)
    client_user_id = Column(Integer, ForeignKey('users.id'))
    current_agent_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    current_queue_id = Column(Integer, ForeignKey('queues.id'))
    ticket_type_id = Column(Integer, ForeignKey('ticket_types.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class TicketComment(Base):
    __tablename__ = 'ticket_comments'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    author_user_id = Column(Integer, ForeignKey('users.id'))
    comment_text = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TicketMovementLog(Base):
    __tablename__ = 'ticket_movement_log'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    action_user_id = Column(Integer, ForeignKey('users.id'))
    action_type = Column(String, nullable=False)
    details = Column(Text, nullable=True)


class Attachment(Base):
    __tablename__ = 'attachments'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    comment_id = Column(Integer, ForeignKey('ticket_comments.id'), nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploader_user_id = Column(Integer, ForeignKey('users.id'))
