import argparse
import sys
import os
from openstack_weblate_tools.client import WeblateClient
from openstack_weblate_tools.tool import WeblateTools, print_success, print_error

class OpenStackWeblateCLI:
    def __init__(self, config_path: str = "config.yaml"):
        self.tool = WeblateTools(config_path)
        
    def run(self):
        """CLI 메인 실행 함수"""
        parser = argparse.ArgumentParser(
            description="OpenStack Weblate Migration Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python -m openstack_weblate_tools.cli migrate neutron-fwaas-dashboard
  python -m openstack_weblate_tools.cli migrate neutron-fwaas-dashboard --config my_config.yaml
            """
        )
        
        parser.add_argument('project_name', help='Name of the OpenStack project to migrate')
        parser.add_argument('--config', default='config.yaml', help='Path to configuration file (default: config.yaml)')
        
        args = parser.parse_args()
        
        try:
            self.migrate_project(args.project_name, args.config)
        except KeyboardInterrupt:
            print_error("\nOperation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print_error(f"Error: {str(e)}")
            sys.exit(1)
    
    def migrate_project(self, project_name: str, config_path: str):
        """프로젝트 전체 마이그레이션"""
        print_success(f"Starting migration for project: {project_name}")
        tool = WeblateTools(config_path)
        tool.migrate(project_name)
        print_success(f"Migration completed for project: {project_name}")

def main():
    """CLI 진입점"""
    cli = OpenStackWeblateCLI()
    cli.run()

if __name__ == "__main__":
    main() 