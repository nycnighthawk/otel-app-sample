sudo sh -c 'set -e
apt-get update
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3.12 python3.12-venv \
   python3.12-dev build-essential git curl wget pkg-config cmake \
   ninja-build autoconf automake libtool gdb valgrind unzip zip
'

