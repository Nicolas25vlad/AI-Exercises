from pydantic import BaseModel

class Recado(BaseModel):
    autor: str
    mensagem: str