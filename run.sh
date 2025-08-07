#!/bin/bash

# 스크립트가 실행되는 디렉토리로 이동
cd "$(dirname "$0")"

# 스크립트 디렉토리의 절대 경로 저장
SCRIPT_DIR="$(pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

function setup_venv() {
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi

    ${VENV_DIR}/bin/pip3 install -r requirements.txt
}

function setup_weblate_tools() {
    if [ ! -d "openstack_weblate_tools" ]; then
        echo "Cloning openstack-weblate-tools..."
        git clone https://github.com/S0okJu/openstack-weblate-tools.git
    fi

    # 가상환경에서 weblate tools 설치
    echo "Installing openstack_weblate_tools package..."
    ${VENV_DIR}/bin/pip3 install -e openstack_weblate_tools/
}

function setup_directory {
    mkdir -p ${PROJECT_NAME}/locale
}

function extract_messages_releasenotes {
    local keep_workdir=$1
    
    echo "Extracting releasenotes messages..."
    echo "Current directory: $(pwd)"
    echo "Checking .venv/bin/sphinx-build: $(ls -la .venv/bin/sphinx-build 2>/dev/null || echo 'NOT FOUND')"
    
    # 메세지 추출 
    cd ${PROJECT_NAME}
    ${VENV_DIR}/bin/sphinx-build -b gettext -d releasenotes/build/doctrees \
        releasenotes/source releasenotes/work
    
    
    # pot 파일들을 저장하는 work 디렉토리를 생성
    echo "Checking work directory..."
    if [ ! -d releasenotes/work ]; then
        mkdir -p releasenotes/work
    fi

    # 기존 빌드 디렉토리 삭제     
    rm -rf releasenotes/build
    
    # work 디렉토리에 있는 pot 파일을 하나로 합친다. 
    mkdir -p releasenotes/source/locale/
    if [ -d releasenotes/work ] && [ "$(ls -A releasenotes/work/*.pot 2>/dev/null)" ]; then
        echo "Found .pot files, concatenating..."

        # 원래 코드에서는 /releasenotes/source/locale/releasenotes.pot 파일을 생성함.
        # 임시로 /locale/releasenotes.pot 파일을 생성함.
        # msgcat --sort-by-file releasenotes/work/*.pot \
        #     > releasenotes/source/locale/releasenotes.pot
        msgcat --sort-by-file releasenotes/work/*.pot \
            > locale/releasenotes.pot
        
        echo "Created releasenotes.pot"
    else
        echo "No .pot files found in work directory"
    fi  
    
    # keep_workdir가 비어 있으면 워크 디렉토리를 삭제한다.
    if [ ! -n "$keep_workdir" ]; then
        rm -rf releasenotes/work
    fi
}

# 공식 문서 참고
# https://opendev.org/openstack/openstack-zuul-jobs/src/branch/master/roles/prepare-zanata-client/files/common_translation_update.sh#L402
function extract_django_messages {

    KEYWORDS="-k gettext_noop -k gettext_lazy -k ngettext_lazy:1,2"
    KEYWORDS+=" -k ugettext_noop -k ugettext_lazy -k ungettext_lazy:1,2"
    KEYWORDS+=" -k npgettext:1c,2,3 -k pgettext_lazy:1c,2 -k npgettext_lazy:1c,2,3"
    
    # babel-django.cfg 또는 babel-djangojs.cfg 파일 존재 시에만 실행
	# 프로젝트 폴더 내에 존재함 
    for DOMAIN in djangojs django ; do
        if [ -f babel-${DOMAIN}.cfg ]; then
            pot=locale/${DOMAIN}.pot
            touch ${pot}
			
            ${VENV_DIR}/bin/pybabel extract -F babel-${DOMAIN}.cfg  \
                --add-comments Translators: \
                --msgid-bugs-address="https://bugs.launchpad.net/openstack-i18n/" \
                --project=${PROJECT_NAME} --version=1.0 \
                $KEYWORDS \
                -o ${pot} .
			# POT 파일이 비어있는지 검증 
            check_empty_pot ${pot}
        fi
    done
    
}

# 공식 문서 참고
# https://opendev.org/openstack/openstack-zuul-jobs/src/branch/master/roles/prepare-zanata-client/files/common_translation_update.sh#L367
function extract_python_messages {

    local pot=locale/${PROJECT_NAME}.pot

    # In case this is an initial run, the locale directory might not
    # exist, so create it since extract_messages will fail if it does
    # not exist. So, create it if needed.
    mkdir -p locale

    # Update the .pot files
    # The "_C" and "_P" prefix are for more-gettext-support blueprint,
    # "_C" for message with context, "_P" for plural form message.
    ${VENV_DIR}/bin/pybabel ${QUIET} extract \
        --add-comments Translators: \
        --msgid-bugs-address="https://bugs.launchpad.net/openstack-i18n/" \
        --project=${PROJECT_NAME} \
        -k "_C:1c,2" -k "_P:1,2" \
        -o ${pot} .
    check_empty_pot ${pot}
}

# Delete empty pot files
# 공식 문서 참고
# https://opendev.org/openstack/openstack-zuul-jobs/src/branch/master/roles/prepare-zanata-client/files/common_translation_update.sh#L352
function check_empty_pot {
    local pot=$1

    # We don't need to add or send around empty source files.
    trans=$(msgfmt --statistics -o /dev/null ${pot} 2>&1)
    if [ "$trans" = "0 translated messages." ] ; then
        rm $pot
        # Remove file from git if it's under version control. We previously
        # had all pot files under version control, so remove file also
        # from git if needed.
        if [ -d .git ]; then
            git rm --ignore-unmatch $pot
        fi
    fi
}

function main() {

    PROJECT_NAME="neutron-fwaas-dashboard"

    # setup 
    setup_venv
    setup_weblate_tools
    setup_directory

    # extract messages
    extract_messages_releasenotes
    extract_django_messages
    extract_python_messages

    # migrate to Weblate using CLI
    echo "Migrating to Weblate..."
    ${VENV_DIR}/bin/python3 -m openstack_weblate_tools.cli ${PROJECT_NAME}
}

main