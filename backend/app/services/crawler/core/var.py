from contextvars import ContextVar
from typing import List
from asyncio.tasks import Task

request_keyword_var: ContextVar[str] = ContextVar("request_keyword", default="")
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
comment_tasks_var: ContextVar[List[Task]] = ContextVar("comment_tasks", default=[])
source_keyword_var: ContextVar[str] = ContextVar("source_keyword", default="")
task_id_var: ContextVar[str] = ContextVar("task_id", default="")
