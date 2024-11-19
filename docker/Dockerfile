ARG base_image=ubuntu:24.04

FROM caddy:2 AS caddy

#
# Invocations common for builder and final stages
#
FROM ${base_image} AS base

ARG runtime_deps="libpq5 postgresql-client gettext \
    libproj25 ^libgdal3[2-9]$ libjpeg6[2345]-turbo$ libtiff6 libxml2 libffi8 libxslt1.1 \
    libwebp7 libvoikko1 voikko-fi curl \
    iputils-ping inetutils-telnet redis-tools restic procps git \
    ca-certificates media-types nano less"
ARG build_time_deps="libpq-dev build-essential \
    zlib1g-dev libjpeg-dev libtiff-dev libopenjp2-7-dev libwebp-dev \
    binutils libproj-dev libgdal-dev \
    libxml2-dev libxslt1-dev libffi-dev"

ARG app_path=/code
ARG app_user_uid=1000
ARG app_user_gid=1000
ARG docker_dir=./kausal_common/docker

# Ubuntu nowadays adds a `ubuntu` user with id 1000, which conflicts
# with our hard-coded uid. Remove the user if it exists.
RUN if id -u ubuntu > /dev/null 2>&1 ; then userdel -r ubuntu ; fi

ENV VIRTUAL_ENV=/venv
ENV UV_HOME=/opt/uv
ENV NVM_DIR=/opt/nvm
ENV PATH=/venv/bin:$PATH
ENV DEBIAN_FRONTEND=noninteractive TZ=UTC

RUN mkdir -p ${app_path}
# Set up APT package caching
RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# Upgrade .deb packages, and install runtime deps.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt update && apt upgrade -y && apt install --no-install-recommends -y \
    ${runtime_deps}

#
# Install node with nvm
#
RUN \
  mkdir -p $NVM_DIR && export METHOD=script ; export PROFILE=/dev/null ; \
  curl -LsSf https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
COPY .nvmrc ${app_path}/
RUN \
  cd ${app_path} && \
  . ${NVM_DIR}/nvm.sh ; \
  nvm install --default && nvm cache clear && chown -R root:root /opt/nvm/versions
RUN \
  for cmd in in /opt/nvm/versions/node/*/bin/* ; do \
    ln -s $cmd /usr/local/bin ; \
  done


#
# Builder stage
#
FROM base AS builder

ARG UV_VERSION=0.5.2

# Install build-time deps, and clean the cache from stale packages.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt update && apt install --no-install-recommends -y \
	${build_time_deps}

# Install uv
ENV \
  XDG_CACHE_HOME=/cache \
  UV_INSTALL_DIR=${UV_HOME} \
  UV_BIN=${UV_HOME}/uv \
  UV_PYTHON_INSTALL_DIR=${UV_HOME}

RUN \
  curl -LsSf https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-installer.sh | sh

WORKDIR ${app_path}

COPY --chown=${app_user_uid}:${app_user_gid} \
  .python-version pyproject.toml ${app_path}/

RUN --mount=type=cache,target=/cache \
  ${UV_BIN} python install
RUN --mount=type=cache,target=/cache \
  ${UV_BIN} venv --link-mode=copy --python-preference only-managed ${VIRTUAL_ENV}

RUN \
  echo ${UV_HOME}/*/lib | tee /etc/ld.so.conf.d/uv-python.conf && \
  ldconfig

COPY requirements.txt requirements-prod.txt ${app_path}/
ENV CC=gcc
# TODO: Should '--compile-bytecode' be included below?
ENV PIP_INSTALL="$UV_BIN pip install --link-mode=copy"
RUN --mount=type=cache,target=${XDG_CACHE_HOME} \
  LIBRARY_PATH=$(cat /etc/ld.so.conf.d/uv-python.conf) \
  ${PIP_INSTALL} -r ${app_path}/requirements-prod.txt -r ${app_path}/requirements.txt

# If uWSGI is installed, check that it actually starts, and if not, purge the uv cache
# and try again. uWSGI might be compiled with an old libc version.
RUN --mount=type=cache,target=${XDG_CACHE_HOME} \
  if which uwsgi 2>&1 > /dev/null ; then \
    if ! uwsgi --version > /dev/null ; then \
      ${UV_BIN} cache clean uwsgi && \
      LIBRARY_PATH=$(cat /etc/ld.so.conf.d/uv-python.conf) \
        ${PIP_INSTALL} --no-binary uwsgi --reinstall-package uwsgi uwsgi ; \
        uwsgi --version ; \
    fi \
  fi

# Install extra dependencies
COPY requirements-kausal.txt ${app_path}/
RUN --mount=type=secret,id=EXTRA_PYPI_INDEX \
    if [ -f /run/secrets/EXTRA_PYPI_INDEX ] ; then \
        UV_EXTRA_INDEX_URL=$(cat /run/secrets/EXTRA_PYPI_INDEX) \
        ${PIP_INSTALL} -r ${app_path}/requirements-kausal.txt ; \
    fi

# Install node
COPY package.json package-lock.json ${app_path}/
RUN npm ci

ARG INSTALL_DEV_DEPS
COPY requirements-dev.txt ${app_path}/
# We'll either install all dev dependencies or only IPython (for convenience)
RUN --mount=type=cache,target=${XDG_CACHE_HOME} \
  export LIBRARY_PATH=$(cat /etc/ld.so.conf.d/uv-python.conf) ; \
  if [ ! -z "${INSTALL_DEV_DEPS}" ] ; then \
    ${PIP_INSTALL} -r ${app_path}/requirements-dev.txt ; \
  else \
    ${PIP_INSTALL} $(cat ${app_path}/requirements-dev.txt | grep '^ipython=') ; \
  fi

#
# Final image
#
FROM base AS final

ENV VENV_PATH=/venv
ENV PATH=${VENV_PATH}/bin:${PATH}

COPY --from=builder /opt/uv /opt/uv
RUN \
  echo ${UV_HOME}/*/lib | tee /etc/ld.so.conf.d/uv-python.conf && \
  ldconfig
COPY --from=builder --chown=${app_user_uid}:${app_user_gid} /venv /venv
COPY --from=builder --chown=${app_user_uid}:${app_user_gid} ${app_path}/node_modules ${app_path}/node_modules

COPY --chown=${app_user_uid}:${app_user_gid} . ${app_path}/

RUN mkdir /scripts
COPY ${docker_dir}/*.sh /scripts/
COPY ${docker_dir}/uwsgi.ini /
RUN chmod a+x /scripts/*.sh

WORKDIR ${app_path}

ARG STATIC_ROOT=/srv/static
ENV STATIC_ROOT=${STATIC_ROOT}

ARG MEDIA_ROOT=/srv/media
ENV MEDIA_ROOT=${MEDIA_ROOT}

ARG DVC_CACHE_DIR=/cache/dvc
ENV DVC_CACHE_DIR=${DVC_CACHE_DIR}
ARG PINT_CACHE_DIR=/cache/pint
ENV PINT_CACHE_DIR=${PINT_CACHE_DIR}
ENV XDG_CACHE_HOME=/cache

RUN groupadd -g ${app_user_gid} user && useradd --no-log-init -m -d /home/user -g ${app_user_gid} -u ${app_user_uid} user
RUN chown ${app_user_uid}:${app_user_gid} ${app_path}

RUN \
  mkdir -p ${MEDIA_ROOT} ${STATIC_ROOT} /cache ${DVC_CACHE_DIR} ${PINT_CACHE_DIR} && \
  chown -R ${app_user_uid}:${app_user_gid} ${MEDIA_ROOT} ${STATIC_ROOT} /cache ${DVC_CACHE_DIR} ${PINT_CACHE_DIR}

# Compile bytecode for venv
RUN cd ${VIRTUAL_ENV} && python -m compileall -q

# Switch to the app user
USER user

# Pre-generate the .pyc bytecode files
RUN python -m compileall -q

RUN ./manage.py collectstatic --no-input
RUN ./manage.py compilemessages
# Run the system checks to import more code and pre-generate the .pyc files
RUN ./manage.py check

RUN if [ -d notifications ] ; then pybabel compile -D notifications -d locale ; fi

RUN \
  if which dvc 2>&1 > /dev/null ; then \
    dvc cache dir --global ${DVC_CACHE_DIR} ; \
  fi

COPY --from=caddy /usr/bin/caddy /usr/bin/caddy
COPY ${docker_dir}/Caddyfile /etc/caddy/

ENV PYTHONUNBUFFERED=1

# Disable this for now
# ENV PYTHONDONTWRITEBYTECODE=1
ARG DJANGO_PROJECT

RUN if [ -z "$DJANGO_PROJECT" ] ; then echo "DJANGO_PROJECT build arg is not set." ; exit 1 ; fi

ENV UWSGI_MODULE=${DJANGO_PROJECT}.wsgi DJANGO_SETTINGS_MODULE=${DJANGO_PROJECT}.settings CELERY_APPLICATION=${DJANGO_PROJECT}
ARG CADDY_PORT=6000
ENV CADDY_PORT=${CADDY_PORT}
ENV LC_CTYPE=C.UTF-8

ARG SENTRY_PROJECT
ARG SENTRY_RELEASE
ARG BUILD_ID
ARG GIT_REV
ENV \
  BUILD_ID=${BUILD_ID} \
  SENTRY_PROJECT=${SENTRY_PROJECT} \
  GIT_REV=${GIT_REV}

# Store the Sentry release information in .env conditionally, because BUILD_ID and SENTRY_PROJECT might be unset.
RUN \
  if [ ! -z "${SENTRY_RELEASE}" ] ; then \
    echo "SENTRY_RELEASE=${SENTRY_RELEASE}" >> ${app_path}/.env ; \
  else \
    if [ ! -z "$BUILD_ID" ] && [ ! -z "$SENTRY_PROJECT" ] ; then \
      echo "SENTRY_RELEASE=${SENTRY_PROJECT}@${BUILD_ID}" >> ${app_path}/.env ; \
    fi \
  fi

# We need to have the default user as root to be able to run tests etc.
USER root

EXPOSE 8000/tcp ${CADDY_PORT}/tcp
ENTRYPOINT ["/scripts/docker-entrypoint.sh"]
