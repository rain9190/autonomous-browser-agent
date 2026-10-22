from typing import Literal
from pydantic import BaseModel,ConfigDict,Field


class Answer(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    field_id:str=Field(pattern=r'^q\d{1,2}$')
    status:Literal['fill','ask','leave']
    text:str|None=Field(max_length=2000)
    choices:list[str]=Field(max_length=20)
    evidence:str|None=Field(max_length=2000)


class Plan(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    answers:list[Answer]=Field(max_length=40)
