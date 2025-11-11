from pydantic import BaseModel


class Page(BaseModel):
    text: str
    number: int


class PageChunk(BaseModel):
    text: str
    start_page: int
    end_page: int
