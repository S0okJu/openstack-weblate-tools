from pydantic import BaseModel

class ProjectRequest(BaseModel):
    name: str
    slug: str
    web: str
    
    def to_dict(self) -> dict:
        return self.model_dump()

class Project(BaseModel):
    name: str

class ComponentRequest(BaseModel):
    name: str
    slug: str
    project: str
    file_format: str = "po-mono"
    source_language: str = "en"


    def to_data_dict(self) -> dict:
        return self.model_dump()

class Component(BaseModel):
    name: str
    slug: str
    url: str

class UploadTranslationFileRequest(BaseModel):
    method: str = "translate"
    
    def to_dict(self) -> dict:
        return self.model_dump()