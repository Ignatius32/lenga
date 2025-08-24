from pydantic import BaseModel, EmailStr
from pydantic import ConfigDict
from typing import List, Optional
from datetime import datetime


class UserBase(BaseModel):
    id: int
    keycloak_id: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[EmailStr]

    model_config = ConfigDict(from_attributes=True)


class UserMinimalOut(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class BuildingCreate(BaseModel):
    name: str
    address: Optional[str]


class BuildingOut(BaseModel):
    id: int
    name: str
    address: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SpaceCreate(BaseModel):
    building_id: int
    name: str
    type: Optional[str] = None
    capacity: Optional[int] = None
    space_type_id: Optional[int] = None
    space_template_id: Optional[int] = None
    custom_fields: Optional[List[dict]] = None


class SpaceFieldOut(BaseModel):
    id: int
    name: str
    value: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SpaceOut(BaseModel):
    id: int
    building_id: int
    name: str
    type: Optional[str]
    capacity: Optional[int]
    space_template_id: Optional[int]
    custom_fields: Optional[List[SpaceFieldOut]] = None

    model_config = ConfigDict(from_attributes=True)


class StockItemCreate(BaseModel):
    category_id: int
    stock_type_id: Optional[int]
    name: str
    sku: str
    description: Optional[str]


class StockItemOut(BaseModel):
    id: int
    category_id: int
    name: str
    sku: str
    description: Optional[str]
    status: str

    model_config = ConfigDict(from_attributes=True)


class QueueOut(BaseModel):
    id: int
    name: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    subject: str
    description: Optional[str]
    queue_id: int
    ticket_type_id: Optional[int] = None
    custom_fields: Optional[List[dict]] = None


class AgentAssignRequest(BaseModel):
    target_agent_id: int


class AgentStatusChangeRequest(BaseModel):
    status: str
    resolved_at: Optional[datetime]


class AgentCommentRequest(BaseModel):
    comment_text: str
    is_internal: Optional[bool] = False


class TicketTransferRequest(BaseModel):
    target_queue_id: int
    reason: Optional[str]


class ActivityCreateRequest(BaseModel):
    title: str
    category_id: int
    activity_type_id: Optional[int]
    start_time: datetime
    end_time: datetime
    organizer_user_id: int
    custom_fields: Optional[List[dict]] = None


class ActivityUpdateRequest(BaseModel):
    title: Optional[str] = None
    category_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class SpaceBookingRequest(BaseModel):
    space_id: int
    status: Optional[str] = 'Pending'


class StockBookingRequest(BaseModel):
    item_id: int
    status: Optional[str] = 'Pending'


class TicketOut(BaseModel):
    id: int
    subject: str
    description: Optional[str]
    status: str
    priority: Optional[str]
    client_user_id: int
    current_agent_id: Optional[int]
    current_queue_id: int
    ticket_type_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    custom_fields: Optional[List[dict]] = None


class TicketFieldCreate(BaseModel):
    name: str
    field_type: str  # 'text', 'select', 'space'
    options: Optional[List[str]] = None


class TicketFieldOut(BaseModel):
    id: int
    name: str
    field_type: str
    options: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class TicketTypeCreate(BaseModel):
    queue_id: int
    name: str
    allowed_group_ids: Optional[List[int]] = None
    fields: Optional[List[TicketFieldCreate]] = None


class TicketTypeOut(BaseModel):
    id: int
    queue_id: int
    name: str
    allowed_group_ids: Optional[List[int]] = None
    fields: Optional[List[TicketFieldOut]] = None

    model_config = ConfigDict(from_attributes=True)


class TicketTypeUpdate(BaseModel):
    queue_id: Optional[int] = None
    name: Optional[str] = None
    allowed_group_ids: Optional[List[int]] = None
    fields: Optional[List[TicketFieldCreate]] = None


class ActivityOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category_id: int
    activity_type_id: Optional[int]
    organizer_user_id: int
    start_time: datetime
    end_time: datetime

    model_config = ConfigDict(from_attributes=True)
    custom_fields: Optional[List[dict]] = None


class ActivityTypeCreate(BaseModel):
    name: str
    metadata: Optional[str]


class ActivityFieldCreate(BaseModel):
    name: str
    field_type: str
    options: Optional[List[str]] = None


class ActivityTypeCreateWithFields(BaseModel):
    name: str
    metadata: Optional[str]
    fields: Optional[List[ActivityFieldCreate]] = None


class ActivityTypeOut(BaseModel):
    id: int
    name: str
    metadata: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ActivityFieldOut(BaseModel):
    id: int
    name: str
    field_type: str
    options: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)

class ActivityTypeWithFieldsOut(BaseModel):
    id: int
    name: str
    metadata: Optional[str]
    fields: Optional[List[ActivityFieldOut]] = None

    model_config = ConfigDict(from_attributes=True)

    model_config = ConfigDict(from_attributes=True)


class SpaceTypeCreate(BaseModel):
    name: str
    metadata: Optional[str]


class SpaceFieldOut(BaseModel):
    id: int
    name: str
    value: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SpaceTypeOut(BaseModel):
    id: int
    name: str
    metadata: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class StockTypeCreate(BaseModel):
    name: str
    metadata: Optional[str]


class StockTypeOut(BaseModel):
    id: int
    name: str
    metadata: Optional[str]

    class Config:
        orm_mode = True


class UserRoleAssign(BaseModel):
    user_id: int
    role_name: Optional[str] = None


class UserCreate(BaseModel):
    keycloak_id: str
    dni: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserUpdate(BaseModel):
    dni: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GroupOut(BaseModel):
    id: int
    name: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class QueueCreate(BaseModel):
    name: str
    description: Optional[str] = None


class QueueOut(BaseModel):
    id: int
    name: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class UserGroupAssign(BaseModel):
    user_id: int


class QueuePermissionAssign(BaseModel):
    group_id: int
    queue_id: int


class AgentAssignmentCreate(BaseModel):
    agent_user_id: int
    queue_id: int
    access_level: Optional[str] = None


class AgentAssignmentOut(BaseModel):
    id: int
    agent_user_id: int
    queue_id: int
    access_level: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class QueuePermissionOut(BaseModel):
    id: int
    group_id: int
    queue_id: int

    model_config = ConfigDict(from_attributes=True)


class UserGroupOut(BaseModel):
    user_id: int
    group_id: int

    model_config = ConfigDict(from_attributes=True)


class UserProfileOut(BaseModel):
    id: int
    keycloak_id: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[EmailStr]
    roles: Optional[List[str]] = []
    groups: Optional[List[int]] = []

    model_config = ConfigDict(from_attributes=True)


class AttachmentOut(BaseModel):
    id: int
    ticket_id: int
    comment_id: Optional[int]
    file_name: str
    file_path: str
    uploader: Optional[dict]

    model_config = ConfigDict(from_attributes=True)


class CommentOut(BaseModel):
    id: int
    ticket_id: int
    author: Optional[dict]
    comment_text: str
    is_internal: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MovementOut(BaseModel):
    id: int
    ticket_id: int
    timestamp: datetime
    action_user: Optional[dict]
    action_type: str
    details: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TicketHistoryOut(BaseModel):
    ticket_id: int
    movements: List[MovementOut]
    comments: List[CommentOut]
    attachments: List[AttachmentOut]

    model_config = ConfigDict(from_attributes=True)

