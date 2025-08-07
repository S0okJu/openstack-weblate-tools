import os
import requests
import yaml
from typing import Optional
from openstack_weblate_tools.model import Project, Component, ProjectRequest, ComponentRequest, UploadTranslationFileRequest

class WeblateClient:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the Weblate client
        
        Args:
            config_path: Path to the configuration file
        """
        self._load_config(config_path)
        
    def _load_config(self, config_path: str):
        """Load configuration from YAML file
        
        Required configuration:
        - weblate.base_url: The base URL of the Weblate instance
        - weblate.api_key: The API key for the Weblate instance
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.base_url = config['weblate']['base_url']
            self.api_key = config['weblate']['api_key']
        except (FileNotFoundError, KeyError, yaml.YAMLError) as e:
            raise ValueError(f"Failed to load configuration from {config_path}: {e}")
        
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def _get(self, endpoint: str, params: dict = None) -> requests.Response:
        """Get a resource from the Weblate instance
        
        Args:
            endpoint: The endpoint of the resource
            params: The parameters to pass to the resource
        """
        url = f"{self.base_url}/api/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        return response
    
    def _post(self, endpoint: str, data: dict, files: dict = None) -> requests.Response:
        """Post a resource to the Weblate instance
        
        Args:
            endpoint: The endpoint of the resource
            data: The data to post to the resource
        """
        url = f"{self.base_url}/api/{endpoint}"
        
        if files is not None:
            # 파일 업로드 시에는 Content-Type을 자동으로 설정하도록 헤더에서 제거
            headers = {k: v for k, v in self.headers.items() if k != "Content-Type"}
            response = requests.post(url, headers=headers, data=data, files=files)
        else:
            response = requests.post(url, headers=self.headers, json=data)
        return response

    
    def get_project(self, name: str) -> Optional[Project]:
        """Get a project from the Weblate instance
        
        Args:
            name: The name of the project
        """
        response = self._get(endpoint=f"projects/{name}/")
        if response.status_code == 200:
            response_data = response.json()
            return Project(name=response_data["name"])
        elif response.status_code == 404:
            return None
        else:
            raise Exception(f"Failed to get project: {response.text}")
        
        
    def create_project(self, project: ProjectRequest) -> Project:
        """Create a project in the Weblate instance
        
        Args:
            project: The project to create
        """
        existing_project = self.get_project(project.name)
        if existing_project is not None:
            return existing_project
        
        response = self._post("projects/", data=project.to_dict())
        if response.status_code == 201:
            response_data = response.json()
            return Project(name=response_data["name"])
        else:
            raise Exception(f"Failed to create project: {response.text}")
    
    def get_component(self, project_slug: str, component_slug: str) -> Optional[Component]:
        """Get a component from the Weblate instance
        
        Args:
            project_slug: The slug of the project
            component_slug: The slug of the component
        """
        response = self._get(endpoint=f"projects/{project_slug}/components/{component_slug}/")
        
        if response.status_code == 200:
            response_data = response.json()
            return Component(
                name=response_data["name"],
                slug=response_data["slug"],
                url=response_data["url"],
            )
        elif response.status_code == 404: 
            return None
        else:
            return None  # 기타 오류도 None으로 처리하여 skip
    
    def create_component(self, component: ComponentRequest, file_path: str) -> Component:
        """Create a component in the Weblate instance
        
        Args:
            component: The component to create
            file_path: The path to the template file
        """
        # 기존 컴포넌트 확인
        existing_component = self.get_component(component.project, component.slug)
        if existing_component is not None:
            return existing_component
        
        data = component.to_data_dict()
        
        # 파일이 존재하는지 확인
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Template file not found: {file_path}")
        
        # 파일 내용을 읽어서 업로드
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # file_format 추가
        data["file_format"] = "po"
        
        files = {
            "docfile": (os.path.basename(file_path), file_content, "application/x-gettext")
        }
        
        # 올바른 엔드포인트 사용: projects/{project}/components/
        endpoint = f"projects/{component.project}/components/"
        response = self._post(endpoint, data=data, files=files)
        if response.status_code == 201:
            response_data = response.json()
            return Component(
                name=response_data["name"],
                slug=response_data["slug"],
                url=response_data["url"],
            )
        elif response.status_code == 400 and "Component or category with the same URL slug already exists" in response.text:
            # 중복 컴포넌트 오류인 경우 기존 컴포넌트로 간주하고 조용히 반환
            return Component(
                name=component.name,
                slug=component.slug,
                url=f"{self.base_url}/projects/{component.project}/components/{component.slug}/"
            )
        else:
            raise Exception(f"Failed to create component: {response.text}")
    
    def upload_translation_file(self, file_path: str, project_name: str, component_name: str, language: str) -> dict:
        """Upload a translation file to the Weblate instance
        
        Args:
            file_path: The path to the file to upload
            project_name: The name of the project
            component_name: The name of the component
            language: The language of the translation
        """
        # 파일이 존재하는지 확인
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Translation file not found: {file_path}")
        
        # 파일 내용을 읽어서 업로드
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        files = {
            "file": (os.path.basename(file_path), file_content, "application/x-gettext")
        }
        
        data = {
            "method": "translate",
            "fuzzy": "process"
        }
        
        # 올바른 Weblate API 엔드포인트: translations/{project}/{component}/{language}/file/
        endpoint = f"translations/{project_name}/{component_name}/{language}/file/"
        
        response = self._post(endpoint, data=data, files=files)
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to upload translation file: {response.text}")
    