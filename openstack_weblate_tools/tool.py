from openstack_weblate_tools.client import WeblateClient
from openstack_weblate_tools.model import ProjectRequest, ComponentRequest
from pathlib import Path
from collections import defaultdict

# ANSI 색깔 코드
class Colors:
    GREEN = '\033[92m'    # SUCCESS용 초록색
    BLUE = '\033[94m'     # PASS용 파란색
    YELLOW = '\033[93m'   # WARNING용 노란색
    RED = '\033[91m'      # ERROR용 빨간색
    RESET = '\033[0m'     # 색깔 리셋

def print_success(message: str):
    """Print success message in green color"""
    print(f"\033[92m✓ {message}\033[0m", flush=True)

def print_pass(message: str):
    """Print pass message in blue color"""
    print(f"\033[94m→ {message}\033[0m", flush=True)

def print_warning(message: str):
    """Print warning message in yellow color"""
    print(f"\033[93m⚠ {message}\033[0m", flush=True)

def print_error(message: str):
    """Print error message in red color"""
    print(f"\033[91m✗ {message}\033[0m", flush=True)

class WeblateTools:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the Weblate tools
        
        Args:
            config_path: Path to the configuration file
        """
        self.client = WeblateClient(config_path)
    
    def create_project(self, project_name: str) -> dict:
        """Create a project in Weblate"""
        print(f"Creating project {project_name}...")
        
        try:
            project_request = ProjectRequest(
                name=project_name,
                slug=project_name.replace('_', '-'),
                web="https://opendev.org/openstack/" + project_name,
                mail="openstack-discuss@lists.openstack.org"
            )
            
            result = self.client.create_project(project_request)
            print_success(f"Project {project_name} created successfully")
            return result
        except Exception as e:
            print_error(f"Failed to create project {project_name}: {str(e)}")
            raise  # 프로그램 중단을 위해 예외를 다시 발생시킴
    
    def create_component(self, project_name: str, component: ComponentRequest, pot_file_path: str) -> dict:
        """Create a component in Weblate"""
        print(f"Creating component {component.name} for project {project_name}...")
        
        try:
            result = self.client.create_component(component, pot_file_path)
            print_success(f"Component {component.name} created successfully")
            return result
        except Exception as e:
            print_error(f"Failed to create component {component.name}: {str(e)}")
            raise  # 프로그램 중단을 위해 예외를 다시 발생시킴
    
    def upload_translation_file(self, project_name: str, component: str, language: str) -> dict:
        """Upload translation file to Weblate"""
        print(f"Uploading translation file for {component} ({language})...")
        
        try:
            # 파일 경로 결정 - PO 파일 경로 사용
            if component == "releasenotes":
                po_file_path = f"{project_name}/releasenotes/source/locale/ko_KR/LC_MESSAGES/releasenotes.po"
            else:
                # django, neutron-fwaas-dashboard 등은 neutron_fwaas_dashboard/locale 디렉토리에 있음
                package_name = project_name.replace('-', '_')
                po_file_path = f"{project_name}/{package_name}/locale/ko_KR/LC_MESSAGES/{component}.po"
            
            result = self.client.upload_translation_file(
                po_file_path, 
                project_name.replace('_', '-'), 
                component.replace('_', '-'), 
                language
            )
            print_success(f"Translation file uploaded successfully for {component} ({language})")
            return result
        except Exception as e:
            print_error(f"Failed to upload translation file for {component} ({language}): {str(e)}")
            raise  # 프로그램 중단을 위해 예외를 다시 발생시킴

    def migrate(self, project_name: str) -> dict:
        """Migrate project to Weblate"""
        print(f"Migrating {project_name}...")
        print("-" * 32)
        
        try:
            # 1. 프로젝트 생성
            self.create_project(project_name)
            
            # 2. POT 파일들 찾기
            pot_files = []
            locale_dir = Path(f"{project_name}/locale")
            
            if locale_dir.exists():
                for pot_file in locale_dir.glob("*.pot"):
                    pot_files.append(pot_file.name.replace('.pot', ''))
            
            # 3. 각 POT 파일에 대해 컴포넌트 생성
            for component_name in pot_files:
                pot_file_path = f"{project_name}/locale/{component_name}.pot"
                
                if Path(pot_file_path).exists():
                    component_request = ComponentRequest(
                        name=component_name,
                        slug=component_name.replace('_', '-'),
                        project=project_name.replace('_', '-'),
                        filemask=f"*/locale/{component_name}.po",
                        template=f"locale/{component_name}.pot",
                        new_base=f"locale/{component_name}.pot",
                        file_format="po"
                    )
                    
                    self.create_component(project_name, component_request, pot_file_path)
                    
                    # 4. 한국어 PO 파일 업로드 (있는 경우에만)
                    if component_name == "releasenotes":
                        # releasenotes는 다른 경로에 있음
                        ko_po_file_path = f"{project_name}/releasenotes/source/locale/ko_KR/LC_MESSAGES/releasenotes.po"
                    else:
                        # django, neutron-fwaas-dashboard 등은 neutron_fwaas_dashboard/locale 디렉토리에 있음
                        ko_po_file_path = f"{project_name}/neutron_fwaas_dashboard/locale/ko_KR/LC_MESSAGES/{component_name}.po"
                    
                    if Path(ko_po_file_path).exists():
                        self.upload_translation_file(project_name, component_name, "ko")
            
            print_success(f"Migration completed for {project_name}")
            return {"status": "success", "project": project_name}
            
        except Exception as e:
            print_error(f"Migration failed for {project_name}: {str(e)}")
            raise  # 프로그램 중단을 위해 예외를 다시 발생시킴
