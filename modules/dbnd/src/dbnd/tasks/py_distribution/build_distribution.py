import logging
import os
import shutil
import subprocess
import sys
import zipfile

from tempfile import mkdtemp
from typing import Optional

from dbnd._core.current import is_verbose
from targets import DirTarget


logger = logging.getLogger(__name__)


def _get_package_name_and_version_from_whl(whl_dir):
    all_files = os.listdir(whl_dir)
    if not all_files:
        raise Exception("No Whl files where created")

    if len(all_files) > 1:
        raise Exception("Directory has more than one whl file")

    whl_file = all_files[0]
    split_name = whl_file.split("-")
    return split_name[0], split_name[1]


def _run_command(generate_command):
    if subprocess.call(generate_command, shell=True) != 0:
        raise Exception("Failed running {} command".format(generate_command))


def build_fat_requirements_py_zip_file(
    fat_py_output_dir, package_dir, requirements_file=None, tmp_build_dir=None
):
    # type: (DirTarget, str, Optional[str], Optional[str]) -> str
    # similar to fat jar in java, when you can have all thirdparty deps in one file

    logger.info("Started building fat bdist_zip file")

    clean_build_dir = False
    if not tmp_build_dir:
        tmp_build_dir = mkdtemp(prefix="dbnd-build-")
        clean_build_dir = True

    try:
        generate_project_whl(package_dir, tmp_build_dir)

        package_name, package_version = _get_package_name_and_version_from_whl(
            tmp_build_dir
        )

        fat_py_output_dir.mkdir()
        fat_py_deps_file = os.path.join(
            str(fat_py_output_dir),
            "{}-{}-package-with-deps.zip".format(package_name, package_version),
        )

        if requirements_file:
            generate_third_party_deps(requirements_file, tmp_build_dir)

        zip_dir(fat_py_deps_file, tmp_build_dir)
        logger.info("successfully build bdist_zip file at %s", fat_py_deps_file)
        return fat_py_deps_file
    finally:
        if clean_build_dir:
            if is_verbose():  # do not clean build dir in verbose mode
                logger.info("Keeping build dir because verbose mode is on")
            else:
                logger.info("Deleting tmp directory: %s", tmp_build_dir)
                shutil.rmtree(tmp_build_dir, ignore_errors=True)


def generate_project_whl(package_dir, output_dir):
    # generating deps wheels

    # Very important to change to the working dir, otherwise, wheel creation won't work as expected
    os.chdir(package_dir)

    setup_py_path = os.path.join(package_dir, "setup.py")
    if not os.path.exists(setup_py_path):
        raise Exception("Can't find setup.py inside package dir {}".format(package_dir))

    generate_command = "{} {} bdist_wheel --dist-dir {}".format(
        sys.executable, setup_py_path, output_dir
    )

    _run_command(generate_command)


def generate_third_party_deps(requirements_file, output_dir):
    # generating deps wheels
    generate_command = "{} -m pip wheel -r {} -w {}".format(
        sys.executable, requirements_file, output_dir
    )

    _run_command(generate_command)


def zip_dir(zip_file_path, source_dir_path):
    result_zip = zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED)

    for dir_name, _, files in os.walk(source_dir_path):
        if dir_name == source_dir_path:
            for file_name in files:
                full_file_name = os.path.join(dir_name, file_name)
                temp_zip = zipfile.ZipFile(file=full_file_name, mode="r")
                for file_info in temp_zip.filelist:
                    file_content = temp_zip.read(file_info.filename)
                    result_zip.writestr(file_info, file_content)
    result_zip.close()
