sudo sh -c 'set -e
apt-get update
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3.12 python3.12-venv \
   python3.12-dev build-essential git curl wget pkg-config cmake \
   ninja-build autoconf automake libtool gdb valgrind unzip zip postgresql-client
'
loginctl enable-linger "$USER"
script_path=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)/$(basename -- "$0")
echo "script path: ${script_path}"

script_dir=$(dirname "${script_path}")
mkdir -p "${script_dir}/../artifacts"
artifacts_dir=$(readlink -f "${script_dir}/../artifacts")

# get python 3.13.11 for Windows
echo "artifacts: ${artifacts_dir}"
curl -fL -o python-3.13.11-amd64.exe https://www.python.org/ftp/python/3.13.11/python-3.13.11-amd64.exe
mv "python-3.13.11-amd64.exe" "${artifacts_dir}"

# get nssm for Windows
curl -fL -o nssm-2.24.zip https://nssm.cc/release/nssm-2.24.zip
mv "nssm-2.24.zip" "${artifacts_dir}"
