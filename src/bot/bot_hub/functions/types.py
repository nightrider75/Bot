from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel
from bot_engine.services.llm_service import PreSayMap

## Function Provider Types


class FunctionParameter(BaseModel):
    property_type: str
    description: str
    enum: Optional[List[str]] = None
    required: bool = False


class FunctionTransitionNode(BaseModel):
    node: str
    description: Optional[str] = None


class BotFunction(BaseModel):
    id: str
    name: str
    description: str
    parameters: Dict[str, FunctionParameter] = []
    transition_nodes: List[FunctionTransitionNode] = list()


## Function Integration Types
# Add support for presay etc related params
class FunctionInstance(BaseModel):
    id: UUID
    function_id: str
    function_label: Optional[str] = None
    node_id: UUID
    bot_id: UUID
    transition_mappings: Dict[str, str] = dict()
    pre_say: PreSayMap = dict()
    ack_llm_description: Optional[str] = None


## Function Invocation Types
class FunctionInvocationInputs(BaseModel):
    bot_id: UUID
    user_id: str
    inputs: Dict[str, Optional[Any]] = dict()
    bot_state: Dict[str, Optional[Any]] = dict()


class FunctionInvocationOutputs(BaseModel):
    output: Union[None, str, Dict[str, Any]] = None
    next_node: Optional[str] = None
    state_updates: Dict[str, Optional[Any]] = dict()
