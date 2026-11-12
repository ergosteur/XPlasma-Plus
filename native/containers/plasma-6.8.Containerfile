# SPDX-License-Identifier: GPL-3.0-or-later
# Build image for XPlasma's forks of Plasma's compiled widgets for the
# Plasma 6.8 series, whose libPlasma is .so.8 (see plasma-6.6.Containerfile
# for the why of it all).
#
# Originally built from Arch's rolling repos, but Arch had already moved
# qt6-base/qt6-declarative on to 6.12.0 by the time plasma-workspace reached
# 6.8.2 (confirmed: qt6-base-6.11.2-3 was superseded by 6.12.0-1 on the Arch
# mirror about a month before plasma-workspace-6.8.2 landed -- no single
# Arch snapshot date carries both). Fedora 44's own updates repo pairs
# plasma-workspace 6.8.2 with qt6-qtbase 6.11.2, matching this series'
# qtFloor of 6.11 exactly (and matching the host this gets installed on), so
# build against Fedora 44 directly instead, same as plasma-6.7.Containerfile.
#
#   podman build -t xplasma-plasma:6.8 -f containers/plasma-6.8.Containerfile containers
FROM registry.fedoraproject.org/fedora:44
RUN dnf -y --setopt=tsflags=noscripts install 'dnf5-command(builddep)' ccache ninja-build cmake gcc-c++ git xz python3 \
 && dnf -y --setopt=tsflags=noscripts builddep plasma-workspace plasma-desktop \
 && dnf clean all \
 && rpm -q qt6-qtbase-devel libplasma-devel
ENV CCACHE_DIR=/ccache
