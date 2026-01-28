sudo sh -c 'set -e
apt-get update
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3.12 python3.12-venv \
   python3.12-dev build-essential git curl wget pkg-config cmake \
   ninja-build autoconf automake libtool gdb valgrind unzip zip
'
script_path=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)/$(basename -- "$0")
echo "$script_path"

$script_dir=$(dirname "${script_path}")
mkdir ${script_dir}/../artifacts
$artifacts_dir=$(readlink -f "${script_dir}/../artifacts")
curl -fL -o python-3.13.11-amd64.exe https://www.python.org/ftp/python/3.13.11/python-3.13.11-amd64.exe
mv python-3.13.11-amd64.exe "${artifacts_dir}"

